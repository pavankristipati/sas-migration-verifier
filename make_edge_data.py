"""
make_edge_data.py: builds an "edge" copy of the 1k practice data with branch
names that contain hyphens and periods, which the original data never had.

Why: the AI reviewer said SAS PROPCASE and Spark initcap disagree on names like
WINSTON-SALEM. Our verifier could not see that, because no branch name in the
test data had a hyphen. This copy adds such names so the verifier can test the
claim directly.

Same loans and payments as data/1k/practice. Only the branch column changes,
for every 10th loan, cycling through the names below in mixed case.

Run:  python make_edge_data.py      -> writes data/1k/edge/loans.csv and payments.csv
"""
import csv
import shutil
from pathlib import Path

SRC = Path("data/1k/practice")
DST = Path("data/1k/edge")
EDGE_BRANCHES = ["WINSTON-SALEM", "st.louis", "Wilkes-Barre", "ST. PAUL", "fort wayne/north"]

DST.mkdir(parents=True, exist_ok=True)
shutil.copy(SRC / "payments.csv", DST / "payments.csv")

with open(SRC / "loans.csv", newline="") as f:
    rows = list(csv.DictReader(f))
for i, row in enumerate(rows):
    if i % 10 == 0:
        row["branch"] = EDGE_BRANCHES[(i // 10) % len(EDGE_BRANCHES)]
with open(DST / "loans.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

changed = sum(1 for i in range(len(rows)) if i % 10 == 0)
print(f"{DST}: {len(rows)} loans, {changed} given edge-case branch names")
