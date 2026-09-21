"""Research a topic. Minecraft uses the built-in fact bank first."""
from __future__ import annotations
import re
from typing import Any
from urllib.parse import quote
from .general_kb import facts_for_general, visual_queries_for
from .minecraft_kb import facts_for_topic, minecraft_topic, minecraft_visuals, topic_keys
from .utils import http_get, info, unique_keep_order

WIKI_API = "https://en.wikipedia.org/w/api.php"
_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about",
    "the", "that", "tips", "tip", "guide", "how", "why", "what", "for", "and",
    "with", "from", "make", "video", "short", "tell", "everything", "mark",
}
_HISTORY = (
    "developed by", "published by", "created by", "founded by",
    "mojang", "persson", "notch", "sandbox video game",
)

def topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)
    return [w for w in words if w.lower() not in _FILLER]

def specific_tokens(topic: str) -> list[str]:
    return topic_tokens(topic)

def clean_topic_query(topic: str) -> str:
    return " ".join(topic_tokens(topic)) or topic.strip() or topic

def is_tips_topic(topic: str) -> bool:
    low = topic.lower()
    return any(w in low for w in ("tip", "tips", "guide", "how to", "pvp", "tricks", "tutorial"))

def related_lookups(topic: str) -> list[str]:
    q = clean_topic_query(topic)
    extra = []
    low = topic.lower()
    if "spitfire" in low:
        extra += ["Supermarine Spitfire", "Spitfire Mk II"]
    if "war thunder" in low or "warthunder" in low:
        extra += ["War Thunder", "Supermarine Spitfire"]
    return unique_keep_order([q, topic] + extra)

def visual_lookups(topic: str) -> list[str]:
    if minecraft_topic(topic):
        return minecraft_visuals(topic)
    query = clean_topic_query(topic)
    extra = visual_queries_for(topic)
    return unique_keep_order(extra + [query, f"{query} aircraft", f"{query} photo"])

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching locked topic: {topic}")
    query = clean_topic_query(topic)
    keywords = visual_lookups(topic)
    facts = []
    sources = []
    if minecraft_topic(topic):
        facts = facts_for_topic(topic, limit=12)
        sources = [{"title": "Built-in Minecraft fact bank", "url": "local:minecraft_kb", "type": "local"}]
    general = facts_for_general(topic, limit=10)
    if general:
        facts = unique_keep_order(general + facts)
        sources.append({"title": "Built-in topic notes", "url": "local:general_kb", "type": "local"})
    wiki_facts, wiki_sources, keywords = _wiki_research(topic, query, keywords)
    facts = unique_keep_order(facts + wiki_facts)
    sources.extend(wiki_sources)
    facts = [f for f in facts if not _is_history_sentence(f)]
    facts = unique_keep_order(facts)[:12]
    if not facts:
        facts = [
            f"{query} is the subject of this Short.",
            f"Every line after this stays on {query}.",
        ]
    info(f"Research kept {len(facts)} facts")
    return {
        "topic": topic,
        "query": query,
        "summary": facts[0] if facts else topic,
        "facts": facts,
        "sources": sources,
        "keywords": unique_keep_order(keywords)[:20],
        "language": language,
        "tips_topic": is_tips_topic(topic),
        "visual_lookups": unique_keep_order(keywords)[:20],
    }

def _wiki_research(topic, query, keywords):
    keys = [t.lower() for t in topic_tokens(topic)]
    pages = []
    seen = set()
    for q in related_lookups(topic):
        for page in _wiki_search(q, limit=8):
            title = page.get("title") or ""
            if title and title.lower() not in seen:
                seen.add(title.lower())
                pages.append(page)
    facts = []
    sources = []
    for page in pages[:8]:
        title = page.get("title") or ""
        if not title or "disambiguation" in title.lower():
            continue
        extract, url = _wiki_extract(title)
        if not extract:
            continue
        blob = f"{title} {extract[:400]}".lower()
        if keys and not any(k in blob for k in keys):
            continue
        sources.append({"title": title, "url": url, "type": "wikipedia"})
        keywords.append(title)
        for sentence in _fact_sentences(extract):
            if _is_history_sentence(sentence):
                continue
            facts.append(sentence)
    return unique_keep_order(facts), sources, keywords

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
    resp = http_get(WIKI_API, params={"action": "query", "prop": "extracts|info", "explaintext": "1", "redirects": "1", "inprop": "url", "titles": title, "format": "json", "utf8": "1"})
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
        if 40 <= len(sentence) <= 200:
            out.append(sentence)
    return out[:20]
