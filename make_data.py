"""
make_data.py: builds fake loan data for the SAS migration verifier lab.

Creates two copies of the same kind of data with different random rows:
  data/practice/  the copy the AI agent is allowed to see and test against
  data/hidden/    the copy kept away from the agent, used only for the final test

Each copy has two files:
  loans.csv     one row per loan (1,000 loans)
  payments.csv  one row per loan per month for 12 months (12,000 rows)

All data is invented. No real people, accounts, or bank data.

Planted on purpose (places where SAS and Python behave differently):
  1. Some balances and days-past-due values are blank (missing).
  2. Some product names have trailing spaces ("AUTO   ").
  3. Branch names come in mixed case ("Columbus", "COLUMBUS").
  4. Some loans share the same origination date, so sorting by date has ties.
  5. Some amounts end in exactly half a cent, so rounding rules matter.

Sizes (each size is its own folder, so tiers never mix):
  python make_data.py              1,000 loans per copy (12,000 payment rows): the agent loop
  python make_data.py --size 100k  100,000 loans (1.2M payment rows): final correctness check vs SAS
  python make_data.py --size 1m    1,000,000 loans (12M payment rows): speed test only, no SAS
"""

import csv
import random
from datetime import date
from pathlib import Path

PRODUCTS = ["AUTO", "MORTGAGE", "CARD", "HELOC"]
BRANCHES = ["Columbus", "Cleveland", "Detroit", "Pittsburgh", "Chicago"]
MONTH_ENDS = [
    date(2025, 10, 31), date(2025, 11, 30), date(2025, 12, 31),
    date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
    date(2026, 4, 30), date(2026, 5, 31), date(2026, 6, 30),
    date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30),
]
SIZES = {"1k": 1_000, "100k": 100_000, "1m": 1_000_000}


def make_copy(folder: Path, seed: int, n_loans: int) -> None:
    rng = random.Random(seed)
    folder.mkdir(parents=True, exist_ok=True)

    # A small pool of origination dates so many loans share a date (quirk 4).
    date_pool = [date(2021 + rng.randint(0, 3), rng.randint(1, 12), 1) for _ in range(40)]

    loans = []
    for i in range(1, n_loans + 1):
        product = rng.choice(PRODUCTS)
        if rng.random() < 0.05:                      # quirk 2: trailing spaces
            product = product + " " * rng.randint(1, 3)

        branch = rng.choice(BRANCHES)
        r = rng.random()
        if r < 0.08:                                 # quirk 3: mixed case
            branch = branch.upper()
        elif r < 0.12:
            branch = branch.lower()

        base = {"AUTO": 25000, "MORTGAGE": 280000, "CARD": 6000, "HELOC": 60000}
        amount = round(base[product.strip()] * rng.uniform(0.3, 1.6), 2)
        if rng.random() < 0.03:                      # quirk 5: half-cent amounts
            amount = int(amount) + 0.005

        loans.append({
            "loan_id": f"L{seed}{i:07d}",
            "customer_id": f"C{rng.randint(1, max(700, n_loans * 7 // 10)):07d}",   # some customers hold several loans
            "product": product,
            "branch": branch,
            "origination_date": rng.choice(date_pool).isoformat(),
            "original_amount": amount,
            "interest_rate": round(rng.uniform(2.5, 24.9), 3),
        })

    with open(folder / "loans.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(loans[0].keys()))
        w.writeheader()
        w.writerows(loans)

    payments = []
    for loan in loans:
        balance = float(loan["original_amount"])
        dpd = 0
        risky = rng.random() < 0.15                  # some loans go delinquent
        for month_end in MONTH_ENDS:
            balance = max(0.0, balance * rng.uniform(0.97, 0.995))
            if risky and rng.random() < 0.5:
                dpd = min(dpd + 30, 180)
            elif rng.random() < 0.7:
                dpd = 0

            bal_out = f"{balance:.2f}"
            dpd_out = str(dpd)
            if rng.random() < 0.02:                  # quirk 1: missing balance
                bal_out = ""
            if rng.random() < 0.02:                  # quirk 1: missing days past due
                dpd_out = ""

            payments.append({
                "loan_id": loan["loan_id"],
                "month_end": month_end.isoformat(),
                "balance": bal_out,
                "days_past_due": dpd_out,
            })

    with open(folder / "payments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(payments[0].keys()))
        w.writeheader()
        w.writerows(payments)

    print(f"{folder}: {len(loans)} loans, {len(payments)} payment rows")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=SIZES.keys(), default="1k")
    size = ap.parse_args().size
    n = SIZES[size]
    make_copy(Path(f"data/{size}/practice"), seed=1, n_loans=n)
    make_copy(Path(f"data/{size}/hidden"), seed=2, n_loans=n)
