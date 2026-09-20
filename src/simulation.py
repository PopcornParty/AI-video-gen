"""Silent satisfying physics simulations. No voice, no captions."""
from __future__ import annotations
import math
import random
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image, ImageDraw
from .utils import ensure_dir, info, save_text, warn

TYPES = {
    "grow": "One ball. Each wall hit makes it bigger until it fills the circle.",
    "shrink": "The circle gets smaller every bounce until the ball barely fits.",
    "squeeze": "Ball grows and the circle shrinks at the same time.",
    "swarm": "Many balls bounce around inside one circle.",
    "spawn": "A bounce can add another ball. Stops when the circle is crowded.",
    "box": "Same grow idea, but inside a square.",
    "triangle": "Same grow idea, but inside a triangle.",
    "hexagon": "Same grow idea, but inside a hexagon.",
    "rings": "Ball tries to slip through gaps in rotating rings.",
    "race": "Blue vs pink. First one to fill the circle wins.",
    "gravity": "Balls fall and bounce in a bowl until they settle.",
    "split": "Each bounce can split one ball into two.",
    "orbit": "Balls skim the rim and leave long trails.",
    "paddle": "A spinning gap-ring. The ball has to find the opening.",
    "random": "Pick a random simulation type each run.",
}

PALETTE = [
    (70, 190, 255), (255, 95, 130), (120, 255, 160),
    (255, 210, 70), (200, 140, 255), (255, 160, 80),
]
BG = (8, 8, 14)
INK = (230, 230, 240)
MAX_SECONDS = 58.0
HOLD_AFTER = 1.4

def simulation_types() -> list[str]:
    return [k for k in TYPES if k != "random"]

def render_simulation(sim_type: str, duration: float, cfg: dict, out_root: Path, work_dir: Path) -> Path:
    rng = random.Random(time.time_ns())
    sim_type = (sim_type or "grow").lower().strip()
    if sim_type == "random" or sim_type not in TYPES:
        sim_type = rng.choice(simulation_types())
    W, H, fps = 540, 960, 30
    ensure_dir(work_dir)
    ensure_dir(out_root)
    raw = work_dir / "simulation.mp4"
    info(f"Simulation: {sim_type} — {TYPES[sim_type]}")
    seconds = _encode(sim_type, fps, W, H, raw, rng)
    info(f"Simulation finished at {seconds:.1f}s")
    final = out_root / "video.mp4"
    _finish(raw, seconds, int(cfg["video"]["width"]), int(cfg["video"]["height"]), work_dir, final, rng)
    _write_meta(sim_type, seconds, out_root)
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

def _encode(sim_type, fps, W, H, dest: Path, rng: random.Random) -> float:
    cx, cy = W / 2.0, H / 2.0
    step_fn, draw_fn, done_fn = {
        "grow": lambda: _grow(cx, cy, rng),
        "shrink": lambda: _shrink(cx, cy, rng),
        "squeeze": lambda: _squeeze(cx, cy, rng),
        "swarm": lambda: _swarm(cx, cy, rng),
        "spawn": lambda: _spawn(cx, cy, rng),
        "box": lambda: _box(cx, cy, W, H, rng),
        "triangle": lambda: _triangle(cx, cy, rng),
        "hexagon": lambda: _hexagon(cx, cy, rng),
        "rings": lambda: _rings(cx, cy, rng),
        "race": lambda: _race(cx, cy, rng),
        "gravity": lambda: _gravity(cx, cy, rng),
        "split": lambda: _split(cx, cy, rng),
        "orbit": lambda: _orbit(cx, cy, rng),
        "paddle": lambda: _paddle(cx, cy, rng),
    }[sim_type]()
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", str(dest),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    dt = 1.0 / fps
    max_frames = int(MAX_SECONDS * fps)
    hold_frames = int(HOLD_AFTER * fps)
    finished_at = None
    frame = 0
    try:
        while frame < max_frames:
            for _ in range(3):
                step_fn(dt / 3)
            if finished_at is None and done_fn():
                finished_at = frame
            img = Image.new("RGB", (W, H), BG)
            draw_fn(ImageDraw.Draw(img), W, H)
            proc.stdin.write(img.tobytes())
            frame += 1
            if finished_at is not None and frame - finished_at >= hold_frames:
                break
    finally:
        proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
    if proc.wait() != 0 or not dest.exists():
        raise RuntimeError("ffmpeg sim encode failed: " + err[-400:])
    return frame / fps

