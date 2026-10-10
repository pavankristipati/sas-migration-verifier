from pyspark.sql import functions as F
from pyspark.sql import Window


def run(spark, loans, payments):
    # Preserve file order so ties on origination_date resolve to the loan listed first.
    l = loans.withColumn("_ord", F.monotonically_increasing_id())

    l = l.select(
        F.rtrim(F.substring(F.col("loan_id"), 1, 12)).alias("loan_id"),
        F.rtrim(F.substring(F.col("customer_id"), 1, 10)).alias("customer_id"),
        F.rtrim(F.substring(F.col("product"), 1, 12)).alias("product"),
        F.to_date(F.trim(F.col("origination_date")), "yyyy-MM-dd").alias("odate"),
        F.col("_ord"),
    )

    # SAS missing values sort first, so use nulls-first ordering on the date.
    w = Window.partitionBy("customer_id").orderBy(
        F.col("odate").asc_nulls_first(),
        F.col("_ord").asc(),
    )

    first = (
        l.withColumn("_rn", F.row_number().over(w))
         .filter(F.col("_rn") == 1)
    )

    result = (
        first.select(
            "customer_id",
            "loan_id",
            F.date_format(F.col("odate"), "yyyy-MM-dd").alias("origination_date"),
            "product",
            "odate",
            "_ord",
        )
        .orderBy(
            F.col("customer_id").asc_nulls_first(),
            F.col("odate").asc_nulls_first(),
            F.col("_ord").asc(),
        )
        .select("loan_id", "customer_id", "product", "origination_date")
    )

    return result
