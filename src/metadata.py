"""YouTube title, description, hashtags, and tags."""
from __future__ import annotations
import re
from pathlib import Path
from .research import clean_topic_query, specific_tokens
from .utils import save_json, save_text, unique_keep_order

def generate_metadata(topic, script, research, out_dir: Path):
    title = _clean_title(_title(topic, script), topic)
    description = _description(topic, script, research)
    hashtags = _normalize_hashtags(_hashtags(topic))
    tags = unique_keep_order(_tags(topic, research))[:20]
    payload = {"title": title, "description": description, "hashtags": hashtags, "tags": tags, "topic": topic}
    save_text(out_dir / "title.txt", title + "\n")
    desc_full = description.rstrip() + "\n\n" + " ".join(hashtags) + "\n"
    save_text(out_dir / "description.txt", desc_full)
    save_text(out_dir / "tags.txt", ",".join(tags) + "\n")
    save_text(out_dir / "hashtags.txt", " ".join(hashtags) + "\n")
    save_json(out_dir / "metadata.json", payload)
    return payload

def _focus(topic):
    specific = specific_tokens(topic)
    return " ".join(specific) if specific else clean_topic_query(topic)

def _title(topic, script):
    label = _focus(topic)
    hook_card = (script.get("hook_card") or "").strip().rstrip(".")
    options = [
        f"{label}: what nobody explains",
        f"Why {label} actually works",
        f"{label} in 30 seconds",
    ]
    if hook_card and len(hook_card) < 42:
        options.insert(0, f"{label}: {hook_card}")
    title = options[abs(hash(topic.lower())) % len(options)]
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > 58:
        title = title[:58].rsplit(" ", 1)[0]
    return title

def _clean_title(title, topic):
    title = re.sub(r"\s+", " ", title).strip().strip('"').replace("#", "")
    return (title or topic)[:70]

def _description(topic, script, research):
    label = _focus(topic)
    hook = script.get("hook") or label
    first = f"{label}. {hook}".strip()
    if len(first) > 100:
        first = first[:97].rsplit(" ", 1)[0] + "."
    lines = [
        first,
        "",
        f"Watch to the end for the part that actually explains {label}.",
        "",
        f"Follow for more {label} Shorts.",
        "",
        "Key points:",
    ]
    for sentence in (script.get("body") or [])[:4]:
        lines.append(f"- {sentence}")
    sources = research.get("sources") or []
    if sources:
        lines += ["", "Sources:"]
        for src in sources[:4]:
            lines.append(f"- {src.get('title')}: {src.get('url')}")
    return "\n".join(lines).strip() + "\n"

def _hashtags(topic):
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", _focus(topic))
    tags = ["#Shorts"]
    if words:
        tags.append("#" + "".join(w.capitalize() for w in words[:3]))
        tags.append("#" + words[0].capitalize())
    tags.append("#facts")
    return unique_keep_order(tags)[:5]

def _tags(topic, research):
    tags = [topic, _focus(topic), "shorts", "facts", "educational"]
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
    return unique_keep_order(out)[:5]
