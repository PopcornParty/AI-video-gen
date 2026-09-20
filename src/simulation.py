"""Silent satisfying physics Shorts. No voice. No captions."""
from __future__ import annotations
import math
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw
from .utils import ensure_dir, info, save_text, warn

TYPES = {
    "grow-bounce": "Ball grows every time it hits the circle",
    "shrink-arena": "Circle shrinks every bounce",
    "grow-and-shrink": "Ball grows and the circle closes in",
    "split": "Every bounce splits the ball until the circle is full",
    "color-race": "Two colors bounce and grow — which fills first",
    "spinning-square": "Ball trapped in a spinning square",
    "spinning-hex": "Ball trapped in a spinning hexagon",
    "rings": "Ball escapes rotating rings through gaps",
    "collide-spawn": "Each collision spawns another ball",
    "plinko": "Balls fall through pegs",
}

def simulation_types() -> list[str]:
    return list(TYPES.keys())

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    r: float
    color: tuple
    trail: list = field(default_factory=list)

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path) -> Path:
    sim_type = (sim_type or "grow-bounce").lower().strip()
    if sim_type not in TYPES:
        sim_type = "grow-bounce"
    duration = max(10.0, min(58.0, float(duration or 34)))
    W = 540
    H = 960
    fps = 30
    ensure_dir(work_dir)
    ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Rendering {duration:.0f}s silent {sim_type} physics sim")
    if not _render_frames(sim_type, duration, W, H, fps, raw):
        raise RuntimeError("Simulation render failed")
    final = out_root / "video.mp4"
    _scale_and_silence(raw, duration, int(cfg["video"]["width"]), int(cfg["video"]["height"]), final)
    _write_meta(sim_type, duration, out_root)
    if not final.exists() or final.stat().st_size < 10000:
        raise RuntimeError("Simulation file was not created")
    return final

def _render_frames(sim_type, duration, W, H, fps, dest: Path) -> bool:
    frames = int(duration * fps)
    sim = _make_sim(sim_type, W, H)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-pix_fmt", "yuv420p", str(dest),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for _ in range(frames):
            img = sim()
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        proc.wait(timeout=120)
        return proc.returncode == 0 and dest.exists()
    except Exception as exc:
        warn(str(exc))
        try:
            proc.kill()
        except Exception:
            pass
        return False

def _make_sim(sim_type: str, W: int, H: int) -> Callable[[], Image.Image]:
    makers = {
        "grow-bounce": _sim_grow,
        "shrink-arena": _sim_shrink,
        "grow-and-shrink": _sim_both,
        "split": _sim_split,
        "color-race": _sim_race,
        "spinning-square": _sim_spin_poly,
        "spinning-hex": lambda w, h: _sim_spin_poly(w, h, sides=6),
        "rings": _sim_rings,
        "collide-spawn": _sim_collide,
        "plinko": _sim_plinko,
    }
    return makers.get(sim_type, _sim_grow)(W, H)

def _bg(W, H, color=(8, 8, 14)):
    return Image.new("RGB", (W, H), color)

def _draw_glow(draw, x, y, r, color, glow=18):
    for i, a in ((int(r + glow), 28), (int(r + glow * 0.5), 70)):
        if i <= 0:
            continue
        c = tuple(min(255, int(ch + (255 - ch) * 0.15)) for ch in color)
        draw.ellipse((x - i, y - i, x + i, y + i), outline=c, width=2)
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

def _bounce_circle(ball: Ball, cx, cy, R):
    dx, dy = ball.x - cx, ball.y - cy
    dist = math.hypot(dx, dy) or 0.001
    if dist + ball.r >= R:
        nx, ny = dx / dist, dy / dist
        ball.x = cx + nx * (R - ball.r - 0.5)
        ball.y = cy + ny * (R - ball.r - 0.5)
        dot = ball.vx * nx + ball.vy * ny
        ball.vx -= 2 * dot * nx
        ball.vy -= 2 * dot * ny
        return True
    return False

def _step_free(ball: Ball):
    ball.x += ball.vx
    ball.y += ball.vy
    ball.trail.append((ball.x, ball.y))
    if len(ball.trail) > 28:
        ball.trail.pop(0)

