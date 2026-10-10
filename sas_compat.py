"""
sas_compat.py: PySpark functions that copy SAS behavior exactly.

Spark's built-in functions sometimes follow different rules than SAS. When a
translation calls Spark's version, the output drifts from SAS on unusual data.
Translations call these functions instead, so PySpark gives the SAS answer.

Each function here must be checked against real SAS output before it is trusted.

  propcase(col)   SAS PROPCASE: lowercases the text, then capitalizes the first
                  letter after the start, a blank, a slash, a hyphen, an open
                  parenthesis, a period or a tab. Spark's initcap only
                  capitalizes after a blank.
"""
from pyspark.sql import Column
from pyspark.sql import functions as F

# SAS PROPCASE default delimiters, other than the blank, which Spark's
# initcap already treats as a word break. Spark does not break on a tab.
_PROPCASE_DELIMITERS = ["/", "-", "(", ".", "\t"]
_MARK = "\u0001"  # a character that never appears in real data


def propcase(col) -> Column:
    """Same result as SAS propcase(text)."""
    c = F.lower(F.col(col) if isinstance(col, str) else col)
    # Put a marker and a blank after each delimiter so initcap sees a new word,
    # then remove the marker and blank again.
    for d in _PROPCASE_DELIMITERS:
        c = F.replace(c, F.lit(d), F.lit(d + _MARK + " "))
    c = F.initcap(c)
    return F.replace(c, F.lit(_MARK + " "), F.lit(""))
