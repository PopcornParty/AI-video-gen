"""YouTube title, description, hashtags, and tags."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .utils import save_json, save_text, unique_keep_order

def generate_metadata(topic, script, research, out_dir: Path):
    title = _clean_title(_title(topic, script), topic)
    description = _description(topic, script, research)
    hashtags = _normalize_hashtags(_hashtags(topic))
    tags = unique_keep_order(_tags(topic, research))[:20]
    payload = {"title": title, "description": description, "hashtags": hashtags, "tags": tags, "topic": topic}
    save_text(out_dir / "title.txt", title + "\n")
    desc_full = description.rstrip() + "\n\n" + " ".join(hashtags) + "\n" if hashtags else description
    save_text(out_dir / "description.txt", desc_full)
    save_text(out_dir / "tags.txt", ",".join(tags) + "\n")
    save_text(out_dir / "hashtags.txt", " ".join(hashtags) + "\n")
    save_json(out_dir / "metadata.json", payload)
    return payload

def _title(topic, script):
    seed = (script.get("title_seed") or topic).strip()
    seed = re.sub(r"\s+", " ", seed)
    if seed.lower() == topic.lower() or len(seed) < 16:
        seed = f"{topic} that sound fake"
    return seed[:70]

def _clean_title(title, topic):
    title = re.sub(r"\s+", " ", title).strip().strip('"').replace("#", "")
    return (title or topic)[:90]

def _description(topic, script, research):
    hook = script.get("hook") or topic
    lines = [hook, "", f"A short, sourced look at {topic}.", "", "Key points:"]
    for sentence in (script.get("body") or [])[:5]:
        lines.append(f"- {sentence}")
    sources = research.get("sources") or []
    if sources:
        lines += ["", "Sources:"]
        for src in sources[:5]:
            lines.append(f"- {src.get('title')}: {src.get('url')}")
    return "\n".join(lines).strip() + "\n"

def _hashtags(topic):
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", topic)
    tags = ["#shorts", "#youtubeshorts", "#facts"]
    if words:
        tags.append("#" + "".join(w.capitalize() for w in words[:3]))
        tags.append("#" + words[0].lower())
    return unique_keep_order(tags)[:8]

def _tags(topic, research):
    tags = [topic, "shorts", "facts", "educational"]
    tags.extend(research.get("keywords") or [])
    return [t for t in unique_keep_order(tags) if 2 < len(t) < 40]

def _normalize_hashtags(items):
    out = []
    for item in items:
        t = str(item).strip()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + re.sub(r"[^A-Za-z0-9]", "", t)
        out.append(t)
    return unique_keep_order(out)[:10]
