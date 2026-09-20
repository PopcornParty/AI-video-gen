"""Write a spoken Short that stays on-topic and sounds connected."""
from __future__ import annotations
import re
from .minecraft_kb import minecraft_topic, minecraft_visuals, topic_keys
from .research import clean_topic_query, visual_lookups
from .utils import info, unique_keep_order

def generate_script(research, target_duration=32, language="en"):
    topic = research.get("topic") or "this topic"
    focus = clean_topic_query(topic)
    info(f"Script locked to: {focus}")
    facts = unique_keep_order([_spoken(f) for f in (research.get("facts") or []) if _on_topic(f, topic)])
    script = _flowing_script(topic, focus, facts)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _on_topic(text, topic):
    low = text.lower()
    if "crystal" in topic.lower():
        return any(w in low for w in ("crystal", "obsidian", "bedrock", "totem", "pearl"))
    keys = [k for k in topic_keys(topic) if k != "minecraft"]
    if not keys:
        return True
    return any(k in low for k in keys)

def _compose_narration(script):
    parts = [script.get("hook", ""), script.get("interest", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    text = " ".join(p.strip() for p in parts if p and p.strip())
    return re.sub(r"\s+", " ", text).strip()

def _flowing_script(topic, focus, facts):
    short = focus if len(focus.split()) <= 5 else " ".join(focus.split()[:5])
    hook = f"Wait. This is {short}."
    hook_card = short[:28]
    if facts:
        interest = f"Stay for this. {facts[0]}"
        rest = facts[1:]
    else:
        interest = f"Stay. This whole Short is about {short}."
        rest = []
    links = ["Here's why.", "And this part matters.", "Then remember this.", "One more thing."]
    body = []
    for i, fact in enumerate(rest[:4]):
        body.append(f"{links[i % len(links)]} {fact}")
    if not body and facts:
        body = facts[1:3]
    ending = f"Follow if you want more {short}."
    return {
        "hook": hook,
        "hook_card": hook_card,
        "interest": interest,
        "body": body,
        "ending": ending,
        "title_seed": short,
        "provider": "flow",
    }

def _spoken(sentence):
    s = re.sub(r"\s+", " ", sentence).strip()
    s = re.sub(r"^(In Minecraft, |Minecraft |A true Minecraft |The Minecraft )", "", s)
    s = s.replace("A true ", "")
    if not s.endswith((".", "!", "?")):
        s += "."
    words = s.split()
    if len(words) > 24:
        s = " ".join(words[:24]).rstrip(",;:") + "."
    return s[0].upper() + s[1:] if s else s

def _plan_scenes(script, research):
    units = [("hook", script.get("hook", "")), ("interest", script.get("interest", ""))]
    for fact in script.get("body") or []:
        units.append(("fact", fact))
    units.append(("ending", script.get("ending", "")))
    units = [(k, t.strip()) for k, t in units if t and t.strip()]
    topic = research.get("topic") or ""
    lookups = minecraft_visuals(topic) if minecraft_topic(topic) else visual_lookups(topic)
    tokens = topic_keys(topic) or [clean_topic_query(topic).lower()]
    scenes = []
    for i, (kind, text) in enumerate(units):
        query = lookups[i % len(lookups)] if lookups else clean_topic_query(topic)
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
