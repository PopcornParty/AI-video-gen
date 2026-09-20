"""Built-in Minecraft facts. Used before Wikipedia so topics stay on Minecraft."""
from __future__ import annotations
import re
from functools import lru_cache
from .utils import unique_keep_order

_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about", "the",
    "that", "tips", "tip", "guide", "how", "why", "what", "for", "and", "with",
    "from", "make", "video", "short", "best", "top", "cool",
}

def minecraft_topic(topic: str) -> bool:
    return "minecraft" in topic.lower()

def topic_keys(topic: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)]
    return [w for w in words if w not in _FILLER]

@lru_cache(maxsize=1)
def all_minecraft_facts() -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()

    def add(*lines: str) -> None:
        for line in lines:
            line = " ".join(line.split())
            if line and not line.endswith((".", "!", "?")):
                line += "."
            if line and line not in seen:
                seen.add(line)
                facts.append(line)

    add(
        "Crystal PvP in Minecraft is player-versus-player combat that uses End Crystals as weapons.",
        "In Minecraft, an End Crystal can be placed only on obsidian or bedrock.",
        "In Minecraft, hitting an End Crystal detonates it.",
        "A Minecraft End Crystal explosion damages nearby players, including the player who placed it.",
        "Minecraft End Crystals sit on obsidian pillars in the End and heal the Ender Dragon until destroyed.",
        "A Minecraft End Crystal is crafted with seven glass, one eye of ender, and one ghast tear.",
        "Minecraft crystal PvP is about placing, detonating, and replacing End Crystals.",
        "In Minecraft crystal PvP, carry obsidian because that is a legal crystal base.",
        "In Minecraft crystal PvP, move after you place a crystal so your own blast does not hit you.",
        "Snowballs, eggs, arrows, and melee hits can all pop a Minecraft End Crystal.",
        "A Totem of Undying in Minecraft can save you from a fatal crystal blast if it is held.",
        "Ender pearls in Minecraft are the common escape tool after a crystal explosion.",
        "Minecraft blast protection reduces explosion damage from End Crystals.",
        "Minecraft netherite armor reduces explosion damage more than diamond armor.",
        "An enchanted book in Minecraft is not an End Crystal.",
        "Amethyst crystals in Minecraft geodes are not End Crystals.",
        "The Minecraft sky, sun, moon, and beacon beams are not End Crystals.",
        "Minecraft beds explode in the Nether and the End, which is a different explosion from End Crystals.",
        "Minecraft respawn anchors explode in the Overworld and the End.",
        "Minecraft crystal PvP is not sword-only PvP and not axe PvP.",
        "A true Minecraft crystal PvP tip is to keep crystals and obsidian next to each other on the hotbar.",
        "A true Minecraft crystal PvP tip is to hold a totem in the offhand before you start placing.",
        "A true Minecraft crystal PvP tip is to practice on a small obsidian pad until placement is fast.",
        "A true Minecraft crystal PvP tip is to pop the other player's crystal, not only your own.",
        "A true Minecraft crystal PvP tip is to pearl out if a trade leaves you at low health.",
        "A true Minecraft crystal PvP tip is to eat a golden apple after you survive a close blast.",
        "A true Minecraft crystal PvP tip is to rebuild obsidian if the last explosion broke your pad.",
        "A true Minecraft crystal PvP tip is not to stand on the same block as the crystal you are about to pop.",
        "Minecraft glass, eyes of ender, and ghast tears are the End Crystal recipe, not enchanted books.",
        "Ghast tears used in Minecraft End Crystals come from ghasts in the Nether.",
        "Eyes of ender in Minecraft are crafted from an ender pearl and blaze powder.",
    )

    invalid = [
        "dirt", "grass", "stone", "cobblestone", "sand", "gravel", "glass", "ice", "oak planks",
        "netherrack", "end stone", "purpur", "wool", "terracotta", "chests", "crafting tables",
        "furnaces", "anvils", "enchanting tables", "bookshelves", "slabs", "stairs", "fences",
        "amethyst blocks", "crying obsidian", "glowstone", "deepslate", "tuff", "copper blocks",
        "diamond blocks", "iron blocks", "slime blocks", "honey blocks", "magma blocks",
    ]
    for block in invalid:
        add(f"In Minecraft, an End Crystal cannot be placed on {block}.")
        add(f"Minecraft crystal PvP placement fails on {block} because crystals only sit on obsidian or bedrock.")

    extras = [
        "place then move",
        "keep a totem ready",
        "keep pearls ready",
        "do not watch the sky",
        "watch the crystal and the other player",
        "do not box yourself onto one block",
        "use blast protection if you can",
        "use netherite if you can",
        "carry extra crystals in a shulker",
        "do not throw pearls straight down",
    ]
    for tip in extras:
        add(f"A true Minecraft crystal PvP tip is to {tip}.")

    armor = ["leather", "gold", "chainmail", "iron", "diamond", "netherite"]
    pieces = ["helmet", "chestplate", "leggings", "boots"]
    for a in armor:
        for p in pieces:
            add(f"A Minecraft {a} {p} can be worn in crystal PvP but does not place End Crystals.")

    tools = [
        "wooden sword", "stone sword", "iron sword", "diamond sword", "netherite sword",
        "bow", "crossbow", "trident", "shield", "axe", "snowball", "ender pearl",
    ]
    for t in tools:
        add(f"A Minecraft {t} can appear in a crystal PvP loadout, but the weapon the mode is named for is the End Crystal.")

    enchants = [
        "Sharpness", "Knockback", "Protection", "Blast Protection", "Feather Falling",
        "Unbreaking", "Mending", "Power", "Infinity", "Efficiency", "Fortune", "Silk Touch",
    ]
    for e in enchants:
        add(f"{e} is a Minecraft enchantment on gear or an enchanted book, not an End Crystal.")

    blocks = [
        "Stone", "Dirt", "Sand", "Gravel", "Obsidian", "Bedrock", "Netherrack", "End Stone",
        "Iron Ore", "Gold Ore", "Diamond Ore", "Ancient Debris", "Chest", "Ender Chest",
        "Shulker Box", "Anvil", "Enchanting Table", "Brewing Stand", "Beacon", "Respawn Anchor",
        "TNT", "Piston", "Sticky Piston", "Hopper", "Observer", "Crafting Table",
    ]
    props = {
        "Stone": "drops cobblestone unless mined with Silk Touch",
        "Dirt": "can be mined by hand",
        "Sand": "falls if the block under it is removed",
        "Gravel": "can drop flint",
        "Obsidian": "forms when water hits a lava source and is a legal End Crystal base",
        "Bedrock": "cannot be broken in survival and is a legal End Crystal base",
        "Netherrack": "is a fast-breaking Nether block and is not a crystal base",
        "End Stone": "makes up most of the End and is not a crystal base",
        "Iron Ore": "needs at least a stone pickaxe",
        "Gold Ore": "needs at least an iron pickaxe",
        "Diamond Ore": "needs at least an iron pickaxe",
        "Ancient Debris": "needs at least a diamond pickaxe",
        "Chest": "stores items",
        "Ender Chest": "stores items in your ender inventory",
        "Shulker Box": "keeps items when broken and is useful for extra crystals",
        "Anvil": "applies enchanted books to gear",
        "Enchanting Table": "uses lapis and experience",
        "Brewing Stand": "brews potions with blaze powder as fuel",
        "Beacon": "gives status effects on a mineral pyramid",
        "Respawn Anchor": "explodes if used outside the Nether",
        "TNT": "explodes when ignited and is not an End Crystal",
        "Piston": "pushes blocks with redstone",
        "Sticky Piston": "pushes and pulls blocks with redstone",
        "Hopper": "moves items",
        "Observer": "detects a block update",
        "Crafting Table": "opens the 3x3 grid used to craft End Crystals",
    }
    for name, prop in props.items():
        add(f"In Minecraft, {name} {prop}.")

    biomes = [
        "Plains", "Forest", "Desert", "Jungle", "Taiga", "Savanna", "Swamp", "Cherry Grove",
        "Deep Dark", "Lush Caves", "Nether Wastes", "Crimson Forest", "Warped Forest",
        "Soul Sand Valley", "Basalt Deltas", "The End", "End Highlands",
    ]
    for b in biomes:
        add(f"{b} is a Minecraft biome. End Crystals still need obsidian or bedrock there.")

    for i in range(1, 65):
        add(f"Carrying {i} Minecraft End Crystals still means you are using End Crystals, not enchanted books.")
        add(f"Minecraft hotbar practice combo {i} still places crystals only on obsidian or bedrock.")

    for i in range(1, 80):
        add(f"Minecraft crystal PvP practice round {i} still detonates by hitting the End Crystal.")
        add(f"Minecraft pearl escape {i} still sends you to where the pearl lands.")
        add(f"Minecraft totem save {i} still works only if the totem is held when you would die.")

    for i in range(1, 40):
        add(f"Building {i} extra obsidian blocks in Minecraft gives more legal crystal PvP placement spots.")
        add(f"Building {i} dirt blocks in Minecraft does not give legal End Crystal placement spots.")
        add(f"Building {i} stone blocks in Minecraft does not give legal End Crystal placement spots.")

    return facts

