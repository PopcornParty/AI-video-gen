"""Satisfying physics sims. No voice, no captions. Ends when the match is over."""
from __future__ import annotations
import math
import random
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image, ImageDraw
from .sim_audio import mix_sim_audio
from .utils import ensure_dir, info, save_text, warn

TYPES = {
    "grow": "grow", "shrink": "shrink", "squeeze": "squeeze", "colorfight": "colorfight",
    "paint": "paint", "merge": "merge", "king": "king", "swarm": "swarm", "spawn": "spawn",
    "rings": "rings", "race": "race", "split": "split", "random": "random",
}
SHAPES = ("circle", "square", "triangle", "hexagon")
SPEEDS = {"slow": 0.95, "normal": 1.35, "fast": 1.85}
NEON = [(0, 255, 255), (255, 40, 180), (180, 255, 40), (255, 220, 0), (80, 140, 255), (255, 90, 40)]
RAINBOW = [(255, 60, 60), (255, 160, 0), (255, 230, 40), (40, 220, 90), (40, 180, 255), (180, 70, 255)]
TWOTONE = [(0, 220, 255), (255, 50, 160)]
BG = (6, 6, 12)
INK = (240, 240, 255)
MIN_SECONDS = 40.0
MAX_SECONDS = 58.0
HOLD_AFTER = 2.0

def simulation_types():
    return [k for k in TYPES if k != "random"]

@dataclass
class Ball:
    x: float; y: float; vx: float; vy: float; r: float; color: tuple
    team: int = 0; trail: list = field(default_factory=list); touching: bool = False; alive: bool = True

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path, options: dict | None = None) -> Path:
    options = options or {}
    rng = random.Random(time.time_ns())
    sim_type = (sim_type or options.get("type") or "grow").lower().strip()
    if sim_type == "random" or sim_type not in TYPES:
        sim_type = rng.choice(simulation_types())
    shape = (options.get("shape") or "circle").lower()
    if shape not in SHAPES:
        shape = "circle"
    speed = SPEEDS.get((options.get("speed") or "fast").lower(), 1.85)
    palette = {"rainbow": RAINBOW, "two-tone": TWOTONE}.get((options.get("colors") or "neon").lower(), NEON)
    music_on = str(options.get("music", "on")).lower() != "off"
    W, H, fps = 540, 960, 30
    ensure_dir(work_dir); ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Simulation {sim_type} / {shape} / {options.get('speed', 'fast')}")
    seconds, hits = _encode(sim_type, shape, speed, palette, fps, W, H, raw, rng)
    info(f"Ended at {seconds:.1f}s after the match finished")
    final = out_root / "video.mp4"
    if music_on:
        mix_sim_audio(raw, final, seconds, hits, int(cfg["video"]["width"]), int(cfg["video"]["height"]), work_dir)
    else:
        _scale_only(raw, final, seconds, int(cfg["video"]["width"]), int(cfg["video"]["height"]))
    _write_meta(sim_type, shape, seconds, out_root)
    if not final.exists() or final.stat().st_size < 10000:
        raise RuntimeError("Simulation file was not created")
    return final

def _encode(sim_type, shape, speed, palette, fps, W, H, dest, rng):
    cx, cy = W / 2.0, H / 2.0
    builders = {
        "grow": lambda: _grow(cx, cy, W, H, shape, speed, palette, rng),
        "shrink": lambda: _shrink(cx, cy, W, H, shape, speed, palette, rng),
        "squeeze": lambda: _squeeze(cx, cy, W, H, shape, speed, palette, rng),
        "colorfight": lambda: _colorfight(cx, cy, W, H, shape, speed, palette, rng),
        "paint": lambda: _paint(cx, cy, W, H, shape, speed, palette, rng),
        "merge": lambda: _merge(cx, cy, W, H, shape, speed, palette, rng),
        "king": lambda: _king(cx, cy, W, H, shape, speed, palette, rng),
        "swarm": lambda: _swarm(cx, cy, W, H, shape, speed, palette, rng),
        "spawn": lambda: _spawn(cx, cy, W, H, shape, speed, palette, rng),
        "rings": lambda: _rings(cx, cy, speed, palette, rng),
        "race": lambda: _race(cx, cy, W, H, shape, speed, palette, rng),
        "split": lambda: _split(cx, cy, W, H, shape, speed, palette, rng),
    }
    step_fn, draw_fn, done_fn = builders[sim_type]()
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    dt = 1.0 / fps
    max_frames = int(MAX_SECONDS * fps)
    min_frames = int(MIN_SECONDS * fps)
    hold = int(HOLD_AFTER * fps)
    finished_at = None
    hits: list[float] = []
    last_hit_flag = [0]
    frame = 0
    try:
        while frame < max_frames:
            before = last_hit_flag[0]
            for _ in range(3):
                step_fn(dt / 3.0, last_hit_flag)
            if last_hit_flag[0] > before:
                hits.append(frame / fps)
            if finished_at is None and frame >= min_frames and done_fn():
                finished_at = frame
            img = Image.new("RGB", (W, H), BG)
            draw_fn(ImageDraw.Draw(img), W, H)
            proc.stdin.write(img.tobytes())
            frame += 1
            if finished_at is not None and frame - finished_at >= hold:
                break
    finally:
        proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
    if proc.wait() != 0 or not dest.exists():
        raise RuntimeError("ffmpeg sim encode failed: " + err[-300:])
    return frame / fps, hits

