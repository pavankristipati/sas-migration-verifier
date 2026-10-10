"""
translate.py: the translator agent loop.

For each SAS program, a small model (Claude Haiku by default) writes a PySpark
translation. The runner runs it on the PRACTICE data and the verifier compares
it with the SAS answer key. On FAIL, the model gets the verifier's short report
(or the error) and tries again, up to a fixed number of attempts.

When a translation passes practice, it is run ONCE on the HIDDEN data. That
result is recorded but never shown to the model.

What the model can and cannot do:
  can     read the SAS program, the expected column names, and the verifier's report
  cannot  see the data, the answer key values, or the hidden copy
  cannot  edit the verifier or the runner; it only returns code as text
  cannot  read or write files: code that tries is rejected before it runs

Every attempt is logged to logs/attempts.jsonl (program, attempt, verdict,
tokens, seconds, the report the model saw).

Usage:
  export ANTHROPIC_API_KEY=$(security find-generic-password -s anthropic-api-key -w)
  python translate.py sas/p01_delinquency_by_product.sas
  python translate.py sas/p*.sas
  python translate.py sas/p*.sas --max-attempts 5 --model claude-haiku-5-5
  python translate.py sas/p01_delinquency_by_product.sas --dry-run   (no API, tests the plumbing)
"""
import argparse
import csv
import json
import re
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from run_pyspark import run_one, spark_session

HERE = Path(__file__).parent
OUT_DIR = HERE / "translations" / "agent"
LOG = HERE / "logs" / "attempts.jsonl"
MAX_OUTPUT_TOKENS = 8000

SYSTEM = """You translate SAS programs into PySpark.

Write a Python module that defines exactly one function:

    def run(spark, loans, payments):
        ...
        return result   # a PySpark DataFrame

Inputs:
- loans and payments are PySpark DataFrames read from the same CSV files the SAS
  program reads. Every column arrives as a string, exactly as stored in the file.
  Blank fields arrive as null. Nothing has been trimmed or converted.
- Column names match the CSV headers.

Output:
- Return one DataFrame with exactly the columns listed by the user, in that order.
- Its contents must match what the SAS program writes in its PROC EXPORT step,
  value for value.

Rules:
- Do not read or write any files, start processes, or use the network.
  Use only pyspark, the sas_compat module below, and the Python standard library.
- Some Spark functions follow different rules than SAS. Where a SAS function has
  a match in sas_compat, use it. Do not use the Spark function in its place.
    SAS propcase(x)  ->  from sas_compat import propcase; propcase(col)
                         (do not use F.initcap: it only capitalizes after a blank)
- Reply with the complete module in one ```python code block and nothing else."""

BLOCKED = [
    r"\bopen\s*\(", r"\bimport\s+os\b", r"\bfrom\s+os\b", r"\bsubprocess\b", r"\bsocket\b",
    r"\b__import__\b", r"\beval\s*\(", r"\bexec\s*\(", r"spark\.read", r"\.write\b",
    r"answer_key", r"\bshutil\b", r"\bpathlib\b", r"requests\b", r"urllib",
]

# Spark functions that do not match SAS. Code that uses one is rejected before it
# runs, with a pointer to the sas_compat function that does match.
NOT_SAS = {
    r"\binitcap\b": "F.initcap does not match SAS PROPCASE. Use propcase from sas_compat.",
}


def expected_columns(name):
    with open(HERE / "answer_key" / "1k" / f"{name}_1k_practice.csv", newline="") as f:
        return next(csv.reader(f))


def extract_code(text):
    m = re.search(r"```python\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"


def blocked_reason(code):
    for pattern in BLOCKED:
        if re.search(pattern, code):
            return f"Code rejected before running: it matches the blocked pattern {pattern!r}. Do not touch files, processes, or the network."
    for pattern, fix in NOT_SAS.items():
        if re.search(pattern, code):
            return f"Code rejected before running: {fix}"
    return None


def log(record):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(record) + "\n")


