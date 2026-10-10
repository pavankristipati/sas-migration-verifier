from pyspark.sql import functions as F


def run(spark, loans, payments):
    q = 0.01

    def sas_round_cents(x):
        # SAS ROUND(x, 0.01) = 0.01 * NINT(x / 0.01), with NINT rounding half away from zero
        t = x / F.lit(q)
        r = F.signum(t) * F.floor(F.abs(t) + F.lit(0.5))
        return r * F.lit(q)

    original_amount = F.trim(F.col("original_amount")).cast("double")

    result = (
        loans
        .select(
            F.col("loan_id"),
            original_amount.alias("original_amount"),
            sas_round_cents(original_amount).alias("amount_cents"),
            sas_round_cents(original_amount * F.lit(0.0125)).alias("origination_fee"),
        )
        .orderBy(F.col("loan_id").asc())
    )

    return result.select("loan_id", "original_amount", "amount_cents", "origination_fee")
