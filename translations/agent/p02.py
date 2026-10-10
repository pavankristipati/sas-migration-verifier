from pyspark.sql import functions as F


def run(spark, loans, payments):
    # Normalise keys: SAS character comparison ignores trailing blanks.
    l = loans.select(
        F.trim(F.col("loan_id")).alias("l_loan_id"),
        F.trim(F.col("customer_id")).alias("customer_id"),
    )

    p = payments.select(
        F.trim(F.col("loan_id")).alias("loan_id"),
        F.to_date(F.trim(F.col("month_end")), "yyyy-MM-dd").alias("month_end"),
        F.col("balance").cast("double").alias("balance"),
    )

    # Inner join on loan_id, filter to the as-of date, one row per payment.
    sep = (
        p.join(l, p["loan_id"] == l["l_loan_id"], "inner")
        .where(F.col("month_end") == F.to_date(F.lit("2026-09-30"), "yyyy-MM-dd"))
        .select("customer_id", "loan_id", "balance")
    )

    # BY-group summary: count every row; sum ignores missing balances,
    # and a group with no non-missing balances totals 0.
    agg = (
        sep.groupBy("customer_id")
        .agg(
            F.count(F.lit(1)).cast("long").alias("loans"),
            F.coalesce(F.sum("balance"), F.lit(0.0)).alias("total_balance"),
        )
        .orderBy(F.col("customer_id").asc_nulls_first())
    )

    return agg.select("customer_id", "loans", "total_balance")
