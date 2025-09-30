# backend/libs/utils/paths.py
# Centralized path utilities for the repo.
# - No hard-coded relative paths elsewhere.
# - Prefer importing constants/functions from this module.
#
# Usage:
#   from backend.libs.utils.paths import (
#       PROJECT_ROOT, BACKEND_DIR, DATA_DIR, CONFIGS_DIR, LOGS_DIR,
#       RAW_DIR, INTERIM_DIR, PROCESSED_DIR, EXTERNAL_DIR,
#       ensure_dir, make_run_dir
#   )

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from datetime import datetime, timezone, timedelta
import os
import re


@lru_cache
def project_root() -> Path:
    """
    Resolve the repository root robustly.

    Resolution order:
      1) Explicit env override: PROJECT_ROOT
      2) Upward scan from this file for a directory that:
         - contains 'backend' folder, and
         - has a repo marker ('.git' or 'pyproject.toml')
      3) Fallback to current working directory.

    Returns
    -------
    Path
        Absolute path to the repository root (parent of 'backend/').
    """
    env = os.getenv("PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    here = Path(__file__).resolve()
    # Walk up and look for a parent that looks like the repo root.
    for p in (here,) + tuple(here.parents):
        # Check if this directory contains both 'backend' and 'libs' folders
        if ((p / "backend").is_dir() and (p / "libs").is_dir() and 
            ((p / ".git").exists() or (p / "pyproject.toml").exists())):
            return p

    # Last resort: CWD (not ideal; prefer setting PROJECT_ROOT)
    return Path.cwd().resolve()


# Canonical top-level directories
PROJECT_ROOT: Path = project_root()
BACKEND_DIR: Path = PROJECT_ROOT / "backend"
DATA_DIR: Path = BACKEND_DIR / "data"
CONFIGS_DIR: Path = BACKEND_DIR / "configs"
LOGS_DIR: Path = BACKEND_DIR / "logs"

# Standard data lifecycle folders
RAW_DIR: Path = DATA_DIR / "raw"
NORMALIZED_DIR: Path = DATA_DIR / "normalized"
HOUSING_DIR: Path = DATA_DIR / "raw" / "housing"
HOUSING_NORMALIZED_DIR: Path = DATA_DIR / "normalized" / "housing"
INFRA_NORMALIZED_DIR: Path = DATA_DIR / "normalized" / "infra"
RTMS_DIR: Path = DATA_DIR / "raw" / "rtms"

def ensure_dir(path: Path) -> Path:
    """Create the directory if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path

KST = timezone(timedelta(hours=9))
def today_ymd(tz: timezone | None = KST) -> str:
    """Return today's date as 'YYYY-MM-DD' (UTC by default)."""
    return datetime.now(tz or KST).strftime("%Y-%m-%d")


def sanitize_component(name: str) -> str:
    """Make a safe filesystem component (letters, numbers, '-', '_')."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())


def make_run_dir(source: str, run_id: str | None = None, date_ymd: str | None = None,
                 tz: timezone | None = KST) -> Path:
    """
    Create and return a canonical run directory under HOUSING_DIR.

    Folder layout:
        data/raw/housing/<source>/<YYYY-MM-DD>/

    Parameters
    ----------
    source : str
        Logical data source (e.g., 'sohouse', 'cohouse', 'lh', 'youth').
    run_id : str | None
        Optional unique identifier for the run. If omitted, uses timestamp.
    date_ymd : str | None
        Optional 'YYYY-MM-DD'. If omitted, uses today's date (UTC).

    Returns
    -------
    Path
        Absolute path to the created run directory.
    """
    src = sanitize_component(source)
    date_str = date_ymd or today_ymd(tz)
    # 날짜까지만 사용 (타임스탬프 제거)
    run_dir = HOUSING_DIR / src / date_str
    return ensure_dir(run_dir)

def make_normalized_dir(source: str, date_ymd: str | None = None,
                       tz: timezone | None = KST) -> Path:
    """
    Create and return a canonical normalized data directory.

    Folder layout:
        data/normalized/housing/<YYYY-MM-DD>/<source>/

    Parameters
    ----------
    source : str
        Logical data source (e.g., 'sohouse', 'cohouse', 'lh', 'youth').
    date_ymd : str | None
        Optional 'YYYY-MM-DD'. If omitted, uses today's date (UTC).

    Returns
    -------
    Path
        Absolute path to the created normalized directory.
    """
    src = sanitize_component(source)
    date_str = date_ymd or today_ymd(tz)
    normalized_dir = HOUSING_NORMALIZED_DIR / date_str / src
    return ensure_dir(normalized_dir)

__all__ = [
    "project_root",
    "PROJECT_ROOT",
    "BACKEND_DIR",
    "DATA_DIR",
    "CONFIGS_DIR",
    "LOGS_DIR",
    "RAW_DIR",
    "NORMALIZED_DIR",
    "HOUSING_DIR",
    "HOUSING_NORMALIZED_DIR",
    "INFRA_NORMALIZED_DIR",
    "RTMS_DIR",
    "ensure_dir",
    "today_ymd",
    "sanitize_component",
    "make_run_dir",
    "make_normalized_dir",
]