def _move(ball: Ball, dt, gravity=0.0):
    ball.vy += gravity * dt
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt
    ball.trail.append((ball.x, ball.y))
    del ball.trail[:-18]

def _circle_hit(ball, cx, cy, R):
    dx, dy = ball.x - cx, ball.y - cy
    dist = math.hypot(dx, dy) or 0.001
    return dist + ball.r >= R - 0.01, dx, dy, dist

def _resolve_circle(ball, cx, cy, R, dx, dy, dist):
    nx, ny = dx / dist, dy / dist
    limit = max(2.0, R - ball.r - 0.6)
    ball.x = cx + nx * limit
    ball.y = cy + ny * limit
    dot = ball.vx * nx + ball.vy * ny
    if dot > 0:
        ball.vx -= 2.0 * dot * nx
        ball.vy -= 2.0 * dot * ny
    speed = math.hypot(ball.vx, ball.vy)
    if speed < 100:
        s = 150 / max(speed, 1)
        ball.vx *= s
        ball.vy *= s

def _new_bounce(ball, hitting):
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

def _rand_ball(cx, cy, rng, r=14):
    ang = rng.random() * math.tau
    spd = rng.uniform(180, 280)
    return Ball(
        cx + rng.uniform(-24, 24),
        cy + rng.uniform(-24, 24),
        math.cos(ang) * spd,
        math.sin(ang) * spd,
        r,
        rng.choice(PALETTE),
    )

def _grow(cx, cy, rng):
    R = rng.uniform(236, 258)
    grow = rng.uniform(3.6, 5.4)
    ball = _rand_ball(cx, cy, rng, rng.uniform(12, 16))
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R)
        if hitting:
            if _new_bounce(ball, True):
                ball.r = min(ball.r + grow, R - 6)
            _resolve_circle(ball, cx, cy, R, dx, dy, dist)
        else:
            ball.touching = False
    return step, lambda d, W, H: (_draw_circle(d, cx, cy, R), _draw_ball(d, ball)), lambda: ball.r >= R - 7

def _shrink(cx, cy, rng):
    R = [rng.uniform(250, 272)]
    cut = rng.uniform(5.0, 7.5)
    ball = _rand_ball(cx, cy, rng, 16)
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R[0])
        if hitting:
            if _new_bounce(ball, True):
                R[0] = max(ball.r + 8, R[0] - cut)
            _resolve_circle(ball, cx, cy, R[0], dx, dy, dist)
        else:
            ball.touching = False
    return step, lambda d, W, H: (_draw_circle(d, cx, cy, R[0], (255, 170, 185)), _draw_ball(d, ball)), lambda: R[0] <= ball.r + 9

def _squeeze(cx, cy, rng):
    R = [rng.uniform(248, 268)]
    ball = _rand_ball(cx, cy, rng, 13)
    def step(dt):
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R[0])
        if hitting:
            if _new_bounce(ball, True):
                ball.r = min(ball.r + 3.0, R[0] - 7)
                R[0] = max(ball.r + 7, R[0] - 3.6)
            _resolve_circle(ball, cx, cy, R[0], dx, dy, dist)
        else:
            ball.touching = False
    return step, lambda d, W, H: (_draw_circle(d, cx, cy, R[0], (255, 230, 140)), _draw_ball(d, ball)), lambda: ball.r >= R[0] - 8