def _arena(shape, cx, cy, W, H):
    if shape == "square":
        return {"kind": "box", "box": (90.0, 200.0, W - 90.0, H - 200.0), "R": 240}
    if shape == "triangle":
        return {"kind": "poly", "pts": _poly(cx, cy + 16, 3, 248), "R": 248}
    if shape == "hexagon":
        return {"kind": "poly", "pts": _poly(cx, cy, 6, 248), "R": 248}
    return {"kind": "circle", "R": 248}

def _poly(cx, cy, n, radius):
    return [(cx + radius * math.cos(-math.pi / 2 + i * math.tau / n), cy + radius * math.sin(-math.pi / 2 + i * math.tau / n)) for i in range(n)]

def _draw_arena(d, arena, cx, cy):
    if arena["kind"] == "circle":
        R = arena["R"]; d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=INK, width=6)
    elif arena["kind"] == "box":
        d.rectangle(list(arena["box"]), outline=INK, width=6)
    else:
        pts = arena["pts"]; d.line(pts + [pts[0]], fill=INK, width=6)

def _bounce_arena(ball, arena, cx, cy, hits):
    if arena["kind"] == "circle":
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, arena["R"])
        if hitting:
            fresh = _new_bounce(ball, True)
            if fresh:
                hits[0] += 1
            _resolve_circle(ball, cx, cy, arena["R"], dx, dy, dist)
            return fresh
        ball.touching = False
        return False
    if arena["kind"] == "box":
        l, t, r, b = arena["box"]; hitting = False
        if ball.x - ball.r <= l:
            ball.x = l + ball.r + 0.4; ball.vx = abs(ball.vx); hitting = True
        elif ball.x + ball.r >= r:
            ball.x = r - ball.r - 0.4; ball.vx = -abs(ball.vx); hitting = True
        if ball.y - ball.r <= t:
            ball.y = t + ball.r + 0.4; ball.vy = abs(ball.vy); hitting = True
        elif ball.y + ball.r >= b:
            ball.y = b - ball.r - 0.4; ball.vy = -abs(ball.vy); hitting = True
        fresh = _new_bounce(ball, hitting)
        if fresh:
            hits[0] += 1
        if not hitting:
            ball.touching = False
        return fresh
    hitting = _hit_polygon(ball, arena["pts"])
    fresh = _new_bounce(ball, hitting)
    if fresh:
        hits[0] += 1
    if not hitting:
        ball.touching = False
    return fresh

def _move(ball, dt):
    ball.x += ball.vx * dt; ball.y += ball.vy * dt
    ball.trail.append((ball.x, ball.y)); del ball.trail[:-28]

def _circle_hit(ball, cx, cy, R):
    dx, dy = ball.x - cx, ball.y - cy
    dist = math.hypot(dx, dy) or 0.001
    return dist + ball.r >= R - 0.01, dx, dy, dist

def _resolve_circle(ball, cx, cy, R, dx, dy, dist):
    nx, ny = dx / dist, dy / dist
    limit = max(2.0, R - ball.r - 0.5)
    ball.x = cx + nx * limit; ball.y = cy + ny * limit
    dot = ball.vx * nx + ball.vy * ny
    if dot > 0:
        ball.vx -= 2 * dot * nx; ball.vy -= 2 * dot * ny
    spd = math.hypot(ball.vx, ball.vy)
    if spd < 220:
        ball.vx *= 280 / max(spd, 1); ball.vy *= 280 / max(spd, 1)

