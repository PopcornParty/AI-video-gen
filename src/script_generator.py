"""Write a Shorts script locked to the typed topic."""
from __future__ import annotations
import re
from .minecraft_kb import minecraft_topic, minecraft_visuals
from .research import clean_topic_query, is_tips_topic, specific_tokens, visual_lookups
from .utils import info, unique_keep_order

HOOK_WORDS = 10
INTEREST_WORDS = 22

def generate_script(research, target_duration=32, language="en"):
    topic = research.get("topic") or "this topic"
    focus = clean_topic_query(topic)
    info(f"Script locked to: {focus}")
    facts = unique_keep_order([_tighten(f) for f in (research.get("facts") or []) if _on_topic(f, topic)])
    script = _structured_script(topic, focus, facts, target_duration)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _on_topic(text, topic):
    low = text.lower()
    keys = [t.lower() for t in specific_tokens(topic) if t.lower() != "minecraft"]
    if minecraft_topic(topic) and any(k in ("crystal", "pvp", "crystals") for k in keys):
        return any(w in low for w in ("crystal", "obsidian", "bedrock", "totem", "pearl", "pvp", "explode", "detonat"))
    if keys:
        return any(k in low for k in keys)
    return True

def _compose_narration(script):
    parts = [script.get("hook", ""), script.get("interest", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts if p and p.strip())).strip()

def _structured_script(topic, focus, facts, target_duration):
    hook = _limit_words(f"Wait. {focus} is not sword PvP.", HOOK_WORDS)
    hook_card = "Crystal PvP" if "crystal" in topic.lower() else _limit_words(focus, 5).rstrip(".")
    if is_tips_topic(topic) and "crystal" in topic.lower():
        hook = "Wait. Crystal PvP only works on obsidian."
        hook_card = "Only obsidian."
    interest = _tighten(_limit_words(
        "Stay. The real rule is End Crystals place on obsidian or bedrock.",
        INTEREST_WORDS,
    )) if "crystal" in topic.lower() else _tighten(_limit_words(
        f"Stay. Every line after this is {focus}.", INTEREST_WORDS
    ))
    fact_budget = max(28, int(min(target_duration, 40) * 2.2) - 20)
    body = []
    used = 0
    for fact in facts:
        if fact.lower() in hook.lower() or fact.lower() in interest.lower():
            continue
        words = len(fact.split())
        if used + words > fact_budget:
            break
        body.append(fact)
        used += words
    if not body:
        body = facts[:4] or [f"This Short stays on {focus}."]
    ending = f"Follow for more {focus}."
    return {
        "hook": hook,
        "hook_card": hook_card,
        "interest": interest,
        "body": body,
        "ending": ending,
        "title_seed": focus,
        "provider": "topic-lock",
    }

def _limit_words(text, n):
    words = re.findall(r"\S+", text)
    if len(words) <= n:
        return text.strip()
    out = " ".join(words[:n]).rstrip(",;:")
    if not out.endswith(("?", "!", ".")):
        out += "."
    return out

def _tighten(sentence):
    s = re.sub(r"\s+", " ", sentence).strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s.endswith((".", "!", "?")):
        s += "."
    words = s.split()
    if len(words) > 26:
        s = " ".join(words[:26]).rstrip(",;:") + "."
    return s

def _plan_scenes(script, research):
    units = [("hook", script.get("hook", "")), ("interest", script.get("interest", ""))]
    for fact in script.get("body") or []:
        units.append(("fact", fact))
    units.append(("ending", script.get("ending", "")))
    units = [(k, t.strip()) for k, t in units if t and t.strip()]
    topic = research.get("topic") or ""
    lookups = visual_lookups(topic) if not minecraft_topic(topic) else minecraft_visuals(topic)
    used = set()
    scenes = []
    for i, (kind, text) in enumerate(units):
        variants = lookups[:] or [clean_topic_query(topic)]
        if kind == "hook" and lookups:
            variants = [lookups[0]] + lookups[1:]
        query = variants[i % len(variants)]
        if query.lower() in used and len(variants) > 1:
            query = variants[(i + 1) % len(variants)]
        used.add(query.lower())
        scenes.append({
            "index": i + 1,
            "text": text,
            "kind": kind,
            "hook_card": script.get("hook_card", "") if kind == "hook" else "",
            "search_query": query,
            "search_queries": variants,
            "match_tokens": ["end crystal", "obsidian", "minecraft", "crystal"] if minecraft_topic(topic) else [clean_topic_query(topic).lower()],
        })
    return scenes
