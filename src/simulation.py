"""Silent Minecraft-style simulations. No voice, no captions."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .utils import ensure_dir, info, save_text, warn

TYPES = {
    "crystal": "End Crystal pulse",
    "redstone": "Redstone circuit",
    "gravity": "Falling blocks",
    "portal": "Nether portal",
    "life": "Living blocks",
    "fire": "Fire spread",
    "rain": "Rain storm",
}

def simulation_types() -> list[str]:
    return list(TYPES.keys())

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path) -> Path:
    sim_type = (sim_type or "crystal").lower().strip()
    if sim_type not in TYPES:
        sim_type = "crystal"
    duration = max(8.0, min(58.0, float(duration or 34)))
    W = int(cfg["video"]["width"])
    H = int(cfg["video"]["height"])
    fps = int(cfg["video"]["fps"])
    ensure_dir(work_dir)
    ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Rendering {duration:.0f}s silent {sim_type} simulation")
    ok = _render(sim_type, duration, W, H, fps, raw)
    if not ok or not raw.exists():
        warn("Primary simulation filter failed, using fallback life grid")
        if not _life(duration, W, H, fps, raw, "20"):
            raise RuntimeError("Simulation render failed")
    final = out_root / "video.mp4"
    _mux_silent(raw, duration, final)
    _write_meta(sim_type, duration, out_root)
    if not final.exists() or final.stat().st_size < 10000:
        raise RuntimeError("Simulation file was not created")
    return final

def _render(sim_type, duration, W, H, fps, dest: Path) -> bool:
    if sim_type == "crystal":
        return _crystal(duration, W, H, fps, dest)
    if sim_type == "redstone":
        return _cell(duration, W, H, fps, dest, rule=30, hue=0)
    if sim_type == "gravity":
        return _gravity(duration, W, H, fps, dest)
    if sim_type == "portal":
        return _portal(duration, W, H, fps, dest)
    if sim_type == "life":
        return _life(duration, W, H, fps, dest, "35")
    if sim_type == "fire":
        return _fire(duration, W, H, fps, dest)
    if sim_type == "rain":
        return _rain(duration, W, H, fps, dest)
    return _life(duration, W, H, fps, dest, "20")

def _life(duration, W, H, fps, dest, hue):
    src = f"life=s={W}x{H}:rate={fps}:ratio=0.14:mold=8,hue=h={hue}:s=2,eq=contrast=1.15:brightness=-0.05,format=yuv420p"
    return _run(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)])

def _cell(duration, W, H, fps, dest, rule, hue):
    src = f"cellauto=s={W}x{H}:rate={fps}:rule={rule},hue=h={hue}:s=2.2,eq=contrast=1.2,format=yuv420p"
    return _run(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)])

def _crystal(duration, W, H, fps, dest):
    expr = (
        f"geq=r='80+175*exp(-hypot(X-{W}/2\,Y-{H}/2)/((40+120*mod(T\,2.4))^2))':"
        f"g='30+140*exp(-hypot(X-{W}/2\,Y-{H}/2)/((40+120*mod(T\,2.4))^2))':"
        f"b='20+40*exp(-hypot(X-{W}/2\,Y-{H}/2)/((40+120*mod(T\,2.4))^2))':"
        f"s={W}x{H}:rate={fps},format=yuv420p"
    )
    if _run(["ffmpeg", "-y", "-f", "lavfi", "-i", expr, "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)]):
        return True
    return _life(duration, W, H, fps, dest, "20")

def _portal(duration, W, H, fps, dest):
    src = f"cellauto=s={W}x{H}:rate={fps}:rule=110,hue=h='120+40*sin(2*PI*t/3)':s=2.4,eq=saturation=2,format=yuv420p"
    return _run(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)])

def _fire(duration, W, H, fps, dest):
    src = f"life=s={W}x{H}:rate={fps}:ratio=0.2:mold=15,hue=h=10:s=3,eq=contrast=1.3:brightness=0.02,format=yuv420p"
    return _run(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)])

def _gravity(duration, W, H, fps, dest):
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x1a140f:s={W}x{H}:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0x6b4f2a:s=160x90:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0x3f3f3f:s=140x140:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0x2f5d2a:s=180x80:d={duration:.3f}:r={fps}",
        "-filter_complex",
        "[0][1]overlay=x=180:y='mod(t*280,H+90)-90'[a];"
        "[a][2]overlay=x=520:y='mod(t*210+200,H+140)-140'[b];"
        "[b][3]overlay=x=780:y='mod(t*330+80,H+80)-80',format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest),
    ]
    return _run(cmd)

def _rain(duration, W, H, fps, dest):
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x0b1020:s={W}x{H}:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0xc8d8ff:s=4x70:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0xa0b8e8:s=3x90:d={duration:.3f}:r={fps}",
        "-f", "lavfi", "-i", f"color=c=0xd0e0ff:s=3x60:d={duration:.3f}:r={fps}",
        "-filter_complex",
        "[0][1]overlay=x=220:y='mod(t*520,H+70)-70'[a];"
        "[a][2]overlay=x=500:y='mod(t*640+120,H+90)-90'[b];"
        "[b][3]overlay=x=840:y='mod(t*480+300,H+60)-60',format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest),
    ]
    return _run(cmd)

def _mux_silent(video: Path, duration: float, dest: Path):
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest),
    ]
    if _run(cmd):
        return
    if not _run(["ffmpeg", "-y", "-i", str(video), "-an", "-c:v", "copy", "-movflags", "+faststart", str(dest)]):
        raise RuntimeError("Could not write silent simulation file")

def _write_meta(sim_type, duration, out_root: Path):
    title = f"Minecraft {TYPES[sim_type]} simulation"
    desc = f"Silent {TYPES[sim_type]} simulation. No voice. No captions.\n"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", desc + "\n#Shorts #Minecraft #simulation\n")
    save_text(out_root / "hashtags.txt", "#Shorts #Minecraft #simulation\n")
    save_text(out_root / "tags.txt", "minecraft,simulation,shorts,silent\n")
    save_text(out_root / "youtube-title.txt", title + "\n")
    save_text(out_root / "youtube-description.txt", desc + "\n#Shorts #Minecraft #simulation\n")
    save_text(out_root / "youtube-hashtags.txt", "#Shorts #Minecraft #simulation\n")

def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        warn("ffmpeg: " + (proc.stderr or "")[-400:].strip())
        return False
    return True