def _swarm(cx, cy, rng):
    R = 252
    balls = [_rand_ball(cx, cy, rng, rng.uniform(10, 15)) for _ in range(rng.randint(6, 10))]
    bounces = [0]
    def step(dt):
        for b in balls:
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                if _new_bounce(b, True):
                    bounces[0] += 1
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
            else:
                b.touching = False
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: bounces[0] >= 70

def _spawn(cx, cy, rng):
    R = 250
    balls = [_rand_ball(cx, cy, rng, 13)]
    def step(dt):
        born = []
        for b in balls:
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                if _new_bounce(b, True) and len(balls) + len(born) < 18 and rng.random() < 0.42:
                    born.append(_rand_ball(b.x, b.y, rng, max(8, b.r * 0.7)))
                    born[-1].x, born[-1].y = b.x, b.y
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
            else:
                b.touching = False
        balls.extend(born)
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: len(balls) >= 16

def _box(cx, cy, W, H, rng):
    left, top, right, bottom = 80.0, 190.0, W - 80.0, H - 190.0
    ball = _rand_ball(cx, cy, rng, 16)
    max_r = min((right - left) / 2 - 6, (bottom - top) / 2 - 6)
    def step(dt):
        _move(ball, dt)
        hitting = False
        if ball.x - ball.r <= left:
            ball.x = left + ball.r + 0.5; ball.vx = abs(ball.vx); hitting = True
        elif ball.x + ball.r >= right:
            ball.x = right - ball.r - 0.5; ball.vx = -abs(ball.vx); hitting = True
        if ball.y - ball.r <= top:
            ball.y = top + ball.r + 0.5; ball.vy = abs(ball.vy); hitting = True
        elif ball.y + ball.r >= bottom:
            ball.y = bottom - ball.r - 0.5; ball.vy = -abs(ball.vy); hitting = True
        if _new_bounce(ball, hitting):
            ball.r = min(ball.r + 5.0, max_r)
        if not hitting:
            ball.touching = False
    return step, lambda d, Ww, Hh: (d.rectangle([left, top, right, bottom], outline=INK, width=6), _draw_ball(d, ball)), lambda: ball.r >= max_r - 1

def _poly(cx, cy, n, radius, rng):
    rot = rng.random() * math.tau
    return [(cx + radius * math.cos(rot + i * math.tau / n), cy + radius * math.sin(rot + i * math.tau / n)) for i in range(n)]

def _triangle(cx, cy, rng):
    pts = _poly(cx, cy + 20, 3, 250, rng)
    ball = _rand_ball(cx, cy, rng, 15)
    def step(dt):
        _move(ball, dt)
        hitting = _hit_polygon(ball, pts)
        if _new_bounce(ball, hitting):
            ball.r = min(ball.r + 4.2, 80)
        if not hitting:
            ball.touching = False
    return step, lambda d, W, H: (d.line(pts + [pts[0]], fill=INK, width=6), _draw_ball(d, ball)), lambda: ball.r >= 78

def _hexagon(cx, cy, rng):
    pts = _poly(cx, cy, 6, 250, rng)
    ball = _rand_ball(cx, cy, rng, 14)
    def step(dt):
        _move(ball, dt)
        hitting = _hit_polygon(ball, pts)
        if _new_bounce(ball, hitting):
            ball.r = min(ball.r + 4.0, 84)
        if not hitting:
            ball.touching = False
    return step, lambda d, W, H: (d.line(pts + [pts[0]], fill=INK, width=6), _draw_ball(d, ball)), lambda: ball.r >= 82

