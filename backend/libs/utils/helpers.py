#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility helper functions
"""

import csv
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from .constants import KST


def sha256(s: str) -> str:
    """Generate SHA256 hash of string"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str):
    """Write text to file with UTF-8 encoding"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes):
    """Write bytes to file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def append_csv(path: Path, header: list, rows: list[dict]):
    """Append rows to CSV file"""
    init = not path.exists()
    
    with path.open("a", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        if init:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def clean_today(kind: str):
    """Clean today's directory for given kind"""
    # backend 루트 기준으로 data/raw 경로 설정 (오늘 날짜의 특정 플랫폼 데이터만 삭제)
    script_dir = Path(__file__).parent.parent.parent.parent
    base = script_dir / "data/raw" / datetime.now(KST).strftime("%Y-%m-%d") / kind
    if base.exists():
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def clean_all_platform_data(kind: str):
    """Clean all existing data for given platform kind"""
    # backend 루트 기준으로 data/raw 경로 설정 (특정 플랫폼의 모든 날짜 데이터 삭제)
    script_dir = Path(__file__).parent.parent.parent.parent
    data_dir = script_dir / "data/raw"

    if not data_dir.exists():
        return

    deleted_count = 0
    for date_dir in data_dir.glob("*/"):
        if date_dir.is_dir():
            platform_dir = date_dir / kind
            if platform_dir.exists():
                import shutil
                shutil.rmtree(platform_dir, ignore_errors=True)
                deleted_count += 1
                print(f"[CLEAN] {kind} 데이터 삭제: {platform_dir}")

    if deleted_count > 0:
        print(f"[CLEAN] 총 {deleted_count}개 날짜의 {kind} 데이터 삭제 완료")
    else:
        print(f"[CLEAN] 삭제할 {kind} 데이터가 없습니다")
def run_dir(kind: str) -> Path:
    """Create and return directory for given kind"""
    # backend 루트 기준으로 data/raw 경로 설정 (크롤링 데이터 저장용 디렉토리 생성)
    # helpers.py -> utils -> libs -> backend
    script_dir = Path(__file__).parent.parent.parent.parent
    base = script_dir / "data/raw" / datetime.now(KST).strftime("%Y-%m-%d") / kind
    base.mkdir(parents=True, exist_ok=True)  # base 디렉토리 생성
    (base / "html").mkdir(parents=True, exist_ok=True)
    (base / "images").mkdir(parents=True, exist_ok=True)
    (base / "tables").mkdir(parents=True, exist_ok=True)
    return base


def ensure_dirs(base: Path):
    """Ensure all necessary subdirectories exist"""
    base.mkdir(parents=True, exist_ok=True)
    (base / "html").mkdir(parents=True, exist_ok=True)
    (base / "images").mkdir(parents=True, exist_ok=True)
    (base / "tables").mkdir(parents=True, exist_ok=True)
    (base / "texts").mkdir(parents=True, exist_ok=True)
    (base / "kv").mkdir(parents=True, exist_ok=True)
    (base / "attachments").mkdir(parents=True, exist_ok=True)


def platform_fixed_id(platform_code: str) -> int | None:
    """Get platform ID for given platform code"""
    from .constants import PLATFORM_ID_MAP
    return PLATFORM_ID_MAP.get(platform_code)


def sanity_check_address(rec):
    """Check if address looks suspicious (contains eligibility info)"""
    addr = (rec.get("address") or "").strip()
    if addr and ("입주대상" in addr or "대상" in addr):
        print(f"[WARN] address suspicious (eligibility?): record_id={rec['record_id']} addr={addr[:40]}")
