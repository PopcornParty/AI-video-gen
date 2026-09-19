"""Research a topic using Wikipedia. No API key required."""
from __future__ import annotations
import re
from typing import Any
from urllib.parse import quote
from .utils import http_get, info, unique_keep_order, warn

WIKI_API = "https://en.wikipedia.org/w/api.php"
_FILLER = {"amazing","insane","wild","crazy","facts","fact","most","about","the","that","sound","fake","people","never","hear","quick","best","top","cool","weird"}

def clean_topic_query(topic: str) -> str:
    low = topic.lower()
    words = re.findall(r"[A-Za-z][A-Za-z0-9+]{2,}", topic)
    kept = [w for w in words if w.lower() not in _FILLER]
    core = " ".join(kept) or topic
    if "minecraft" in low:
        return "Minecraft"
    if "space" in low and "myspace" not in low:
        return "outer space"
    if "engineering" in low:
        return "engineering"
    return core

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching: {topic}")
    query = clean_topic_query(topic)
    pages = _wiki_search(query, limit=5) or _wiki_search(topic, limit=5)
    facts = []
    sources = []
    summary = ""
    keywords = [query] + re.findall(r"[A-Za-z][A-Za-z0-9+]{2,}", topic)
    for page in pages:
        title = page.get("title") or ""
        if not title or _off_topic_title(title, topic):
            continue
        extract, url = _wiki_extract(title)
        if not extract:
            continue
        if not summary:
            summary = extract[:600]
        sources.append({"title": title, "url": url, "type": "wikipedia"})
        facts.extend(_fact_sentences(extract))
        keywords.append(title)
    facts = unique_keep_order(facts)[:18]
    if not facts:
        warn("Wikipedia returned few facts; using topic talking points")
        facts = [f"Public sources still surprise people who look closely at {topic}.", f"The details behind {topic} are easy to underestimate."]
    return {"topic": topic, "summary": summary or topic, "facts": facts, "sources": sources, "keywords": unique_keep_order(keywords)[:16], "language": language}

def _wiki_search(topic, limit=5):
    resp = http_get(WIKI_API, params={"action": "query", "list": "search", "srsearch": topic, "srlimit": str(limit), "format": "json", "utf8": "1"})
    if resp is None:
        return []
    try:
        return resp.json().get("query", {}).get("search", []) or []
    except ValueError:
        return []

def _wiki_extract(title):
    resp = http_get(WIKI_API, params={"action": "query", "prop": "extracts|info", "exintro": "1", "explaintext": "1", "redirects": "1", "inprop": "url", "titles": title, "format": "json", "utf8": "1"})
    if resp is None:
        return "", ""
    try:
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            extract = (page.get("extract") or "").strip()
            url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            return extract, url
    except ValueError:
        return "", ""
    return "", ""

def _fact_sentences(extract):
    text = re.sub(r"\s+", " ", extract).strip()
    out = []
    for part in re.split(r"(?<=[.!?])\s+", text):
        sentence = part.strip()
        low = sentence.lower()
        if len(sentence) < 40 or len(sentence) > 240:
            continue
        if any(p in low for p in ("this article", "coordinates", "see also", "references")):
            continue
        out.append(sentence)
    return out[:10]

def _off_topic_title(title, topic):
    low = title.lower()
    topic_l = topic.lower()
    if "disambiguation" in low:
        return True
    blocked = ("film", "movie", "album", "song", "novel", "episode", "video game", "tv series", "klown", "adult", "kernel space", "user space", "nonprofit")
    return any(b in low for b in blocked) and not any(b in topic_l for b in blocked)
