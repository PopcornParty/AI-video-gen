"""Research a topic using Wikipedia. Stay on the typed topic."""
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
    "make", "video", "short",
}
_HISTORY = (
    "developed by", "published by", "created by", "founded by", "released in",
    "released on", "originally released", "headquarters", "born in",
)
_GENERIC = {"game", "games", "world", "history", "company", "science", "music", "sport", "sports", "video"}

def topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)
    return [w for w in words if w.lower() not in _FILLER]

def specific_tokens(topic: str) -> list[str]:
    return [t for t in topic_tokens(topic) if t.lower() not in _GENERIC]

def clean_topic_query(topic: str) -> str:
    kept = topic_tokens(topic)
    return " ".join(kept) or topic.strip() or topic

def focus_phrase(topic: str) -> str:
    return clean_topic_query(topic)

def is_tips_topic(topic: str) -> bool:
    low = topic.lower()
    return any(w in low for w in ("tip", "tips", "guide", "how to", "pvp", "tricks", "tutorial", "build", "combo"))

def related_lookups(topic: str) -> list[str]:
    query = clean_topic_query(topic)
    specific = specific_tokens(topic)
    extras = [f"\"{query}\"", query, topic]
    if specific:
        extras.append(" ".join(specific))
        if len(specific) >= 2:
            extras.append(" ".join(specific[:2]))
    return unique_keep_order([e for e in extras if e and e.strip()])

def visual_lookups(topic: str) -> list[str]:
    query = clean_topic_query(topic)
    specific = specific_tokens(topic)
    extras = [query]
    if specific:
        extras.append(" ".join(specific))
        if len(specific) >= 2:
            extras.append(f"{specific[0]} {specific[1]}")
    extras.append(f"{query} photo")
    return unique_keep_order([e for e in extras if e and e.strip()])

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching locked topic: {topic}")
    query = clean_topic_query(topic)
    tokens = [t.lower() for t in topic_tokens(topic)]
    specific = [t.lower() for t in specific_tokens(topic)]
    must = specific or tokens
    pages = []
    seen = set()
    for q in related_lookups(topic):
        for page in _wiki_search(q, limit=8):
            title = page.get("title") or ""
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            pages.append(page)
    pages.sort(key=lambda p: _title_score(p.get("title") or "", p.get("snippet") or "", tokens, must), reverse=True)
    facts = []
    sources = []
    summary = ""
    keywords = visual_lookups(topic)
    for page in pages[:8]:
        title = page.get("title") or ""
        if not title or _off_topic_title(title, topic, must):
            continue
        if _title_score(title, page.get("snippet") or "", tokens, must) <= 0:
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
            if _sentence_matches_topic(sentence, must):
                facts.append(_pin_sentence(sentence, query))
    facts = unique_keep_order(facts)[:12]
    if len(facts) < 3:
        warn("Not enough on-topic encyclopedia lines; writing locked talking points")
        facts = unique_keep_order(facts + _subject_points(topic, query))
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

def _pin_sentence(sentence, query):
    if query.lower() in sentence.lower():
        return sentence
    return f"On {query}: {sentence}"

def _subject_points(topic, query):
    return [
        f"This video is only about {query}.",
        f"Every point here stays on {query}.",
        f"If a detail is not {query}, it gets cut.",
        f"The useful part is how {query} works in practice.",
        f"Watch for {query}, not a wider subject around it.",
    ]

def _title_score(title, snippet, tokens, must):
    blob = f"{title} {re.sub('<[^>]+>', ' ', snippet)}".lower()
    title_l = title.lower()
    score = 0
    if must and not any(t in blob for t in must):
        return -10
    for t in must:
        if t in title_l:
            score += 8
        elif t in blob:
            score += 3
    if tokens and title_l == tokens[0]:
        score -= 8
    return score

def _sentence_matches_topic(sentence, must):
    low = sentence.lower()
    if _is_history_sentence(sentence):
        return False
    if not must:
        return True
    return any(t in low for t in must)

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
    resp = http_get(
        WIKI_API,
        params={
            "action": "query",
            "prop": "extracts|info",
            "explaintext": "1",
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
            return extract[:4000], url
    except ValueError:
        return "", ""
    return "", ""

def _fact_sentences(extract):
    text = re.sub(r"\s+", " ", extract).strip()
    out = []
    for part in re.split(r"(?<=[.!?])\s+", text):
        sentence = part.strip()
        low = sentence.lower()
        if len(sentence) < 35 or len(sentence) > 220:
            continue
        if any(p in low for p in ("this article", "coordinates", "see also", "references", "citation needed")):
            continue
        out.append(sentence)
    return out[:20]

def _off_topic_title(title, topic, must):
    low = title.lower()
    topic_l = topic.lower()
    if "disambiguation" in low:
        return True
    tokens = [t.lower() for t in topic_tokens(topic)]
    if must and tokens and low == tokens[0] and tokens[0] not in must:
        return True
    if must and not any(t in low for t in must) and low not in topic_l:
        return True
    blocked = ["film", "movie", "album", "song", "novel", "episode", "tv series", "klown", "adult", "kernel space", "user space"]
    return any(b in low for b in blocked) and not any(b in topic_l for b in blocked)
