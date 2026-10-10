from pyspark.sql import functions as F
from pyspark.sql import Window


def run(spark, loans, payments):
    # loans: loan_id $12, product $12 (SAS lengths), blanks compare as trailing-blank-insensitive
    loan_keys = loans.select(
        F.rtrim(F.substring(F.coalesce(F.col("loan_id"), F.lit("")), 1, 12)).alias("loan_id"),
        F.rtrim(F.substring(F.coalesce(F.col("product"), F.lit("")), 1, 12)).alias("product"),
    )

    # payments: loan_id $12, month_end yymmdd10 (ISO), balance numeric (invalid -> missing)
    p = payments.select(
        F.rtrim(F.substring(F.coalesce(F.col("loan_id"), F.lit("")), 1, 12)).alias("loan_id"),
        F.to_date(F.col("month_end"), "yyyy-MM-dd").alias("month_end"),
        F.col("balance").cast("double").alias("balance"),
    )

    # proc sort by loan_id month_end; data chg with lag reset at first.loan_id
    w = Window.partitionBy("loan_id").orderBy(F.col("month_end").asc_nulls_first())
    chg = (
        p.withColumn("prev_balance", F.lag("balance").over(w))
         .withColumn("change", F.col("balance") - F.col("prev_balance"))
    )

    # proc sql: inner join, group by product, count non-missing changes, mean rounded to 0.01
    joined = (
        chg.alias("c")
           .join(loan_keys.alias("l"), F.col("c.loan_id") == F.col("l.loan_id"), "inner")
    )

    result = (
        joined.groupBy(F.col("l.product").alias("product"))
              .agg(
                  F.count(F.col("c.change")).alias("months_with_change"),
                  F.round(F.avg(F.col("c.change")), 2).alias("avg_monthly_change"),
              )
              .orderBy("product")
              .select("product", "months_with_change", "avg_monthly_change")
    )

    return result
