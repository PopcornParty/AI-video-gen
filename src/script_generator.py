"""Write a Shorts script from researched facts. No API key required."""
from __future__ import annotations
import re
from typing import Any
from .research import clean_topic_query, topic_tokens
from .utils import info, unique_keep_order

def generate_script(research, target_duration=45, language="en"):
    facts = research.get("facts") or []
    topic = research.get("topic") or "this topic"
    info("Script written from Wikipedia facts (no LLM key)")
    script = _template_script(topic, facts, target_duration)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _compose_narration(script):
    parts = [script.get("hook", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts if p and p.strip())).strip()

def _template_script(topic, facts, target_duration):
    label = clean_topic_query(topic)
    usable = unique_keep_order([_tighten(f) for f in facts if len(f) > 35])[:8]
    if not usable:
        usable = [f"The details behind {label} are what people usually miss."]
    hook = _hook_from_fact(topic, usable[0])
    budget = max(55, int(target_duration * 2.4))
    body = []
    used = len(hook.split())
    for fact in usable:
        if used + len(fact.split()) > budget:
            break
        if fact.lower() not in hook.lower():
            body.append(fact)
            used += len(fact.split())
    if not body:
        body = [usable[0]]
    return {
        "hook": hook,
        "body": body,
        "ending": f"Follow if you want more on {label}.",
        "title_seed": label,
        "provider": "template",
    }

def _hook_from_fact(topic, fact):
    label = clean_topic_query(topic)
    clean = _tighten(fact)
    return f"This is about {label}, not the whole category around it. {clean}"

def _tighten(sentence):
    s = re.sub(r"\s+", " ", sentence).strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s.endswith((".", "!", "?")):
        s += "."
    words = s.split()
    if len(words) > 32:
        s = " ".join(words[:32]).rstrip(",;:") + "."
    return s

def _plan_scenes(script, research):
    units = [script.get("hook", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    units = [u.strip() for u in units if u and u.strip()]
    topic = research.get("topic") or ""
    keywords = research.get("keywords") or []
    used_queries = set()
    scenes = []
    for i, text in enumerate(units):
        variants = _query_variants(text, topic, keywords, i)
        query = variants[0]
        for item in variants:
            if item.lower() not in used_queries:
                query = item
                break
        used_queries.add(query.lower())
        scenes.append({
            "index": i + 1,
            "text": text,
            "search_query": query,
            "search_queries": variants,
            "kind": "hook" if i == 0 else ("ending" if i == len(units) - 1 else "body"),
        })
    return scenes

_STOP = {
    "this", "that", "with", "from", "have", "most", "people", "about", "actually",
    "follow", "short", "facts", "fact", "true", "real", "never", "hear", "want",
    "like", "more", "next", "stop", "scrolling", "amazing", "insane", "idea",
    "simply", "often", "usually", "called", "known", "also", "their", "them",
    "category", "around", "whole", "public", "guides",
}

def _query_variants(text, topic, keywords, index):
    subject = clean_topic_query(topic)
    tokens = topic_tokens(topic)
    sentence_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text) if w.lower() not in _STOP]
    variants = []
    if sentence_words:
        variants.append(f"{subject} {' '.join(sentence_words[:5])}")
        variants.append(" ".join(sentence_words[:6]))
    variants.append(subject)
    if tokens:
        variants.append(" ".join(tokens))
    if keywords:
        variants.append(f"{subject} {keywords[min(index, len(keywords) - 1)]}")
    variants.append(f"{subject} screenshot")
    variants.append(f"{subject} gameplay")
    cleaned = []
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()[:80]
        if query and query.lower() not in {v.lower() for v in cleaned}:
            cleaned.append(query)
    return cleaned or [topic]
