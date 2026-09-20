"""Minecraft-only topic lineup plus category / random / prompt picker."""
from __future__ import annotations
import random
from typing import Optional

ANGLES = [
    "facts",
    "tips",
    "mistakes people make",
    "how it actually works",
    "things nobody explains",
    "simple rules",
    "beginner guide",
]

WRAPPERS = [
    "{subject} {angle}",
    "{subject}: {angle}",
    "the real {subject} {angle}",
]

CATEGORIES: dict[str, list[str]] = {
    "crystal-pvp": [
        "Minecraft crystal PvP", "Minecraft End Crystals", "Minecraft crystal placement",
        "Minecraft obsidian crystal bases", "Minecraft totem of undying in crystal PvP",
    ],
    "pvp": [
        "Minecraft Java combat", "Minecraft sword PvP", "Minecraft axe PvP",
        "Minecraft shields", "Minecraft golden apples in PvP",
    ],
    "redstone": [
        "Minecraft redstone", "Minecraft pistons", "Minecraft hoppers",
        "Minecraft observers", "Minecraft comparators",
    ],
    "nether": [
        "Minecraft Nether portals", "Minecraft netherite", "Minecraft ancient debris",
        "Minecraft beds in the Nether", "Minecraft respawn anchors",
    ],
    "end": [
        "Minecraft Ender Dragon", "Minecraft End Crystals", "Minecraft elytra",
        "Minecraft shulker boxes", "Minecraft end cities",
    ],
    "enchanting": [
        "Minecraft enchanting table", "Minecraft mending", "Minecraft silk touch",
        "Minecraft fortune", "Minecraft anvils",
    ],
    "mobs": [
        "Minecraft creepers", "Minecraft endermen", "Minecraft wardens",
        "Minecraft villagers", "Minecraft evokers",
    ],
    "items": [
        "Minecraft totem of undying", "Minecraft golden apples", "Minecraft ender pearls",
        "Minecraft shulker boxes", "Minecraft elytra",
    ],
    "building": [
        "Minecraft obsidian", "Minecraft scaffolding", "Minecraft beacons",
        "Minecraft copper", "Minecraft amethyst",
    ],
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
        cat = category if category in CATEGORIES else random.choice(category_names())
        return _random_in_category(cat)
    if mode == "category":
        cat = category if category in CATEGORIES else "items"
        return _random_in_category(cat)
    return _random_in_category("items")

def _random_in_category(category: str) -> str:
    subjects = CATEGORIES[category]
    subject = random.choice(subjects)
    angle = random.choice(ANGLES)
    wrapper = random.choice(WRAPPERS)
    return wrapper.format(subject=subject, angle=angle)
