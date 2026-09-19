"""Assemble 9:16 Shorts with FFmpeg. No paid services."""
from __future__ import annotations
import subprocess
from pathlib import Path
from PIL import Image
from .utils import info, warn

def render_short(scenes, audio_path, caption_groups, music_path, output_path: Path, cfg, work_dir: Path) -> Path:
    video_cfg = cfg["video"]
    cap_cfg = cfg["captions"]
    music_cfg = cfg["music"]
    W, H = int(video_cfg["width"]), int(video_cfg["height"])
    fps = int(video_cfg["fps"])
    work_dir.mkdir(parents=True, exist_ok=True)
    duration = _media_duration(audio_path)
    if duration < 1:
        raise RuntimeError("Narration audio is empty")
    scene_files = []
    for i, scene in enumerate(scenes):
        dest = work_dir / f"scene_{i:02d}.mp4"
        info(f"Rendering scene {i + 1}/{len(scenes)}")
        _render_scene(scene, dest, W, H, fps)
        scene_files.append(dest)
    concat_path = work_dir / "visuals.mp4"
    _ffmpeg_concat(scene_files, concat_path, fps)
    visuals_fit = work_dir / "visuals_fit.mp4"
    _fit_length(concat_path, visuals_fit, duration, fps)
    captioned = work_dir / "captioned.mp4"
    hook_card = ""
    for scene in scenes:
        if scene.get("kind") == "hook" and scene.get("hook_card"):
            hook_card = scene["hook_card"]
            break
    if cap_cfg.get("enabled", True) and (caption_groups or hook_card):
        info("Burning captions")
        ass_path = work_dir / "captions.ass"
        _write_ass(caption_groups, ass_path, W, H, cap_cfg, hook_card)
        _burn_subtitles(visuals_fit, ass_path, captioned)
        if not captioned.exists():
            captioned = visuals_fit
    else:
        captioned = visuals_fit
    mixed_audio = work_dir / "mixed.m4a"
    _mix_audio(audio_path, music_path, mixed_audio, duration, music_cfg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    info(f"Muxing final {W}x{H} @ {fps}fps")
    _mux(captioned, mixed_audio, output_path)
    if not output_path.exists() or output_path.stat().st_size < 10000:
        raise RuntimeError("Final MP4 was not created")
    return output_path

def _media_duration(path: str) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], text=True).strip()
    return float(out)

def _render_scene(scene, dest: Path, W, H, fps):
    duration = max(0.7, float(scene.get("duration") or (scene["end"] - scene["start"])))
    visual = scene.get("visual") or {}
    path = visual.get("path")
    kind = (visual.get("kind") or "").lower()
    if path and Path(path).exists():
        suffix = Path(path).suffix.lower()
        if kind == "video" or suffix in {".mp4", ".webm", ".mov", ".mkv", ".ogv"}:
            if _render_clip(path, dest, W, H, fps, duration):
                return
        if _cover_still(path, dest, W, H, fps, duration, int(scene.get("index") or 0)):
            return
    _generated_scene(dest, W, H, fps, duration, int(scene.get("index") or 0))

def _natural_vf(W, H):
    return (
        f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={W}:{H},"
        f"eq=contrast=1.02:saturation=0.97:brightness=0.01,"
        f"noise=alls=3:allf=t+u,"
        f"format=yuv420p"
    )

def _render_clip(src, dest, W, H, fps, duration):
    vf = _natural_vf(W, H)
    cmd = [
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{duration:.3f}", "-vf", vf, "-an",
        "-r", str(fps), "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", str(dest),
    ]
    return _run(cmd) and dest.exists()

def _cover_still(src, dest, W, H, fps, duration, index):
    z0 = 1.0
    z1 = 1.04 if index % 2 == 0 else 1.03
    frames = max(1, int(duration * fps))
    vf = (
        f"scale=2160:-2:flags=lanczos,"
        f"zoompan=z='{z0}+({z1}-{z0})*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},"
        f"eq=contrast=1.02:saturation=0.97:brightness=0.01,"
        f"noise=alls=3:allf=t+u"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(src),
        "-t", f"{duration:.3f}", "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", str(dest),
    ]
    return _run(cmd) and dest.exists()

def _generated_scene(dest, W, H, fps, duration, index):
    palettes = [("#101418", "#2a3540"), ("#16120f", "#3a322c"), ("#101614", "#2c3a34")]
    c1, c2 = palettes[index % len(palettes)]
    img_path = dest.with_suffix(".png")
    _write_gradient(img_path, W, H, c1, c2)
    if not _cover_still(str(img_path), dest, W, H, fps, duration, index):
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(img_path), "-t", f"{duration:.3f}", "-vf", f"scale={W}:{H}", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dest)]
        if not _run(cmd):
            raise RuntimeError("Could not create fallback scene")

def _write_gradient(path: Path, W, H, c1, c2):
    def hx(v):
        v = v.lstrip("#")
        return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))
    a, b = hx(c1), hx(c2)
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / max(H - 1, 1)
        rgb = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = rgb
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")

def _ffmpeg_concat(files, dest, fps):
    lst = dest.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{f.resolve().as_posix()}'" for f in files) + "\n", encoding="utf-8")
    if _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dest)]):
        return
    if not _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), str(dest)]):
        raise RuntimeError("FFmpeg concat failed")

def _fit_length(src, dest, duration, fps):
    if not _run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src), "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), str(dest)]):
        raise RuntimeError("Could not fit video length to narration")

def _write_ass(groups, path, W, H, cap_cfg, hook_card=""):
    size = int(cap_cfg.get("font_size", 68))
    hook_size = max(72, size + 10)
    header = f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Lato,{size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,70,70,{int(H * 0.28)},1\nStyle: Hook,Lato,{hook_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,0,8,50,50,{int(H * 0.16)},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    events = []
    if hook_card:
        events.append(f"Dialogue: 1,0:00:00.00,0:00:02.80,Hook,,0,0,0,,{_ass_escape(hook_card)}")
    for g in groups or []:
        text = _ass_escape(g.get("text") or "")
        events.append(f"Dialogue: 0,{_ass_time(g['start'])},{_ass_time(g['end'])},Default,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def _ass_escape(text):
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")

def _ass_time(seconds):
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def _burn_subtitles(video, ass_path, dest):
    fonts = "/usr/share/fonts/truetype/lato"
    filt = f"ass={ass_path.resolve().as_posix()}:fontsdir={fonts}"
    if not _run(["ffmpeg", "-y", "-i", str(video), "-vf", filt, "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(dest)]):
        warn("Caption burn failed, exporting without captions")
        subprocess.run(["cp", str(video), str(dest)], check=False)

def _mix_audio(narration, music_path, dest, duration, music_cfg):
    if music_path and Path(music_path).exists() and music_cfg.get("enabled", True):
        vol = float(music_cfg.get("duck_volume", 0.07))
        cmd = ["ffmpeg", "-y", "-i", narration, "-stream_loop", "-1", "-i", str(music_path), "-t", f"{duration:.3f}", "-filter_complex", f"[1:a]volume={vol}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]", "-map", "[a]", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(dest)]
        if _run(cmd):
            return
        warn("Music mix failed, using narration only")
    if not _run(["ffmpeg", "-y", "-i", narration, "-t", f"{duration:.3f}", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(dest)]):
        raise RuntimeError("Could not encode narration audio")

def _mux(video, audio, dest):
    if _run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dest)]):
        return
    if not _run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest)]):
        raise RuntimeError("Final mux failed")

def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        warn("ffmpeg: " + (proc.stderr or "")[-400:].strip())
        return False
    return True
