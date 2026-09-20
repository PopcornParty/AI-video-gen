"""Silent satisfying physics simulations. No voice, no captions."""
from __future__ import annotations
import math
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
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

BG = (8, 8, 14)
INK = (230, 230, 240)

def simulation_types() -> list[str]:
    return list(TYPES.keys())

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path) -> Path:
    sim_type = (sim_type or "grow").lower().strip()
    if sim_type not in TYPES:
        sim_type = "grow"
    duration = max(8.0, min(58.0, float(duration or 34)))
    W, H, fps = 540, 960, 30
    frames = int(duration * fps)
    ensure_dir(work_dir)
    ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Rendering {duration:.0f}s silent '{sim_type}' physics sim")
    _encode(sim_type, frames, fps, W, H, raw)
    final = out_root / "video.mp4"
    _scale_silent(raw, duration, int(cfg["video"]["width"]), int(cfg["video"]["height"]), final)
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
    touching: bool = False

def _encode(sim_type, frames, fps, W, H, dest: Path):
    cx, cy = W / 2.0, H / 2.0
    rng = random.Random(hash(sim_type) & 0xFFFFFFFF)
    builders = {
        "grow": lambda: _grow(cx, cy, rng),
        "shrink": lambda: _shrink(cx, cy, rng),
        "squeeze": lambda: _squeeze(cx, cy, rng),
        "swarm": lambda: _swarm(cx, cy, rng),
        "spawn": lambda: _spawn(cx, cy, rng),
        "box": lambda: _box(cx, cy, W, H, rng),
        "triangle": lambda: _triangle(cx, cy, rng),
        "rings": lambda: _rings(cx, cy, rng),
        "race": lambda: _race(cx, cy, rng),
        "gravity": lambda: _gravity(cx, cy, rng),
    }
    step_fn, draw_fn = builders[sim_type]()
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", str(dest),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    dt = 1.0 / fps
    subs = 3
    try:
        for i in range(frames):
            for _ in range(subs):
                step_fn(dt / subs)
            img = Image.new("RGB", (W, H), BG)
            draw_fn(ImageDraw.Draw(img), W, H)
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
    if proc.wait() != 0 or not dest.exists():
        raise RuntimeError("ffmpeg sim encode failed: " + err[-400:])

def _move(ball: Ball, dt, gravity=0.0):
    ball.vy += gravity * dt
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt
    ball.trail.append((ball.x, ball.y))
    del ball.trail[:-16]

def _circle_hit(ball: Ball, cx, cy, R):
    dx, dy = ball.x - cx, ball.y - cy
    dist = math.hypot(dx, dy) or 0.001
    return dist + ball.r >= R - 0.01, dx, dy, dist

def _resolve_circle(ball: Ball, cx, cy, R, dx, dy, dist):
    nx, ny = dx / dist, dy / dist
    limit = max(2.0, R - ball.r - 0.6)
    ball.x = cx + nx * limit
    ball.y = cy + ny * limit
    dot = ball.vx * nx + ball.vy * ny
    if dot > 0:
        ball.vx -= 2.0 * dot * nx
        ball.vy -= 2.0 * dot * ny
    speed = math.hypot(ball.vx, ball.vy)
    if speed < 90:
        scale = 140 / max(speed, 1)
        ball.vx *= scale
        ball.vy *= scale

def _new_bounce(ball: Ball, hitting: bool) -> bool:
    fresh = hitting and not ball.touching
    ball.touching = hitting
    return fresh

def _draw_trail(draw, ball):
    for i, (x, y) in enumerate(ball.trail):
        t = (i + 1) / max(1, len(ball.trail))
        rr = max(1.2, ball.r * 0.22 * t)
        col = tuple(max(0, min(255, int(c * (0.2 + 0.8 * t)))) for c in ball.color)
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)

def _draw_ball(draw, ball):
    _draw_trail(draw, ball)
    r = ball.r
    draw.ellipse([ball.x - r, ball.y - r, ball.x + r, ball.y + r], fill=ball.color)
    g = max(2.0, r * 0.28)
    draw.ellipse([ball.x - g, ball.y - g - r * 0.18, ball.x + g * 0.55, ball.y], fill=(255, 255, 255))

def _draw_circle(draw, cx, cy, R, color=INK, width=6):
    draw.ellipse([cx - R, cy - R, cx + R, cy + R], outline=color, width=width)

def _grow(cx, cy, rng):
    R = 250.0
    ball = Ball(cx + 8, cy + 30, 210, -250, 14, (70, 190, 255))
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R)
        if hitting:
            if _new_bounce(ball, True):
                ball.r = min(ball.r + 4.5, R - 8)
            _resolve_circle(ball, cx, cy, R, dx, dy, dist)
        else:
            ball.touching = False
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        _draw_ball(d, ball)
    return step, draw

