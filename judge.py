"""
judge.py: the AI reviewer experiment.

For every translation attempt the verifier already graded, a separate AI model
(the reviewer) reads the SAS program and the PySpark code, with no data and no
answer key, and says SAME or DIFFERENT. Each case is asked several times,
because the same reviewer can give different answers to the same question.

Then it counts:
  missed       the verifier proved the code wrong, the reviewer said SAME
  false alarm  the verifier proved the code right, the reviewer said DIFFERENT
  wobbled      the reviewer gave different verdicts on repeats of the same case

Only attempts that ran and produced an output are used. Attempts that crashed,
were cut off, or were blocked are left out: any tool catches a crash.

Usage:
  export ANTHROPIC_API_KEY=$(security find-generic-password -s anthropic-api-key -w)
  python judge.py                          reviewer = Claude Sonnet, 3 asks per case
  python judge.py --model claude-haiku-5-5 --repeats 3
  python judge.py --dry-run                no API, tests the plumbing
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
LOG = HERE / "logs" / "attempts.jsonl"
OUT = HERE / "logs" / "judge.jsonl"

SYSTEM = """You review code migrations from SAS to PySpark.

You get a SAS program and a PySpark module meant to replace it. The module's
run(spark, loans, payments) function receives the same CSV files the SAS
program reads, as DataFrames with every column as a string (blanks as null),
and returns the table the SAS program writes with PROC EXPORT.

Decide whether the PySpark module produces exactly the same output as the SAS
program: same rows, same values, for any data with these columns. You cannot
run either program. Judge from the code.

Reply with only a JSON object:
{"verdict": "SAME" or "DIFFERENT", "reason": "one or two sentences"}"""


def load_cases():
    rows = [json.loads(line) for line in open(LOG)]
    latest = {}
    for r in rows:
        latest[r["program"]] = max(latest.get(r["program"], ""), r["run_id"])
    cases = []
    for r in rows:
        if not r["copy"].startswith("practice") or r["run_id"] != latest[r["program"]]:
            continue
        if not (r["report"].startswith("PASS") or r["report"].startswith("FAIL")):
            continue
        code_file = HERE / "translations" / "agent" / f"{r['program']}_attempt{r['attempt']}.py"
        sas_file = next((HERE / "sas").glob(f"{r['program']}_*.sas"))
        if code_file.exists():
            cases.append({**r, "code": code_file.read_text(), "sas": sas_file.read_text(),
                          "truth": "SAME" if r["pass"] else "DIFFERENT"})
    return cases


def parse_verdict(text):
    """Find the verdict even if the reviewer wrapped it in prose or a code block.

    Takes the LAST {"verdict": ...} object in the reply (reviewers often think
    out loud first). Falls back to the last bare SAME or DIFFERENT word.
    """
    for blob in reversed(re.findall(r"\{[^{}]*\"verdict\"[^{}]*\}", text, re.S)):
        try:
            answer = json.loads(blob)
            answer["verdict"] = str(answer.get("verdict", "")).strip().upper()
            if answer["verdict"] in ("SAME", "DIFFERENT"):
                return answer
        except json.JSONDecodeError:
            pass
    m = re.search(r'"verdict"\s*:\s*"(SAME|DIFFERENT)"', text, re.I)
    if m:
        return {"verdict": m.group(1).upper(), "reason": "(parsed from text)"}
    words = re.findall(r"\b(SAME|DIFFERENT)\b", text)
    if words:
        return {"verdict": words[-1], "reason": "(last verdict word in reply)"}
    return {"verdict": "UNREADABLE", "reason": text[:200]}


class Reviewer:
    def __init__(self, model_name, dry_run):
        self.model_name, self.dry_run = model_name, dry_run
        if not dry_run:
            import anthropic
            self.client = anthropic.Anthropic()

    def review(self, case):
        if self.dry_run:
            return {"verdict": "SAME", "reason": "dry run"}, 0, 0
        resp = self.client.messages.create(
            model=self.model_name, max_tokens=4000, system=SYSTEM,
            messages=[{"role": "user", "content":
                       f"SAS program:\n```sas\n{case['sas']}\n```\n\nPySpark module:\n```python\n{case['code']}\n```"}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        answer = parse_verdict(text)
        answer["stop_reason"] = resp.stop_reason
        if answer["verdict"] == "UNREADABLE":
            answer["raw"] = text
        return answer, resp.usage.input_tokens, resp.usage.output_tokens


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reviewer = Reviewer("dry-run" if args.dry_run else args.model, args.dry_run)
    cases = load_cases()
    verdicts = defaultdict(list)

    for case in cases:
        key = f"{case['program']} attempt {case['attempt']}"
        for i in range(args.repeats):
            answer, t_in, t_out = reviewer.review(case)
            verdicts[key].append(answer["verdict"])
            with open(OUT, "a") as f:
                f.write(json.dumps({
                    "run_id": run_id, "model": reviewer.model_name, "program": case["program"],
                    "attempt": case["attempt"], "repeat": i + 1, "truth": case["truth"],
                    "verdict": answer["verdict"], "reason": answer.get("reason", ""),
                    "stop_reason": answer.get("stop_reason"), "raw": answer.get("raw"),
                    "input_tokens": t_in, "output_tokens": t_out,
                }) + "\n")
        print(f"{key:16} verifier: {case['truth']:9}  reviewer: {', '.join(verdicts[key])}")

    wrong = [c for c in cases if c["truth"] == "DIFFERENT"]
    right = [c for c in cases if c["truth"] == "SAME"]
    key_of = lambda c: f"{c['program']} attempt {c['attempt']}"
    missed = sum(v == "SAME" for c in wrong for v in verdicts[key_of(c)])
    alarms = sum(v == "DIFFERENT" for c in right for v in verdicts[key_of(c)])
    wobbled = sum(len(set(verdicts[key_of(c)])) > 1 for c in cases)
    unreadable = sum(v == "UNREADABLE" for vs in verdicts.values() for v in vs)

    print()
    print(f"Reviewer: {reviewer.model_name}, asked {args.repeats} times per case")
    print(f"Wrong code (verifier FAIL): {len(wrong)} cases. Reviewer said SAME {missed} of {len(wrong) * args.repeats} times.")
    print(f"Right code (verifier PASS): {len(right)} cases. Reviewer said DIFFERENT {alarms} of {len(right) * args.repeats} times.")
    print(f"Cases where the reviewer changed its answer between asks: {wobbled} of {len(cases)}")
    print(f"Replies with no readable verdict: {unreadable}")
