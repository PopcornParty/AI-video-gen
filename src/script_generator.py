"""Write a Shorts script from researched facts. No API key required."""
from __future__ import annotations
import re
from .research import clean_topic_query, is_tips_topic, topic_tokens, visual_lookups
from .utils import info, unique_keep_order

def generate_script(research, target_duration=45, language="en"):
    facts = research.get("facts") or []
    topic = research.get("topic") or "this topic"
    info("Script written from on-topic research")
    if is_tips_topic(topic) or research.get("tips_topic"):
        script = _tips_script(topic, facts, target_duration)
    else:
        script = _template_script(topic, facts, target_duration)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _compose_narration(script):
    parts = [script.get("hook", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts if p and p.strip())).strip()

def _tips_script(topic, facts, target_duration):
    label = clean_topic_query(topic)
    hook = f"This is {label}. Not the origin story of the game."
    body = []
    for fact in unique_keep_order([_tighten(f) for f in facts])[:6]:
        low = fact.lower()
        if any(w in low for w in ("developed", "mojang", "released", "sandbox", "studio")):
            continue
        body.append(fact)
    if len(body) < 3:
        body = unique_keep_order(body + _fallback_tips(topic, label))
    budget = max(55, int(target_duration * 2.4))
    kept = []
    used = len(hook.split())
    for line in body:
        if used + len(line.split()) > budget:
            break
        kept.append(line)
        used += len(line.split())
    return {"hook": hook, "body": kept or body[:3], "ending": f"Follow for more {label}.", "title_seed": label, "provider": "tips"}

def _fallback_tips(topic, label):
    low = topic.lower()
    if "crystal" in low and "minecraft" in low:
        return [
            "Use end crystals, not random swords-only advice.",
            "Place a crystal on obsidian or bedrock, then detonate it.",
            "Move after you place it. The blast can hit you too.",
            "Keep obsidian ready so you can place another crystal fast.",
        ]
    return [f"Stay on {label} and skip the company history.", f"Focus on how {label} is actually used."]

def _template_script(topic, facts, target_duration):
    label = clean_topic_query(topic)
    usable = unique_keep_order([_tighten(f) for f in facts if len(f) > 35])[:8]
    if not usable:
        usable = [f"The details behind {label} are what people usually miss."]
    hook = f"This is about {label}. {_tighten(usable[0])}"
    budget = max(55, int(target_duration * 2.4))
    body = []
    used = len(hook.split())
    for fact in usable:
        if used + len(fact.split()) > budget:
            break
        if fact.lower() not in hook.lower():
            body.append(fact)
            used += len(fact.split())
    return {"hook": hook, "body": body or [usable[0]], "ending": f"Follow if you want more on {label}.", "title_seed": label, "provider": "template"}

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
    lookups = research.get("visual_lookups") or visual_lookups(topic)
    used_queries = set()
    scenes = []
    for i, text in enumerate(units):
        variants = _query_variants(text, topic, lookups, i)
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
    "this", "that", "with", "from", "have", "most", "people", "about", "follow",
    "short", "facts", "true", "real", "want", "like", "more", "next", "origin",
    "story", "company", "history", "category",
}

def _query_variants(text, topic, lookups, index):
    subject = clean_topic_query(topic)
    variants = []
    if lookups:
        variants.append(lookups[index % len(lookups)])
        variants.extend(lookups)
    sentence_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text) if w.lower() not in _STOP]
    if sentence_words:
        variants.append(f"{subject} {' '.join(sentence_words[:4])}")
    variants.append(subject)
    cleaned = []
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()[:80]
        if query and query.lower() not in {v.lower() for v in cleaned}:
            cleaned.append(query)
    return cleaned or [topic]