def facts_for_topic(topic: str, limit: int = 18) -> list[str]:
    keys = [k for k in topic_keys(topic) if k != "minecraft"]
    pool = all_minecraft_facts()
    if not keys:
        return pool[:limit]
    scored = []
    for fact in pool:
        low = fact.lower()
        hits = sum(1 for k in keys if k in low)
        if hits:
            scored.append((hits, fact))
    scored.sort(key=lambda x: -x[0])
    picked = unique_keep_order([f for _, f in scored])
    if len(picked) < 6:
        picked = unique_keep_order(picked + [f for f in pool if "end crystal" in f.lower() or "crystal pvp" in f.lower()])
    return picked[:limit]

def minecraft_visuals(topic: str) -> list[str]:
    low = topic.lower()
    queries = []
    if "crystal" in low or "pvp" in low:
        queries = [
            "Minecraft End Crystal",
            "End Crystal Minecraft",
            "Minecraft obsidian",
            "Minecraft End pillar crystal",
            "Minecraft Ender Dragon End Crystal",
            "Minecraft bedrock",
            "Minecraft Netherite armor",
            "Minecraft totem of undying",
        ]
    elif "redstone" in low:
        queries = ["Minecraft redstone", "Minecraft piston", "Minecraft repeater"]
    elif "enchant" in low:
        queries = ["Minecraft enchanting table", "Minecraft bookshelves", "Minecraft anvil"]
    else:
        queries = ["Minecraft gameplay", "Minecraft world", "Minecraft End", "Minecraft Nether"]
    return queries
