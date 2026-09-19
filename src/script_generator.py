"""Write a Shorts script from researched facts. No API key required."""
from __future__ import annotations
import re
from typing import Any
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
    usable = unique_keep_order([_tighten(f) for f in facts if len(f) > 35])[:8]
    if not usable:
        usable = [f"Public sources still surprise people who look closely at {topic}."]
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
    return {"hook": hook, "body": body, "ending": "If you want more quick facts like this, follow for the next Short.", "title_seed": topic, "provider": "template"}

def _hook_from_fact(topic, fact):
    from .research import clean_topic_query
    label = clean_topic_query(topic)
    clean = _tighten(fact)
    if len(clean.split()) <= 18:
        return f"Most people have no idea this is true about {label}. {clean}"
    return f"Stop scrolling. This {label} fact is actually real. {clean}"

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
        query = _visual_query(text, topic, keywords, i, used_queries)
        used_queries.add(query.lower())
        scenes.append({
            "index": i + 1,
            "text": text,
            "search_query": query,
            "search_queries": _query_variants(text, topic, keywords, i),
            "kind": "hook" if i == 0 else ("ending" if i == len(units) - 1 else "body"),
        })
    return scenes

_STOP = {
    "this", "that", "with", "from", "have", "most", "people", "about", "actually",
    "follow", "short", "facts", "fact", "true", "real", "never", "hear", "want",
    "like", "more", "next", "stop", "scrolling", "amazing", "insane", "idea",
    "simply", "often", "usually", "called", "known", "also", "their", "them",
}

def _visual_query(text, topic, keywords, index, used_queries):
    variants = _query_variants(text, topic, keywords, index)
    for query in variants:
        if query.lower() not in used_queries:
            return query
    return variants[0] if variants else topic

def _query_variants(text, topic, keywords, index):
    from .research import clean_topic_query
    core = clean_topic_query(topic)
    subject = core or topic
    sentence_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text) if w.lower() not in _STOP]
    extras = []
    if keywords:
        extras.append(str(keywords[min(index, len(keywords) - 1)]))
    if sentence_words:
        extras.append(" ".join(sentence_words[:4]))
        extras.append(sentence_words[0])
    extras.extend(_subject_angles(subject, index))
    variants = []
    for extra in extras:
        query = f"{subject} {extra}".strip()
        query = re.sub(r"\s+", " ", query)[:80]
        if query and query.lower() not in {v.lower() for v in variants}:
            variants.append(query)
    if not variants:
        variants = [subject]
    return variants

def _subject_angles(subject, index):
    low = subject.lower()
    banks = {
        "space": ["earth from space", "milky way galaxy", "nebula clouds", "saturn planet", "rocket launch", "astronaut spacewalk", "hubble telescope image"],
        "minecraft": ["minecraft mountains", "minecraft forest", "minecraft cave", "minecraft village", "minecraft ocean", "minecraft night sky"],
        "engineering": ["suspension bridge", "skyscraper construction", "factory machines", "high speed train", "dam hydroelectric", "aircraft assembly"],
        "ocean": ["coral reef", "ocean waves aerial", "whale underwater", "deep sea", "rocky coastline"],
        "volcano": ["erupting volcano", "lava flow", "volcanic crater", "ash cloud"],
        "animal": ["wildlife close up", "animal habitat", "birds in flight"],
    }
    for key, angles in banks.items():
        if key in low:
            return [angles[index % len(angles)], angles[(index + 2) % len(angles)]]
    generic = ["photograph", "landscape", "close up", "aerial view", "historic photo", "diagram photo"]
    return [generic[index % len(generic)]]
