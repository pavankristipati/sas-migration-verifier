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

    # Percentile rule that matches the SAS output:
    # pos = n*p. If pos is not an integer, the value is x[ceil(pos)].
    # If pos is an integer, the value is the average of x[pos] and x[pos+1].
    # Indices are clipped to the range [1, n].
    def pct(p, name):
        q = (
            nstats
            .withColumn("pos", F.col("n") * F.lit(p))
            .withColumn(
                "ja",
                F.least(F.greatest(F.ceil(F.col("pos")), F.lit(1)), F.col("n")).cast("long"),
            )
            .withColumn(
                "jb",
                F.least(
                    F.greatest(F.floor(F.col("pos")).cast("long") + 1, F.lit(1)),
                    F.col("n"),
                ).cast("long"),
            )
        )
        a1 = ranked.select(
            "product", F.col("rn").alias("ja"), F.col("amt").alias("x_a")
        )
        a2 = ranked.select(
            "product", F.col("rn").alias("jb"), F.col("amt").alias("x_b")
        )
        return (
            q.join(a1, ["product", "ja"], "left")
             .join(a2, ["product", "jb"], "left")
             .withColumn(name, (F.col("x_a") + F.col("x_b")) / F.lit(2.0))
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
