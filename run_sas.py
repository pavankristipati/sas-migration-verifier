"""
run_sas.py: sends a SAS program from your Mac to SAS OnDemand, runs it,
and downloads the output CSV into answer_key/.

Usage:
  python run_sas.py --test                                   check the connection only
  python run_sas.py sas/p01_delinquency_by_product.sas       run one program on 1k practice and hidden
  python run_sas.py sas/p*.sas                               run every program, one connection

Before running, load your login from Keychain into this Terminal window:
  export ODA_USER=$(security find-generic-password -s oda-user -w)
  export ODA_PW=$(security find-generic-password -s oda-password -w)
"""
import argparse
import re
import sys
from pathlib import Path

import saspy

HERE = Path(__file__).parent


def connect():
    return saspy.SASsession(cfgfile=str(HERE / "sascfg_personal.py"), cfgname="oda")


def run_program(sas, sas_file: Path, size: str, copy: str) -> None:
    code = sas_file.read_text()
    # Point the program at the right size and copy without editing the file.
    code = re.sub(r"%let size\s*=\s*\w+;", f"%let size = {size};", code)
    code = re.sub(r"%let copy\s*=\s*\w+;", f"%let copy = {copy};", code)

    result = sas.submit(code)
    log = result["LOG"]
    # A real SAS error line starts with "ERROR". Checking for the word anywhere
    # is wrong: PROC EXPORT's generated code contains _ERROR_ and _EFIERR_.
    if re.search(r"^ERROR", log, re.MULTILINE):
        print(log)
        sys.exit(f"SAS reported an error running {sas_file.name} on {size}/{copy}")

    name = sas_file.stem.split("_")[0]                    # p01
    remote = f"/home/{sas.symget('sysuserid')}/lab/out/{name}_{size}_{copy}.csv"
    local_dir = HERE / "answer_key" / size
    local_dir.mkdir(parents=True, exist_ok=True)
    got = sas.download(str(local_dir), remote)
    if not got["Success"]:
        sys.exit(f"Download failed: {got['LOG']}")
    print(f"{sas_file.name} {size}/{copy}: saved answer_key/{size}/{name}_{size}_{copy}.csv")


def upload_copy(sas, size, copy):
    """Create the folder on SAS OnDemand if needed and upload the two CSV files."""
    remote = f"/home/{sas.symget('sysuserid')}/lab/data/{size}/{copy}"
    sas.submit(f'options dlcreatedir; libname _up "{remote}"; libname _up clear;')
    for name in ["loans.csv", "payments.csv"]:
        got = sas.upload(str(HERE / "data" / size / copy / name), f"{remote}/{name}")
        if not got["Success"]:
            sys.exit(f"Upload failed for {copy}/{name}: {got['LOG']}")
    print(f"Uploaded data/{size}/{copy} to {remote}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sas_files", nargs="*")
    ap.add_argument("--size", default="1k")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--copies", nargs="+", default=["practice", "hidden"])
    ap.add_argument("--upload", action="store_true",
                    help="upload data/<size>/<copy>/*.csv to SAS OnDemand first")
    args = ap.parse_args()

    sas = connect()
    if args.test:
        print("Connected as", sas.symget("sysuserid"))
        sas.endsas()
        sys.exit(0)

    if args.upload:
        for copy in args.copies:
            upload_copy(sas, args.size, copy)

    for f in args.sas_files:
        for copy in args.copies:
            run_program(sas, Path(f), args.size, copy)
    sas.endsas()
