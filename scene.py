"""
engine/scene.py
Scene engine: scripted beats, encounter tables, travel resolution.

A scene is a structured unit of play:
  - location with atmosphere and connections
  - active NPCs
  - available actions (pre-computed from context)
  - encounter rolls (random events with mechanical weight)
  - scripted beats (fire once when conditions met)
  - transition triggers (what causes a move to next scene)

The scene engine does NOT narrate. It produces structured state that
the LLM and display layer consume.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# Location loader
# ---------------------------------------------------------------------------

_locations: dict = {}


def load_locations() -> dict:
    global _locations
    if _locations:
        return _locations
    path = DATA_DIR / "locations.json"
    if path.exists():
        with open(path) as f:
            _locations = json.load(f)
    return _locations


def get_location(loc_id: str) -> Optional[dict]:
    return load_locations().get(loc_id)


# ---------------------------------------------------------------------------
# Encounter tables
# One table per travel/location context. Weighted random draw.
# ---------------------------------------------------------------------------

ENCOUNTER_TABLES: dict[str, list[dict]] = {
    "road_to_sablewake": [
        {
            "id": "black_tide_patrol",
            "weight": 30,
            "type": "social",
            "description": "A Black Tide patrol — two armed men checking travel documents. Token scanner on the belt.",
            "dc": 14, "stat": "cha",
            "success_outcome": "Waved through. One of them looks at Carrow's robes too long.",
            "failure_outcome": "Documents demanded. Carrow's liturgical seal draws questions.",
            "combat_escalation": True,
        },
        {
            "id": "veiled_throne_courier",
            "weight": 20,
            "type": "event",
            "description": "A lone rider drops a sealed packet at the roadside and rides on without stopping.",
            "dc": 0, "stat": None,
            "success_outcome": "The packet is addressed to Damon. Veiled Throne handwriting.",
            "failure_outcome": None,
            "flags_set": {"veiled_throne_courier_contact": True},
        },
        {
            "id": "hollow_trace",
            "weight": 15,
            "type": "occult",
            "description": "The Anchor Shard pulses cold. Something hollow-adjacent passed through here recently.",
            "dc": 13, "stat": "wis",
            "success_outcome": "Damon reads the trace: Malrec's proxy passed this way within the week.",
            "failure_outcome": "The trace is there but unreadable. The shard goes quiet.",
            "requires_item": "anchor_shard",
        },
        {
            "id": "saervan_outrider",
            "weight": 25,
            "type": "stealth",
            "description": "A mounted outrider in Saervan's livery on the road ahead. Watching.",
            "dc": 15, "stat": "dex",
            "success_outcome": "Slipped past. He'll report a group on the road — not who.",
            "failure_outcome": "Seen. Saervan will know Damon's description by nightfall.",
            "flags_set_on_failure": {"damon_seen_by_saervan_outrider": True},
            "combat_escalation": True,
        },
        {
            "id": "carrow_revelation",
            "weight": 10,
            "type": "dialogue",
            "description": "Carrow speaks unprompted during a rest stop. He's been holding something back.",
            "dc": 14, "stat": "wis",
            "success_outcome": "Damon reads the hesitation. Carrow admits: the displaced witness requires a living voice-of-record, not just a claimant mark.",
            "failure_outcome": "Carrow stops himself. Whatever he was about to say, stays unsaid.",
        },
    ],
    "sablewake_dockside": [
        {
            "id": "mara_veys_contact",
            "weight": 40,
            "type": "social",
            "description": "Mara Veys finds Elira near the token-exchange stall. She has information — for a price.",
            "dc": 12, "stat": "cha",
            "success_outcome": "Mara sells: Saervan locked the lower Vice. Something's missing from his access kit.",
            "failure_outcome": "Mara takes the coin and gives nothing useful.",
        },
        {
            "id": "token_verification",
            "weight": 25,
            "type": "social",
            "description": "A Black Tide checker runs a courtesy-token sweep. Elira's token is genuine — but the timing is suspicious.",
            "dc": 13, "stat": "cha",
            "success_outcome": "Token passes. The checker marks it in a ledger. Elira is now in the system.",
            "failure_outcome": "Token passes but flagged for secondary review.",
            "flags_set_on_failure": {"elira_token_flagged": True},
        },
        {
            "id": "ring_recognition",
            "weight": 20,
            "type": "investigation",
            "description": "Someone at the docks reacts to the dark-stone ring — a flicker of recognition, quickly suppressed.",
            "dc": 14, "stat": "wis",
            "success_outcome": "Elira clocks it. The ring is a functional access marker, not just valuable.",
            "failure_outcome": "The moment passes. The recognition was real but Elira missed it.",
        },
        {
            "id": "saervan_net",
            "weight": 15,
            "type": "stealth",
            "description": "Saervan's people are showing a description around the docks. It matches Elira closely.",
            "dc": 15, "stat": "dex",
            "success_outcome": "Elira slips the net. She knows they're hunting now.",
            "failure_outcome": "She's spotted. Has to move fast. HP -1d4.",
            "damage_on_failure": "1d4",
        },
    ],
    "gilded_vice_main_floor": [
        {
            "id": "saervan_present",
            "weight": 50,
            "type": "social_high_stakes",
            "description": "Lord Saervan is on the floor. He hasn't seen Elira yet — but he will if she stays visible.",
            "dc": 16, "stat": "cha",
            "success_outcome": "Elira maneuvers to the side approach. Saervan doesn't look up.",
            "failure_outcome": "Eye contact. The room gets very quiet around the two of them.",
            "combat_escalation": True,
        },
        {
            "id": "lower_door_observed",
            "weight": 35,
            "type": "investigation",
            "description": "The lower access door is visible from the east tables. Two people go through. Neither returns during Elira's watch.",
            "dc": 12, "stat": "wis",
            "success_outcome": "Elira clocks the guard rotation and the token reader beside the door.",
            "failure_outcome": "The door is noted but the rotation is unclear.",
            "flags_set": {"gilded_vice_lower_door_observed": True},
        },
    ],
    "sablewake_harbor_damon": [
        {
            "id": "brannock_hale_contact",
            "weight": 45,
            "type": "social",
            "description": "Brannock Hale finds Damon at the harbormaster's posting board. He doesn't introduce himself. He doesn't need to.",
            "dc": 13, "stat": "cha",
            "success_outcome": "Brannock talks: courtesy mark forgery is possible. Expensive. Two days. And he wants something in return.",
            "failure_outcome": "Brannock quotes a price that's either a test or extortion. Hard to tell.",
            "flags_set": {"brannock_hale_contacted": True},
        },
        {
            "id": "black_tide_increased_presence",
            "weight": 30,
            "type": "investigation",
            "description": "The harbor is over-watched. Too many unmarked coats. Something elevated the alert level.",
            "dc": 12, "stat": "wis",
            "success_outcome": "Kest counts the patrols. They doubled within the last day. Someone told them to.",
            "failure_outcome": "The patrols are noted but the pattern isn't clear.",
        },
        {
            "id": "carrow_knowledge_check",
            "weight": 25,
            "type": "dialogue",
            "description": "Carrow recognizes the courtesy-house architecture. He's been here before.",
            "dc": 14, "stat": "wis",
            "success_outcome": "Carrow identifies the courtesy-house entrance. He knows which amber lantern marks the lower-tier access. He does not explain how he knows.",
            "failure_outcome": "Carrow goes quiet when asked. His injured leg is bothering him.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Scripted beats — fire once when specific conditions are met in a scene
# ---------------------------------------------------------------------------

@dataclass
class ScriptedBeat:
    id: str
    location_id: str
    trigger_flags: dict          # All must be true
    trigger_flags_false: dict    # All must be false (blockers)
    description: str             # What happens
    mechanical_effect: dict      # State changes: hp, flags, items, statuses
    narrative_context: str       # For LLM injection
    fired: bool = False
    pov: str = "any"             # "damon", "elira", or "any"


SCRIPTED_BEATS: list[ScriptedBeat] = [
    ScriptedBeat(
        id="kest_confronts_damon_on_road",
        location_id="sablewake_road",
        trigger_flags={},
        trigger_flags_false={"kest_confrontation_done": True},
        pov="damon",
        description="Kest pulls up beside Damon and speaks plainly: he wants to know the actual plan before they walk into a city that's looking for them.",
        mechanical_effect={"flags": {"kest_confrontation_done": True}},
        narrative_context="Kest is owed an honest answer. How Damon responds affects trust. This is a character beat, not a check — but the LLM should make it land.",
    ),
    ScriptedBeat(
        id="carrow_injury_worsens",
        location_id="sablewake_road",
        trigger_flags={"carrow_injured": True},
        trigger_flags_false={"carrow_injury_treated": True},
        pov="damon",
        description="Carrow's wound from Saint Vaelor has been reopened by the road. He is slower and quieter than he should be.",
        mechanical_effect={
            "character_hp": {"carrow": -2},
            "flags": {"carrow_critical_injury": True},
        },
        narrative_context="Carrow is deteriorating. Damon must decide whether to stop, push on, or find a way to treat the wound on the road.",
    ),
    ScriptedBeat(
        id="elira_understands_the_ring",
        location_id="sablewake_dockside",
        trigger_flags={"elira_in_sablewake": True, "ring_recognition": True},
        trigger_flags_false={"elira_understands_ring_purpose": True},
        pov="elira",
        description="The pieces connect. The ring isn't just an access marker — it's Saervan's personal custody key to the lower Vice. Without it, he can't open the Node from his side. With it, Elira can.",
        mechanical_effect={"flags": {"elira_understands_ring_purpose": True}},
        narrative_context="This is a revelation beat for Elira. She now has leverage she didn't know she had. The LLM should make this land — the weight of what she's been carrying.",
    ),
    ScriptedBeat(
        id="damon_sees_elira_sablewake_rumor",
        location_id="sablewake_harbor",
        trigger_flags={"elira_sablewake_rumor_active": True, "sablewake_reached": True},
        trigger_flags_false={"damon_registered_elira_rumor": True},
        pov="damon",
        description="Someone at the harbor mentions an elf who beat the Vice and has been seen near the courtesy houses. Damon recognizes the description immediately.",
        mechanical_effect={"flags": {"damon_registered_elira_rumor": True}},
        narrative_context="Damon now knows Elira is in Sablewake. This is a significant moment — she's either a liability or an asset he didn't plan for. The LLM should voice Damon's cold calculation.",
    ),
]


# ---------------------------------------------------------------------------
# Encounter resolution
# ---------------------------------------------------------------------------

@dataclass
class EncounterResult:
    encounter_id: str
    encounter_type: str
    description: str
    stat: Optional[str]
    dc: int
    roll_needed: bool
    flags_set: dict = field(default_factory=dict)
    flags_set_on_failure: dict = field(default_factory=dict)
    damage_on_failure: Optional[str] = None
    combat_escalation: bool = False
    success_outcome: str = ""
    failure_outcome: str = ""


def draw_encounter(table_id: str) -> Optional[EncounterResult]:
    """
    Weighted random draw from an encounter table.
    Returns None if no table found or empty.
    """
    table = ENCOUNTER_TABLES.get(table_id)
    if not table:
        return None

    total_weight = sum(e["weight"] for e in table)
    roll = random.randint(1, total_weight)
    cumulative = 0
    chosen = None
    for entry in table:
        cumulative += entry["weight"]
        if roll <= cumulative:
            chosen = entry
            break

    if not chosen:
        return None

    return EncounterResult(
        encounter_id=chosen["id"],
        encounter_type=chosen["type"],
        description=chosen["description"],
        stat=chosen.get("stat"),
        dc=chosen.get("dc", 10),
        roll_needed=chosen.get("dc", 0) > 0 and chosen.get("stat") is not None,
        flags_set=chosen.get("flags_set", {}),
        flags_set_on_failure=chosen.get("flags_set_on_failure", {}),
        damage_on_failure=chosen.get("damage_on_failure"),
        combat_escalation=chosen.get("combat_escalation", False),
        success_outcome=chosen.get("success_outcome", ""),
        failure_outcome=chosen.get("failure_outcome", ""),
    )


# ---------------------------------------------------------------------------
# Scripted beat checker
# ---------------------------------------------------------------------------

def check_scripted_beats(location_id: str, pov: str, game_flags) -> list[ScriptedBeat]:
    """
    Check all unfired scripted beats for a location/pov.
    Returns those whose conditions are met.
    """
    triggered = []
    for beat in SCRIPTED_BEATS:
        if beat.fired:
            continue
        if beat.location_id != location_id:
            continue
        if beat.pov not in ("any", pov):
            continue

        # Check required flags
        required_met = all(
            game_flags.get(k) == v
            for k, v in beat.trigger_flags.items()
        )
        # Check blocking flags
        blocked = any(
            game_flags.get(k) == v
            for k, v in beat.trigger_flags_false.items()
        )

        if required_met and not blocked:
            triggered.append(beat)

    return triggered


def fire_beat(beat: ScriptedBeat, state) -> dict:
    """
    Apply a scripted beat's mechanical effects to game state.
    Returns a summary dict for display/LLM.
    """
    beat.fired = True
    effects_applied = {}

    effects = beat.mechanical_effect

    # Apply flags
    for k, v in effects.get("flags", {}).items():
        state.flags.set(k, v)
        effects_applied[k] = v

    # Apply HP changes
    for char_id, delta in effects.get("character_hp", {}).items():
        char = state.get_character(char_id)
        if char:
            char.hp = max(0, min(char.max_hp, char.hp + delta))
            effects_applied[f"{char_id}_hp"] = char.hp

    return effects_applied


# ---------------------------------------------------------------------------
# Travel resolution
# ---------------------------------------------------------------------------

@dataclass
class TravelResult:
    destination: str
    days: int
    encounters: list[EncounterResult] = field(default_factory=list)
    beats_fired: list[str] = field(default_factory=list)
    arrival_flags: dict = field(default_factory=dict)


def resolve_travel(
    from_location: str,
    to_location: str,
    pov: str,
    state,
    encounter_table_id: Optional[str] = None,
) -> TravelResult:
    """
    Resolve travel between two locations.
    Draws 1 encounter per travel day, checks scripted beats at destination.
    """
    from_loc = get_location(from_location)
    to_loc = get_location(to_location)

    days = 1
    if from_loc:
        days = from_loc.get("travel_days", 1)
        if encounter_table_id is None:
            encounter_table_id = from_loc.get("encounter_table")

    encounters = []
    if encounter_table_id:
        for _ in range(days):
            enc = draw_encounter(encounter_table_id)
            if enc:
                encounters.append(enc)

    # Update scene location
    state.scene.location = to_location
    state.scene.id = f"travel_{from_location}_to_{to_location}"

    # Check scripted beats at destination
    fired_beats = []
    if to_loc:
        beats = check_scripted_beats(to_location, pov, state.flags)
        for beat in beats:
            effects = fire_beat(beat, state)
            fired_beats.append(beat.id)

    # Set arrival flag
    arrival_flags = {}
    loc_flag_map = {
        "sablewake_harbor": "sablewake_reached",
        "sablewake_dockside": "elira_in_sablewake",
        "gilded_vice_main_floor": "gilded_vice_infiltrated",
        "western_node_chamber": "western_node_accessed",
    }
    if to_location in loc_flag_map:
        flag = loc_flag_map[to_location]
        state.flags.set(flag, True)
        arrival_flags[flag] = True

    return TravelResult(
        destination=to_location,
        days=days,
        encounters=encounters,
        beats_fired=fired_beats,
        arrival_flags=arrival_flags,
    )


# ---------------------------------------------------------------------------
# Scene context builder — for LLM injection
# ---------------------------------------------------------------------------

def build_scene_context(location_id: str, pov: str, state) -> str:
    """
    Build a compact scene context string for the LLM prompt.
    Includes location atmosphere, NPCs present, faction presence, notable facts.
    """
    loc = get_location(location_id)
    if not loc:
        return f"[Unknown location: {location_id}]"

    atmosphere = ", ".join(loc.get("atmosphere", []))
    npcs = ", ".join(loc.get("npcs_present", [])) or "none visible"
    factions = ", ".join(
        f"{f} ({s})" for f, s in loc.get("faction_presence", {}).items()
    ) or "none"
    notable = "; ".join(loc.get("notable", [])) or "none"
    access = loc.get("access", "open")

    # Narrative hints from crossrail
    from engine.crossrail import get_crossrail
    crossrail = get_crossrail()
    hints = crossrail.get_narrative_hints(pov, state.flags)
    hint_str = " | ".join(hints[:2]) if hints else "none"

    return (
        f"LOCATION: {loc['name']}\n"
        f"Atmosphere: {atmosphere}\n"
        f"NPCs present: {npcs}\n"
        f"Faction presence: {factions}\n"
        f"Access: {access}\n"
        f"Notable: {notable}\n"
        f"World echoes (crossrail): {hint_str}"
    )
