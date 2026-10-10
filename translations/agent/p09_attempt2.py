from pyspark.sql import Window
from pyspark.sql import functions as F


def run(spark, loans, payments):
    # SAS ignores trailing blanks in character CLASS values, so trim product
    # before grouping. Drop blank/missing products (SAS excludes missing
    # CLASS levels) and non-numeric/missing original_amount (ignored as
    # missing analysis values).
    valid = (
        loans
        .withColumn("product", F.trim(F.col("product")))
        .where(F.col("product").isNotNull() & (F.col("product") != ""))
        .withColumn("amt", F.expr("try_cast(original_amount as double)"))
        .where(F.col("amt").isNotNull())
        .select("product", "amt")
    )

    ranked = valid.withColumn(
        "rk", F.row_number().over(Window.partitionBy("product").orderBy("amt"))
    )

    stats = valid.groupBy("product").agg(F.count("amt").alias("n"))

    def pctl(p, name):
        # SAS PROC MEANS default percentile definition (QNTLDEF=5):
        # pos = n*p + 0.5; interpolate between x_j and x_{j+1}, clipped to [1, n].
        s = (
            stats
            .withColumn("pos", F.col("n") * F.lit(p) + F.lit(0.5))
            .withColumn("j", F.floor(F.col("pos")).cast("long"))
            .withColumn("g", F.col("pos") - F.col("j").cast("double"))
            .withColumn("lo", F.least(F.greatest(F.col("j"), F.lit(1)), F.col("n")))
            .withColumn("hi", F.least(F.greatest(F.col("j") + 1, F.lit(1)), F.col("n")))
        )
        a = ranked.select("product", F.col("rk").alias("lo"), F.col("amt").alias("xlo"))
        b = ranked.select("product", F.col("rk").alias("hi"), F.col("amt").alias("xhi"))
        joined = s.join(a, ["product", "lo"]).join(b, ["product", "hi"])
        return joined.select(
            "product",
            F.round(
                (F.lit(1.0) - F.col("g")) * F.col("xlo") + F.col("g") * F.col("xhi"),
                2,
            ).alias(name),
        )

    med = pctl(0.5, "median_amount")
    p90 = pctl(0.9, "p90_amount")

    result = (
        stats
        .join(med, "product")
        .join(p90, "product")
        .select("product", "n", "median_amount", "p90_amount")
        .orderBy("product")
    )
    return result
