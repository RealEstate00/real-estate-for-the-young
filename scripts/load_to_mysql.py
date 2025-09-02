#!/usr/bin/env python
# No emojis in comments.
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYEXE = sys.executable

def ensure_exists(p: Path):
    if not p.exists():
        raise SystemExit(f"Missing script: {p}")

def load_gold():
    s = HERE / "load_gold_to_mysql.py"
    ensure_exists(s)
    subprocess.run([PYEXE, str(s)], check=True)

def load_rtms():
    s = HERE / "load_rtms_to_mysql.py"
    ensure_exists(s)
    subprocess.run([PYEXE, str(s)], check=True)

def main():
    ap = argparse.ArgumentParser(description="Load curated data into MySQL.")
    ap.add_argument("--what", choices=["gold","rtms","all"], default="all")
    args = ap.parse_args()
    if args.what in ("gold","all"):
        load_gold()
    if args.what in ("rtms","all"):
        load_rtms()

if __name__ == "__main__":
    main()
