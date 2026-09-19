"""Turn narration timestamps + visuals into a timed scene list."""
from __future__ import annotations
import re
from typing import Any

def build_timed_scenes(scenes, words, audio_duration, target_duration):
    timed = _split_by_words(scenes, words, audio_duration) if words else _split_evenly(scenes, audio_duration)
    if timed:
        timed[-1]["end"] = max(timed[-1]["end"], audio_duration)
        timed[0]["start"] = 0.0
    for i, scene in enumerate(timed):
        if i > 0:
            scene["start"] = timed[i - 1]["end"]
        scene["duration"] = max(0.7, scene["end"] - scene["start"])
        scene["end"] = scene["start"] + scene["duration"]
    return timed

def _split_by_words(scenes, words, audio_duration):
    cursor = 0
    timed = []
    for i, scene in enumerate(scenes):
        tokens = _tokens(scene.get("text", ""))
        if not tokens:
            continue
        start = words[min(cursor, len(words) - 1)]["start"] if words else 0.0
        matched = 0
        last_end = start
        j = cursor
        while j < len(words) and matched < len(tokens):
            wt = _norm(words[j]["text"])
            tt = _norm(tokens[matched])
            last_end = words[j]["end"]
            j += 1
            if not wt:
                continue
            if wt == tt or wt in tt or tt in wt:
                matched += 1
        if matched == 0:
            remain_scenes = max(1, len(scenes) - i)
            remain_time = max(0.8, audio_duration - start)
            last_end = start + remain_time / remain_scenes
            j = min(len(words), cursor + max(1, len(tokens)))
        cursor = j
        item = dict(scene)
        item["start"] = float(start)
        item["end"] = float(min(audio_duration, max(start + 0.7, last_end)))
        timed.append(item)
    return timed or _split_evenly(scenes, audio_duration)

def _split_evenly(scenes, audio_duration):
    n = max(1, len(scenes))
    slice_len = audio_duration / n
    timed = []
    t = 0.0
    for scene in scenes:
        item = dict(scene)
        item["start"] = t
        item["end"] = t + slice_len
        timed.append(item)
        t += slice_len
    return timed

def _tokens(text):
    return [t for t in re.findall(r"[A-Za-z0-9']+", text) if t]

def _norm(token):
    return re.sub(r"[^a-z0-9']", "", token.lower())
