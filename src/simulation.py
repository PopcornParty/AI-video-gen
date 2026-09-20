"""Silent satisfying physics simulations. No voice, no captions."""
from __future__ import annotations
import math
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from PIL import Image, ImageDraw
from .utils import ensure_dir, info, save_text, warn

TYPES = {
    "grow": "Ball grows on every bounce",
    "shrink": "Circle shrinks on every bounce",
    "squeeze": "Ball grows and the circle shrinks",
    "swarm": "Lots of balls inside one circle",
    "spawn": "A bounce can add another ball",
    "box": "Ball grows inside a square",
    "triangle": "Ball grows inside a triangle",
    "rings": "Ball tries to escape rotating rings",
    "race": "Two balls, who fills the circle",
    "gravity": "Balls fall and bounce in a bowl",
}

BG = (8, 8, 12)
INK = (235, 235, 245)

def simulation_types() -> list[str]:
    return list(TYPES.keys())

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path) -> Path:
    sim_type = (sim_type or "grow").lower().strip()
    if sim_type not in TYPES:
        sim_type = "grow"
    duration = max(8.0, min(58.0, float(duration or 34)))
    W = 540
    H = 960
    fps = 30
    frames = int(duration * fps)
    ensure_dir(work_dir)
    ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Rendering {duration:.0f}s silent '{sim_type}' physics sim ({frames} frames)")
    _encode(sim_type, frames, fps, W, H, raw)
    final = out_root / "video.mp4"
    out_w = int(cfg["video"]["width"])
    out_h = int(cfg["video"]["height"])
    _scale_silent(raw, duration, out_w, out_h, final)
    _write_meta(sim_type, duration, out_root)
    if not final.exists() or final.stat().st_size < 10000:
        raise RuntimeError("Simulation file was not created")
    return final

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    r: float
    color: tuple
    trail: list = field(default_factory=list)

def _encode(sim_type, frames, fps, W, H, dest: Path):
    cx, cy = W / 2, H / 2
    rng = random.Random(sim_type + "-seed")
    maker = {
        "grow": lambda: _state_grow(cx, cy, rng),
        "shrink": lambda: _state_shrink(cx, cy, rng),
        "squeeze": lambda: _state_squeeze(cx, cy, rng),
        "swarm": lambda: _state_swarm(cx, cy, rng),
        "spawn": lambda: _state_spawn(cx, cy, rng),
        "box": lambda: _state_box(cx, cy, W, H, rng),
        "triangle": lambda: _state_triangle(cx, cy, rng),
        "rings": lambda: _state_rings(cx, cy, rng),
        "race": lambda: _state_race(cx, cy, rng),
        "gravity": lambda: _state_gravity(cx, cy, rng),
    }[sim_type]
    state, step_fn, draw_fn = maker()
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", str(dest),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for i in range(frames):
        step_fn(state, 1.0 / fps, i)
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        draw_fn(draw, state, W, H)
        proc.stdin.write(img.tobytes())
        if i % 90 == 0:
            info(f"sim frame {i}/{frames}")
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
    code = proc.wait()
    if code != 0 or not dest.exists():
        raise RuntimeError("ffmpeg sim encode failed: " + err[-400:])

def _bounce_circle(ball: Ball, cx, cy, R, grow=0.0):
    dx, dy = ball.x - cx, ball.y - cy
    dist = math.hypot(dx, dy) or 0.001
    limit = R - ball.r
    if dist >= limit:
        nx, ny = dx / dist, dy / dist
        dot = ball.vx * nx + ball.vy * ny
        if dot > 0:
            ball.vx -= 2 * dot * nx
            ball.vy -= 2 * dot * ny
        ball.x = cx + nx * (limit - 0.4)
        ball.y = cy + ny * (limit - 0.4)
        if grow:
            ball.r = min(ball.r + grow, max(4.0, R - 3))
        return True
    return False

