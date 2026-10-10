from pyspark.sql import functions as F


def run(spark, loans, payments):
    # Mirror SAS fixed-length character variables (length $12 truncates).
    src = loans.select(
        F.substring(F.col("product"), 1, 12).alias("product"),
        F.substring(F.col("branch"), 1, 12).alias("branch"),
        F.col("original_amount").cast("double").alias("original_amount"),
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
            F.round(F.sum("original_amount"), 2).alias("total_original"),
        )
        .select("branch_name", "loans", "total_original")
        .orderBy("branch_name")
    )

    return result
