"""
engine/world.py
Loads and queries the NPC and faction databases.
Faction reactions fire based on game flags — this is where the world pushes back.
"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path("data")


class WorldData:
    def __init__(self):
        self.npcs: dict = {}
        self.factions: dict = {}
        self._loaded = False

    def load(self):
        npc_path = DATA_DIR / "npcs.json"
        faction_path = DATA_DIR / "factions.json"

        if npc_path.exists():
            with open(npc_path) as f:
                self.npcs = json.load(f)

        if faction_path.exists():
            with open(faction_path) as f:
                self.factions = json.load(f)

        self._loaded = True

    def get_npc(self, npc_id: str) -> Optional[dict]:
        return self.npcs.get(npc_id)

    def get_faction(self, faction_id: str) -> Optional[dict]:
        return self.factions.get(faction_id)

    def npc_attitude(self, npc_id: str) -> dict:
        """Return simplified attitude snapshot for an NPC."""
        npc = self.get_npc(npc_id)
        if not npc:
            return {"trust": 0, "hostility": 50, "state": "unknown"}
        return {
            "trust": npc.get("trust_toward_player", 0),
            "hostility": npc.get("hostility", 50),
            "state": npc.get("state", "unknown"),
        }

    def faction_attitude(self, faction_id: str, toward: str = "damon") -> str:
        faction = self.get_faction(faction_id)
        if not faction:
            return "unknown"
        key = f"attitude_toward_{toward}"
        return faction.get(key, "unknown")

    def check_faction_reactions(self, flags: dict) -> list[dict]:
        """
        Scan all factions for triggered reactions based on current flags.
        Returns list of {faction, trigger, reaction} dicts that are newly active.
        """
        triggered = []
        for fid, faction in self.factions.items():
            reactions = faction.get("triggered_reactions", {})
            for trigger_key, reaction in reactions.items():
                if flags.get(trigger_key):
                    triggered.append({
                        "faction": faction["name"],
                        "faction_id": fid,
                        "trigger": trigger_key,
                        "reaction": reaction,
                    })
        return triggered

    def build_npc_context(self, npc_id: str) -> str:
        """
        Build a compact NPC context string for injection into LLM prompts.
        Used when an NPC is present in a scene.
        """
        npc = self.get_npc(npc_id)
        if not npc:
            return f"[Unknown NPC: {npc_id}]"

        knows = ", ".join(npc.get("knows", [])[:4])
        wants = ", ".join(npc.get("wants", [])[:2])
        agenda = npc.get("hidden_agenda") or "none"

        return (
            f"{npc['name']} [{npc['role']}] | "
            f"Trust: {npc['trust_toward_player']} Hostility: {npc['hostility']} | "
            f"State: {npc['state']} | "
            f"Knows: {knows} | "
            f"Wants: {wants} | "
            f"Hidden: {agenda} | "
            f"Voice: {npc['speech_style']}"
        )

    def build_faction_summary(self, faction_id: str, pov: str = "damon") -> str:
        faction = self.get_faction(faction_id)
        if not faction:
            return f"[Unknown faction: {faction_id}]"

        attitude = self.faction_attitude(faction_id, pov)
        return (
            f"{faction['name']} | "
            f"Attitude toward {pov}: {attitude} | "
            f"Active interests: {', '.join(faction.get('active_interests', [])[:2])}"
        )


# Singleton
_world: Optional[WorldData] = None


def get_world() -> WorldData:
    global _world
    if _world is None or not _world._loaded:
        _world = WorldData()
        _world.load()
    return _world
