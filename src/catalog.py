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
    "surprising details",
    "beginner guide",
    "what to do first",
]

WRAPPERS = [
    "{subject} {angle}",
    "true {subject} {angle}",
    "{subject}: {angle}",
    "the real {subject} {angle}",
    "{subject} in 30 seconds",
]

CATEGORIES: dict[str, list[str]] = {
    "crystal-pvp": [
        "Minecraft crystal PvP", "Minecraft End Crystals", "Minecraft crystal placement",
        "Minecraft obsidian crystal bases", "Minecraft crystal detonations",
        "Minecraft totem of undying in crystal PvP", "Minecraft ender pearls in crystal PvP",
        "Minecraft blast protection", "Minecraft crystal PvP hotbar", "Minecraft crystal PvP movement",
    ],
    "pvp": [
        "Minecraft Java combat cooldown", "Minecraft sword PvP", "Minecraft axe PvP",
        "Minecraft shields", "Minecraft offhand totems", "Minecraft golden apples in PvP",
        "Minecraft knockback", "Minecraft ender pearls", "Minecraft water bucket clutch",
    ],
    "redstone": [
        "Minecraft redstone", "Minecraft pistons", "Minecraft sticky pistons",
        "Minecraft repeaters", "Minecraft comparators", "Minecraft observers",
        "Minecraft hoppers", "Minecraft note blocks", "Minecraft target blocks",
    ],
    "nether": [
        "Minecraft Nether portals", "Minecraft ancient debris", "Minecraft netherite",
        "Minecraft bastions", "Minecraft fortress blaze rods", "Minecraft ghasts",
        "Minecraft respawn anchors", "Minecraft beds in the Nether", "Minecraft soul sand",
    ],
    "end": [
        "Minecraft Ender Dragon", "Minecraft End Crystals", "Minecraft end cities",
        "Minecraft elytra", "Minecraft shulker boxes", "Minecraft chorus fruit",
        "Minecraft eyes of ender", "Minecraft End gateways", "Minecraft outer End islands",
    ],
    "enchanting": [
        "Minecraft enchanting table", "Minecraft mending", "Minecraft silk touch",
        "Minecraft fortune", "Minecraft blast protection", "Minecraft sharpness",
        "Minecraft unbreaking", "Minecraft enchanted books", "Minecraft anvils",
    ],
    "mobs": [
        "Minecraft creepers", "Minecraft endermen", "Minecraft wardens",
        "Minecraft villagers", "Minecraft iron golems", "Minecraft raids",
        "Minecraft evokers", "Minecraft shulkers", "Minecraft blazes",
    ],
    "items": [
        "Minecraft totem of undying", "Minecraft golden apples", "Minecraft ender pearls",
        "Minecraft shulker boxes", "Minecraft elytra", "Minecraft netherite",
        "Minecraft shields", "Minecraft fireworks", "Minecraft water buckets",
    ],
    "building": [
        "Minecraft obsidian", "Minecraft scaffolding", "Minecraft deepslate",
        "Minecraft copper", "Minecraft amethyst", "Minecraft dripstone",
        "Minecraft lodestones", "Minecraft beacons", "Minecraft conduits",
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
    if mode == "prompt" and prompt:
        return prompt
    if mode == "random":
        if category and category in CATEGORIES:
            return _random_in_category(category)
        cat = random.choice(category_names())
        return _random_in_category(cat)
    if mode == "category":
        cat = category if category in CATEGORIES else "crystal-pvp"
        return _random_in_category(cat)
    if prompt:
        return prompt
    return _random_in_category("crystal-pvp")

def _random_in_category(category: str) -> str:
    subjects = CATEGORIES[category]
    subject = random.choice(subjects)
    angle = random.choice(ANGLES)
    wrapper = random.choice(WRAPPERS)
    return wrapper.format(subject=subject, angle=angle)
