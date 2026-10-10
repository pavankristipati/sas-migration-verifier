from pyspark.sql import functions as F


def run(spark, loans, payments):
    # SAS reads origination_date with the yymmdd10. informat. Values that are
    # blank or not a valid yyyy-mm-dd date become missing (null).
    date_str = F.trim(F.col("origination_date"))
    valid_date = date_str.rlike(r"^\d{4}-\d{2}-\d{2}$")
    orig = F.when(valid_date, F.to_date(date_str, "yyyy-MM-dd"))

    # SAS intck('month', ...) with the default discrete method counts month
    # boundaries crossed, which is the difference in (year*12 + month).
    # The reference date is '30SEP2026'd.
    ref_index = 2026 * 12 + 9
    orig_index = F.year(orig) * 12 + F.month(orig)
    age_months = F.lit(ref_index) - orig_index

    # Blank product fields are missing in SAS, and missing groups together.
    product = F.trim(F.col("product"))
    product = F.when(product == "", F.lit(None).cast("string")).otherwise(product)

    # In SAS a missing age_months compares as smaller than any number, so
    # "age_months <= 12" is true and the row falls into '0-12'.
    age_bucket = (
        F.when(age_months.isNull() | (age_months <= 12), F.lit("0-12"))
        .when(age_months <= 24, F.lit("13-24"))
        .when(age_months <= 36, F.lit("25-36"))
        .otherwise(F.lit("37+"))
    )

    aged = loans.select(
        product.alias("product"),
        age_bucket.alias("age_bucket"),
    )

    result = (
        aged.groupBy("product", "age_bucket")
        .agg(F.count(F.lit(1)).alias("loans"))
        .orderBy(F.col("product").asc_nulls_first(), F.col("age_bucket").asc_nulls_first())
        .select("product", "age_bucket", "loans")
    )

    return result
