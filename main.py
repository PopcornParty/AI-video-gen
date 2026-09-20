#!/usr/bin/env python3
"""Generate a complete YouTube Short from a topic."""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.audio_pad import pad_audio_to
from src.captions import group_captions, write_srt
from src.catalog import category_names, lineup_size, pick_topic
from src.config_loader import load_config
from src.fact_checker import sources_text
from src.metadata import generate_metadata
from src.music import get_music_track
from src.research import research_topic
from src.scene_generator import build_timed_scenes
from src.script_generator import generate_script
from src.simulation import TYPES, render_simulation, simulation_types
from src.utils import ensure_dir, info, save_json, save_text, slugify, step, warn
from src.video_editor import render_short
from src.visual_search import find_visuals_for_scenes
from src.voice_generator import generate_voice

TOTAL_STEPS = 8

def parse_args():
    parser = argparse.ArgumentParser(description="Generate YouTube Shorts from a topic.")
    parser.add_argument("--topic", "-t", default="")
    parser.add_argument("--mode", choices=["prompt", "category", "random", "simulation"], default="prompt")
    parser.add_argument("--category", default="items")
    parser.add_argument("--simulation-type", default="grow")
    parser.add_argument("--topics-file", default=str(ROOT / "topics.txt"))
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--duration", type=int)
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--all", action="store_true")
    return parser.parse_args()

def load_topics(args):
    if args.mode in {"category", "random", "prompt"} or args.topic.strip():
        topic = pick_topic(args.mode if args.mode != "simulation" else "prompt", args.category, args.topic)
        info(f"Catalog size: {lineup_size():,} possible Minecraft topic lines")
        info(f"Picked topic: {topic}")
        return [topic]
    return [pick_topic("random", "items", "")]

def generate_simulation(args, cfg):
    out_root = ensure_dir(ROOT / cfg.get("output_folder", "output"))
    work_dir = ensure_dir(ROOT / "tmp" / "simulation")
    duration = float(cfg["video"].get("target_duration", 34))
    video = render_simulation(args.simulation_type, duration, cfg, out_root, work_dir)
    print("\nVIDEO COMPLETE\n")
    print(f"Video:\n{video}")
    print("Simulation finished on its own ending. No voice. No captions.")
    return video

def generate_one(topic, cfg):
    video_cfg = cfg["video"]
    target = float(video_cfg.get("target_duration", 32))
    out_root = ensure_dir(ROOT / cfg.get("output_folder", "output"))
    cache_dir = ensure_dir(ROOT / cfg.get("cache_folder", "cache"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(topic)
    run_dir = ensure_dir(out_root / f"{slug}-{stamp}")
    work_dir = ensure_dir(ROOT / "tmp" / f"{slug}-{stamp}")
    print(f"\n=== Generating Short: {topic} ===\n")
    step(1, TOTAL_STEPS, "Researching topic...")
    research = research_topic(topic, language=cfg.get("language", "en"))
    save_json(run_dir / "research.json", research)
    save_text(run_dir / "sources.txt", sources_text(research))
    step(2, TOTAL_STEPS, "Writing script...")
    script = generate_script(research, target_duration=int(target), language=cfg.get("language", "en"))
    save_json(run_dir / "script.json", script)
    save_text(run_dir / "script.txt", script.get("full_narration", ""))
    step(3, TOTAL_STEPS, "Generating voice...")
    voice = generate_voice(script["full_narration"], cache_dir=cache_dir, voice_cfg=cfg["voice"], work_dir=work_dir)
    audio_path = pad_audio_to(Path(voice["audio_path"]), work_dir / "narration_padded.m4a", target)
    shutil.copy2(audio_path, run_dir / "narration.mp3")
    save_json(run_dir / "words.json", voice.get("words") or [])
    audio_duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)], text=True).strip())
    step(4, TOTAL_STEPS, "Finding visuals...")
    scenes = find_visuals_for_scenes(script.get("scenes") or [], topic, cache_dir, cfg.get("visuals") or {})
    step(5, TOTAL_STEPS, "Building scenes...")
    timed = build_timed_scenes(scenes, voice.get("words") or [], audio_duration, target)
    save_json(run_dir / "scenes.json", timed)
    step(6, TOTAL_STEPS, "Creating captions...")
    groups = group_captions(voice.get("words") or [], max_words=int(cfg["captions"].get("max_words_per_line", 5)))
    write_srt(groups, run_dir / "captions.srt")
    music_path = None
    if cfg["music"].get("enabled", True):
        music_path = get_music_track(cache_dir, topic, audio_duration, cfg["music"])
    step(7, TOTAL_STEPS, "Rendering video...")
    video_path = run_dir / "video.mp4"
    render_short(timed, str(audio_path), groups, music_path, video_path, cfg, work_dir)
    shutil.copy2(video_path, out_root / "video.mp4")
    step(8, TOTAL_STEPS, "Creating YouTube metadata...")
    meta = generate_metadata(topic, script, research, run_dir)
    for name in ("title.txt", "description.txt", "tags.txt", "hashtags.txt", "metadata.json"):
        src = run_dir / name
        if src.exists():
            shutil.copy2(src, out_root / name)
    if cfg.get("cleanup_temp", True):
        shutil.rmtree(work_dir, ignore_errors=True)
    print("\nVIDEO COMPLETE\n")
    print(f"Video:\n{video_path}")
    print(f"YouTube title:\n{meta.get('title')}\n")
    return video_path

def main():
    args = parse_args()
    cfg = load_config(Path(args.config))
    if args.duration:
        cfg["video"]["target_duration"] = max(8, min(58, args.duration))
    if args.no_music:
        cfg["music"]["enabled"] = False
    if args.mode == "simulation" or args.category == "simulation":
        try:
            generate_simulation(args, cfg)
            return 0
        except Exception as exc:
            warn(f"Simulation failed: {exc}")
            import traceback
            traceback.print_exc()
            return 1
    if args.category and args.category not in category_names() and args.mode != "prompt":
        warn(f"Unknown category '{args.category}', using items")
        args.category = "items"
    topics = load_topics(args)
    if not topics:
        warn("No topic provided.")
        return 1
    failures = 0
    for topic in topics:
        try:
            generate_one(topic, cfg)
        except Exception as exc:
            failures += 1
            warn(f"Failed to generate '{topic}': {exc}")
            import traceback
            traceback.print_exc()
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
