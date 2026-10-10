"""
Reference translation of sas/p01_delinquency_by_product.sas, written by hand.

Its only job is to prove the plumbing works (Spark runs, the output file is
written, the verifier compares it) before any AI-written code goes through.
Each place SAS behaves differently from Spark is handled on purpose and noted.
"""
from pyspark.sql import functions as F


def run(spark, loans, payments):
    # SAS ignores trailing spaces in text, so "AUTO   " is the same as "AUTO".
    loans = loans.select("loan_id", F.rtrim("product").alias("product"))

    payments = payments.select(
        "loan_id",
        F.to_date("month_end").alias("month_end"),
        F.col("balance").cast("double").alias("balance"),
        F.col("days_past_due").cast("double").alias("days_past_due"),
    )

    last_month = payments.where(F.col("month_end") == F.lit("2026-09-30").cast("date")).join(
        loans, "loan_id"
    )

    flagged = last_month.select(
        "product",
        "balance",
        # SAS: a blank is smaller than any number, so blank >= 30 is false (0).
        F.when(F.col("days_past_due") >= 30, 1).otherwise(0).alias("delinquent"),
        # SAS: blank < 1000 is TRUE. Spark would treat it as unknown, so say so explicitly.
        F.when(F.col("balance").isNull() | (F.col("balance") < 1000), 1)
        .otherwise(0)
        .alias("low_balance"),
    )

    return (
        flagged.groupBy("product")
        .agg(
            F.count(F.lit(1)).alias("loans"),
            F.sum("delinquent").alias("delinquent_loans"),
            F.sum("low_balance").alias("low_balance_loans"),
            F.round(F.sum("balance"), 2).alias("total_balance"),
        )
        .orderBy("product")
    )