def _shrink(cx, cy, rng):
    R = [268.0]
    ball = Ball(cx - 16, cy, 240, -120, 16, (255, 95, 130))
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R[0])
        if hitting:
            if _new_bounce(ball, True):
                R[0] = max(ball.r + 10, R[0] - 6)
            _resolve_circle(ball, cx, cy, R[0], dx, dy, dist)
        else:
            ball.touching = False
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R[0], (255, 170, 185))
        _draw_ball(d, ball)
    return step, draw

def _squeeze(cx, cy, rng):
    R = [262.0]
    ball = Ball(cx + 12, cy - 20, 200, -210, 13, (255, 210, 70))
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R[0])
        if hitting:
            if _new_bounce(ball, True):
                ball.r = min(ball.r + 3.2, R[0] - 8)
                R[0] = max(ball.r + 8, R[0] - 4)
            _resolve_circle(ball, cx, cy, R[0], dx, dy, dist)
        else:
            ball.touching = False
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R[0], (255, 230, 140))
        _draw_ball(d, ball)
    return step, draw

def _swarm(cx, cy, rng):
    R = 252.0
    palette = [(70, 190, 255), (255, 95, 130), (120, 255, 160), (255, 210, 70), (200, 140, 255)]
    balls = []
    for i in range(7):
        ang = rng.random() * math.tau
        spd = rng.uniform(140, 260)
        balls.append(Ball(cx + rng.uniform(-30, 30), cy + rng.uniform(-30, 30), math.cos(ang) * spd, math.sin(ang) * spd, rng.uniform(11, 15), palette[i % 5]))
    def step(dt):
        for b in balls:
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
                b.touching = True
            else:
                b.touching = False
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw

def _spawn(cx, cy, rng):
    R = 250.0
    palette = [(70, 190, 255), (255, 95, 130), (120, 255, 160), (255, 210, 70), (200, 140, 255)]
    balls = [Ball(cx, cy, 190, -70, 13, palette[0])]
    def step(dt):
        born = []
        for b in balls:
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                if _new_bounce(b, True) and len(balls) + len(born) < 16 and rng.random() < 0.38:
                    ang = rng.random() * math.tau
                    born.append(Ball(b.x, b.y, math.cos(ang) * 200, math.sin(ang) * 200, max(8, b.r * 0.72), palette[len(balls) % 5]))
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
            else:
                b.touching = False
        balls.extend(born)
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw

def _box(cx, cy, W, H, rng):
    left, top, right, bottom = 80.0, 190.0, W - 80.0, H - 190.0
    ball = Ball(cx, cy, 230, -190, 16, (120, 255, 160))
    def step(dt):
        _move(ball, dt)
        hitting = False
        if ball.x - ball.r <= left:
            ball.x = left + ball.r + 0.5
            ball.vx = abs(ball.vx)
            hitting = True
        elif ball.x + ball.r >= right:
            ball.x = right - ball.r - 0.5
            ball.vx = -abs(ball.vx)
            hitting = True
        if ball.y - ball.r <= top:
            ball.y = top + ball.r + 0.5
            ball.vy = abs(ball.vy)
            hitting = True
        elif ball.y + ball.r >= bottom:
            ball.y = bottom - ball.r - 0.5
            ball.vy = -abs(ball.vy)
            hitting = True
        if _new_bounce(ball, hitting):
            max_r = min((right - left) / 2 - 6, (bottom - top) / 2 - 6)
            ball.r = min(ball.r + 5.0, max_r)
        if not hitting:
            ball.touching = False
    def draw(d, Ww, Hh):
        d.rectangle([left, top, right, bottom], outline=INK, width=6)
        _draw_ball(d, ball)
    return step, draw

def _triangle(cx, cy, rng):
    pts = [(cx, cy - 220), (cx + 220, cy + 200), (cx - 220, cy + 200)]
    ball = Ball(cx, cy + 20, 170, -200, 15, (200, 140, 255))
    def step(dt):
        _move(ball, dt)
        hitting = _hit_polygon(ball, pts)
        if _new_bounce(ball, hitting):
            ball.r = min(ball.r + 4.0, 78)
        if not hitting:
            ball.touching = False
    def draw(d, W, H):
        d.line(pts + [pts[0]], fill=INK, width=6)
        _draw_ball(d, ball)
    return step, draw

