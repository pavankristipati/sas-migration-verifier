from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


def run(spark, loans, payments):
    # Exact decimal arithmetic avoids binary floating-point boundary errors
    # (e.g. x.xx5 values) when rounding to cents.
    amt_dec = F.trim(F.col("original_amount")).cast(DecimalType(30, 10))
    fee_rate = F.lit(0.0125).cast(DecimalType(5, 4))

    result = (
        loans
        .select(
            F.col("loan_id"),
            F.trim(F.col("original_amount")).cast("double").alias("original_amount"),
            F.round(amt_dec, 2).cast(DecimalType(30, 2)).alias("amount_cents"),
            F.round(amt_dec * fee_rate, 2).cast(DecimalType(30, 2)).alias("origination_fee"),
        )
        .orderBy(F.col("loan_id").asc())
    )

    return result.select("loan_id", "original_amount", "amount_cents", "origination_fee")