def _rings(cx, cy, rng):
    radii = [95.0, 155.0, 215.0, 275.0]
    gaps = [rng.uniform(0.6, 0.95) for _ in radii]
    speeds = [rng.choice([-1, 1]) * rng.uniform(0.5, 1.5) for _ in radii]
    angles = [rng.random() * math.tau for _ in radii]
    ball = _rand_ball(cx, cy, rng, 11)
    ball.x, ball.y = cx, cy
    escaped = [False]
    def step(dt):
        _move(ball, dt)
        for k, R in enumerate(radii):
            angles[k] += speeds[k] * dt
            dx, dy = ball.x - cx, ball.y - cy
            dist = math.hypot(dx, dy) or 0.001
            if abs(dist - R) > ball.r + 3:
                continue
            if abs(_wrap(math.atan2(dy, dx) - angles[k])) < gaps[k] / 2:
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
        if math.hypot(ball.x - cx, ball.y - cy) > 310:
            escaped[0] = True
    def draw(d, W, H):
        for k, R in enumerate(radii):
            _ring_gap(d, cx, cy, R, angles[k], gaps[k])
        _draw_ball(d, ball)
    return step, draw, lambda: escaped[0]

def _race(cx, cy, rng):
    R = 252
    a = Ball(cx - 22, cy, -180, -200, 12, (70, 190, 255))
    b = Ball(cx + 22, cy, 190, -170, 12, (255, 95, 130))
    def step(dt):
        for ball in (a, b):
            _move(ball, dt)
            hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R)
            if hitting:
                if _new_bounce(ball, True):
                    ball.r = min(ball.r + 3.0, R - 8)
                _resolve_circle(ball, cx, cy, R, dx, dy, dist)
            else:
                ball.touching = False
        _collide([a, b])
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        _draw_ball(d, a); _draw_ball(d, b)
    return step, draw, lambda: a.r >= R - 9 or b.r >= R - 9

def _gravity(cx, cy, rng):
    R = 258
    balls = [_rand_ball(cx, cy - 80, rng, 13) for _ in range(4)]
    for b in balls:
        b.vy = rng.uniform(-20, 40)
    still = [0]
    def step(dt):
        moving = False
        for b in balls:
            _move(b, dt, gravity=820)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
                b.vx *= 0.985; b.vy *= 0.985
            if math.hypot(b.vx, b.vy) > 40:
                moving = True
        _collide(balls)
        still[0] = 0 if moving else still[0] + 1
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R, (180, 200, 255))
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: still[0] > 45

def _split(cx, cy, rng):
    R = 250
    balls = [_rand_ball(cx, cy, rng, 18)]
    def step(dt):
        born = []
        for b in list(balls):
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                if _new_bounce(b, True) and b.r > 9 and len(balls) + len(born) < 20:
                    b.r *= 0.72
                    twin = Ball(b.x, b.y, -b.vy, b.vx, b.r, rng.choice(PALETTE))
                    born.append(twin)
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
            else:
                b.touching = False
        balls.extend(born)
        _collide(balls)
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: len(balls) >= 14

def _orbit(cx, cy, rng):
    R = 250
    balls = [_rand_ball(cx, cy, rng, rng.uniform(8, 12)) for _ in range(rng.randint(3, 5))]
    laps = [0]
    def step(dt):
        for b in balls:
            _move(b, dt)
            hitting, dx, dy, dist = _circle_hit(b, cx, cy, R)
            if hitting:
                if _new_bounce(b, True):
                    laps[0] += 1
                _resolve_circle(b, cx, cy, R, dx, dy, dist)
            else:
                b.touching = False
    def draw(d, W, H):
        _draw_circle(d, cx, cy, R)
        for b in balls:
            _draw_ball(d, b)
    return step, draw, lambda: laps[0] >= 55

