import re
from typing import Tuple

def parse_krw_one(val: str) -> int:
    """Extract the first integer-like number from '350,000원' etc."""
    if not val:
        return 0
    m = re.findall(r"\d[\d,]*", str(val))
    return int(m[0].replace(",", "")) if m else 0

def parse_krw_range(s: str) -> Tuple[int, int]:
    """Return (min,max) from '350,000 ~ 450,000' or a single number."""
    if not s:
        return (0, 0)
    parts = re.split(r"[~\-–to]+", s)
    if len(parts) == 1:
        v = parse_krw_one(parts[0])
        return (v, v)
    lo, hi = parse_krw_one(parts[0]), parse_krw_one(parts[-1])
    if hi and lo and hi < lo:
        lo, hi = min(lo, hi), max(lo, hi)
    return (lo, hi)

def sanity_monthly(v: int) -> bool:
    """Reject unrealistic monthly rent like 44,000."""
    return v == 0 or v >= 100_000