def _new_bounce(ball, hitting):
    fresh = hitting and not ball.touching
    ball.touching = hitting
    return fresh

def _draw_ball(d, ball):
    for i, (x, y) in enumerate(ball.trail):
        t = (i + 1) / max(1, len(ball.trail)); rr = max(1.2, ball.r * 0.22 * t)
        col = tuple(int(c * (0.25 + 0.75 * t)) for c in ball.color)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
    r = ball.r
    d.ellipse([ball.x - r, ball.y - r, ball.x + r, ball.y + r], fill=ball.color)
    g = max(2.0, r * 0.26)
    d.ellipse([ball.x - g, ball.y - g - r * 0.16, ball.x + g * 0.5, ball.y], fill=(255, 255, 255))

def _mk(cx, cy, rng, palette, speed, r=13, team=0):
    ang = rng.random() * math.tau
    spd = rng.uniform(360, 560) * speed
    col = palette[team % len(palette)]
    return Ball(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd, r, col, team)

def _spread(cx, cy, rng, palette, speed, n, r=12, teams=3):
    balls = []
    for i in range(n):
        ang = (i / max(1, n)) * math.tau
        rad = 70 + (i % 4) * 22
        b = _mk(cx + math.cos(ang) * rad, cy + math.sin(ang) * rad, rng, palette, speed, r + (i % 3), team=i % teams)
        b.x = cx + math.cos(ang) * rad
        b.y = cy + math.sin(ang) * rad
        balls.append(b)
    return balls

def _collide(balls):
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            a, b = balls[i], balls[j]
            if not a.alive or not b.alive:
                continue
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.hypot(dx, dy) or 0.001
            need = a.r + b.r
            if dist >= need:
                continue
            nx, ny = dx / dist, dy / dist
            overlap = need - dist
            a.x -= nx * overlap / 2; a.y -= ny * overlap / 2
            b.x += nx * overlap / 2; b.y += ny * overlap / 2
            va = a.vx * nx + a.vy * ny; vb = b.vx * nx + b.vy * ny
            a.vx += (vb - va) * nx; a.vy += (vb - va) * ny
            b.vx += (va - vb) * nx; b.vy += (va - vb) * ny
            yield a, b

def _fresh_pairs(balls, seen):
    now = set(); fresh = []
    for a, b in _collide(balls):
        key = tuple(sorted((id(a), id(b))))
        now.add(key)
        if key not in seen:
            fresh.append((a, b))
    seen.clear(); seen.update(now)
    return fresh

def _grow(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); ball = _mk(cx, cy, rng, palette, speed, 14); grow = 2.4; cap = arena.get("R", 240) - 8
    def step(dt, hits):
        _move(ball, dt)
        if _bounce_arena(ball, arena, cx, cy, hits):
            ball.r = min(ball.r + grow, cap)
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy); _draw_ball(d, ball)
    return step, draw, lambda: ball.r >= cap - 1

def _shrink(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); ball = _mk(cx, cy, rng, palette, speed, 16); R = [arena.get("R", 250)]
    def step(dt, hits):
        arena["R"] = R[0]; _move(ball, dt)
        if _bounce_arena(ball, arena, cx, cy, hits) and arena["kind"] == "circle":
            R[0] = max(ball.r + 8, R[0] - 4.2); arena["R"] = R[0]
        elif arena["kind"] == "box" and hits:
            l, t, r, b = arena["box"]; arena["box"] = (l + 1.6, t + 1.6, r - 1.6, b - 1.6)
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy); _draw_ball(d, ball)
    return step, draw, lambda: (arena["kind"] == "circle" and R[0] <= ball.r + 9) or (arena["kind"] == "box" and arena["box"][2] - arena["box"][0] < ball.r * 2 + 20)

def _squeeze(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); ball = _mk(cx, cy, rng, palette, speed, 13); R = [arena.get("R", 250)]
    def step(dt, hits):
        arena["R"] = R[0]; _move(ball, dt)
        if _bounce_arena(ball, arena, cx, cy, hits):
            ball.r = min(ball.r + 2.4, R[0] - 7)
            if arena["kind"] == "circle":
                R[0] = max(ball.r + 7, R[0] - 3.0); arena["R"] = R[0]
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy); _draw_ball(d, ball)
    return step, draw, lambda: ball.r >= R[0] - 8

