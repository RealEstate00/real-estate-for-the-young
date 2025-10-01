import re, math

DATE_RE = re.compile(r"(20\d{2})[.\-년/ ]\s*(\d{1,2})[.\-월/ ]\s*(\d{1,2})")
MONEY_RE = re.compile(r"(\d[\d,]*)\s*(만원|원)")
AREA_RE  = re.compile(r"(\d+(?:\.\d+)?)\s*(㎡|m2|제곱미터|평)")

def norm_date(txt: str) -> str | None:
    m = DATE_RE.search(txt or "")
    if not m: return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"

def norm_money(txt: str) -> int | None:
    m = MONEY_RE.search(txt or "")
    if not m: return None
    n = int(m.group(1).replace(",", ""))
    unit = m.group(2)
    return n*10000 if unit=="만원" else n

def norm_area_m2(txt: str) -> float | None:
    m = AREA_RE.search(txt or "")
    if not m: return None
    v = float(m.group(1)); unit = m.group(2)
    return v*3.3058 if unit=="평" else v
