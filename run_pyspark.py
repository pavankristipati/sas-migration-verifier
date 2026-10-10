"""
run_pyspark.py: runs one PySpark translation on one copy of the data,
writes its output table, and checks it with the verifier.

Every translation is a Python file with one function:

    def run(spark, loans, payments):
        ...
        return result_dataframe

The harness, not the translation, reads the input files and writes the output.
It hands the translation two DataFrames with every column as text, exactly as
stored in the CSV (blanks become null, nothing is trimmed). Converting types is
part of the translation's job, the same way the SAS program's INPUT statement
does it. The translation never touches a file, so it cannot read an answer key.

Usage:
  python run_pyspark.py translations/reference/p01.py
  python run_pyspark.py translations/reference/p01.py --copy hidden
  python run_pyspark.py translations/reference/p01.py --size 100k
"""
import argparse
import importlib.util
import os
import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession

from verify import verify

HERE = Path(__file__).parent


def spark_session():
    spark = (
        SparkSession.builder.master("local[*]")
        .appName("sas-migration-verifier")
        .config("spark.driver.memory", "3g")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def load(spark, size, copy):
    folder = HERE / "data" / size / copy
    read = lambda name: spark.read.option("header", True).csv(str(folder / name))
    return read("loans.csv"), read("payments.csv")


def load_translation(path):
    spec = importlib.util.spec_from_file_location("translation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def run_one(spark, translation_path, size, copy):
    name = Path(translation_path).stem.split("_")[0]            # p01
    loans, payments = load(spark, size, copy)
    run = load_translation(translation_path)

    start = time.time()
    result = run(spark, loans, payments).toPandas()
    seconds = time.time() - start

    out_dir = HERE / "output" / size
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}_{size}_{copy}.csv"
    result.to_csv(out_path, index=False)

    key_path = HERE / "answer_key" / size / f"{name}_{size}_{copy}.csv"
    ok, problems = verify(str(key_path), str(out_path))
    return ok, problems, seconds


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("translation")
    ap.add_argument("--size", default="1k")
    ap.add_argument("--copy", default="practice", choices=["practice", "hidden"])
    args = ap.parse_args()

    spark = spark_session()
    ok, problems, seconds = run_one(spark, args.translation, args.size, args.copy)
    print(f"{'PASS' if ok else 'FAIL'}  {args.translation} on {args.size}/{args.copy}  ({seconds:.1f}s)")
    for p in problems:
        print("  " + p)
    spark.stop()
    sys.exit(0 if ok else 1)
