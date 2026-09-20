"""Built-in Minecraft facts. Prompt words decide which facts and pictures get used."""
from __future__ import annotations
import re
from .utils import unique_keep_order

_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about", "the",
    "that", "tips", "tip", "guide", "how", "why", "what", "for", "and", "with",
    "from", "make", "video", "short", "best", "top", "cool", "true", "real",
    "simple", "rules", "things", "nobody", "explains", "beginner", "seconds",
    "please", "talk", "something",
}

def minecraft_topic(topic: str) -> bool:
    return "minecraft" in topic.lower()

def topic_keys(topic: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)]
    return [w for w in words if w not in _FILLER]

def specific_keys(topic: str) -> list[str]:
    return [k for k in topic_keys(topic) if k != "minecraft"]

def _all_facts() -> list[str]:
    return [
        "Crystal PvP means using End Crystals against another player.",
        "An End Crystal only places on obsidian or bedrock.",
        "Hitting the End Crystal is what makes it explode.",
        "Your own crystal blast can hurt you if you stand too close.",
        "Keep obsidian next to the crystals on your hotbar.",
        "Move right after you place a crystal.",
        "Snowballs and arrows can pop a crystal from a short distance.",
        "A totem in the offhand can save you from a bad crystal blast.",
        "Pearl out if a crystal trade leaves you low.",
        "Enchanted books and amethyst are not End Crystals.",
        "Redstone carries a signal that can power doors, lamps, and pistons.",
        "A redstone torch is a power source and can invert a signal.",
        "Repeaters delay a redstone signal and only send it forward.",
        "Comparators can read how full a chest or hopper is.",
        "Observers fire when the block in front of them changes.",
        "Pistons push blocks. Sticky pistons can pull them back.",
        "Hoppers move items into and out of containers.",
        "A hopper clock uses hoppers feeding each other to make a timer.",
        "A redstone block stays powered all the time.",
        "Redstone dust loses strength as the line gets longer.",
        "Target blocks give a signal when a projectile hits them.",
        "A Nether portal is an obsidian frame lit with fire.",
        "Ancient debris is the ore you smelt toward netherite.",
        "Four netherite scrap and four gold ingots make one netherite ingot.",
        "Netherite gear is upgraded from diamond on a smithing table.",
        "Blaze rods come from nether fortresses and fuel brewing.",
        "Ghasts can drop a tear used in some brewing and crystal recipes.",
        "Beds explode if you try to sleep in the Nether.",
        "A respawn anchor sets your Nether spawn when charged with glowstone.",
        "A respawn anchor explodes if you use it in the Overworld.",
        "Soul sand slows you down and grows nether wart.",
        "The End is where the Ender Dragon fight happens.",
        "End Crystals on the pillars heal the Ender Dragon until you break them.",
        "Eyes of ender lead you to a stronghold portal.",
        "End cities can have shulkers, loot, and sometimes an elytra ship.",
        "Shulker boxes keep their items when you break them.",
        "Chorus fruit teleports you a short random distance.",
        "End gateways appear after the Ender Dragon is defeated.",
        "Elytra let you glide if you have space to fly.",
        "An enchanting table uses lapis and experience levels.",
        "Bookshelves around the enchanting table raise the enchantment level.",
        "An anvil applies an enchanted book to gear.",
        "Mending repairs an item with collected experience orbs.",
        "Unbreaking makes tools and armor last longer.",
        "Fortune can make ores drop extra items.",
        "Silk Touch makes a block drop itself instead of its usual item.",
        "Blast Protection lowers explosion damage.",
        "Sharpness raises melee damage on a sword.",
        "Protection and Blast Protection do not go on the same armor piece in normal survival.",
        "Creepers explode if they get close and finish their fuse.",
        "Endermen get angry if you look them in the eyes.",
        "The Warden is tied to the deep dark and sculk shriekers.",
        "Villagers can trade if you have emeralds and the right workstation.",
        "Iron golems protect villagers and can be built by players.",
        "Evokers can drop a Totem of Undying.",
        "Raids start after a Bad Omen player enters a village.",
        "Blazes spawn in nether fortresses and drop blaze rods.",
        "Shulkers hide in End cities and shoot levitation shots.",
        "A Totem of Undying saves you once if you are holding it.",
        "A golden apple gives absorption and regeneration.",
        "An ender pearl teleports you to where it lands.",
        "Firework rockets can boost elytra flight.",
        "A water bucket can save a fall or clear fire.",
        "A shield blocks many hits from the front.",
        "Java combat uses an attack cooldown, so timing matters.",
        "Axes disable shields when they land.",
        "Swords can do a sweep attack on nearby mobs.",
        "Obsidian forms when water touches a lava source.",
        "Scaffolding is a fast block for climbing and building.",
        "Deepslate takes longer to mine than normal stone.",
        "Copper oxidizes over time unless you wax it.",
        "Amethyst grows in geodes from budding amethyst.",
        "A lodestone makes a compass point at that block.",
        "A beacon needs a pyramid of iron, gold, emerald, diamond, or netherite.",
        "A conduit gives water power when framed in the sea.",
    ]

def facts_for_topic(topic: str, limit: int = 8) -> list[str]:
    keys = specific_keys(topic)
    pool = _all_facts()
    if not keys:
        return pool[:limit]
    scored = []
    for fact in pool:
        low = fact.lower()
        hits = sum(1 for k in keys if k in low or k.rstrip("s") in low)
        if hits:
            scored.append((hits, fact))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    picked = unique_keep_order([f for _, f in scored])
    if not picked:
        label = " ".join(keys)
        picked = [
            f"This Short is about {label} in Minecraft.",
            f"Every point here stays on {label}.",
            f"If a detail is not {label}, it does not belong in this video.",
        ]
    return picked[:limit]

def minecraft_visuals(topic: str) -> list[str]:
    keys = specific_keys(topic)
    label = " ".join(keys) if keys else topic_keys(topic) and " ".join(topic_keys(topic)) or "Minecraft"
    queries = [f"Minecraft {label}", label]
    for key in keys[:6]:
        queries.append(f"Minecraft {key}")
    queries.extend([
        f"Minecraft {label} screenshot",
        f"Minecraft {label} block",
        f"Minecraft {label} item",
    ])
    return unique_keep_order([q for q in queries if q.strip()])
