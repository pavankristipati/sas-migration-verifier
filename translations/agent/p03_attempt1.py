from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def run(spark, loans, payments) -> DataFrame:
    # SAS: length loan_id $12 truncates values to 12 characters.
    p = (
        payments
        .select(
            F.substring(F.col("loan_id"), 1, 12).alias("loan_id"),
            F.to_date(F.col("month_end"), "yyyy-MM-dd").alias("month_end"),
            F.col("balance"),
            F.col("days_past_due").cast("double").alias("days_past_due"),
        )
    )

    # Ordering by loan_id then month_end, as in PROC SORT BY loan_id month_end.
    w_loan_ordered = (
        Window.partitionBy("loan_id")
        .orderBy(F.col("month_end").asc_nulls_first())
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )

    # A row is "delinquent" when days_past_due >= 30. A missing value is not
    # >= 30 in SAS, so it counts as not delinquent (null -> false here).
    flag = F.when(F.col("days_past_due") >= 30, 1).otherwise(0)
    not_flag = 1 - flag

    # Running group id that increments at each non-delinquent month.
    p = p.withColumn("grp", F.sum(not_flag).over(w_loan_ordered))

    # Current streak = running count of delinquent months within the group.
    w_streak = (
        Window.partitionBy("loan_id", "grp")
        .orderBy(F.col("month_end").asc_nulls_first())
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
    p = p.withColumn("streak", F.sum(flag).over(w_streak))

    # Longest run per loan.
    streaks = (
        p.groupBy("loan_id")
        .agg(F.max("streak").cast("int").alias("max_streak"))
    )

    result = (
        streaks
        .where(F.col("max_streak") >= 3)
        .select("loan_id", "max_streak")
    )
    return result
