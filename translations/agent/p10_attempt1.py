from pyspark.sql import functions as F


def run(spark, loans, payments):
    # SAS: product is $12, so values are truncated to 12 characters.
    # SAS: interest_rate is numeric; non-numeric or blank values become missing.
    base = loans.select(
        F.substring(F.col("product"), 1, 12).alias("product"),
        F.col("interest_rate").cast("double").alias("interest_rate"),
    )

    # PROC FORMAT ratetier:
    #   low -< 5 = 'Low'; 5 -< 12 = 'Mid'; 12 - high = 'High'; other = 'Unknown'
    # OTHER also captures missing numeric values.
    rate_tier = (
        F.when(F.col("interest_rate").isNull(), F.lit("Unknown"))
        .when(F.col("interest_rate") < 5, F.lit("Low"))
        .when(F.col("interest_rate") < 12, F.lit("Mid"))
        .otherwise(F.lit("High"))
    )

    tiered = base.withColumn("rate_tier", rate_tier)

    # PROC SQL: count(*) counts all rows; mean ignores missing values;
    # round(x, 0.001) implemented as round to 3 decimals (half away from zero).
    grouped = (
        tiered.groupBy("product", "rate_tier")
        .agg(
            F.count(F.lit(1)).alias("loans"),
            F.round(F.avg("interest_rate"), 3).alias("avg_rate"),
        )
    )

    result = (
        grouped.orderBy(
            F.col("product").asc_nulls_first(),
            F.col("rate_tier").asc_nulls_first(),
        )
        .select("product", "rate_tier", "loans", "avg_rate")
    )

    return result
