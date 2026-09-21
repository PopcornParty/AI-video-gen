"""True short facts for common non-Minecraft prompts."""
from __future__ import annotations

BANKS = {
    "spitfire": [
        "The Spitfire Mk II used the Rolls-Royce Merlin XII engine.",
        "Spitfire Mk II fighters were a main RAF Battle of Britain era follow-on mark.",
        "Many Mk II Spitfires had armour and a better constant-speed propeller than the earliest marks.",
        "In War Thunder the Spitfire Mk II is a low-rank British fighter, not a late-war Griffon plane.",
        "The Mk II is light and climbs hard, but it does not turn as tightly as later clipped or Griffon Spitfires.",
        "In War Thunder, energy fighting suits the Mk II better than turning with early Japanese fighters forever.",
        "The real Mk II armed with eight .303 machine guns, not the later 20 mm Hispano pair on many Mk Vs.",
        "War Thunder players often boom and zoom in the Mk II, then climb back above the fight.",
    ],
    "war thunder": [
        "War Thunder mixes planes, tanks, and ships in one game.",
        "Arcade, realistic, and simulator battles change how much help the plane gives you.",
        "British early fighters in War Thunder climb well and want altitude before they dive in.",
        "A mark number on a War Thunder plane is the real airframe version, not a random skin.",
    ],
}

def facts_for_general(topic: str, limit: int = 8) -> list[str]:
    low = topic.lower()
    out = []
    for key, facts in BANKS.items():
        if key in low:
            out.extend(facts)
    if "spitfire" in low and "mk" in low.replace("mark", "mk"):
        out = BANKS["spitfire"] + [f for f in BANKS["war thunder"] if f not in out]
    return out[:limit]

def visual_queries_for(topic: str) -> list[str]:
    low = topic.lower()
    q = []
    if "spitfire" in low:
        q += ["Supermarine Spitfire", "Spitfire Mk II", "Spitfire fighter aircraft", "RAF Spitfire"]
    if "war thunder" in low or "warthunder" in low:
        q += ["fighter aircraft", "Supermarine Spitfire", "World War II fighter"]
    return q
