"""
test_verifier.py: tests the verifier before anyone trusts it.

For every answer key in answer_key/1k, it makes copies we already know are
right or wrong, and checks the verifier gives the expected verdict:

  should PASS   the answer key compared with itself
  should PASS   the same rows in a different order
  should FAIL   one number changed by one unit of the last decimal (a cent)
  should FAIL   one row removed
  should FAIL   one text value given a trailing space ("AUTO" -> "AUTO ")
  should FAIL   one number replaced by a blank

Run:  python test_verifier.py
"""
import csv
import glob
import os
import tempfile

from verify import BLANKS, column_kinds, is_number, read, verify


def write(rows, header):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def variants(header, rows):
    kinds = column_kinds(header, rows)
    num_cols = [i for i, (k, _) in enumerate(kinds) if k == "num"]
    txt_cols = [i for i, (k, _) in enumerate(kinds) if k == "text"]
    out = [("itself", True, rows), ("reordered", True, list(reversed(rows)))]

    if num_cols:
        i = num_cols[-1]
        dec = kinds[i][1]
        r = [list(x) for x in rows]
        target = next(j for j, x in enumerate(r) if x[i].strip() not in BLANKS)
        r[target][i] = f"{float(r[target][i]) + 10 ** (-dec):.{dec}f}"
        out.append(("one value off by one unit", False, r))

        r = [list(x) for x in rows]
        r[target][i] = ""
        out.append(("one value made blank", False, r))

    out.append(("one row removed", False, rows[1:]))

    if txt_cols:
        i = txt_cols[0]
        r = [list(x) for x in rows]
        r[0][i] = r[0][i] + " "
        out.append(("trailing space added", False, r))
    return out


failures = 0
keys = sorted(glob.glob("answer_key/1k/*.csv"))
for key in keys:
    header, rows = read(key)
    for name, should_pass, rows_v in variants(header, rows):
        path = write(rows_v, header)
        ok, _ = verify(key, path)
        os.remove(path)
        if ok != should_pass:
            failures += 1
            print(f"WRONG  {os.path.basename(key)}: '{name}' should {'PASS' if should_pass else 'FAIL'}")

print(f"Checked {len(keys)} answer keys. Verifier gave {failures} wrong verdicts.")
