"""Write a spoken Short that stays on the prompt without repeating the title."""
from __future__ import annotations
import re
from .minecraft_kb import minecraft_topic, minecraft_visuals, specific_keys, topic_keys
from .research import clean_topic_query, visual_lookups
from .utils import info, unique_keep_order

def generate_script(research, target_duration=32, language="en"):
    topic = (research.get("topic") or "this topic").strip()
    focus = clean_topic_query(topic)
    info(f"Script locked to prompt: {topic}")
    raw = research.get("facts") or []
    facts = unique_keep_order([_spoken(f) for f in raw if _usable(f, topic)])
    if len(facts) < 3:
        facts = unique_keep_order(facts + [_spoken(f) for f in raw])
    script = _human_script(topic, focus, facts)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _usable(text, topic):
    low = text.lower()
    if low.startswith("this video is only about") or low.startswith("this whole short"):
        return False
    if low.count(topic.lower()) > 0 and len(text.split()) < 10:
        return False
    return True

def _human_script(topic, focus, facts):
    short = focus if focus else topic
    if len(short.split()) > 5:
        short = " ".join(short.split()[:5])
    hook = f"Real quick, {short}."
    hook_card = short[:28]
    facts = [f for f in facts if f and short.lower() not in f.lower() or len(f.split()) > 8]
    if not facts:
        facts = ["Here is the part most people skip."]
    interest = facts[0]
    body = facts[1:5]
    ending = "Follow if you want the next one."
    parts = [hook, interest] + body + [ending]
    narration = re.sub(r"\s+", " ", " ".join(parts))
    return {
        "hook": hook,
        "hook_card": hook_card,
        "interest": interest,
        "body": body,
        "ending": ending,
        "full_narration": narration,
        "title_seed": short,
        "provider": "human-flow",
    }

def _spoken(sentence):
    s = re.sub(r"\s+", " ", sentence).strip()
    s = re.sub(r"^(In Minecraft, |Minecraft |A true Minecraft |The Minecraft )", "", s)
    if not s.endswith((".", "!", "?")):
        s += "."
    words = s.split()
    if len(words) > 22:
        s = " ".join(words[:22]).rstrip(",;:") + "."
    return s[0].upper() + s[1:] if s else s

def _plan_scenes(script, research):
    units = [("hook", script.get("hook", "")), ("interest", script.get("interest", ""))]
    for fact in script.get("body") or []:
        units.append(("fact", fact))
    units.append(("ending", script.get("ending", "")))
    units = [(k, t.strip()) for k, t in units if t and t.strip()]
    topic = research.get("topic") or ""
    lookups = minecraft_visuals(topic) if minecraft_topic(topic) else visual_lookups(topic)
    tokens = specific_keys(topic) or topic_keys(topic) or [clean_topic_query(topic).lower()]
    tokens = [t for t in tokens if t not in {"mark", "facts", "fact"}]
    scenes = []
    for i, (kind, text) in enumerate(units):
        query = lookups[i % len(lookups)] if lookups else topic
        scenes.append({
            "index": i + 1,
            "text": text,
            "kind": kind,
            "hook_card": script.get("hook_card", "") if kind == "hook" else "",
            "search_query": query,
            "search_queries": lookups[i:] + lookups[:i],
            "match_tokens": tokens,
        })
    return scenes