def _colorfight(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H)
    teams = 3 if len(palette) > 2 else 2
    balls = _spread(cx, cy, rng, palette, speed, teams * 6, r=11, teams=teams)
    seen = set(); won = [False]
    def step(dt, hits):
        for b in balls:
            _move(b, dt); _bounce_arena(b, arena, cx, cy, hits)
        for a, b in _fresh_pairs(balls, seen):
            if a.team != b.team and rng.random() < 0.55:
                if rng.random() < 0.5:
                    b.team, b.color = a.team, a.color
                else:
                    a.team, a.color = b.team, b.color
        won[0] = len({b.team for b in balls}) == 1
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: won[0]

def _paint(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); ball = _mk(cx, cy, rng, palette, speed, 16); dots = []
    def step(dt, hits):
        _move(ball, dt)
        if _bounce_arena(ball, arena, cx, cy, hits):
            ball.color = rng.choice(palette)
        dots.append((ball.x, ball.y, ball.color, ball.r * 0.9))
        if len(dots) > 420:
            del dots[:40]
    def draw(d, Ww, Hh):
        for x, y, c, r in dots:
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        _draw_arena(d, arena, cx, cy); _draw_ball(d, ball)
    return step, draw, lambda: len(dots) >= 380

def _merge(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H)
    balls = _spread(cx, cy, rng, palette, speed, 12, r=12, teams=3)
    seen = set()
    def step(dt, hits):
        live = [b for b in balls if b.alive]
        for b in live:
            _move(b, dt); _bounce_arena(b, arena, cx, cy, hits)
        for a, b in _fresh_pairs(live, seen):
            if a.team == b.team and a.alive and b.alive:
                a.r = min(46, math.sqrt(a.r * a.r + b.r * b.r)); b.alive = False
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            if b.alive:
                _draw_ball(d, b)
    return step, draw, lambda: sum(1 for b in balls if b.alive) <= 3

def _king(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H)
    balls = _spread(cx, cy, rng, palette, speed, 12, r=13, teams=3)
    seen = set()
    grace = [90]
    def step(dt, hits):
        grace[0] = max(0, grace[0] - 1)
        live = [b for b in balls if b.alive]
        for b in live:
            _move(b, dt); _bounce_arena(b, arena, cx, cy, hits)
        if grace[0]:
            list(_collide(live))
            return
        for a, b in _fresh_pairs(live, seen):
            if a.r > b.r + 1.2:
                a.r = min(44, a.r + 2.2); b.alive = False
            elif b.r > a.r + 1.2:
                b.r = min(44, b.r + 2.2); a.alive = False
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            if b.alive:
                _draw_ball(d, b)
    return step, draw, lambda: sum(1 for b in balls if b.alive) == 1

def _swarm(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); balls = _spread(cx, cy, rng, palette, speed, 10, r=12, teams=10); n = [0]
    def step(dt, hits):
        for b in balls:
            _move(b, dt)
            if _bounce_arena(b, arena, cx, cy, hits):
                n[0] += 1
        list(_collide(balls))
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: n[0] >= 80

def _spawn(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); balls = [_mk(cx, cy, rng, palette, speed, 13)]
    def step(dt, hits):
        born = []
        for b in balls:
            _move(b, dt)
            if _bounce_arena(b, arena, cx, cy, hits) and len(balls) + len(born) < 16 and rng.random() < 0.4:
                nb = _mk(b.x, b.y, rng, palette, speed, max(8, b.r * 0.7), team=len(balls)); nb.x, nb.y = b.x, b.y; born.append(nb)
        balls.extend(born); list(_collide(balls))
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: len(balls) >= 14