def _draw_trails(draw, balls):
    for ball in balls:
        for i, (tx, ty) in enumerate(ball.trail):
            rr = max(1, int(ball.r * (i + 1) / (len(ball.trail) + 3)))
            col = tuple(int(c * (0.25 + 0.75 * i / max(1, len(ball.trail)))) for c in ball.color)
            draw.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), fill=col)

def _sim_grow(W, H):
    cx, cy, R = W / 2, H / 2, min(W, H) * 0.38
    ball = Ball(cx, cy + 40, 6.2, -5.1, 14, (80, 220, 255))
    def frame():
        hit = False
        _step_free(ball)
        if _bounce_circle(ball, cx, cy, R):
            hit = True
            ball.r = min(R - 4, ball.r * 1.045 + 0.6)
            ball.vx *= 1.01
            ball.vy *= 1.01
            if ball.r >= R - 5:
                ball.r = 12
                ball.x, ball.y = cx, cy + 30
                ball.vx, ball.vy = 6.4, -5.0
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(70, 80, 120), width=4)
        _draw_trails(d, [ball])
        _draw_glow(d, ball.x, ball.y, ball.r, ball.color, 16 if hit else 10)
        return img
    return frame

def _sim_shrink(W, H):
    cx, cy = W / 2, H / 2
    R = [min(W, H) * 0.40]
    ball = Ball(cx - 20, cy, 7.0, 4.8, 16, (255, 190, 70))
    def frame():
        _step_free(ball)
        if _bounce_circle(ball, cx, cy, R[0]):
            R[0] = max(ball.r + 8, R[0] * 0.985)
            if R[0] <= ball.r + 9:
                R[0] = min(W, H) * 0.40
                ball.x, ball.y = cx - 20, cy
                ball.vx, ball.vy = 7.0, 4.8
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R[0], cy - R[0], cx + R[0], cy + R[0]), outline=(255, 160, 60), width=4)
        _draw_trails(d, [ball])
        _draw_glow(d, ball.x, ball.y, ball.r, ball.color)
        return img
    return frame

def _sim_both(W, H):
    cx, cy = W / 2, H / 2
    R = [min(W, H) * 0.41]
    ball = Ball(cx + 10, cy - 30, 5.6, 6.4, 12, (255, 90, 160))
    def frame():
        _step_free(ball)
        if _bounce_circle(ball, cx, cy, R[0]):
            ball.r = min(R[0] - 6, ball.r + 1.1)
            R[0] = max(ball.r + 7, R[0] * 0.992)
            if R[0] <= ball.r + 8:
                R[0] = min(W, H) * 0.41
                ball.r = 12
                ball.x, ball.y = cx + 10, cy - 30
                ball.vx, ball.vy = 5.6, 6.4
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R[0], cy - R[0], cx + R[0], cy + R[0]), outline=(255, 80, 150), width=4)
        _draw_trails(d, [ball])
        _draw_glow(d, ball.x, ball.y, ball.r, ball.color)
        return img
    return frame

def _sim_split(W, H):
    cx, cy, R = W / 2, H / 2, min(W, H) * 0.38
    balls = [Ball(cx, cy, 5.5, -4.8, 11, (120, 255, 170))]
    def frame():
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(80, 160, 110), width=4)
        spawned = []
        for ball in balls:
            _step_free(ball)
            if _bounce_circle(ball, cx, cy, R) and len(balls) + len(spawned) < 18:
                ang = random.uniform(0, 6.28)
                spawned.append(Ball(ball.x, ball.y, 4.2 * math.cos(ang), 4.2 * math.sin(ang), max(7, ball.r * 0.78), ball.color))
                ball.r = max(7, ball.r * 0.78)
            _draw_glow(d, ball.x, ball.y, ball.r, ball.color, 8)
        balls.extend(spawned)
        if len(balls) >= 18:
            balls[:] = [Ball(cx, cy, 5.5, -4.8, 11, (120, 255, 170))]
        return img
    return frame

def _sim_race(W, H):
    cx, cy, R = W / 2, H / 2, min(W, H) * 0.38
    balls = [
        Ball(cx - 25, cy, 5.8, 4.2, 13, (70, 160, 255)),
        Ball(cx + 25, cy, -4.4, 5.9, 13, (255, 90, 90)),
    ]
    def frame():
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(180, 180, 200), width=4)
        for ball in balls:
            _step_free(ball)
            if _bounce_circle(ball, cx, cy, R):
                ball.r = min(R - 6, ball.r + 0.9)
            if ball.r >= R - 7:
                balls[0].r = balls[1].r = 13
                balls[0].x, balls[0].y = cx - 25, cy
                balls[1].x, balls[1].y = cx + 25, cy
            _draw_trails(d, [ball])
            _draw_glow(d, ball.x, ball.y, ball.r, ball.color, 10)
        return img
    return frame

