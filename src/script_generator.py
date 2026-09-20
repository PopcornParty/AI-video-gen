"""Write a spoken Short that sounds like a person explaining the prompt."""
from __future__ import annotations
import re
from .minecraft_kb import minecraft_topic, minecraft_visuals, specific_keys, topic_keys
from .research import clean_topic_query, visual_lookups
from .utils import info, unique_keep_order

def generate_script(research, target_duration=32, language="en"):
    topic = (research.get("topic") or "this topic").strip()
    focus = clean_topic_query(topic)
    info(f"Script locked to prompt: {topic}")
    facts = unique_keep_order([_spoken(f) for f in (research.get("facts") or []) if _on_topic(f, topic)])
    script = _human_script(topic, focus, facts)
    script["full_narration"] = script["full_narration"]
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _on_topic(text, topic):
    low = text.lower()
    keys = specific_keys(topic)
    if not keys:
        return True
    return any(k in low or k.rstrip("s") in low for k in keys)

def _human_script(topic, focus, facts):
    label = focus if focus else topic
    short = label if len(label.split()) <= 6 else " ".join(label.split()[:6])
    hook = f"Okay, real quick. {short}."
    hook_card = short[:32]
    if not facts:
        facts = [f"This whole Short stays on {short}."]
    spoken = [hook, facts[0]]
    bridges = ["Also,", "And", "That's why", "One more thing."]
    for i, fact in enumerate(facts[1:5]):
        fact = fact[0].lower() + fact[1:] if fact and fact[0].isupper() else fact
        spoken.append(f"{bridges[i % len(bridges)]} {fact}")
    spoken.append(f"Anyway, that's {short}. Follow if you want more.")
    narration = re.sub(r"\s+", " ", " ".join(spoken)).replace("..", ".")
    body = facts[1:5]
    return {
        "hook": hook,
        "hook_card": hook_card,
        "interest": facts[0],
        "body": body,
        "ending": f"Anyway, that's {short}. Follow if you want more.",
        "full_narration": narration,
        "title_seed": short,
        "provider": "human-flow",
    }

def _spoken(sentence):
    s = re.sub(r"\s+", " ", sentence).strip()
    s = re.sub(r"^(In Minecraft, |Minecraft |A true Minecraft |The Minecraft )", "", s)
    s = s.replace("This Short is about", "This is")
    if not s.endswith((".", "!", "?")):
        s += "."
    words = s.split()
    if len(words) > 26:
        s = " ".join(words[:26]).rstrip(",;:") + "."
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
