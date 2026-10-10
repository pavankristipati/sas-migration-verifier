from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType
from sas_compat import propcase


def run(spark, loans, payments):
    # SAS character variables have fixed length: product and branch are $12,
    # so values are truncated to 12 characters on input.
    # Comparisons ignore trailing blanks, so product is right-trimmed before comparing.
    auto = (
        loans
        .withColumn("_prod", F.rtrim(F.substring(F.col("product"), 1, 12)))
        .filter(F.col("_prod") == F.lit("AUTO"))
        .withColumn("_br", F.substring(F.col("branch"), 1, 12))
        .withColumn(
            "branch_name",
            F.rtrim(F.substring(propcase(F.col("_br")), 1, 12))
        )
        # original_amount is numeric in SAS; non-numeric or blank values become missing (null)
        .withColumn("_amt", F.col("original_amount").cast("double"))
    )

    # SAS SUM ignores missing values; count(*) counts every row in the group.
    agg = (
        auto.groupBy("branch_name")
        .agg(
            F.count(F.lit(1)).alias("loans"),
            F.sum("_amt").alias("_total"),
        )
    )

    # round(sum, 0.01) then format 15.2 -> decimal with two places
    result = (
        agg
        .select(
            F.col("branch_name"),
            F.col("loans").cast("int").alias("loans"),
            F.round(F.col("_total"), 2)
             .cast(DecimalType(15, 2))
             .alias("total_original"),
        )
        .orderBy("branch_name")
        .select("branch_name", "loans", "total_original")
    )

    return result
