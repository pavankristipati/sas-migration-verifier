from pyspark.sql import functions as F
from pyspark.sql import Window


def run(spark, loans, payments):
    # Product is a $12 variable in SAS: values are truncated to 12 characters.
    # SAS compares character values ignoring trailing blanks, so CLASS groups
    # "AUTO" and "AUTO " together. Right-trim before grouping.
    # Blank or missing products are excluded from the CLASS grouping (nway).
    prod = (
        loans
        .withColumn("product", F.rtrim(F.substring(F.col("product"), 1, 12)))
        .where(F.col("product").isNotNull() & (F.col("product") != ""))
        .select("product", F.col("original_amount").cast("double").alias("amt"))
    )

    groups = prod.select("product").distinct()

    # Only nonmissing amounts contribute to N and the percentiles.
    vals = prod.where(F.col("amt").isNotNull())

    nstats = vals.groupBy("product").agg(F.count("amt").cast("long").alias("n"))

    w = Window.partitionBy("product").orderBy("amt")
    ranked = (
        vals.withColumn("rn", F.row_number().over(w))
        .join(nstats, "product")
        .select("product", "amt", "rn", "n")
    )

    # SAS default percentile definition (QNTLDEF=5):
    # pos = n*p + 0.5, linear interpolation between x[floor(pos)] and x[floor(pos)+1],
    # clipped to the first and last observation.
    def pct(p, name):
        q = (
            nstats
            .withColumn("pos", F.col("n") * F.lit(p) + F.lit(0.5))
            .withColumn("j", F.floor(F.col("pos")))
            .withColumn("g", F.col("pos") - F.col("j"))
            .withColumn(
                "jc",
                F.least(F.greatest(F.col("j"), F.lit(1)), F.col("n")).cast("long"),
            )
            .withColumn(
                "jh",
                F.least(F.greatest(F.col("j") + 1, F.lit(1)), F.col("n")).cast("long"),
            )
        )
        a1 = ranked.select(
            "product", F.col("rn").alias("jc"), F.col("amt").alias("x_lo")
        )
        a2 = ranked.select(
            "product", F.col("rn").alias("jh"), F.col("amt").alias("x_hi")
        )
        return (
            q.join(a1, ["product", "jc"], "left")
             .join(a2, ["product", "jh"], "left")
             .withColumn(name, F.col("x_lo") + F.col("g") * (F.col("x_hi") - F.col("x_lo")))
             .select("product", name)
        )

    med = pct(0.5, "median_amount")
    p90 = pct(0.9, "p90_amount")

    result = (
        groups
        .join(nstats, "product", "left")
        .join(med, "product", "left")
        .join(p90, "product", "left")
        .withColumn("n", F.coalesce(F.col("n"), F.lit(0)).cast("long"))
        .withColumn("median_amount", F.round(F.col("median_amount"), 2))
        .withColumn("p90_amount", F.round(F.col("p90_amount"), 2))
        .orderBy("product")
        .select("product", "n", "median_amount", "p90_amount")
    )

    return result
