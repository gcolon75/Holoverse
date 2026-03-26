"""
engine/status.py
Status effect definitions, application, and tick logic.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class StatusCategory(Enum):
    WOUND = "wound"
    OCCULT = "occult"
    CLAIMANT = "claimant"
    LEGAL = "legal"
    CONTAMINATION = "contamination"
    SOCIAL = "social"


@dataclass
class StatusEffect:
    id: str
    name: str
    category: StatusCategory
    description: str
    duration_rounds: Optional[int] = None  # None = permanent until removed
    rounds_remaining: Optional[int] = None
    stat_modifiers: dict = field(default_factory=dict)  # e.g. {"ac": -1, "str": -2}
    blocks_actions: list[str] = field(default_factory=list)
    grants_actions: list[str] = field(default_factory=list)
    flag_effects: dict = field(default_factory=dict)  # game flag changes on apply

    def is_expired(self) -> bool:
        if self.rounds_remaining is None:
            return False
        return self.rounds_remaining <= 0

    def tick(self):
        if self.rounds_remaining is not None:
            self.rounds_remaining -= 1


# --- Status Registry ---
# All known statuses in the game. Add entries here as the campaign expands.

STATUS_REGISTRY: dict[str, StatusEffect] = {
    "brine_scald_stabilized": StatusEffect(
        id="brine_scald_stabilized",
        name="Brine Scald (Stabilized)",
        category=StatusCategory.WOUND,
        description="Severe burn from salt-corrosive contact. Stabilized — not worsening, but still tender.",
        stat_modifiers={"con": -1},
    ),
    "minor_hollow_echo": StatusEffect(
        id="minor_hollow_echo",
        name="Minor Hollow Echo",
        category=StatusCategory.OCCULT,
        description="Residual hollow-binding resonance. Causes disorientation near active binding sites.",
        stat_modifiers={"wis": -1},
    ),
    "blood_read": StatusEffect(
        id="blood_read",
        name="Blood Read",
        category=StatusCategory.CLAIMANT,
        description="Bloodline has been scanned by an old system. Claimant identity partially exposed to ancient structures.",
    ),
    "tide_marked_clear": StatusEffect(
        id="tide_marked_clear",
        name="Tide-Marked (Clear)",
        category=StatusCategory.OCCULT,
        description="Marked by the Tide. The mark is clean — no corruption detected. Opens certain old-law doors.",
        grants_actions=["invoke_tide_authority"],
    ),
    "witness_seared": StatusEffect(
        id="witness_seared",
        name="Witness-Seared",
        category=StatusCategory.CLAIMANT,
        description="Has witnessed a bound memory of succession law. The witness cannot be undone.",
        flag_effects={"witnessed_high_empress_record": True},
    ),
    "claimant_imprint_complete": StatusEffect(
        id="claimant_imprint_complete",
        name="Claimant Imprint Complete",
        category=StatusCategory.CLAIMANT,
        description="Saint Vaelor has recognized the bloodline and recorded the claimant mark. This is lawful and permanent.",
        grants_actions=["invoke_claimant_authority"],
        flag_effects={"claimant_verified_at_saint_vaelor": True},
    ),
    "claim_contested": StatusEffect(
        id="claim_contested",
        name="Claim Contested",
        category=StatusCategory.LEGAL,
        description="Hostile factions have registered a counter-challenge to the bloodline claim.",
    ),
    "registry_scored_contained": StatusEffect(
        id="registry_scored_contained",
        name="Registry-Scored (Contained)",
        category=StatusCategory.LEGAL,
        description="A hostile registry remnant marked this bloodline as a threat. Remnant destroyed — mark contained but not erased.",
    ),
    "unlawful_substitution_recorded": StatusEffect(
        id="unlawful_substitution_recorded",
        name="Unlawful Substitution Recorded",
        category=StatusCategory.LEGAL,
        description="The system has recorded evidence of an unlawful substitution in the succession chain.",
    ),
}


class StatusManager:
    def __init__(self):
        self.active: dict[str, StatusEffect] = {}

    def apply(self, status_id: str) -> StatusEffect:
        """Apply a status by ID from the registry."""
        if status_id not in STATUS_REGISTRY:
            raise ValueError(f"Unknown status: {status_id}")
        # Deep copy so each character instance is independent
        import copy
        effect = copy.deepcopy(STATUS_REGISTRY[status_id])
        if effect.duration_rounds is not None:
            effect.rounds_remaining = effect.duration_rounds
        self.active[status_id] = effect
        return effect

    def remove(self, status_id: str) -> bool:
        if status_id in self.active:
            del self.active[status_id]
            return True
        return False

    def has(self, status_id: str) -> bool:
        return status_id in self.active

    def tick_all(self):
        """Advance all timed statuses by one round. Remove expired."""
        expired = []
        for sid, effect in self.active.items():
            effect.tick()
            if effect.is_expired():
                expired.append(sid)
        for sid in expired:
            del self.active[sid]

    def get_all_modifiers(self) -> dict:
        """Aggregate all stat modifiers from active statuses."""
        totals = {}
        for effect in self.active.values():
            for stat, val in effect.stat_modifiers.items():
                totals[stat] = totals.get(stat, 0) + val
        return totals

    def list_ids(self) -> list[str]:
        return list(self.active.keys())
