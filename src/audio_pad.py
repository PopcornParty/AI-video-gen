"""Pad narration so the finished Short matches the requested length."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .utils import info, warn

def pad_audio_to(audio_path: Path, dest: Path, target: float) -> Path:
    target = max(8.0, min(58.0, float(target)))
    current = _duration(audio_path)
    if current >= target - 0.15:
        return audio_path
    info(f"Padding voice from {current:.1f}s to {target:.1f}s")
    pad = target - current
    cmd = [
        "ffmpeg", "-y", "-i", str(audio_path),
        "-f", "lavfi", "-t", f"{pad:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex", "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];[1:a][a0]acrossfade=d=0.01[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(dest),
    ]
    if _run(cmd):
        return dest
    cmd = [
        "ffmpeg", "-y", "-i", str(audio_path),
        "-af", f"apad=pad_dur={pad:.3f}", "-t", f"{target:.3f}",
        "-c:a", "aac", "-b:a", "192k", str(dest),
    ]
    if _run(cmd):
        return dest
    warn("Could not pad audio; video will stay at voice length")
    return audio_path

def _duration(path: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True).strip()
    try:
        return float(out)
    except ValueError:
        return 0.0

def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0
