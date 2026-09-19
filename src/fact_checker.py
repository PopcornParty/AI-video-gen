"""Keep scripts anchored to researched sources."""
from __future__ import annotations
import re
from typing import Any
from .utils import unique_keep_order

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_STOP = {"this","that","with","from","have","been","were","they","them","their","about","which","when","what","your","more","most","into","over","also","than","then","just","like","some","could","would","there","these","those"}

def filter_script_to_sources(sentences, facts, allow_cta=True):
    source_blob = " ".join(facts).lower()
    source_numbers = set(_NUMBER.findall(source_blob.replace(",", "")))
    kept = []
    for sentence in sentences:
        low = sentence.lower()
        if allow_cta and any(p in low for p in ("follow", "subscribe", "watch more", "another short")):
            kept.append(sentence)
            continue
        nums = [n.replace(",", "") for n in _NUMBER.findall(sentence)]
        invented = [n for n in nums if n not in source_numbers and n not in {"1", "2", "3"}]
        if invented and not _sentence_supported(low, facts):
            continue
        kept.append(sentence)
    return unique_keep_order(kept)

def _sentence_supported(low, facts):
    tokens = [t for t in re.findall(r"[a-z0-9]{4,}", low) if t not in _STOP]
    if not tokens:
        return True
    for fact in facts:
        f = fact.lower()
        hits = sum(1 for t in tokens if t in f)
        if hits >= max(2, len(tokens) // 3):
            return True
    return False

def sources_text(research: dict[str, Any]) -> str:
    lines = [f"Topic: {research.get('topic', '')}", "", "Sources used:"]
    for src in research.get("sources") or []:
        lines.append(f"- {src.get('title', 'Source')}: {src.get('url', '')}")
    lines += ["", "Facts considered:"]
    for fact in research.get("facts") or []:
        lines.append(f"- {fact}")
    return "\n".join(lines).strip() + "\n"
