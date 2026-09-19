"""Natural TTS via Microsoft Edge (free, no key) with gTTS fallback."""
from __future__ import annotations
import asyncio
import re
from pathlib import Path
from typing import Any
from .utils import cache_path, info, save_json, warn

def generate_voice(text, cache_dir: Path, voice_cfg: dict[str, Any], work_dir: Path):
    spoken = _humanize_script(text)
    provider = (voice_cfg.get("provider") or "edge").lower()
    fallback = (voice_cfg.get("fallback_provider") or "gtts").lower()
    last_error = None
    for name in (provider, fallback, "edge", "gtts"):
        try:
            if name == "edge":
                result = _edge_tts(spoken, cache_dir, voice_cfg)
            elif name == "gtts":
                result = _gtts(spoken, cache_dir, voice_cfg)
            else:
                continue
            if result and Path(result["audio_path"]).exists():
                info(f"Voice generated with {name}")
                return result
        except Exception as exc:
            last_error = exc
            warn(f"{name} voice failed: {exc}")
    raise RuntimeError(f"All voice providers failed: {last_error}")

def _humanize_script(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" — ", ", ").replace(" – ", ", ")
    text = re.sub(r"\s*\.\s*", ". ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i > 0 and len(part.split()) > 8:
            out.append(part)
        else:
            out.append(part)
    spoken = " ".join(out)
    spoken = spoken.replace("...", ".")
    return spoken

def _edge_tts(text, cache_dir, voice_cfg):
    import edge_tts
    voice = voice_cfg.get("voice") or "en-US-AndrewNeural"
    rate = voice_cfg.get("rate") or "-6%"
    pitch = voice_cfg.get("pitch") or "-1Hz"
    audio_path = cache_path(cache_dir, "audio", f"edge:{voice}:{rate}:{pitch}:{text}", "mp3")
    words_path = audio_path.with_suffix(".words.json")
    if audio_path.exists() and words_path.exists() and audio_path.stat().st_size > 2000:
        from .utils import load_json
        return {"audio_path": str(audio_path), "words": load_json(words_path, []), "provider": "edge"}
    async def _run():
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch, boundary="WordBoundary")
        words = []
        with audio_path.open("wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 10_000_000
                    dur = chunk["duration"] / 10_000_000
                    words.append({"text": chunk.get("text", ""), "start": round(start, 3), "end": round(start + dur, 3)})
        return words
    words = asyncio.run(_run())
    if not audio_path.exists() or audio_path.stat().st_size < 1000:
        raise RuntimeError("edge-tts produced no audio")
    save_json(words_path, words)
    return {"audio_path": str(audio_path), "words": words, "provider": "edge"}

def _gtts(text, cache_dir, voice_cfg):
    from gtts import gTTS
    lang = voice_cfg.get("fallback_voice") or "en"
    audio_path = cache_path(cache_dir, "audio", f"gtts:{lang}:{text}", "mp3")
    if not audio_path.exists() or audio_path.stat().st_size < 1000:
        gTTS(text=text, lang=lang, slow=False).save(str(audio_path))
    words = _estimate_words(text, _probe_duration(audio_path))
    return {"audio_path": str(audio_path), "words": words, "provider": "gtts"}

def _probe_duration(path: Path) -> float:
    import subprocess
    try:
        out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True).strip()
        return float(out)
    except Exception:
        return max(2.0, path.stat().st_size / 16000)

def _estimate_words(text, duration):
    tokens = [t for t in text.replace("\n", " ").split(" ") if t]
    if not tokens:
        return []
    step = duration / len(tokens)
    words = []
    t = 0.0
    for tok in tokens:
        words.append({"text": tok, "start": round(t, 3), "end": round(t + step, 3)})
        t += step
    return words