def _sim_spin_poly(W, H, sides=4):
    cx, cy = W / 2, H / 2
    radius = min(W, H) * 0.36
    ang = [0.0]
    ball = Ball(cx, cy, 5.4, 3.6, 16, (255, 210, 80))
    def frame():
        ang[0] += 0.028
        ball.x += ball.vx
        ball.y += ball.vy
        pts = []
        for i in range(sides):
            a = ang[0] + i * 2 * math.pi / sides
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
        for i in range(sides):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % sides]
            if _bounce_segment(ball, x1, y1, x2, y2):
                ball.r = min(42, ball.r + 0.35)
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.polygon(pts, outline=(220, 220, 240), width=4)
        _draw_glow(d, ball.x, ball.y, ball.r, ball.color)
        return img
    return frame

def _bounce_segment(ball: Ball, x1, y1, x2, y2):
    sx, sy = x2 - x1, y2 - y1
    sl = math.hypot(sx, sy) or 1
    nx, ny = -sy / sl, sx / sl
    if (ball.x - cx_fix(x1, x2)) * nx + (ball.y - cy_fix(y1, y2)) * ny > 0:
        nx, ny = -nx, -ny
    px, py = ball.x - x1, ball.y - y1
    t = max(0.0, min(1.0, (px * sx + py * sy) / (sl * sl)))
    qx, qy = x1 + t * sx, y1 + t * sy
    dx, dy = ball.x - qx, ball.y - qy
    dist = math.hypot(dx, dy)
    if dist < ball.r and dist > 0:
        nx, ny = dx / dist, dy / dist
        ball.x = qx + nx * (ball.r + 0.6)
        ball.y = qy + ny * (ball.r + 0.6)
        dot = ball.vx * nx + ball.vy * ny
        if dot < 0:
            ball.vx -= 2 * dot * nx
            ball.vy -= 2 * dot * ny
        return True
    return False

def cx_fix(a, b):
    return (a + b) / 2

def cy_fix(a, b):
    return (a + b) / 2

def _sim_rings(W, H):
    cx, cy = W / 2, H / 2
    rings = [min(W, H) * s for s in (0.18, 0.28, 0.38)]
    gaps = [0.0, 1.2, 2.4]
    spin = [0.018, -0.022, 0.016]
    ball = Ball(cx, cy, 4.8, 0.6, 10, (255, 240, 120))
    def frame():
        ball.x += ball.vx
        ball.y += ball.vy
        dist = math.hypot(ball.x - cx, ball.y - cy) or 0.001
        ang = math.atan2(ball.y - cy, ball.x - cx)
        for i, R in enumerate(rings):
            gaps[i] += spin[i]
            gap = (gaps[i]) % (2 * math.pi)
            in_gap = abs((_wrap(ang - gap))) < 0.42
            if abs(dist + ball.r - R) < 6 and not in_gap:
                nx, ny = (ball.x - cx) / dist, (ball.y - cy) / dist
                if dist < R:
                    ball.x = cx + nx * (R - ball.r - 1)
                    ball.y = cy + ny * (R - ball.r - 1)
                else:
                    ball.x = cx + nx * (R + ball.r + 1)
                    ball.y = cy + ny * (R + ball.r + 1)
                dot = ball.vx * nx + ball.vy * ny
                ball.vx -= 2 * dot * nx
                ball.vy -= 2 * dot * ny
        if dist > rings[-1] + 30:
            ball.x, ball.y, ball.vx, ball.vy = cx, cy, 4.8, 0.8
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        for i, R in enumerate(rings):
            d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(90, 140, 255), width=3)
            gap = gaps[i]
            gx = cx + R * math.cos(gap)
            gy = cy + R * math.sin(gap)
            d.ellipse((gx - 8, gy - 8, gx + 8, gy + 8), fill=(8, 8, 14))
        _draw_glow(d, ball.x, ball.y, ball.r, ball.color)
        return img
    return frame

def _wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a

