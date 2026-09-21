"""Background music plus a click each time the ball hits a wall."""
from __future__ import annotations
import math
import struct
import subprocess
import wave
from pathlib import Path

def mix_sim_audio(video: Path, dest: Path, duration: float, hit_times: list[float], W: int, H: int, work_dir: Path) -> None:
    music = work_dir / "sim_music.wav"
    clicks = work_dir / "sim_clicks.wav"
    _tone_bed(music, duration)
    _click_track(clicks, duration, hit_times)
    cmd = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(music), "-i", str(clicks),
        "-filter_complex",
        f"[0:v]scale={W}:{H}:flags=lanczos[v];[1:a]volume=0.16[m];[2:a]volume=0.55[c];[m][c]amix=inputs=2:duration=longest[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        raise RuntimeError("Could not mix simulation audio")

def _tone_bed(path: Path, duration: float):
    sr = 22050
    n = int(duration * sr)
    freqs = (196.0, 247.0, 294.0)
    samples = bytearray()
    for i in range(n):
        t = i / sr
        val = 0.0
        for f in freqs:
            val += 0.18 * math.sin(2 * math.pi * f * t)
        fade = min(1.0, t / 0.4, max(0.0, (duration - t) / 0.6))
        samples += struct.pack("<h", int(max(-1, min(1, val * fade)) * 9000))
    _write_wav(path, sr, samples)

def _click_track(path: Path, duration: float, hits: list[float]):
    sr = 22050
    n = int(duration * sr)
    buf = [0] * n
    span = int(0.045 * sr)
    for t in hits[:160]:
        start = int(t * sr)
        for k in range(span):
            i = start + k
            if 0 <= i < n:
                env = math.exp(-k / 140)
                buf[i] += int(20000 * env * math.sin(2 * math.pi * 980 * k / sr))
    samples = bytearray()
    for v in buf:
        samples += struct.pack("<h", max(-32767, min(32767, v)))
    _write_wav(path, sr, samples)

def _write_wav(path: Path, sr: int, samples: bytearray):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples)
