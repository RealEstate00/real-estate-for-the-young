#!/usr/bin/env python
# No emojis in comments.
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYEXE = sys.executable

def ensure_exists(p: Path):
    if not p.exists():
        raise SystemExit(f"Missing script: {p}")

def crawl_rtms(housing, jw, gu, dong, start_year, end_year, quarters, download_excel, headed):
    rtms = HERE / "crawl_rtms_rent.py"
    ensure_exists(rtms)
    args = [PYEXE, str(rtms),
            "--housing", housing, "--jw", jw, "--gu", gu,
            "--start-year", str(start_year), "--end-year", str(end_year),
            "--quarters", quarters]
    if dong is not None:
        args += ["--dong", dong]
    if download_excel:
        args += ["--download-excel"]
    if headed:
        print("Tip: headed는 Playwright 브라우저 옵션으로 제어하세요.")
    subprocess.run(args, check=True)

def crawl_landprice():
    lp = HERE / "crawl_land_official_files.py"
    ensure_exists(lp)
    subprocess.run([PYEXE, str(lp)], check=True)

def main():
    ap = argparse.ArgumentParser(description="Crawl public data: RTMS rent & official land price files.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("rtms", help="RTMS rent by quarter.")
    s1.add_argument("--housing", choices=["apartment","single","multi","officetel","city"], default="apartment")
    s1.add_argument("--jw", choices=["jeonse","wolse","junwolse","junjeonse"], default="wolse")
    s1.add_argument("--gu", default="11740")
    s1.add_argument("--dong", default="")
    s1.add_argument("--start-year", type=int, default=2024)
    s1.add_argument("--end-year", type=int, default=2024)
    s1.add_argument("--quarters", default="1,2,3,4")
    s1.add_argument("--download-excel", action="store_true")
    s1.add_argument("--headed", action="store_true")

    s2 = sub.add_parser("landprice", help="Download official land price ZIP files.")

    args = ap.parse_args()
    if args.cmd == "rtms":
        crawl_rtms(args.housing, args.jw, args.gu, args.dong, args.start_year, args.end_year, args.quarters, args.download_excel, args.headed)
    elif args.cmd == "landprice":
        crawl_landprice()

if __name__ == "__main__":
    main()