def _sim_collide(W, H):
    cx, cy, R = W / 2, H / 2, min(W, H) * 0.38
    palette = [(80, 200, 255), (255, 110, 110), (120, 255, 160), (255, 210, 80), (200, 130, 255)]
    balls = [
        Ball(cx - 30, cy, 5.2, 3.4, 12, palette[0]),
        Ball(cx + 30, cy, -3.8, 5.0, 12, palette[1]),
    ]
    def frame():
        img = _bg(W, H)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(120, 120, 160), width=4)
        extra = []
        for i, ball in enumerate(balls):
            _step_free(ball)
            _bounce_circle(ball, cx, cy, R)
            for j in range(i + 1, len(balls)):
                other = balls[j]
                dx, dy = other.x - ball.x, other.y - ball.y
                dist = math.hypot(dx, dy) or 0.001
                if dist < ball.r + other.r and len(balls) + len(extra) < 16:
                    extra.append(Ball(
                        (ball.x + other.x) / 2, (ball.y + other.y) / 2,
                        -dy * 0.15, dx * 0.15, 10, palette[len(balls) % len(palette)],
                    ))
                    nx, ny = dx / dist, dy / dist
                    overlap = ball.r + other.r - dist
                    ball.x -= nx * overlap / 2
                    ball.y -= ny * overlap / 2
                    other.x += nx * overlap / 2
                    other.y += ny * overlap / 2
            _draw_glow(d, ball.x, ball.y, ball.r, ball.color, 8)
        balls.extend(extra)
        if len(balls) >= 16:
            balls[:] = [
                Ball(cx - 30, cy, 5.2, 3.4, 12, palette[0]),
                Ball(cx + 30, cy, -3.8, 5.0, 12, palette[1]),
            ]
        return img
    return frame

def _sim_plinko(W, H):
    pegs = []
    for row in range(8):
        count = 4 + row
        for col in range(count):
            x = W * (col + 1) / (count + 1)
            y = 140 + row * 70
            pegs.append((x, y))
    balls = [Ball(W / 2, 40, random.uniform(-1.2, 1.2), 1.4, 9, (255, 220, 90))]
    spawn = [0]
    def frame():
        spawn[0] += 1
        if spawn[0] % 28 == 0 and len(balls) < 12:
            balls.append(Ball(W / 2 + random.uniform(-20, 20), 40, random.uniform(-1.4, 1.4), 1.5, 9, random.choice([(255, 220, 90), (90, 200, 255), (255, 120, 160)])))
        img = _bg(W, H, (10, 10, 18))
        d = ImageDraw.Draw(img)
        for px, py in pegs:
            d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(180, 180, 200))
        alive = []
        for ball in balls:
            ball.vy += 0.18
            ball.x += ball.vx
            ball.y += ball.vy
            if ball.x < ball.r or ball.x > W - ball.r:
                ball.vx *= -0.9
                ball.x = min(max(ball.x, ball.r), W - ball.r)
            for px, py in pegs:
                dx, dy = ball.x - px, ball.y - py
                dist = math.hypot(dx, dy) or 0.001
                if dist < ball.r + 6:
                    nx, ny = dx / dist, dy / dist
                    ball.x = px + nx * (ball.r + 7)
                    ball.y = py + ny * (ball.r + 7)
                    dot = ball.vx * nx + ball.vy * ny
                    ball.vx -= 1.6 * dot * nx
                    ball.vy -= 1.6 * dot * ny
            if ball.y < H + 20:
                alive.append(ball)
                _draw_glow(d, ball.x, ball.y, ball.r, ball.color, 6)
        balls[:] = alive or [Ball(W / 2, 40, 0.4, 1.4, 9, (255, 220, 90))]
        return img
    return frame

def _scale_and_silence(src: Path, duration: float, W: int, H: int, dest: Path):
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", f"scale={W}:{H}:flags=lanczos",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        warn((proc.stderr or "")[-300:])
        raise RuntimeError("Could not finish simulation export")

def _write_meta(sim_type, duration, out_root: Path):
    title = f"{TYPES[sim_type]}"
    desc = f"Silent physics simulation. No voice. No captions.\n{TYPES[sim_type]}\n"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", desc + "\n#Shorts #simulation #satisfying\n")
    save_text(out_root / "hashtags.txt", "#Shorts #simulation #satisfying\n")
    save_text(out_root / "tags.txt", "simulation,satisfying,shorts,physics\n")
