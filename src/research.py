"""Research a topic using Wikipedia. No API key required."""
from __future__ import annotations
import re
from typing import Any
from urllib.parse import quote
from .utils import http_get, info, unique_keep_order, warn

WIKI_API = "https://en.wikipedia.org/w/api.php"
_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about",
    "the", "that", "sound", "fake", "people", "never", "hear", "quick",
    "best", "top", "cool", "weird", "explain", "how", "why", "what",
}

def topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)
    return [w for w in words if w.lower() not in _FILLER]

def clean_topic_query(topic: str) -> str:
    kept = topic_tokens(topic)
    return " ".join(kept) or topic.strip() or topic

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching: {topic}")
    query = clean_topic_query(topic)
    tokens = [t.lower() for t in topic_tokens(topic)]
    pages = []
    seen = set()
    for q in unique_keep_order([topic, query, f"{query} gameplay", query.split(" ")[0] if query else topic]):
        for page in _wiki_search(q, limit=8):
            title = page.get("title") or ""
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            pages.append(page)
    pages.sort(key=lambda p: _title_score(p.get("title") or "", p.get("snippet") or "", tokens), reverse=True)
    facts = []
    sources = []
    summary = ""
    keywords = [query] + topic_tokens(topic)
    for page in pages[:8]:
        title = page.get("title") or ""
        if not title or _off_topic_title(title, topic):
            continue
        if tokens and _title_score(title, page.get("snippet") or "", tokens) <= 0 and sources:
            continue
        extract, url = _wiki_extract(title)
        if not extract:
            continue
        if not summary:
            summary = extract[:600]
        sources.append({"title": title, "url": url, "type": "wikipedia"})
        keywords.append(title)
        for sentence in _fact_sentences(extract):
            if _sentence_matches_topic(sentence, tokens):
                facts.append(sentence)
    facts = unique_keep_order(facts)[:18]
    if not facts:
        warn("Few on-topic facts found; staying on the typed subject")
        facts = [
            f"{query} is more specific than people think when they only look at the surface of the topic.",
            f"The way {query} works is what actually makes it interesting.",
            f"Public guides and encyclopedia pages still focus on how {query} behaves, not just the bigger category around it.",
        ]
    return {
        "topic": topic,
        "query": query,
        "summary": summary or topic,
        "facts": facts,
        "sources": sources,
        "keywords": unique_keep_order(keywords)[:16],
        "language": language,
    }

def _title_score(title: str, snippet: str, tokens: list[str]) -> int:
    blob = f"{title} {re.sub('<[^>]+>', ' ', snippet)}".lower()
    if not tokens:
        return 1
    return sum(3 if t in title.lower() else 1 for t in tokens if t in blob)

def _sentence_matches_topic(sentence: str, tokens: list[str]) -> bool:
    if not tokens:
        return True
    low = sentence.lower()
    specific = [t for t in tokens if t not in {"game", "games", "video", "world"}]
    check = specific or tokens
    hits = sum(1 for t in check if t in low)
    if len(check) == 1:
        return hits >= 1
    return hits >= 1

def _wiki_search(topic, limit=5):
    resp = http_get(WIKI_API, params={"action": "query", "list": "search", "srsearch": topic, "srlimit": str(limit), "format": "json", "utf8": "1"})
    if resp is None:
        return []
    try:
        return resp.json().get("query", {}).get("search", []) or []
    except ValueError:
        return []

def _wiki_extract(title):
    resp = http_get(
        WIKI_API,
        params={
            "action": "query",
            "prop": "extracts|info",
            "explaintext": "1",
            "exsentences": "18",
            "redirects": "1",
            "inprop": "url",
            "titles": title,
            "format": "json",
            "utf8": "1",
        },
    )
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
        if any(p in low for p in ("this article", "coordinates", "see also", "references", "citation needed")):
            continue
        out.append(sentence)
    return out[:12]

def _off_topic_title(title, topic):
    low = title.lower()
    topic_l = topic.lower()
    if "disambiguation" in low:
        return True
    game_topic = any(w in topic_l for w in ("game", "minecraft", "roblox", "fortnite", "mechanic", "redstone"))
    blocked = ["film", "movie", "album", "song", "novel", "episode", "tv series", "klown", "adult", "kernel space", "user space", "nonprofit"]
    if not game_topic:
        blocked.append("video game")
    return any(b in low for b in blocked) and not any(b in topic_l for b in blocked)
