KEYWORDS = ["다세대주택","연립주택","아파트","도시형생활주택","오피스텔"]

def map_building_form(raw_form: str, blob_text: str) -> str:
    raw_form = raw_form or ""
    blob_text = blob_text or ""
    for k in KEYWORDS:
        if k in raw_form or k in blob_text:
            return k
    return "기타"