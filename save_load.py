"""
game/save_load.py
JSON save and load. Rule of Ash: no rewinds, no retcons.
Saves are append-only checkpoints — you don't get to reload an old one.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from game.state import GameState, GameFlags, SceneState, Character, CharacterStats
from engine.status import StatusManager
from engine.inventory import Inventory, ITEM_REGISTRY
import copy


SAVE_DIR = Path("data/saves")
CURRENT_SAVE = SAVE_DIR / "current_save.json"


def ensure_save_dir():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


def state_to_dict(state: GameState) -> dict:
    """Serialize GameState to a JSON-compatible dict."""
    characters = {}
    for cid, char in state.characters.items():
        characters[cid] = {
            "id": char.id,
            "name": char.name,
            "hp": char.hp,
            "max_hp": char.max_hp,
            "ac": char.ac,
            "stats": {
                "str": char.stats.str,
                "dex": char.stats.dex,
                "con": char.stats.con,
                "int": char.stats.int,
                "wis": char.stats.wis,
                "cha": char.stats.cha,
            },
            "statuses": char.statuses.list_ids(),
            "inventory": char.inventory.list_ids(),
            "flags": char.flags,
            "relationship_ids": char.relationship_ids,
            "is_alive": char.is_alive,
        }

    return {
        "meta": {
            "saved_at": datetime.now().isoformat(),
            "turn": state.turn,
        },
        "active_pov": state.active_pov,
        "chapter": state.chapter,
        "scene": {
            "id": state.scene.id,
            "chapter_id": state.scene.chapter_id,
            "pov": state.scene.pov,
            "location": state.scene.location,
            "goal": state.scene.goal,
            "resolved": state.scene.resolved,
            "description": state.scene.description,
            "available_actions": state.scene.available_actions,
        },
        "flags": state.flags.to_dict(),
        "characters": characters,
        "in_combat": state.in_combat,
        "crossrail_fired": state.crossrail_fired,
        "rails": {
            pov: {
                "current_chapter": r.current_chapter,
                "last_switch_trigger": r.last_switch_trigger,
                "turns_on_this_rail": r.turns_on_this_rail,
                "pending_switch": r.pending_switch,
                "pending_switch_to": r.pending_switch_to,
            }
            for pov, r in state.rails.items()
        },
    }


def dict_to_state(data: dict) -> GameState:
    """Deserialize a JSON dict back to GameState."""
    from engine.status import STATUS_REGISTRY

    state = GameState()
    state.active_pov = data["active_pov"]
    state.chapter = data["chapter"]
    state.turn = data.get("meta", {}).get("turn", 0)
    state.in_combat = data.get("in_combat", False)
    state.crossrail_fired = data.get("crossrail_fired", [])

    from game.state import RailState
    from engine.crossrail import get_crossrail
    if "rails" in data:
        for pov, rd in data["rails"].items():
            state.rails[pov] = RailState(
                current_chapter=rd.get("current_chapter", ""),
                last_switch_trigger=rd.get("last_switch_trigger", ""),
                turns_on_this_rail=rd.get("turns_on_this_rail", 0),
                pending_switch=rd.get("pending_switch", False),
                pending_switch_to=rd.get("pending_switch_to", ""),
            )
    # Re-sync crossrail fired state
    crossrail = get_crossrail()
    for eid in state.crossrail_fired:
        if eid in crossrail.events:
            crossrail.events[eid].fired = True

    # Scene
    sd = data["scene"]
    state.scene = SceneState(
        id=sd["id"],
        chapter_id=sd["chapter_id"],
        pov=sd["pov"],
        location=sd["location"],
        goal=sd["goal"],
        resolved=sd["resolved"],
        description=sd.get("description", ""),
        available_actions=sd.get("available_actions", []),
    )

    # Flags
    flags = GameFlags()
    for k, v in data["flags"].items():
        flags.set(k, v)
    state.flags = flags

    # Characters
    for cid, cd in data["characters"].items():
        stats = CharacterStats(**cd["stats"])
        char = Character(
            id=cd["id"],
            name=cd["name"],
            hp=cd["hp"],
            max_hp=cd["max_hp"],
            ac=cd["ac"],
            stats=stats,
            flags=cd.get("flags", {}),
            relationship_ids=cd.get("relationship_ids", []),
            is_alive=cd.get("is_alive", True),
        )
        char.inventory = Inventory(cid)

        # Restore statuses
        for sid in cd.get("statuses", []):
            if sid in STATUS_REGISTRY:
                char.statuses.apply(sid)

        # Restore inventory
        for item_id in cd.get("inventory", []):
            if item_id in ITEM_REGISTRY:
                char.inventory.add(item_id)

        state.characters[cid] = char

    return state


def save(state: GameState, path: Path = CURRENT_SAVE):
    ensure_save_dir()
    data = state_to_dict(state)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(path: Path = CURRENT_SAVE) -> GameState:
    if not path.exists():
        raise FileNotFoundError(f"No save file found at {path}")
    with open(path, "r") as f:
        data = json.load(f)
    return dict_to_state(data)


def save_exists() -> bool:
    return CURRENT_SAVE.exists()


def checkpoint(state: GameState):
    """Save a timestamped checkpoint alongside the current save."""
    ensure_save_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_path = SAVE_DIR / f"checkpoint_{ts}.json"
    save(state, checkpoint_path)
    save(state)  # Also update current
