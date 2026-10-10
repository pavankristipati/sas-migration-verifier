"""
A plausible first-try translation of p01, the kind a person or an AI writes
when reading the SAS code quickly. It looks right. Two SAS behaviors are missed:
trailing spaces in product names, and how SAS compares a blank balance.
Kept on purpose to show what the verifier catches.
"""
from pyspark.sql import functions as F


def run(spark, loans, payments):
    loans = loans.select("loan_id", "product")
    payments = payments.select(
        "loan_id",
        F.to_date("month_end").alias("month_end"),
        F.col("balance").cast("double").alias("balance"),
        F.col("days_past_due").cast("double").alias("days_past_due"),
    )
    last_month = payments.where(F.col("month_end") == "2026-09-30").join(loans, "loan_id")
    flagged = last_month.select(
        "product",
        "balance",
        F.when(F.col("days_past_due") >= 30, 1).otherwise(0).alias("delinquent"),
        F.when(F.col("balance") < 1000, 1).otherwise(0).alias("low_balance"),
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
