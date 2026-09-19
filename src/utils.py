"""Shared helpers: paths, slugs, HTTP, caching, logging."""
from __future__ import annotations
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "AIShortsGenerator/1.0 (educational local tool; +https://github.com/PopcornParty/AI-video-gen)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

def project_root() -> Path:
    return ROOT

def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text or "short")[:max_len]

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def cache_path(cache_dir: Path, namespace: str, key: str, ext: str) -> Path:
    ensure_dir(cache_dir / namespace)
    return cache_dir / namespace / f"{sha1(key)[:20]}.{ext.lstrip('.')}"

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")

def step(n: int, total: int, message: str) -> None:
    print(f"[{n}/{total}] {message}", flush=True)

def warn(message: str) -> None:
    print(f"  ! {message}", flush=True)

def info(message: str) -> None:
    print(f"  · {message}", flush=True)

def http_get(url: str, *, headers: Optional[dict] = None, params: Optional[dict] = None, timeout: int = 25, retries: int = 2):
    last_err = None
    merged = dict(SESSION.headers)
    if headers:
        merged.update(headers)
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, headers=merged, params=params, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                last_err = f"429 rate limited: {url}"
                continue
            if resp.status_code >= 400:
                last_err = f"HTTP {resp.status_code}: {url}"
                if resp.status_code in (401, 403):
                    break
                time.sleep(0.6 * (attempt + 1))
                continue
            return resp
        except requests.RequestException as exc:
            last_err = str(exc)
            time.sleep(0.6 * (attempt + 1))
    if last_err:
        warn(last_err)
    return None

def download_file(url: str, dest: Path, *, headers: Optional[dict] = None, timeout: int = 60, max_bytes: int = 45_000_000) -> bool:
    if dest.exists() and dest.stat().st_size > 2048:
        return True
    ensure_dir(dest.parent)
    resp = http_get(url, headers=headers, timeout=timeout, retries=2)
    if resp is None:
        return False
    content_type = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" in content_type and len(resp.content) < 5000:
        warn(f"Download looked like HTML, skipped: {url}")
        return False
    if len(resp.content) < 1500:
        warn(f"Download too small ({len(resp.content)} bytes): {url}")
        return False
    if len(resp.content) > max_bytes:
        warn(f"Download too large ({len(resp.content)} bytes), skipped")
        return False
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(resp.content)
    tmp.replace(dest)
    return dest.exists()

def extension_from_url(url: str, default: str = ".jpg") -> str:
    path = urlparse(url).path.lower()
    for ext in (".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(ext):
            return ext
    return default

def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