def _integrate(ball: Ball, dt, gravity=0.0):
    ball.vy += gravity * dt
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt
    ball.trail.append((ball.x, ball.y))
    if len(ball.trail) > 18:
        ball.trail.pop(0)

def _draw_trail(draw, ball):
    for i, (x, y) in enumerate(ball.trail):
        t = (i + 1) / max(1, len(ball.trail))
        rr = max(1, int(ball.r * 0.25 * t))
        col = tuple(int(c * (0.25 + 0.75 * t)) for c in ball.color)
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)

def _draw_ball(draw, ball):
    _draw_trail(draw, ball)
    r = ball.r
    draw.ellipse([ball.x - r, ball.y - r, ball.x + r, ball.y + r], fill=ball.color)
    glow = max(2, r * 0.35)
    draw.ellipse([ball.x - glow, ball.y - glow - r * 0.2, ball.x + glow * 0.6, ball.y + glow * 0.2], fill=(255, 255, 255))

def _draw_ring(draw, cx, cy, R, color=INK, width=6):
    draw.ellipse([cx - R, cy - R, cx + R, cy + R], outline=color, width=width)

def _state_grow(cx, cy, rng):
    R = [250]
    ball = Ball(cx, cy + 40, rng.uniform(-180, 180), rng.uniform(-220, -80), 16, (80, 190, 255))
    def step(state, dt, i):
        _integrate(ball, dt)
        _bounce_circle(ball, cx, cy, R[0], grow=2.4)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R[0])
        _draw_ball(d, ball)
    return {"ball": ball}, step, draw

def _state_shrink(cx, cy, rng):
    R = [270]
    ball = Ball(cx - 20, cy, rng.uniform(160, 240), rng.uniform(-90, 90), 18, (255, 90, 130))
    def step(state, dt, i):
        _integrate(ball, dt)
        if _bounce_circle(ball, cx, cy, R[0], grow=0):
            R[0] = max(ball.r + 8, R[0] - 3.2)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R[0], (255, 170, 180))
        _draw_ball(d, ball)
    return {}, step, draw

def _state_squeeze(cx, cy, rng):
    R = [265]
    ball = Ball(cx + 10, cy - 30, 170, -150, 14, (255, 210, 70))
    def step(state, dt, i):
        _integrate(ball, dt)
        if _bounce_circle(ball, cx, cy, R[0], grow=1.8):
            R[0] = max(ball.r + 6, R[0] - 2.2)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R[0], (255, 230, 140))
        _draw_ball(d, ball)
    return {}, step, draw

def _state_swarm(cx, cy, rng):
    R = 255
    colors = [(80, 190, 255), (255, 90, 130), (120, 255, 160), (255, 210, 70), (200, 140, 255)]
    balls = []
    for i in range(8):
        ang = rng.random() * 6.28
        spd = rng.uniform(90, 220)
        balls.append(Ball(cx + rng.uniform(-40, 40), cy + rng.uniform(-40, 40), math.cos(ang) * spd, math.sin(ang) * spd, rng.uniform(10, 16), colors[i % 5]))
    def step(state, dt, i):
        for b in balls:
            _integrate(b, dt)
            _bounce_circle(b, cx, cy, R, grow=0)
        _ball_collisions(balls)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return {}, step, draw

def _state_spawn(cx, cy, rng):
    R = 250
    colors = [(80, 190, 255), (255, 90, 130), (120, 255, 160), (255, 210, 70), (200, 140, 255)]
    balls = [Ball(cx, cy, 160, -40, 14, colors[0])]
    def step(state, dt, i):
        extra = []
        for b in balls:
            _integrate(b, dt)
            if _bounce_circle(b, cx, cy, R, grow=0.4) and len(balls) + len(extra) < 18 and rng.random() < 0.35:
                ang = rng.random() * 6.28
                extra.append(Ball(b.x, b.y, math.cos(ang) * 180, math.sin(ang) * 180, max(8, b.r * 0.7), colors[len(balls) % 5]))
        balls.extend(extra)
        _ball_collisions(balls)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return {}, step, draw

