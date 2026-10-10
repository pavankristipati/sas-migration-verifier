from pyspark.sql import functions as F


def run(spark, loans, payments):
    # Loan attributes needed: product (keyed by loan_id).
    l = loans.select(
        F.trim(F.col("loan_id")).alias("loan_id"),
        F.trim(F.col("product")).alias("product"),
    )

    # Payment fields, converted from strings. month_end is yymmdd10 (yyyy-mm-dd,
    # with yyyy/mm/dd also accepted by the SAS informat). Unparseable -> null.
    p = payments.select(
        F.trim(F.col("loan_id")).alias("loan_id"),
        F.coalesce(
            F.to_date(F.trim(F.col("month_end")), "yyyy-MM-dd"),
            F.to_date(F.trim(F.col("month_end")), "yyyy/MM/dd"),
        ).alias("month_end"),
        F.trim(F.col("balance")).cast("double").alias("balance"),
        F.trim(F.col("days_past_due")).cast("double").alias("days_past_due"),
    )

    # Last month-end snapshot, inner-joined to loans.
    last_month = (
        p.filter(F.col("month_end") == F.lit("2026-09-30").cast("date"))
         .join(l, on="loan_id", how="inner")
         .select("loan_id", "product", "balance", "days_past_due")
    )

    # SAS missing-value semantics:
    #  - delinquent: (missing >= 30) is false -> 0
    #  - low_balance: (missing < 1000) is true -> 1
    flagged = last_month.select(
        F.col("product"),
        F.col("balance"),
        F.when(F.col("days_past_due") >= 30, F.lit(1)).otherwise(F.lit(0)).alias("delinquent"),
        F.when(
            F.col("balance").isNull() | (F.col("balance") < 1000), F.lit(1)
        ).otherwise(F.lit(0)).alias("low_balance"),
    )

    result = (
        flagged.groupBy("product")
        .agg(
            F.count(F.lit(1)).alias("loans"),
            F.sum("delinquent").alias("delinquent_loans"),
            F.sum("low_balance").alias("low_balance_loans"),
            F.round(F.sum("balance"), 2).alias("total_balance"),
        )
        .orderBy(F.col("product").asc_nulls_first())
        .select("product", "loans", "delinquent_loans", "low_balance_loans", "total_balance")
    )

    return result
