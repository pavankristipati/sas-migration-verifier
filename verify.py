"""
verify.py: the verifier. Compares one output table against its SAS answer key.

It is a plain program with no AI in it. The translator agent may run it but may
never edit it.

Rules, in plain words:
  1. Same column names, in the same order.
  2. Same number of rows.
  3. Row order does not matter (both tables are sorted the same way first).
  4. Text must match exactly. "AUTO" and "AUTO " are different.
  5. Numbers must match to the precision SAS printed. If the answer key shows
     two decimals, the output may differ by less than half a cent. A one-cent
     difference fails.
  6. Blank must match blank. A 0 where SAS printed blank fails, and the reverse.

Usage:
  python verify.py answer_key/1k/p01_1k_practice.csv output/p01_1k_practice.csv

Prints PASS or FAIL with a short summary (at most 5 example rows), so an agent
reading the result never sees the whole table.
Exit code 0 means PASS, 1 means FAIL.
"""
import csv
import sys

BLANKS = {"", ".", "nan", "NaN", "null", "NULL", "None"}
MAX_EXAMPLES = 5


def read(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def column_kinds(header, rows):
    """For each column: ('num', decimals) if every non-blank value is a number, else ('text', None)."""
    kinds = []
    for i in range(len(header)):
        vals = [r[i].strip() for r in rows if r[i].strip() not in BLANKS]
        if vals and all(is_number(v) for v in vals):
            decimals = max((len(v.split(".")[1]) if "." in v else 0) for v in vals)
            kinds.append(("num", decimals))
        else:
            kinds.append(("text", None))
    return kinds


def sort_key(row, kinds):
    key = []
    for v, (kind, dec) in zip(row, kinds):
        if v.strip() in BLANKS:
            key.append((0, ""))
        elif kind == "num" and is_number(v):
            key.append((1, f"{round(float(v), dec):030.{dec}f}"))
        else:
            key.append((2, v))
    return key


def normalize(row, kinds):
    """Row as the verifier sees it: numbers rounded to the decimals SAS printed."""
    out = []
    for v, (kind, dec) in zip(row, kinds):
        if v.strip() in BLANKS:
            out.append("")
        elif kind == "num" and is_number(v):
            out.append(f"{round(float(v), dec):.{dec}f}")
        else:
            out.append(v)
    return tuple(out)


def same(a, b, kind, dec):
    a_blank, b_blank = a.strip() in BLANKS, b.strip() in BLANKS
    if a_blank or b_blank:
        return a_blank and b_blank
    if kind == "num":
        if not is_number(b):
            return False
        return abs(float(a) - float(b)) < 0.5 * 10 ** (-dec) + 1e-9
    return a == b


def verify(key_path, out_path):
    key_header, key_rows = read(key_path)
    try:
        out_header, out_rows = read(out_path)
    except FileNotFoundError:
        return False, [f"No output file at {out_path}"]

    problems = []
    if [h.lower() for h in out_header] != [h.lower() for h in key_header]:
        return False, [f"Columns differ. Expected {key_header}, got {out_header}"]

    kinds = column_kinds(key_header, key_rows)

    if len(out_rows) != len(key_rows):
        # Different row counts: show which rows are missing or extra.
        from collections import Counter
        k_count = Counter(normalize(r, kinds) for r in key_rows)
        o_count = Counter(normalize(r, kinds) for r in out_rows)
        missing = list((k_count - o_count).elements())
        extra = list((o_count - k_count).elements())
        problems.append(f"Row count differs. Expected {len(key_rows)}, got {len(out_rows)}")
        problems += [f"Missing row: {list(r)}" for r in missing[:MAX_EXAMPLES]]
        problems += [f"Unexpected row: {list(r)}" for r in extra[:MAX_EXAMPLES]]
        return False, problems
    k_sorted = sorted(key_rows, key=lambda r: sort_key(r, kinds))
    o_sorted = sorted(out_rows, key=lambda r: sort_key(r, kinds))

    bad = 0
    for k, o in zip(k_sorted, o_sorted):
        diffs = [
            f"{h}: expected {kv!r}, got {ov!r}"
            for h, kv, ov, (kind, dec) in zip(key_header, k, o, kinds)
            if not same(kv, ov, kind, dec)
        ]
        if diffs:
            bad += 1
            if bad <= MAX_EXAMPLES:
                problems.append(f"Row {k[0]!r}: " + "; ".join(diffs))
    if bad:
        problems.insert(0, f"{bad} of {len(key_rows)} rows differ")
    return not problems, problems


if __name__ == "__main__":
    ok, problems = verify(sys.argv[1], sys.argv[2])
    print("PASS" if ok else "FAIL")
    for p in problems:
        print("  " + p)
    sys.exit(0 if ok else 1)
