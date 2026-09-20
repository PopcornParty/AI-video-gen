"""Write a Shorts script locked to the typed topic."""
from __future__ import annotations
import re
from .research import clean_topic_query, is_tips_topic, specific_tokens, topic_tokens, visual_lookups
from .utils import info, unique_keep_order

HOOK_WORDS = 10
INTEREST_WORDS = 24

_STOP = {
    "this", "that", "with", "from", "have", "most", "people", "about", "follow",
    "short", "facts", "true", "real", "want", "like", "more", "next", "stay",
    "wait", "stop", "swipe", "wrong", "think", "works", "coming", "loop",
    "missed", "first", "line", "reason", "actually", "what", "does", "don't",
    "video", "only", "every", "point", "here", "gets",
}

def generate_script(research, target_duration=32, language="en"):
    topic = research.get("topic") or "this topic"
    focus = clean_topic_query(topic)
    info(f"Script locked to: {focus}")
    facts = [_keep_on_topic(f, focus) for f in (research.get("facts") or [])]
    facts = [f for f in facts if _mentions_focus(f, focus, topic)]
    script = _structured_script(topic, focus, facts, target_duration)
    script["full_narration"] = _compose_narration(script)
    script["scenes"] = _plan_scenes(script, research)
    script["sources"] = research.get("sources") or []
    return script

def _mentions_focus(text, focus, topic):
    low = text.lower()
    needles = [focus.lower()] + [t.lower() for t in specific_tokens(topic)]
    needles = [n for n in needles if n]
    return any(n in low for n in needles)

def _keep_on_topic(sentence, focus):
    s = _tighten(sentence)
    if focus.lower() in s.lower():
        return s
    return f"On {focus}: {s}"

def _compose_narration(script):
    parts = [script.get("hook", ""), script.get("interest", "")] + list(script.get("body") or []) + [script.get("ending", "")]
    return re.sub(r"\s+", " ", " ".join(p.strip() for p in parts if p and p.strip())).strip()

def _structured_script(topic, focus, facts, target_duration):
    cleaned = unique_keep_order([_tighten(f) for f in facts if len(f) > 20])
    hook = _limit_words(f"This is {focus}. Not something else.", HOOK_WORDS)
    hook_card = _limit_words(focus, 6).rstrip(".")
    if is_tips_topic(topic):
        hook = _limit_words(f"{focus}. That's the only topic.", HOOK_WORDS)
    interest = _tighten(_limit_words(
        f"Stay if you want {focus}. Every line after this is {focus}.",
        INTEREST_WORDS,
    ))
    fact_budget = max(28, int(min(target_duration, 40) * 2.2) - len(hook.split()) - len(interest.split()) - 12)
    body = []
    used = 0
    for fact in cleaned:
        if fact.lower() in hook.lower() or fact.lower() in interest.lower():
            continue
        fact = _keep_on_topic(fact, focus)
        words = len(fact.split())
        if used + words > fact_budget:
            break
        body.append(fact)
        used += words
    if not body:
        body = [
            f"On {focus}: this Short does not switch subjects.",
            f"On {focus}: the details stay on that one request.",
        ]
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
    if len(words) > 28:
        s = " ".join(words[:28]).rstrip(",;:") + "."
    return s

def _content_words(text):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text) if w.lower() not in _STOP]

def _plan_scenes(script, research):
    units = [("hook", script.get("hook", "")), ("interest", script.get("interest", ""))]
    for fact in script.get("body") or []:
        units.append(("fact", fact))
    units.append(("ending", script.get("ending", "")))
    units = [(k, t.strip()) for k, t in units if t and t.strip()]
    topic = research.get("topic") or ""
    focus = clean_topic_query(topic)
    lookups = [focus] + list(research.get("visual_lookups") or visual_lookups(topic))
    used_queries = set()
    scenes = []
    for i, (kind, text) in enumerate(units):
        variants = _query_variants(kind, text, topic, lookups)
        query = variants[0]
        for item in variants:
            if item.lower() not in used_queries:
                query = item
                break
        used_queries.add(query.lower())
        match = unique_keep_order([w.lower() for w in (specific_tokens(topic) + topic_tokens(topic) + _content_words(text))])
        scenes.append({
            "index": i + 1,
            "text": text,
            "kind": kind,
            "hook_card": script.get("hook_card", "") if kind == "hook" else "",
            "search_query": query,
            "search_queries": variants,
            "match_tokens": match[:12],
        })
    return scenes

def _query_variants(kind, text, topic, lookups):
    subject = clean_topic_query(topic)
    nouns = _content_words(text)
    variants = [subject]
    if nouns:
        variants.append(f"{subject} {' '.join(nouns[:4])}")
    variants.extend(lookups[:8])
    cleaned = []
    for query in variants:
        query = re.sub(r"\s+", " ", query).strip()[:80]
        if query and query.lower() not in {v.lower() for v in cleaned}:
            cleaned.append(query)
    return cleaned or [topic]
