"""Royalty-free background music or generated ambient bed."""
from __future__ import annotations
import math
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Optional
from .utils import cache_path, info, project_root, warn

def get_music_track(cache_dir: Path, topic: str, duration: float, music_cfg: dict[str, Any]) -> Optional[Path]:
    if not music_cfg.get("enabled", True):
        info("Music disabled in config")
        return None
    folder = project_root() / "assets" / "music"
    if folder.exists():
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            files = [p for p in folder.glob(ext) if p.is_file() and p.stat().st_size > 10000]
            if files:
                info(f"Using local music: {files[0].name}")
                return sorted(files)[0]
    generated = _generate_ambient(cache_dir, duration)
    if generated:
        info("Using generated royalty-free ambient bed")
        return generated
    warn("No music track available")
    return None

def _generate_ambient(cache_dir: Path, duration: float) -> Optional[Path]:
    seconds = max(20, int(math.ceil(duration + 4)))
    wav_path = cache_path(cache_dir, "music", f"ambient-{seconds}", "wav")
    mp3_path = wav_path.with_suffix(".mp3")
    if mp3_path.exists() and mp3_path.stat().st_size > 5000:
        return mp3_path
    sr = 44100
    freqs = [261.63, 329.63, 392.00, 440.00]
    n = seconds * sr
    samples = []
    for i in range(n):
        t = i / sr
        val = 0.0
        for idx, f in enumerate(freqs):
            env = 0.5 + 0.5 * math.sin(2 * math.pi * (0.03 + idx * 0.007) * t)
            val += 0.12 * env * math.sin(2 * math.pi * f * t)
        val += 0.05 * math.sin(2 * math.pi * 55 * t)
        fade = min(1.0, t / 1.2, (seconds - t) / 1.2)
        sample = int(max(-1.0, min(1.0, val * fade)) * 30000)
        samples.append(struct.pack("<h", sample))
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"".join(samples))
    try:
        subprocess.run(["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "4", str(mp3_path)], check=True, capture_output=True)
        return mp3_path
    except Exception:
        return wav_path
