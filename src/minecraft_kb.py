"""Built-in Minecraft facts, split by subject so topics do not collapse into crystal PvP."""
from __future__ import annotations
import hashlib
import re
from .utils import unique_keep_order

_FILLER = {
    "amazing", "insane", "wild", "crazy", "facts", "fact", "most", "about", "the",
    "that", "tips", "tip", "guide", "how", "why", "what", "for", "and", "with",
    "from", "make", "video", "short", "best", "top", "cool", "true", "real",
    "simple", "rules", "things", "nobody", "explains", "beginner", "seconds",
}

def minecraft_topic(topic: str) -> bool:
    return "minecraft" in topic.lower()

def topic_keys(topic: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{2,}", topic)]
    return [w for w in words if w not in _FILLER]

def _bank() -> dict[str, list[str]]:
    return {
        "crystal": [
            "Crystal PvP means using End Crystals against another player.",
            "An End Crystal only places on obsidian or bedrock.",
            "Hitting the crystal is what makes it explode.",
            "The blast can hurt you too if you stand too close.",
            "Keep obsidian next to the crystals on your hotbar.",
            "Move right after you place one.",
            "Snowballs and arrows can pop a crystal from a short distance.",
            "A totem in the offhand can save you from a bad blast.",
            "Pearl out if the trade leaves you low.",
            "Enchanted books and amethyst are not End Crystals.",
        ],
        "redstone": [
            "Redstone carries a signal that can power doors, lamps, and pistons.",
            "A redstone torch is a power source and can also invert a signal.",
            "Repeaters delay a signal and only send it forward.",
            "Comparators can read how full a chest or hopper is.",
            "Observers fire when the block in front of them changes.",
            "Pistons push blocks. Sticky pistons can pull them back.",
            "Hoppers move items into and out of containers.",
            "A redstone block stays on all the time.",
            "Dust on the ground loses strength as the line gets longer.",
            "Target blocks give a signal when a projectile hits them.",
        ],
        "nether": [
            "A Nether portal is an obsidian frame lit with fire.",
            "Ancient debris is the ore you smelt toward netherite.",
            "Four netherite scrap and four gold ingots make one ingot.",
            "Netherite gear is upgraded from diamond on a smithing table.",
            "Blaze rods come from nether fortresses and fuel brewing.",
            "Ghasts can drop a tear used in End Crystal crafting.",
            "Beds explode if you try to sleep in the Nether.",
            "A respawn anchor sets your Nether spawn when charged with glowstone.",
            "That same anchor explodes if you use it in the Overworld.",
            "Soul sand slows you down and grows nether wart.",
        ],
        "end": [
            "The End is where the Ender Dragon fight happens.",
            "End Crystals on the pillars heal the dragon until you break them.",
            "Eyes of ender lead you to a stronghold portal.",
            "End cities can have shulkers, loot, and sometimes an elytra ship.",
            "Shulker boxes keep their items when you break them.",
            "Chorus fruit teleports you a short random distance.",
            "End gateways appear after the dragon is defeated.",
            "The outer islands are where End cities generate.",
            "Elytra let you glide if you have space to fly.",
        ],
        "enchanting": [
            "An enchanting table uses lapis and experience levels.",
            "Bookshelves around the table raise the enchantment level.",
            "An anvil applies an enchanted book to gear.",
            "Mending repairs an item with collected experience orbs.",
            "Unbreaking makes tools and armor last longer.",
            "Fortune can make ores drop extra items.",
            "Silk Touch makes a block drop itself instead of its usual item.",
            "Blast Protection lowers explosion damage.",
            "Sharpness raises melee damage on a sword.",
            "You cannot put Protection and Blast Protection on the same piece in normal survival.",
        ],
        "mobs": [
            "Creepers explode if they get close and finish their fuse.",
            "Endermen get angry if you look them in the eyes.",
            "The Warden is tied to the deep dark and sculk shriekers.",
            "Villagers can trade if you have emeralds and the right workstation.",
            "Iron golems protect villagers and can be built by players.",
            "Evokers can drop a Totem of Undying.",
            "Raids start after a Bad Omen player enters a village.",
            "Blazes spawn in nether fortresses and drop blaze rods.",
            "Shulkers hide in End cities and shoot levitation shots.",
        ],
        "items": [
            "A Totem of Undying saves you once if you are holding it.",
            "A golden apple gives absorption and regeneration.",
            "An ender pearl teleports you to where it lands.",
            "Shulker boxes are portable chests that keep their items.",
            "Elytra are found in some End ships.",
            "Netherite does not burn in lava.",
            "A shield blocks many frontal hits.",
            "Firework rockets can boost elytra flight.",
            "A water bucket can save a fall or clear fire.",
        ],
        "building": [
            "Obsidian forms when water touches a lava source.",
            "Scaffolding is a fast block for climbing and building.",
            "Deepslate takes longer to mine than normal stone.",
            "Copper oxidizes over time unless you wax it.",
            "Amethyst grows in geodes from budding amethyst.",
            "Pointed dripstone can drip lava or water into cauldrons.",
            "A lodestone makes a compass point at that block.",
            "A beacon needs a pyramid of iron, gold, emerald, diamond, or netherite.",
            "A conduit gives water power when framed in the sea.",
        ],
        "pvp": [
            "Java combat uses an attack cooldown, so timing matters more than old spam clicking.",
            "Axes disable shields when they land.",
            "Swords are the standard melee option with sweep attacks.",
            "A shield blocks many hits from the front.",
            "Totems go in the offhand so your main hand can still fight.",
            "Golden apples help you recover after a trade.",
            "Ender pearls are for movement, not extra damage.",
            "Knockback can throw someone off a platform.",
            "A water bucket clutch can save a bad fall.",
        ],
    }

def facts_for_topic(topic: str, limit: int = 10) -> list[str]:
    banks = _bank()
    low = topic.lower()
    order = []
    if "crystal" in low:
        order.append("crystal")
    elif "redstone" in low or "piston" in low or "hopper" in low:
        order.append("redstone")
    elif "nether" in low or "netherite" in low or "debris" in low or "ghast" in low or "blaze" in low:
        order.append("nether")
    elif "dragon" in low or "elytra" in low or "shulker" in low or re.search(r"\bend\b", low):
        order.append("end")
    elif "enchant" in low or "mending" in low or "fortune" in low or "silk" in low:
        order.append("enchanting")
    elif "creeper" in low or "warden" in low or "villager" in low or "mob" in low or "raid" in low:
        order.append("mobs")
    elif "totem" in low or "pearl" in low or "apple" in low or "elytra" in low:
        order.append("items")
    elif "build" in low or "obsidian" in low or "scaffold" in low or "beacon" in low:
        order.append("building")
    elif "pvp" in low or "sword" in low or "axe" in low or "shield" in low:
        order.append("pvp")
    if not order:
        keys = topic_keys(topic)
        for name, lines in banks.items():
            blob = " ".join(lines).lower()
            if any(k in blob and k not in {"minecraft"} for k in keys):
                order.append(name)
    if not order:
        order = ["items"]
    picked = []
    for name in unique_keep_order(order):
        picked.extend(banks[name])
    return unique_keep_order(picked)[:limit]

def minecraft_visuals(topic: str) -> list[str]:
    low = topic.lower()
    if "crystal" in low:
        queries = ["Minecraft End Crystal", "Minecraft obsidian block", "Minecraft End dimension"]
    elif "redstone" in low or "piston" in low:
        queries = ["Minecraft redstone dust", "Minecraft piston", "Minecraft repeater circuit"]
    elif "nether" in low or "netherite" in low:
        queries = ["Minecraft Nether fortress", "Minecraft netherite", "Minecraft ancient debris"]
    elif "enchant" in low:
        queries = ["Minecraft enchanting table", "Minecraft bookshelves", "Minecraft anvil"]
    elif "warden" in low or "deep dark" in low:
        queries = ["Minecraft deep dark", "Minecraft sculk", "Minecraft ancient city"]
    elif "villager" in low:
        queries = ["Minecraft village", "Minecraft villager", "Minecraft iron golem"]
    elif "dragon" in low or re.search(r"\bend\b", low):
        queries = ["Minecraft Ender Dragon", "Minecraft End island", "Minecraft End city"]
    elif "elytra" in low:
        queries = ["Minecraft elytra", "Minecraft End ship", "Minecraft chorus plant"]
    else:
        queries = ["Minecraft world screenshot", "Minecraft cave", "Minecraft village", "Minecraft forest"]
    seed = int(hashlib.sha1(topic.encode()).hexdigest(), 16)
    start = seed % len(queries)
    return queries[start:] + queries[:start]
