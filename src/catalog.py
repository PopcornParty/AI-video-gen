"""Huge topic lineup plus category / random / prompt picker."""
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
    "advanced basics",
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
    "minecraft": [
        "Minecraft crystal PvP", "Minecraft End Crystals", "Minecraft obsidian",
        "Minecraft totem of undying", "Minecraft ender pearls", "Minecraft netherite",
        "Minecraft blast protection", "Minecraft redstone", "Minecraft pistons",
        "Minecraft enchanting table", "Minecraft villagers", "Minecraft Ender Dragon",
        "Minecraft Nether portals", "Minecraft elytra", "Minecraft shulker boxes",
        "Minecraft golden apples", "Minecraft brewing", "Minecraft beacons",
        "Minecraft wardens", "Minecraft ocean monuments", "Minecraft raids",
        "Minecraft iron farms basics", "Minecraft villager trading", "Minecraft fortune",
        "Minecraft silk touch", "Minecraft mending", "Minecraft boats",
        "Minecraft water bucket clutch", "Minecraft scaffolding", "Minecraft hoppers",
        "Minecraft comparators", "Minecraft observers", "Minecraft note blocks",
        "Minecraft ancient debris", "Minecraft bastions", "Minecraft fortress blaze rods",
        "Minecraft end cities", "Minecraft chorus fruit", "Minecraft respawn anchors",
        "Minecraft beds in the Nether", "Minecraft shields", "Minecraft axes in PvP",
        "Minecraft Java combat cooldown", "Minecraft offhand totems", "Minecraft crystal placement",
    ],
    "space": [
        "the Moon", "Mars", "Jupiter", "Saturn's rings", "Venus", "Mercury",
        "Neptune", "Uranus", "Pluto", "the Sun", "black holes", "neutron stars",
        "the Milky Way", "the Orion Nebula", "comets", "asteroids", "the ISS",
        "Earth's magnetic field", "solar wind", "eclipses", "tides and the Moon",
        "light years", "constellations", "the Kuiper Belt", "the Oort Cloud",
    ],
    "ocean": [
        "coral reefs", "whales", "octopuses", "great white sharks", "sea turtles",
        "hydrothermal vents", "the Mariana Trench", "tides", "waves", "plankton",
        "kelp forests", "dolphins", "manta rays", "deep sea fish", "ocean currents",
    ],
    "animals": [
        "honeybees", "elephants", "penguins", "owls", "wolves", "octopuses",
        "cheetahs", "giraffes", "crocodiles", "frogs", "bats", "ants",
        "migrating birds", "hummingbirds", "polar bears", "kangaroos",
    ],
    "volcanoes": [
        "how volcanoes erupt", "lava vs magma", "shield volcanoes", "stratovolcanoes",
        "volcanic ash", "calderas", "hot spots", "Mount Vesuvius", "Mauna Loa",
        "geyser basics", "volcanic lightning",
    ],
    "engineering": [
        "suspension bridges", "skyscraper foundations", "dams", "tunnels",
        "high speed trains", "wind turbines", "solar panels", "gears",
        "levers", "pulleys", "arches", "cantilevers",
    ],
    "weather": [
        "lightning", "thunder", "hurricanes", "tornadoes", "rainbows",
        "snowflakes", "hail", "fog", "clouds", "the water cycle",
    ],
    "inventions": [
        "the printing press", "the compass", "the steam engine", "the airplane",
        "the light bulb", "radio", "GPS", "the World Wide Web", "vaccines history basics",
        "refrigeration", "paper", "the wheel",
    ],
    "human-body": [
        "bones", "muscles", "the heart", "the lungs", "the brain",
        "red blood cells", "skin", "eyes", "ears", "digestion",
    ],
}

def category_names() -> list[str]:
    return list(CATEGORIES.keys())

def lineup_size() -> int:
    total = 0
    for subjects in CATEGORIES.values():
        total += len(subjects) * len(ANGLES) * len(WRAPPERS)
    return total

def iter_lineup():
    for category, subjects in CATEGORIES.items():
        for subject in subjects:
            for angle in ANGLES:
                for wrapper in WRAPPERS:
                    yield category, wrapper.format(subject=subject, angle=angle)

def topic_at(index: int) -> tuple[str, str]:
    size = lineup_size()
    index = index % size
    for i, item in enumerate(iter_lineup()):
        if i == index:
            return item
    return "minecraft", "Minecraft crystal PvP tips"

def pick_topic(mode: str, category: Optional[str] = None, prompt: Optional[str] = None) -> str:
    mode = (mode or "prompt").strip().lower()
    prompt = (prompt or "").strip()
    if mode == "prompt" and prompt:
        return prompt
    if mode == "random":
        if category and category in CATEGORIES:
            return _random_in_category(category)
        _cat, topic = topic_at(random.randrange(lineup_size()))
        return topic
    if mode == "category":
        cat = category if category in CATEGORIES else "minecraft"
        return _random_in_category(cat)
    if prompt:
        return prompt
    return _random_in_category("minecraft")

def _random_in_category(category: str) -> str:
    subjects = CATEGORIES[category]
    subject = random.choice(subjects)
    angle = random.choice(ANGLES)
    wrapper = random.choice(WRAPPERS)
    return wrapper.format(subject=subject, angle=angle)
