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
    "tip", "guide", "tricks",
}
_HISTORY = (
    "developed by", "published by", "created by", "mojang", "persson", "notch",
    "released in", "released on", "originally", "studio", "video game developed",
    "sandbox game", "java edition", "xbox", "playstation",
)

def topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)
    return [w for w in words if w.lower() not in _FILLER]

def clean_topic_query(topic: str) -> str:
    kept = topic_tokens(topic)
    return " ".join(kept) or topic.strip() or topic

def is_tips_topic(topic: str) -> bool:
    low = topic.lower()
    return any(w in low for w in ("tip", "tips", "guide", "how to", "pvp", "tricks", "tutorial"))

def related_lookups(topic: str) -> list[str]:
    low = topic.lower()
    query = clean_topic_query(topic)
    extras = [topic, query]
    if "minecraft" in low and "crystal" in low:
        extras.extend(["End crystal", "End Crystal Minecraft", "Obsidian Minecraft", "Minecraft player versus player"])
    if "minecraft" in low and "redstone" in low:
        extras.extend(["Redstone Minecraft", "Piston Minecraft", "Redstone circuit"])
    if "minecraft" in low and "enchant" in low:
        extras.extend(["Enchanting Minecraft", "Enchantment Minecraft"])
    if "minecraft" in low and "pvp" in low:
        extras.extend(["Minecraft combat", "Player versus player", "Netherite Minecraft"])
    if "minecraft" in low:
        extras.append("Minecraft gameplay")
    return unique_keep_order(extras)

def visual_lookups(topic: str) -> list[str]:
    low = topic.lower()
    query = clean_topic_query(topic)
    extras = [query]
    if "minecraft" in low and "crystal" in low:
        extras.extend([
            "Minecraft End Crystal",
            "End crystal Minecraft",
            "Minecraft obsidian",
            "Minecraft End island",
            "Minecraft explosion",
            "Minecraft PvP combat",
            "Ender Dragon crystal",
        ])
    elif "minecraft" in low and "redstone" in low:
        extras.extend(["Minecraft redstone", "Minecraft piston", "Minecraft wiring"])
    elif "minecraft" in low:
        extras.extend(["Minecraft gameplay screenshot", "Minecraft world", "Minecraft combat"])
    return unique_keep_order(extras)

def research_topic(topic: str, language: str = "en") -> dict[str, Any]:
    info(f"Researching: {topic}")
    query = clean_topic_query(topic)
    tokens = [t.lower() for t in topic_tokens(topic)]
    pages = []
    seen = set()
    for q in related_lookups(topic):
        for page in _wiki_search(q, limit=8):
            title = page.get("title") or ""
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            pages.append(page)
    pages.sort(key=lambda p: _title_score(p.get("title") or "", p.get("snippet") or "", tokens, topic), reverse=True)
    facts = []
    sources = []
    summary = ""
    keywords = visual_lookups(topic) + topic_tokens(topic)
    for page in pages[:8]:
        title = page.get("title") or ""
        if not title or _off_topic_title(title, topic):
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
            if _sentence_matches_topic(sentence, tokens, topic):
                facts.append(sentence)
    facts = unique_keep_order(facts)[:18]
    if not facts:
        warn("Few on-topic encyclopedia sentences; using subject-focused talking points")
        facts = _subject_points(topic, query)
    return {
        "topic": topic,
        "query": query,
        "summary": summary or topic,
        "facts": facts,
        "sources": sources,
        "keywords": unique_keep_order(keywords)[:20],
        "language": language,
        "tips_topic": is_tips_topic(topic),
        "visual_lookups": visual_lookups(topic),
    }

def _subject_points(topic, query):
    low = topic.lower()
    if "minecraft" in low and "crystal" in low:
        return [
            "Minecraft crystal PvP is a combat style that uses end crystals, not a history lesson about the game.",
            "End crystals can be placed on obsidian or bedrock and then detonated.",
            "The explosion is strong, so the fight is about placing, breaking, and moving around crystals.",
            "Players usually keep blocks like obsidian nearby so a crystal can be placed again quickly.",
            "Do not stand in your own blast. The same explosion that hits the other player can hit you.",
        ]
    if "minecraft" in low and "redstone" in low:
        return [
            f"This is about {query} inside Minecraft, not the story of the game.",
            "Redstone carries a signal that can power lamps, pistons, and other blocks.",
            "The useful part is how you build the circuit, not who published the game.",
        ]
    return [
        f"This Short is about {query}, not the broader category around it.",
        f"The useful part of {query} is how it works in practice.",
        f"Stay on {query} instead of the origin story of the bigger topic.",
    ]

def _title_score(title, snippet, tokens, topic):
    blob = f"{title} {re.sub('<[^>]+>', ' ', snippet)}".lower()
    topic_l = topic.lower()
    score = 0
    if "minecraft" in topic_l and title.lower() == "minecraft":
        score -= 4
    for t in tokens:
        if t in title.lower():
            score += 4
        elif t in blob:
            score += 1
    if any(w in title.lower() for w in ("end crystal", "redstone", "obsidian", "pvp", "combat")):
        score += 5
    return score

def _sentence_matches_topic(sentence, tokens, topic):
    low = sentence.lower()
    if _is_history_sentence(sentence):
        return False
    specific = [t for t in tokens if t not in {"game", "games", "video", "world", "minecraft"}]
    if specific:
        return any(t in low for t in specific)
    if "minecraft" in topic.lower() and is_tips_topic(topic):
        return any(w in low for w in ("gameplay", "combat", "player", "block", "craft", "pvp"))
    return True

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

def _off_topic_title(title, topic):
    low = title.lower()
    topic_l = topic.lower()
    if "disambiguation" in low:
        return True
    if "minecraft" in topic_l and low == "minecraft":
        return True
    blocked = ["film", "movie", "album", "song", "novel", "episode", "tv series", "klown", "adult", "kernel space", "user space", "nonprofit"]
    return any(b in low for b in blocked) and not any(b in topic_l for b in blocked)
