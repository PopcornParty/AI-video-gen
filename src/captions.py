"""Build Shorts-style caption groups from word timestamps."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .utils import save_text


EMPHASIS = {
    "never", "insane", "actually", "secret", "hidden", "biggest",
    "smallest", "fastest", "oldest", "first", "only", "million",
    "billion", "impossible", "real", "true", "nobody", "everyone", "stop",
}


def group_captions(words: list[dict[str, Any]], max_words: int = 5) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []
    for word in words:
        token = (word.get("text") or "").strip()
        if not token:
            continue
        bucket.append(word)
        punct = bool(re.search(r"[.!?,]$", token))
        if len(bucket) >= max_words or punct:
            groups.append(_pack(bucket))
            bucket = []
    if bucket:
        groups.append(_pack(bucket))
    return groups


def _pack(bucket: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [(w.get("text") or "").strip() for w in bucket]
    return {
        "text": " ".join(texts),
        "words": texts,
        "start": float(bucket[0]["start"]),
        "end": float(bucket[-1]["end"]),
        "emphasis": [i for i, t in enumerate(texts) if _is_emphasis(t)],
    }


def _is_emphasis(token: str) -> bool:
    clean = re.sub(r"[^A-Za-z0-9]", "", token).lower()
    if clean.isdigit() and len(clean) >= 2:
        return True
    return clean in EMPHASIS


def write_srt(groups: list[dict[str, Any]], path: Path) -> None:
    lines = []
    for i, g in enumerate(groups, start=1):
        lines.append(str(i))
        lines.append(f"{_ts(g['start'])} --> {_ts(g['end'])}")
        lines.append(g["text"])
        lines.append("")
    save_text(path, "\n".join(lines))


def _ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"
