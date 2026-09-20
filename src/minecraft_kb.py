"""Built-in Minecraft facts. Prompt words decide which facts and pictures get used."""
from __future__ import annotations
import re
from .utils import unique_keep_order

_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about", "the",
    "that", "tips", "tip", "guide", "how", "why", "what", "for", "and", "with",
    "from", "make", "video", "short", "best", "top", "cool", "true", "real",
    "simple", "rules", "things", "nobody", "explains", "beginner", "seconds",
    "please", "talk", "something", "tell", "everything",
}

_MC_WORDS = {
    "minecraft", "totem", "undying", "crystal", "obsidian", "redstone", "piston",
    "nether", "netherite", "elytra", "shulker", "enchant", "villager", "creeper",
    "warden", "dragon", "hopper", "pearl", "beacon", "conduit", "evoker", "raid",
}

def minecraft_topic(topic: str) -> bool:
    low = topic.lower()
    return any(w in low for w in _MC_WORDS)

def topic_keys(topic: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)]
    return [w for w in words if w not in _FILLER]

def specific_keys(topic: str) -> list[str]:
    return [k for k in topic_keys(topic) if k != "minecraft"]

def _all_facts() -> list[str]:
    return [
        "A Totem of Undying only works if you are holding it when you would have died.",
        "Put the Totem of Undying in your offhand so your main hand can still use items.",
        "A Totem of Undying in a chest or shulker does nothing if you die.",
        "When a Totem of Undying pops, you survive that death and get a burst of effects.",
        "Evokers drop Totems of Undying in woodland mansions and in raids.",
        "You can get more than one Totem of Undying by fighting more evokers.",
        "After a totem pops you still need food, armor, and space to recover.",
        "Crystal PvP players often keep a Totem of Undying ready because explosions hit hard.",
        "A Totem of Undying does not stop you from dying again a moment later if you keep taking damage.",
        "Crystal PvP means using End Crystals against another player.",
        "An End Crystal only places on obsidian or bedrock.",
        "Hitting the End Crystal is what makes it explode.",
        "Your own crystal blast can hurt you if you stand too close.",
        "Keep obsidian next to the crystals on your hotbar so you can place another one fast.",
        "Snowballs and arrows can pop a crystal from a short distance.",
        "Move right after you place a crystal so you are not inside the blast.",
        "Redstone carries a signal that can power doors, lamps, and pistons.",
        "A redstone torch is a power source and can invert a signal.",
        "Repeaters delay a redstone signal and only send it forward.",
        "Comparators can read how full a chest or hopper is.",
        "Observers fire when the block in front of them changes.",
        "Pistons push blocks. Sticky pistons can pull them back.",
        "Hoppers move items into and out of containers.",
        "A hopper clock uses hoppers feeding each other to make a timer.",
        "Redstone dust gets weaker as the line gets longer, up to fifteen blocks.",
        "A Nether portal is an obsidian frame lit with fire.",
        "Ancient debris is the ore you smelt toward netherite.",
        "Four netherite scrap and four gold ingots make one netherite ingot.",
        "Netherite gear is upgraded from diamond on a smithing table.",
        "Netherite does not burn if it falls in lava.",
        "Beds explode if you try to sleep in the Nether.",
        "A respawn anchor sets your Nether spawn when charged with glowstone.",
        "A respawn anchor explodes if you try to use it in the Overworld.",
        "Blaze rods come from nether fortresses and fuel brewing stands.",
        "The End is where the Ender Dragon fight happens.",
        "End Crystals on the pillars heal the Ender Dragon until you break them.",
        "Eyes of ender lead you to a stronghold portal.",
        "End cities can have shulkers, loot, and sometimes a ship with elytra.",
        "Shulker boxes keep their items when you break them.",
        "Elytra let you glide if you have space to fly.",
        "Firework rockets can boost elytra flight.",
        "An enchanting table uses lapis and experience levels.",
        "Bookshelves around the table raise the highest enchantment you can roll.",
        "An anvil puts an enchanted book onto gear.",
        "Mending repairs an item with experience orbs you collect.",
        "Unbreaking makes tools and armor last longer.",
        "Fortune can make ores drop extra items.",
        "Silk Touch makes a block drop itself instead of its usual item.",
        "Blast Protection lowers explosion damage, including crystals and creepers.",
        "Creepers explode if they get close and finish their fuse.",
        "Endermen get angry if you look them in the eyes.",
        "The Warden is tied to the deep dark and sculk shriekers.",
        "Villagers trade if you have emeralds and the right workstation.",
        "Iron golems protect villagers and can be built by players.",
        "A golden apple gives absorption and regeneration.",
        "An enchanted golden apple is stronger and cannot be crafted in current survival.",
        "An ender pearl teleports you to where it lands, and the land hurts a little.",
        "A shield blocks many hits from the front.",
        "An axe can disable a shield when it lands.",
        "Java combat uses an attack cooldown, so timing beats old-style spam clicking.",
        "Obsidian forms when water touches a lava source block.",
        "Scaffolding is a fast block for climbing and building up.",
        "A beacon needs a pyramid of iron, gold, emerald, diamond, or netherite.",
        "A conduit gives water power when you frame it correctly underwater.",
    ]

def facts_for_topic(topic: str, limit: int = 10) -> list[str]:
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
        picked = [f"This is about {label} in Minecraft."]
    return picked[:limit]

def minecraft_visuals(topic: str) -> list[str]:
    keys = specific_keys(topic)
    label = " ".join(keys) if keys else "Minecraft"
    queries = [f"Minecraft {label}", label, f"Minecraft {label} gameplay"]
    for key in keys[:6]:
        queries.append(f"Minecraft {key}")
    if "totem" in topic.lower() or "undying" in topic.lower():
        queries = ["Minecraft Totem of Undying", "Totem of Undying", "Minecraft evoker", "Minecraft raid"] + queries
    queries.append("Minecraft gameplay")
    return unique_keep_order([q for q in queries if q.strip()])
