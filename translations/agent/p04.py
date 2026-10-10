from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


def run(spark, loans, payments):
    # Mirror SAS fixed-length character variables (length $12 truncates).
    src = loans.select(
        F.substring(F.col("product"), 1, 12).alias("product"),
        F.substring(F.col("branch"), 1, 12).alias("branch"),
        # Exact decimal arithmetic avoids binary floating-point drift in sums,
        # so ties at the cent level round the same way SAS does.
        F.col("original_amount").cast(DecimalType(38, 10)).alias("original_amount"),
    )

    # SAS character comparison ignores trailing blanks.
    auto = src.where(F.rtrim(F.col("product")) == F.lit("AUTO"))

    # PROPCASE: lowercase everything, then capitalize first letter of each word.
    # Missing branch becomes a blank string in SAS, so coalesce to "".
    auto = auto.withColumn(
        "branch_name",
        F.substring(
            F.initcap(F.lower(F.coalesce(F.col("branch"), F.lit("")))), 1, 12
        ),
    )

    result = (
        auto.groupBy("branch_name")
        .agg(
            F.count(F.lit(1)).cast("long").alias("loans"),
            F.sum("original_amount").alias("_total"),
        )
        .select(
            "branch_name",
            "loans",
            # HALF_UP rounding on the exact decimal sum to 2 places.
            F.round(F.col("_total"), 2).cast(DecimalType(18, 2)).alias("total_original"),
        )
        .orderBy("branch_name")
    )

    return result