def _rings(cx, cy, rng):
    radii = [95.0, 155.0, 215.0, 275.0]
    gaps = [0.85, 0.75, 0.7, 0.65]
    speeds = [1.35, -1.05, 0.8, -0.55]
    angles = [0.2, 1.4, 2.6, 3.8]
    ball = Ball(cx, cy, 40, -240, 11, (255, 210, 70))
    def step(dt):
        _move(ball, dt)
        for k, R in enumerate(radii):
            angles[k] += speeds[k] * dt
            dx, dy = ball.x - cx, ball.y - cy
            dist = math.hypot(dx, dy) or 0.001
            if abs(dist - R) > ball.r + 3:
                continue
            ang = math.atan2(dy, dx)
            if abs(_wrap(ang - angles[k])) < gaps[k] / 2:
                continue
            nx, ny = dx / dist, dy / dist
            outward = dist >= R
            dot = ball.vx * nx + ball.vy * ny
            if (outward and dot > 0) or ((not outward) and dot < 0):
                ball.vx -= 2 * dot * nx
                ball.vy -= 2 * dot * ny
            side = 1 if outward else -1
            ball.x = cx + nx * (R - side * (ball.r + 2))
            ball.y = cy + ny * (R - side * (ball.r + 2))
        if math.hypot(ball.x - cx, ball.y - cy) > 340:
            ball.x, ball.y, ball.vx, ball.vy = cx, cy, rng.uniform(-60, 60), -240
    def draw(d, W, H):
        for k, R in enumerate(radii):
            _ring_with_gap(d, cx, cy, R, angles[k], gaps[k])
        _draw_ball(d, ball)
    return step, draw

def _race(cx, cy, rng):
    R = 252.0
    a = Ball(cx - 20, cy, -170, -200, 12, (70, 190, 255))
    b = Ball(cx + 20, cy, 180, -170, 12, (255, 95, 130))
    def step(dt):
        for ball in (a, b):
            _move(ball, dt)
            hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R)
            if hitting:
                if _new_bounce(ball, True):
                    ball.r = min(ball.r + 3.0, R - 10)
                _resolve_circle(ball, cx, cy, R, dx, dy, dist)
            else:
                ball.touching = False
        _collide([a, b])
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        _draw_ball(d, a)
        _draw_ball(d, b)
    return step, draw

def _gravity(cx, cy, rng):
    R = 258.0
    palette = [(70, 190, 255), (255, 210, 70), (120, 255, 160), (255, 95, 130)]
    balls = [Ball(cx + rng.uniform(-28, 28), cy - 90, rng.uniform(-50, 50), 20, 13, palette[i]) for i in range(4)]
    def step(dt):
        for b in balls:
            _move(b, dt, gravity=780)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
                b.vx *= 0.992
                b.vy *= 0.992
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R, (180, 200, 255))
        for b in balls:
            _draw_ball(d, b)
    return step, draw

def _collide(balls):
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            a, b = balls[i], balls[j]
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.hypot(dx, dy) or 0.001
            need = a.r + b.r
            if dist >= need:
                continue
            nx, ny = dx / dist, dy / dist
            overlap = need - dist
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

def _hit_polygon(ball: Ball, pts) -> bool:
    hit = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if _reflect_segment(ball, x1, y1, x2, y2):
            hit = True
    return hit

def _reflect_segment(ball, x1, y1, x2, y2) -> bool:
    vx, vy = x2 - x1, y2 - y1
    ln = math.hypot(vx, vy) or 1.0
    nx, ny = -vy / ln, vx / ln
    px, py = ball.x - x1, ball.y - y1
    side = px * nx + py * ny
    t = (px * vx + py * vy) / (ln * ln)
    if t < -0.02 or t > 1.02:
        return False
    if abs(side) > ball.r + 1.2:
        return False
    if side < 0:
        nx, ny, side = -nx, -ny, -side
    dot = ball.vx * nx + ball.vy * ny
    if dot < 0:
        ball.vx -= 2 * dot * nx
        ball.vy -= 2 * dot * ny
        ball.x += nx * (ball.r + 1.2 - side)
        ball.y += ny * (ball.r + 1.2 - side)
        return True
    return False

def _wrap(a):
    while a > math.pi:
        a -= math.tau
    while a < -math.pi:
        a += math.tau
    return a

def _ring_with_gap(draw, cx, cy, R, mid, gap):
    steps = 96
    for i in range(steps):
        a0 = i / steps * math.tau
        a1 = (i + 1) / steps * math.tau
        am = (a0 + a1) / 2
        if abs(_wrap(am - mid)) < gap / 2:
            continue
        draw.line(
            [cx + R * math.cos(a0), cy + R * math.sin(a0), cx + R * math.cos(a1), cy + R * math.sin(a1)],
            fill=INK,
            width=6,
        )

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
        warn((proc.stderr or "")[-300:])
        raise RuntimeError("Could not finish simulation video")

def _write_meta(sim_type, duration, out_root: Path):
    title = TYPES[sim_type]
    desc = f"Silent satisfying simulation: {title}. No voice. No captions.\n"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", desc + "\n#Shorts #satisfying #simulation\n")
    save_text(out_root / "hashtags.txt", "#Shorts #satisfying #simulation\n")
    save_text(out_root / "tags.txt", "simulation,satisfying,shorts,silent\n")
