"""Minecraft-only topic lineup plus category / random / prompt picker."""
from __future__ import annotations
import random
from typing import Optional

ANGLES = ["facts", "tips", "how it actually works", "simple rules", "beginner guide"]
WRAPPERS = ["{subject} {angle}", "{subject}: {angle}"]

CATEGORIES: dict[str, list[str]] = {
    "crystal-pvp": ["Minecraft crystal PvP", "Minecraft End Crystals", "Minecraft crystal placement"],
    "pvp": ["Minecraft Java combat", "Minecraft sword PvP", "Minecraft shields"],
    "redstone": ["Minecraft redstone", "Minecraft pistons", "Minecraft hoppers"],
    "nether": ["Minecraft Nether portals", "Minecraft netherite", "Minecraft ancient debris"],
    "end": ["Minecraft Ender Dragon", "Minecraft elytra", "Minecraft end cities"],
    "enchanting": ["Minecraft enchanting table", "Minecraft mending", "Minecraft silk touch"],
    "mobs": ["Minecraft creepers", "Minecraft endermen", "Minecraft wardens"],
    "items": ["Minecraft totem of undying", "Minecraft golden apples", "Minecraft ender pearls"],
    "building": ["Minecraft obsidian", "Minecraft scaffolding", "Minecraft beacons"],
    "simulation": ["Minecraft simulation"],
}

def category_names() -> list[str]:
    return list(CATEGORIES.keys())

def lineup_size() -> int:
    total = 0
    for subjects in CATEGORIES.values():
        total += len(subjects) * len(ANGLES) * len(WRAPPERS)
    return total

def pick_topic(mode: str, category: Optional[str] = None, prompt: Optional[str] = None) -> str:
    mode = (mode or "prompt").strip().lower()
    prompt = (prompt or "").strip()
    if prompt:
        return prompt
    if mode == "random":
        cat = category if category in CATEGORIES and category != "simulation" else random.choice([c for c in category_names() if c != "simulation"])
        return _random_in_category(cat)
    if mode == "category":
        cat = category if category in CATEGORIES else "items"
        if cat == "simulation":
            return "Minecraft simulation"
        return _random_in_category(cat)
    return _random_in_category("items")

def _random_in_category(category: str) -> str:
    subjects = CATEGORIES[category]
    subject = random.choice(subjects)
    angle = random.choice(ANGLES)
    wrapper = random.choice(WRAPPERS)
    return wrapper.format(subject=subject, angle=angle)