def _rings(cx, cy, speed, palette, rng):
    radii = [95.0, 155.0, 215.0, 275.0]
    gaps = [rng.uniform(0.55, 0.85) for _ in radii]
    speeds = [rng.choice([-1, 1]) * rng.uniform(0.7, 1.6) * speed for _ in radii]
    angles = [rng.random() * math.tau for _ in radii]
    ball = _mk(cx, cy, rng, palette, speed, 11); ball.x, ball.y = cx, cy; escaped = [False]
    def step(dt, hits):
        _move(ball, dt)
        for k, R in enumerate(radii):
            angles[k] += speeds[k] * dt
            dx, dy = ball.x - cx, ball.y - cy; dist = math.hypot(dx, dy) or 0.001
            if abs(dist - R) > ball.r + 3:
                continue
            if abs(_wrap(math.atan2(dy, dx) - angles[k])) < gaps[k] / 2:
                continue
            nx, ny = dx / dist, dy / dist; outward = dist >= R; dot = ball.vx * nx + ball.vy * ny
            if (outward and dot > 0) or ((not outward) and dot < 0):
                ball.vx -= 2 * dot * nx; ball.vy -= 2 * dot * ny; hits[0] += 1
            side = 1 if outward else -1
            ball.x = cx + nx * (R - side * (ball.r + 2)); ball.y = cy + ny * (R - side * (ball.r + 2))
        if math.hypot(ball.x - cx, ball.y - cy) > 310:
            escaped[0] = True
    def draw(d, W, H):
        for k, R in enumerate(radii):
            _ring_gap(d, cx, cy, R, angles[k], gaps[k])
        _draw_ball(d, ball)
    return step, draw, lambda: escaped[0]

def _race(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H)
    a = _mk(cx - 70, cy - 40, rng, palette, speed, 12, 0)
    b = _mk(cx + 70, cy + 40, rng, palette, speed, 12, 1)
    cap = arena.get("R", 240) - 8
    def step(dt, hits):
        for ball in (a, b):
            _move(ball, dt)
            if _bounce_arena(ball, arena, cx, cy, hits):
                ball.r = min(ball.r + 2.6, cap)
        list(_collide([a, b]))
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy); _draw_ball(d, a); _draw_ball(d, b)
    return step, draw, lambda: a.r >= cap - 1 or b.r >= cap - 1

def _split(cx, cy, W, H, shape, speed, palette, rng):
    arena = _arena(shape, cx, cy, W, H); balls = [_mk(cx, cy, rng, palette, speed, 18)]
    def step(dt, hits):
        born = []
        for b in list(balls):
            _move(b, dt)
            if _bounce_arena(b, arena, cx, cy, hits) and b.r > 9 and len(balls) + len(born) < 18:
                b.r *= 0.72; born.append(Ball(b.x, b.y, -b.vy, b.vx, b.r, rng.choice(palette)))
        balls.extend(born); list(_collide(balls))
    def draw(d, Ww, Hh):
        _draw_arena(d, arena, cx, cy)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: len(balls) >= 14

def _hit_polygon(ball, pts):
    hit = False; n = len(pts)
    for i in range(n):
        if _reflect_segment(ball, *pts[i], *pts[(i + 1) % n]):
            hit = True
    return hit

def _reflect_segment(ball, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1; ln = math.hypot(vx, vy) or 1.0; nx, ny = -vy / ln, vx / ln
    px, py = ball.x - x1, ball.y - y1; side = px * nx + py * ny; t = (px * vx + py * vy) / (ln * ln)
    if t < -0.02 or t > 1.02 or abs(side) > ball.r + 1.2:
        return False
    if side < 0:
        nx, ny, side = -nx, -ny, -side
    dot = ball.vx * nx + ball.vy * ny
    if dot < 0:
        ball.vx -= 2 * dot * nx; ball.vy -= 2 * dot * ny
        ball.x += nx * (ball.r + 1.2 - side); ball.y += ny * (ball.r + 1.2 - side)
        return True
    return False

def _wrap(a):
    while a > math.pi:
        a -= math.tau
    while a < -math.pi:
        a += math.tau
    return a

def _ring_gap(draw, cx, cy, R, mid, gap):
    steps = 90
    for i in range(steps):
        a0 = i / steps * math.tau; a1 = (i + 1) / steps * math.tau
        if abs(_wrap((a0 + a1) / 2 - mid)) < gap / 2:
            continue
        draw.line([cx + R * math.cos(a0), cy + R * math.sin(a0), cx + R * math.cos(a1), cy + R * math.sin(a1)], fill=INK, width=6)

def _scale_only(video, dest, duration, W, H):
    cmd = ["ffmpeg", "-y", "-i", str(video), "-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=44100:cl=stereo", "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(dest)]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        raise RuntimeError("Could not scale simulation")

def _write_meta(sim_type, shape, duration, out_root):
    title = f"{sim_type} {shape} simulation"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", f"Silent {title}. No voice. No captions.\n\n#Shorts #satisfying #simulation\n")
    save_text(out_root / "hashtags.txt", "#Shorts #satisfying #simulation\n")
    save_text(out_root / "tags.txt", "simulation,satisfying,shorts\n")