def _paddle(cx, cy, rng):
    R = 240
    gap = rng.uniform(0.7, 1.0)
    ang = [rng.random() * math.tau]
    spd = rng.choice([-1, 1]) * rng.uniform(0.9, 1.6)
    ball = _rand_ball(cx, cy, rng, 12)
    ball.x, ball.y = cx, cy + 20
    escaped = [False]
    def step(dt):
        ang[0] += spd * dt
        _move(ball, dt)
        hitting, dx, dy, dist = _circle_hit(ball, cx, cy, R)
        if hitting:
            a = math.atan2(dy, dx)
            if abs(_wrap(a - ang[0])) < gap / 2:
                escaped[0] = True
            else:
                _resolve_circle(ball, cx, cy, R, dx, dy, dist)
                ball.touching = True
        else:
            ball.touching = False
        if math.hypot(ball.x - cx, ball.y - cy) > 320:
            escaped[0] = True
    def draw(d, W, H):
        _ring_gap(d, cx, cy, R, ang[0], gap)
        _draw_ball(d, ball)
    return step, draw, lambda: escaped[0]

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
            a.x -= nx * overlap / 2; a.y -= ny * overlap / 2
            b.x += nx * overlap / 2; b.y += ny * overlap / 2
            va = a.vx * nx + a.vy * ny
            vb = b.vx * nx + b.vy * ny
            a.vx += (vb - va) * nx; a.vy += (vb - va) * ny
            b.vx += (va - vb) * nx; b.vy += (va - vb) * ny

def _hit_polygon(ball, pts):
    hit = False
    n = len(pts)
    for i in range(n):
        if _reflect_segment(ball, *pts[i], *pts[(i + 1) % n]):
            hit = True
    return hit

def _reflect_segment(ball, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    ln = math.hypot(vx, vy) or 1.0
    nx, ny = -vy / ln, vx / ln
    px, py = ball.x - x1, ball.y - y1
    side = px * nx + py * ny
    t = (px * vx + py * vy) / (ln * ln)
    if t < -0.02 or t > 1.02 or abs(side) > ball.r + 1.2:
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

def _ring_gap(draw, cx, cy, R, mid, gap):
    steps = 96
    for i in range(steps):
        a0 = i / steps * math.tau
        a1 = (i + 1) / steps * math.tau
        if abs(_wrap((a0 + a1) / 2 - mid)) < gap / 2:
            continue
        draw.line(
            [cx + R * math.cos(a0), cy + R * math.sin(a0), cx + R * math.cos(a1), cy + R * math.sin(a1)],
            fill=INK, width=6,
        )

def _finish(video: Path, duration: float, W, H, work_dir: Path, dest: Path, rng: random.Random):
    music = work_dir / "sim_music.m4a"
    f1, f2, f3 = rng.choice([196, 220, 247]), rng.choice([294, 330, 349]), rng.choice([392, 440])
    mus = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"sine=frequency={f1}:sample_rate=44100",
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"sine=frequency={f2}:sample_rate=44100",
        "-f", "lavfi", "-t", f"{duration:.3f}", "-i", f"sine=frequency={f3}:sample_rate=44100",
        "-filter_complex", "amix=inputs=3:duration=longest,volume=0.07,afade=t=in:st=0:d=0.8,afade=t=out:st={max(0, duration-1.2):.2f}:d=1.1",
        "-c:a", "aac", str(music),
    ]
    if subprocess.run(mus, capture_output=True).returncode != 0:
        music = None
    cmd = ["ffmpeg", "-y", "-i", str(video)]
    if music and music.exists():
        cmd += ["-i", str(music), "-filter_complex", f"[0:v]scale={W}:{H}:flags=lanczos[v]", "-map", "[v]", "-map", "1:a"]
    else:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=44100:cl=stereo", "-vf", f"scale={W}:{H}:flags=lanczos"]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        warn((proc.stderr or "")[-300:])
        raise RuntimeError("Could not finish simulation video")

def _write_meta(sim_type, duration, out_root: Path):
    title = TYPES[sim_type].split(".")[0]
    desc = f"{TYPES[sim_type]}\nSilent satisfying simulation. No voice. No captions.\n"
    save_text(out_root / "title.txt", title + "\n")
    save_text(out_root / "description.txt", desc + "\n#Shorts #satisfying #simulation\n")
    save_text(out_root / "hashtags.txt", "#Shorts #satisfying #simulation\n")
    save_text(out_root / "tags.txt", "simulation,satisfying,shorts\n")