class Model:
    def __init__(self, model_name, dry_run):
        self.model_name, self.dry_run = model_name, dry_run
        if not dry_run:
            import anthropic
            self.client = anthropic.Anthropic()

    def ask(self, messages, name):
        if self.dry_run:
            ref = HERE / "translations" / "reference" / f"{name}.py"
            text = f"```python\n{ref.read_text()}```" if ref.exists() else "```python\ndef run(spark, loans, payments):\n    return loans\n```"
            return text, 0, 0, False
        resp = self.client.messages.create(
            model=self.model_name, max_tokens=MAX_OUTPUT_TOKENS, system=SYSTEM, messages=messages
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        cut_off = resp.stop_reason == "max_tokens"
        return text, resp.usage.input_tokens, resp.usage.output_tokens, cut_off


def practice_copies(name):
    """Copies the model is checked against while it works: practice, plus the
    edge copy when SAS has made an answer key for it."""
    copies = ["practice"]
    if (HERE / "answer_key" / "1k" / f"{name}_1k_edge.csv").exists():
        copies.append("edge")
    return copies


def translate(spark, model, sas_path, max_attempts, run_id):
    name = sas_path.stem.split("_")[0]
    columns = expected_columns(name)
    messages = [{
        "role": "user",
        "content": f"Translate this SAS program.\n\nRequired output columns, in order: {columns}\n\n```sas\n{sas_path.read_text()}\n```",
    }]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    code_path = OUT_DIR / f"{name}.py"

    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        text, tok_in, tok_out, cut_off = model.ask(messages, name)
        code = extract_code(text)
        code_path.write_text(code)

        reason = blocked_reason(code)
        if cut_off:
            ok, report = False, (
                f"Your reply was cut off at the {MAX_OUTPUT_TOKENS}-token limit, so the code is incomplete. "
                "Reply again with the complete module, shorter: no explanations and few comments."
            )
        elif reason:
            ok, report = False, reason
        else:
            try:
                ok, report = True, "PASS"
                for copy in practice_copies(name):
                    ok, problems, _ = run_one(spark, str(code_path), "1k", copy)
                    if not ok:
                        report = f"FAIL on the {copy} copy of the data\n" + "\n".join(problems)
                        break
            except Exception:
                ok = False
                lines = traceback.format_exc().strip().splitlines()
                report = "Your code raised an error:\n" + "\n".join(lines[-15:])

        log({
            "run_id": run_id, "program": name, "attempt": attempt, "model": model.model_name,
            "copy": "+".join(practice_copies(name)), "pass": ok, "input_tokens": tok_in, "output_tokens": tok_out,
            "cut_off": cut_off,
            "seconds": round(time.time() - t0, 1), "report": report,
        })
        print(f"{name} attempt {attempt}: {'PASS' if ok else 'FAIL'}  ({tok_in} in / {tok_out} out tokens)")
        (OUT_DIR / f"{name}_attempt{attempt}.py").write_text(code)

        if ok:
            break
        messages += [
            {"role": "assistant", "content": text},
            {"role": "user", "content": f"The verifier compared your output with the SAS output.\n\n{report}\n\nFix the code and reply with the complete module."},
        ]
    else:
        print(f"{name}: gave up after {max_attempts} attempts")
        return

    # Final exam: hidden copy, run once, never shown to the model.
    try:
        hidden_ok, problems, _ = run_one(spark, str(code_path), "1k", "hidden")
        hidden_report = "PASS" if hidden_ok else "FAIL\n" + "\n".join(problems)
    except Exception:
        hidden_ok, hidden_report = False, traceback.format_exc().strip().splitlines()[-1]
    log({"run_id": run_id, "program": name, "attempt": attempt, "model": model.model_name,
         "copy": "hidden", "pass": hidden_ok, "report": hidden_report})
    print(f"{name} hidden copy: {'PASS' if hidden_ok else 'FAIL'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sas_files", nargs="+")
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--max-attempts", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    spark = spark_session()
    model = Model("dry-run" if args.dry_run else args.model, args.dry_run)
    for f in args.sas_files:
        translate(spark, model, Path(f), args.max_attempts, run_id)
    spark.stop()