def _state_box(cx, cy, W, H, rng):
    left, top, right, bottom = 70, 180, W - 70, H - 180
    ball = Ball(cx, cy, 210, -160, 18, (120, 255, 160))
    def step(state, dt, i):
        _integrate(ball, dt)
        hit = False
        if ball.x - ball.r <= left:
            ball.x = left + ball.r + 0.4
            ball.vx = abs(ball.vx)
            hit = True
        if ball.x + ball.r >= right:
            ball.x = right - ball.r - 0.4
            ball.vx = -abs(ball.vx)
            hit = True
        if ball.y - ball.r <= top:
            ball.y = top + ball.r + 0.4
            ball.vy = abs(ball.vy)
            hit = True
        if ball.y + ball.r >= bottom:
            ball.y = bottom - ball.r - 0.4
            ball.vy = -abs(ball.vy)
            hit = True
        if hit:
            max_r = min((right - left) / 2 - 4, (bottom - top) / 2 - 4)
            ball.r = min(ball.r + 3.0, max_r)
    def draw(d, state, Ww, Hh):
        d.rectangle([left, top, right, bottom], outline=INK, width=6)
        _draw_ball(d, ball)
    return {}, step, draw

def _state_triangle(cx, cy, rng):
    pts = [(cx, cy - 230), (cx + 230, cy + 200), (cx - 230, cy + 200)]
    ball = Ball(cx, cy + 40, 150, -170, 16, (200, 140, 255))
    def step(state, dt, i):
        _integrate(ball, dt)
        if _bounce_polygon(ball, pts, grow=2.6):
            pass
    def draw(d, state, W, H):
        d.polygon(pts, outline=INK)
        d.line(pts + [pts[0]], fill=INK, width=6)
        _draw_ball(d, ball)
    return {}, step, draw

def _state_rings(cx, cy, rng):
    radii = [90, 150, 210, 270]
    gaps = [0.7, 0.9, 1.2, 1.5]
    speeds = [1.1, -0.8, 0.6, -0.45]
    angles = [0.0, 1.0, 2.0, 3.0]
    ball = Ball(cx, cy, 0, -220, 12, (255, 210, 70))
    def step(state, dt, i):
        _integrate(ball, dt)
        for k, R in enumerate(radii):
            angles[k] += speeds[k] * dt
            dx, dy = ball.x - cx, ball.y - cy
            dist = math.hypot(dx, dy)
            if abs(dist - R) < ball.r + 3:
                ang = math.atan2(dy, dx)
                gap_center = angles[k]
                diff = abs((_wrap(ang - gap_center)))
                if diff < gaps[k] / 2:
                    continue
                nx, ny = dx / (dist or 1), dy / (dist or 1)
                dot = ball.vx * nx + ball.vy * ny
                going_out = dist >= R
                if (going_out and dot > 0) or ((not going_out) and dot < 0):
                    ball.vx -= 2 * dot * nx
                    ball.vy -= 2 * dot * ny
                    ball.x = cx + nx * (R + (-ball.r - 2 if going_out else ball.r + 2))
                    ball.y = cy + ny * (R + (-ball.r - 2 if going_out else ball.r + 2))
        if math.hypot(ball.x - cx, ball.y - cy) > 330:
            ball.x, ball.y, ball.vx, ball.vy = cx, cy, rng.uniform(-80, 80), -220
    def draw(d, state, W, H):
        for k, R in enumerate(radii):
            _draw_arc_gap(d, cx, cy, R, angles[k], gaps[k])
        _draw_ball(d, ball)
    return {}, step, draw

