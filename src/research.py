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
    "best", "top", "cool", "weird", "explain", "how", "why", "what", "tips",
    "tip", "guide", "tricks", "tutorial", "for", "and", "with", "from",
}
_HISTORY = (
    "developed by", "published by", "created by", "founded by", "released in",
    "released on", "originally", "studio", "headquarters", "born in",
)
_BROAD = {
    "game", "games", "video", "world", "history", "company", "minecraft",
    "fortnite", "roblox", "space", "science", "music", "sport", "sports",
}

def topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)
    return [w for w in words if w.lower() not in _FILLER]

def specific_tokens(topic: str) -> list[str]:
    return [t for t in topic_tokens(topic) if t.lower() not in _BROAD]

def clean_topic_query(topic: str) -> str:
    kept = topic_tokens(topic)
    return " ".join(kept) or topic.strip() or topic

def is_tips_topic(topic: str) -> bool:
    low = topic.lower()
    return any(w in low for w in ("tip", "tips", "guide", "how to", "pvp", "tricks", "tutorial", "build", "combo"))

def related_lookups(topic: str) -> list[str]:
    query = clean_topic_query(topic)
    tokens = topic_tokens(topic)
    specific = specific_tokens(topic)
    extras = [topic, query]
    if specific:
        extras.append(" ".join(specific))
        extras.extend(specific)
        if len(specific) >= 2:
            extras.append(" ".join(specific[:2]))
            extras.append(" ".join(specific[-2:]))
    if tokens and specific:
        extras.append(f"{tokens[0]} {' '.join(specific[:2])}")
    return unique_keep_order([e for e in extras if e and e.strip()])

def visual_lookups(topic: str) -> list[str]:
    query = clean_topic_query(topic)
    tokens = topic_tokens(topic)
    specific = specific_tokens(topic)
    extras = [query]
    if specific:
        extras.append(" ".join(specific))
        for word in specific:
            extras.append(word)
            if tokens:
                extras.append(f"{tokens[0]} {word}")
    extras.append(f"{query} photograph")
    extras.append(f"{query} screenshot")
    extras.append(f"{specific[0]} photograph" if specific else f"{query} image")
    return unique_keep_order([e for e in extras if e and e.strip()])

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching: {topic}")
    query = clean_topic_query(topic)
    tokens = [t.lower() for t in topic_tokens(topic)]
    specific = [t.lower() for t in specific_tokens(topic)]
    pages = []
    seen = set()
    for q in related_lookups(topic):
        for page in _wiki_search(q, limit=8):
            title = page.get("title") or ""
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            pages.append(page)
    pages.sort(key=lambda p: _title_score(p.get("title") or "", p.get("snippet") or "", tokens, specific), reverse=True)
    facts = []
    sources = []
    summary = ""
    keywords = visual_lookups(topic)
    for page in pages[:10]:
        title = page.get("title") or ""
        if not title or _off_topic_title(title, topic, specific):
            continue
        extract, url = _wiki_extract(title)
        if not extract:
            continue
        if not summary:
            summary = extract[:600]
        sources.append({"title": title, "url": url, "type": "wikipedia"})
        keywords.append(title)
        for sentence in _fact_sentences(extract):
            if _is_history_sentence(sentence):
                continue
            if _sentence_matches_topic(sentence, tokens, specific):
                facts.append(sentence)
    facts = unique_keep_order(facts)[:18]
    if not facts:
        warn("Few on-topic encyclopedia sentences; staying on the typed subject")
        facts = _subject_points(topic, query, specific)
    return {
        "topic": topic,
        "query": query,
        "summary": summary or topic,
        "facts": facts,
        "sources": sources,
        "keywords": unique_keep_order(keywords)[:20],
        "language": language,
        "tips_topic": is_tips_topic(topic),
        "visual_lookups": unique_keep_order(keywords)[:20],
    }

def _subject_points(topic, query, specific):
    focus = " ".join(specific) if specific else query
    if is_tips_topic(topic):
        return [
            f"This is about {focus}, not the origin story of the bigger topic.",
            f"The useful part of {focus} is how it is used in practice.",
            f"Stay on {focus}: what it is, how it works, and what to do with it.",
            f"Ignore company history and talk about {focus} itself.",
        ]
    return [
        f"This Short is about {focus}, not the broader category around it.",
        f"The details that matter are the ones that explain {focus}.",
        f"Keep the focus on {focus} instead of a generic overview.",
    ]

def _title_score(title, snippet, tokens, specific):
    blob = f"{title} {re.sub('<[^>]+>', ' ', snippet)}".lower()
    score = 0
    title_l = title.lower()
    if specific and title_l in {t for t in tokens if t not in specific}:
        score -= 6
    for t in specific:
        if t in title_l:
            score += 6
        elif t in blob:
            score += 2
    for t in tokens:
        if t in title_l:
            score += 1
    return score

def _sentence_matches_topic(sentence, tokens, specific):
    low = sentence.lower()
    if _is_history_sentence(sentence):
        return False
    if specific:
        return any(t in low for t in specific)
    return any(t in low for t in tokens) if tokens else True

def _is_history_sentence(sentence):
    low = sentence.lower()
    return any(p in low for p in _HISTORY)

def _wiki_search(topic, limit=5):
    resp = http_get(WIKI_API, params={"action": "query", "list": "search", "srsearch": topic, "srlimit": str(limit), "format": "json", "utf8": "1"})
    if resp is None:
        return []
    try:
        return resp.json().get("query", {}).get("search", []) or []
    except ValueError:
        return []

def _wiki_extract(title):
    resp = http_get(WIKI_API, params={"action": "query", "prop": "extracts|info", "explaintext": "1", "exsentences": "18", "redirects": "1", "inprop": "url", "titles": title, "format": "json", "utf8": "1"})
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

def _off_topic_title(title, topic, specific):
    low = title.lower()
    topic_l = topic.lower()
    if "disambiguation" in low:
        return True
    tokens = [t.lower() for t in topic_tokens(topic)]
    broad_only = [t for t in tokens if t not in specific]
    if specific and low in broad_only:
        return True
    blocked = ["film", "movie", "album", "song", "novel", "episode", "tv series", "klown", "adult", "kernel space", "user space"]
    return any(b in low for b in blocked) and not any(b in topic_l for b in blocked)
