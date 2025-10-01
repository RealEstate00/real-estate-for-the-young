from pathlib import Path
import hashlib, mimetypes

def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def file_hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def guess_mime(p: Path) -> str:
    return mimetypes.guess_type(str(p))[0] or "application/octet-stream"
