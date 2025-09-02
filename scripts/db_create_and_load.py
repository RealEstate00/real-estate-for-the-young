#!/usr/bin/env python
# No emojis in comments.
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYEXE = sys.executable

def ensure_exists(p: Path):
    if not p.exists():
        raise SystemExit(f"Missing script: {p}")

def run_db_setup():
    s = HERE / "db_setup.py"
    if s.exists():
        subprocess.run([PYEXE, str(s)], check=True)
    else:
        print("db_setup.py not found; skipping schema bootstrap.")

def run_update_sql():
    upd = Path("db/update_rtms_landprice.sql")
    if upd.exists():
        # MySQL CLI 필요. 환경에 맞게 수정 가능.
        print("Applying db/update_rtms_landprice.sql via mysql client...")
        subprocess.run(["mysql", "-u", "root", "-p", "<", str(upd)], shell=True, check=False)
        print("If shell redirection fails on your OS, run manually: mysql -u root -p < db/update_rtms_landprice.sql")
    else:
        print("db/update_rtms_landprice.sql not found; skipping.")

def run_load(what: str):
    s = HERE / "load_to_mysql.py"
    ensure_exists(s)
    subprocess.run([PYEXE, str(s), "--what", what], check=True)

def main():
    ap = argparse.ArgumentParser(description="Create schema and load curated data.")
    ap.add_argument("--what", choices=["gold","rtms","all"], default="all")
    args = ap.parse_args()
    run_db_setup()
    run_update_sql()
    run_load(args.what)

if __name__ == "__main__":
    main()
