"""Write a Shorts script: 3s hook, 10s interest, then facts."""
from __future__ import annotations
import re
from .research import clean_topic_query, is_tips_topic, specific_tokens, visual_lookups
from .utils import info, unique_keep_order

HOOK_WORDS = 8
INTEREST_WORDS = 24

def generate_script(research, target_duration=32, language="en"):
    facts = research.get("facts") or []
    topic = research.get("topic") or "this topic"
    info("Script: 3s hook, 10s interest, then facts")
    script = _structured_script(topic, facts, target_duration)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _compose_narration(script):
    parts = [script.get("hook", ""), script.get("interest", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts if p and p.strip())).strip()

def _focus_label(topic):
    specific = specific_tokens(topic)
    return " ".join(specific) if specific else clean_topic_query(topic)

def _structured_script(topic, facts, target_duration):
    label = _focus_label(topic)
    cleaned = unique_keep_order([_tighten(f) for f in facts if len(f) > 30])
    hook, hook_card = _make_hook(topic, label, cleaned)
    interest = _make_interest(topic, label, cleaned)
    fact_budget = max(28, int(min(target_duration, 40) * 2.2) - len(hook.split()) - len(interest.split()) - 12)
    body = []
    used = 0
    for fact in cleaned:
        if fact.lower() in hook.lower() or fact.lower() in interest.lower():
            continue
        if any(w in fact.lower() for w in ("developed by", "published by", "founded by", "released in", "headquarters")):
            continue
        words = len(fact.split())
        if used + words > fact_budget:
            break
        body.append(fact)
        used += words
    if not body:
        body = [f"Here is the part that actually matters about {label}."]
        if cleaned:
            body.append(cleaned[0])
    ending = _make_ending(label, hook)
    return {
        "hook": hook,
        "hook_card": hook_card,
        "interest": interest,
        "body": body,
        "ending": ending,
        "title_seed": label,
        "provider": "hook-interest-facts",
    }

def _make_hook(topic, label, facts):
    """First ~2-3 seconds. Pattern interrupt + curiosity. Spoken + on-screen."""
    short_label = label if len(label.split()) <= 4 else " ".join(label.split()[:4])
    formulas = [
        (f"Wait. {short_label} is not what you think.", f"Wait. {short_label}."),
        (f"Stop. This is the real {short_label} part.", f"The real {short_label}"),
        (f"Why does {short_label} actually work like this?", f"Why {short_label}?"),
        (f"Don't swipe. {short_label} gets weird next.", f"Don't swipe."),
    ]
    if is_tips_topic(topic):
        formulas.insert(0, (f"You're doing {short_label} wrong.", f"Wrong {short_label}?"))
    if facts:
        snippet = " ".join(facts[0].split()[:6]).rstrip(",;:.")
        formulas.insert(0, (f"{snippet}. That's the trap.", snippet))
    idx = abs(hash(topic.lower())) % len(formulas)
    hook, card = formulas[idx]
    return _limit_words(hook, HOOK_WORDS), _limit_words(card, 5).rstrip(".")

def _make_interest(topic, label, facts):
    tease = ""
    if facts:
        tease = " ".join(facts[0].split()[:10]).rstrip(",;:")
    line = f"Stay. The reason {label} works is coming. {tease}."
    return _tighten(_limit_words(line, INTEREST_WORDS))

def _make_ending(label, hook):
    return f"Follow for more {label}. Loop it if you missed the first line."

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
    if len(words) > 28:
        s = " ".join(words[:28]).rstrip(",;:") + "."
    return s

def _plan_scenes(script, research):
    units = [("hook", script.get("hook", "")), ("interest", script.get("interest", ""))]
    for fact in script.get("body") or []:
        units.append(("fact", fact))
    units.append(("ending", script.get("ending", "")))
    units = [(k, t.strip()) for k, t in units if t and t.strip()]
    topic = research.get("topic") or ""
    lookups = research.get("visual_lookups") or visual_lookups(topic)
    used_queries = set()
    scenes = []
    for i, (kind, text) in enumerate(units):
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
            "kind": kind,
            "hook_card": script.get("hook_card", "") if kind == "hook" else "",
            "search_query": query,
            "search_queries": variants,
        })
    return scenes

_STOP = {
    "this", "that", "with", "from", "have", "most", "people", "about", "follow",
    "short", "facts", "true", "real", "want", "like", "more", "next", "stay",
    "wait", "stop", "swipe", "wrong", "think", "works", "coming", "loop",
}

def _query_variants(text, topic, lookups, index):
    subject = _focus_label(topic)
    variants = []
    if lookups:
        variants.append(lookups[index % len(lookups)])
        variants.extend(lookups)
    sentence_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text) if w.lower() not in _STOP]
    if sentence_words:
        variants.insert(0, " ".join(sentence_words[:6]))
        variants.append(f"{subject} {' '.join(sentence_words[:4])}")
    variants.append(subject)
    cleaned = []
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()[:80]
        if query and query.lower() not in {v.lower() for v in cleaned}:
            cleaned.append(query)
    return cleaned or [topic]
