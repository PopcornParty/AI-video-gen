"""Write a Shorts script from researched facts. No API key required."""
from __future__ import annotations
import re
from typing import Any
from .fact_checker import filter_script_to_sources
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
    scenes = []
    for i, text in enumerate(units):
        scenes.append({"index": i + 1, "text": text, "search_query": _visual_query(text, topic, research.get("keywords") or []), "kind": "hook" if i == 0 else ("ending" if i == len(units) - 1 else "body")})
    return scenes

def _visual_query(text, topic, keywords):
    from .research import clean_topic_query
    core = clean_topic_query(topic)
    low = (core + " " + topic).lower()
    if "minecraft" in low:
        return "minecraft overworld landscape"
    if "space" in low:
        return "outer space galaxy stars nebula"
    if "engineering" in low:
        return "engineering construction bridge machines"
    return (core or topic)[:80]