def _state_race(cx, cy, rng):
    R = 255
    a = Ball(cx - 18, cy, -140, -180, 12, (80, 190, 255))
    b = Ball(cx + 18, cy, 150, -160, 12, (255, 90, 130))
    def step(state, dt, i):
        for ball in (a, b):
            _integrate(ball, dt)
            _bounce_circle(ball, cx, cy, R, grow=1.5)
        _ball_collisions([a, b])
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R)
        _draw_ball(d, a)
        _draw_ball(d, b)
    return {}, step, draw

def _state_gravity(cx, cy, rng):
    R = 260
    colors = [(80, 190, 255), (255, 210, 70), (120, 255, 160), (255, 90, 130)]
    balls = [Ball(cx + rng.uniform(-30, 30), cy - 80, rng.uniform(-40, 40), 0, 14, colors[i]) for i in range(4)]
    def step(state, dt, i):
        for b in balls:
            _integrate(b, dt, gravity=520)
            _bounce_circle(b, cx, cy, R, grow=0)
            b.vx *= 0.999
            b.vy *= 0.999
        _ball_collisions(balls)
    def draw(d, state, W, H):
        _draw_ring(d, cx, cy, R, (180, 200, 255))
        for b in balls:
            _draw_ball(d, b)
    return {}, step, draw

def _ball_collisions(balls):
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            a, b = balls[i], balls[j]
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.hypot(dx, dy) or 0.001
            min_d = a.r + b.r
            if dist < min_d:
                nx, ny = dx / dist, dy / dist
                overlap = min_d - dist
                a.x -= nx * overlap / 2
                a.y -= ny * overlap / 2
                b.x += nx * overlap / 2
                b.y += ny * overlap / 2
                va = a.vx * nx + a.vy * ny
                vb = b.vx * nx + b.vy * ny
                a.vx += (vb - va) * nx
                a.vy += (vb - va) * ny
                b.vx += (va - vb) * nx
                b.vy += (va - vb) * ny

def _bounce_polygon(ball: Ball, pts, grow=0.0):
    hit = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if _reflect_segment(ball, x1, y1, x2, y2):
            hit = True
            if grow:
                ball.r = min(ball.r + grow, 90)
    return hit

def _reflect_segment(ball, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    ln = math.hypot(vx, vy) or 1
    nx, ny = -vy / ln, vx / ln
    px, py = ball.x - x1, ball.y - y1
    dist = px * nx + py * ny
    if abs(dist) > ball.r + 1:
        return False
    t = (px * vx + py * vy) / (ln * ln)
    if t < 0 or t > 1:
        return False
    if dist < 0:
        nx, ny = -nx, -ny
        dist = -dist
    dot = ball.vx * nx + ball.vy * ny
    if dot < 0:
        ball.vx -= 2 * dot * nx
        ball.vy -= 2 * dot * ny
        ball.x += nx * (ball.r + 1 - dist)
        ball.y += ny * (ball.r + 1 - dist)
        return True
    return False

def _wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a

def _draw_arc_gap(draw, cx, cy, R, mid, gap):
    start = math.degrees(mid + gap / 2)
    end = math.degrees(mid - gap / 2 + 2 * math.pi)
    bbox = [cx - R, cy - R, cx + R, cy + R]
    draw.arc(bbox, start=start, end=end, fill=INK, width=7)

def _scale_silent(video: Path, duration: float, W, H, dest: Path):
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", f"scale={W}:{H}:flags=lanczos",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        warn(proc.stderr[-300:] if proc.stderr else "scale failed")
        raise RuntimeError("Could not finish simulation video")

def _write_meta(sim_type, duration, out_root: Path):
    title = f"{TYPES[sim_type]}"
    desc = f"Silent satisfying simulation: {TYPES[sim_type]}. No voice. No captions.\n"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", desc + "\n#Shorts #satisfying #simulation\n")
    save_text(out_root / "hashtags.txt", "#Shorts #satisfying #simulation\n")
    save_text(out_root / "tags.txt", "simulation,satisfying,shorts,silent\n")
