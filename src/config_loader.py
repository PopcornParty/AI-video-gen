"""Load config.json + .env settings."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from .utils import project_root, warn

def load_env() -> None:
    load_dotenv(project_root() / ".env")

def load_config(path: Path | None = None) -> dict[str, Any]:
    load_env()
    cfg_path = path or (project_root() / "config.json")
    if not cfg_path.exists():
        warn("config.json missing, using defaults")
        data: dict[str, Any] = {}
    else:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    return _with_defaults(data)

def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()

def _with_defaults(data: dict[str, Any]) -> dict[str, Any]:
    video = data.setdefault("video", {})
    video.setdefault("width", 1080)
    video.setdefault("height", 1920)
    video.setdefault("fps", 30)
    video.setdefault("target_duration", 45)
    video.setdefault("min_duration", 21)
    video.setdefault("max_duration", 58)
    video.setdefault("bitrate", "8M")
    video.setdefault("codec", "libx264")
    video.setdefault("audio_codec", "aac")
    video.setdefault("preset", "medium")
    voice = data.setdefault("voice", {})
    voice.setdefault("provider", "edge")
    voice.setdefault("voice", "en-US-AndrewNeural")
    voice.setdefault("rate", "+8%")
    voice.setdefault("pitch", "+0Hz")
    voice.setdefault("fallback_provider", "gtts")
    voice.setdefault("fallback_voice", "en")
    music = data.setdefault("music", {})
    music.setdefault("enabled", True)
    music.setdefault("volume", 0.11)
    music.setdefault("duck_volume", 0.07)
    captions = data.setdefault("captions", {})
    captions.setdefault("enabled", True)
    captions.setdefault("style", "modern")
    captions.setdefault("font_name", "Lato-Bold.ttf")
    captions.setdefault("font_size", 68)
    captions.setdefault("color", "#FFFFFF")
    captions.setdefault("highlight_color", "#FFD60A")
    captions.setdefault("stroke_color", "#000000")
    captions.setdefault("stroke_width", 4)
    captions.setdefault("max_words_per_line", 5)
    captions.setdefault("position", "center")
    visuals = data.setdefault("visuals", {})
    visuals.setdefault("prefer_video", True)
    visuals.setdefault("max_per_provider", 8)
    visuals.setdefault("quality", "high")
    visuals.setdefault("allow_images", True)
    visuals.setdefault("ken_burns", True)
    scenes = data.setdefault("scenes", {})
    scenes.setdefault("min_count", 4)
    scenes.setdefault("max_count", 8)
    data.setdefault("language", "en")
    data.setdefault("output_folder", "output")
    data.setdefault("cache_folder", "cache")
    data.setdefault("cleanup_temp", True)
    return data
