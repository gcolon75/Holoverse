"""
llm/parser.py
Converts raw player input into a structured intent dict.
The engine then decides what check (if any) to run based on intent.

Intent categories:
  move        — travel, go, head, walk
  examine     — look, inspect, search, check
  interact    — talk, ask, use, give, show
  use_item    — use <item>, invoke <relic>
  attack      — attack, strike, fight, draw
  hide        — hide, stealth, slip away
  invoke      — invoke authority, use signet, invoke tide mark
  social      — bluff, persuade, intimidate, deceive
  rest        — rest, wait, camp
  investigate — investigate, cross-reference, read, study
  numeric     — player typed a number (chose a suggested action)
  unknown     — catch-all
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Intent:
    category: str
    verb: str
    target: Optional[str] = None
    item: Optional[str] = None
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "verb": self.verb,
            "target": self.target,
            "item": self.item,
        }


# Keyword maps — order matters, first match wins
INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("attack",      ["attack", "strike", "fight", "draw sword", "draw weapon", "stab", "slash", "shoot"]),
    ("invoke",      ["invoke", "claim authority", "use signet", "present signet", "tide mark", "blood right", "claimant"]),
    ("use_item",    ["use ", "activate ", "open ", "read "]),
    ("hide",        ["hide", "stealth", "slip away", "conceal", "blend in", "disappear"]),
    ("social",      ["bluff", "persuade", "intimidate", "deceive", "lie", "charm", "bribe", "negotiate"]),
    ("investigate", ["investigate", "cross-reference", "study", "analyze", "research", "cross reference"]),
    ("examine",     ["look", "inspect", "search", "check", "examine", "observe", "scan", "peer"]),
    ("interact",    ["talk", "speak", "ask", "tell", "give", "show", "approach", "confront"]),
    ("move",        ["go ", "move ", "head ", "travel ", "walk ", "run ", "climb ", "descend ", "enter ", "leave ", "follow "]),
    ("rest",        ["rest", "wait", "camp", "sleep", "tend wound", "treat"]),
]

# Known item keywords for target extraction
ITEM_KEYWORDS = [
    "anchor shard", "anchor_shard",
    "succession signet", "succession_signet",
    "veiled throne packet", "veiled_throne_packet",
    "malrec tablet", "malrec_tablet",
    "bronze tablet",
    "longsword", "sword",
    "courtesy token", "black_tide_courtesy_token",
    "dark stone ring", "dark_stone_ring",
]


def parse_intent(raw: str) -> Intent:
    """Parse raw player input into a structured Intent."""
    normalized = raw.lower().strip()

    # Numeric shortcut — player chose a suggested action by number
    if re.match(r"^[1-4]$", normalized):
        return Intent(category="numeric", verb="choose", target=normalized, raw=raw)

    # Check for item references
    item_found = None
    for kw in ITEM_KEYWORDS:
        if kw in normalized:
            item_found = kw.replace(" ", "_")
            break

    # Match category
    for category, keywords in INTENT_PATTERNS:
        for kw in keywords:
            if kw in normalized:
                # Extract target: everything after the keyword
                idx = normalized.find(kw)
                after = normalized[idx + len(kw):].strip()
                target = after if after else None
                return Intent(
                    category=category,
                    verb=kw.strip(),
                    target=target,
                    item=item_found,
                    raw=raw,
                )

    # Unknown — pass raw to LLM for interpretation
    return Intent(category="unknown", verb="unknown", target=normalized, raw=raw)


# --- DC table ---
# Default DCs by category and rough difficulty.
# The loop can override these based on context.

DC_TABLE = {
    "attack":      {"easy": 10, "normal": 13, "hard": 16, "deadly": 19},
    "hide":        {"easy": 10, "normal": 14, "hard": 17, "deadly": 20},
    "social":      {"easy": 10, "normal": 13, "hard": 16, "deadly": 20},
    "investigate": {"easy": 10, "normal": 13, "hard": 16, "deadly": 19},
    "examine":     {"easy":  8, "normal": 12, "hard": 15, "deadly": 18},
    "invoke":      {"easy": 12, "normal": 15, "hard": 18, "deadly": 22},
    "move":        {"easy":  8, "normal": 11, "hard": 14, "deadly": 17},
    "use_item":    {"easy": 10, "normal": 13, "hard": 16, "deadly": 19},
    "interact":    {"easy":  8, "normal": 11, "hard": 14, "deadly": 17},
    "rest":        {"easy":  8, "normal": 10, "hard": 12, "deadly": 15},
}

# Stat used per category by default
STAT_MAP = {
    "attack":      "str",
    "hide":        "dex",
    "social":      "cha",
    "investigate": "int",
    "examine":     "wis",
    "invoke":      "cha",
    "move":        "dex",
    "use_item":    "int",
    "interact":    "cha",
    "rest":        "con",
    "unknown":     "wis",
}


def get_default_check(intent: Intent) -> tuple[str, int]:
    """Return (stat, dc) for a given intent at 'normal' difficulty."""
    stat = STAT_MAP.get(intent.category, "wis")
    dc = DC_TABLE.get(intent.category, {}).get("normal", 13)
    return stat, dc
