"""
engine/crossrail.py
Shared flag system — the event bus between Damon and Elira's rails.

When something happens on one rail, it can ripple into the other
through shared world flags. This is NOT a merge — it's an echo.
The rails stay separate. The world doesn't.

Rule: A crossrail effect fires when a flag is set AND the
receiving rail has a handler registered for it.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum


class RailEffect(Enum):
    """How a cross-rail event manifests on the receiving side."""
    FACTION_ALERT    = "faction_alert"    # A faction learns something
    NPC_ATTITUDE     = "npc_attitude"     # An NPC's trust/hostility shifts
    LOCATION_CHANGE  = "location_change"  # A location becomes more/less accessible
    INTEL_AVAILABLE  = "intel_available"  # New information becomes discoverable
    THREAT_ELEVATED  = "threat_elevated"  # Heat goes up on the other rail
    DOOR_OPENS       = "door_opens"       # An access path becomes available
    DOOR_CLOSES      = "door_closes"      # An access path shuts


@dataclass
class CrossRailEvent:
    id: str
    trigger_flag: str           # What flag triggers this
    trigger_value: object       # What value it must be set to
    source_pov: str             # Which rail triggers it ("damon" or "elira")
    target_pov: str             # Which rail receives the effect
    effect_type: RailEffect
    description: str            # Human-readable: what happened in the world
    narrative_hint: str         # What the target POV might notice (for LLM)
    side_effects: dict = field(default_factory=dict)  # Flag changes to apply
    fired: bool = False


# ---
# Cross-rail event registry
# ---
# These are the moments where one character's actions ripple into the other's world.
# Add entries here as the campaign expands.

CROSSRAIL_EVENTS: list[CrossRailEvent] = [

    CrossRailEvent(
        id="damon_claimant_verified_raises_heat",
        trigger_flag="claimant_verified_at_saint_vaelor",
        trigger_value=True,
        source_pov="damon",
        target_pov="elira",
        effect_type=RailEffect.THREAT_ELEVATED,
        description="Damon's claimant proof triggered old registry systems. Black Tide alert level elevated.",
        narrative_hint=(
            "Elira notices the harbor is unusually tense. More private guards. "
            "Courtesy-house staff are checking tokens more carefully."
        ),
        side_effects={"black_tide_alert_elevated": True},
    ),

    CrossRailEvent(
        id="damon_western_node_located_activates_saervan",
        trigger_flag="western_node_located",
        trigger_value=True,
        source_pov="damon",
        target_pov="elira",
        effect_type=RailEffect.NPC_ATTITUDE,
        description="Saervan received word that someone is moving toward the Node. He is now actively hunting.",
        narrative_hint=(
            "Saervan has been seen near the docks. He's asking about a man traveling with an archer."
        ),
        side_effects={"saervan_actively_hunting": True},
    ),

    CrossRailEvent(
        id="elira_token_in_play_opens_lower_access",
        trigger_flag="elira_has_courtesy_token",
        trigger_value=True,
        source_pov="elira",
        target_pov="damon",
        effect_type=RailEffect.DOOR_OPENS,
        description="Elira's genuine courtesy token is trackable by the Black Tide network.",
        narrative_hint=(
            "Kest finds a Black Tide route marker near the road. Someone with a real token "
            "passed through recently — and the mark is fresh."
        ),
        side_effects={"elira_token_trackable_by_black_tide": True},
    ),

    CrossRailEvent(
        id="elira_ring_stolen_closes_saervan_door",
        trigger_flag="elira_has_saervan_ring",
        trigger_value=True,
        source_pov="elira",
        target_pov="damon",
        effect_type=RailEffect.DOOR_CLOSES,
        description="Saervan's access key is missing. He's locked out of certain western node functions.",
        narrative_hint=(
            "Brannock Hale mentions that someone at the Vice is furious about a missing access piece. "
            "The lower floors have been partially locked down."
        ),
        side_effects={"saervan_access_key_missing": True},
    ),

    CrossRailEvent(
        id="elira_in_sablewake_creates_social_asset",
        trigger_flag="elira_in_sablewake",
        trigger_value=True,
        source_pov="elira",
        target_pov="damon",
        effect_type=RailEffect.INTEL_AVAILABLE,
        description="Elira is now in Sablewake and moving in Black Tide-adjacent circles.",
        narrative_hint=(
            "There are rumors of a sharp-tongued elf who beat the house at the Vice "
            "and has been seen near the courtesy houses. She's either an asset or a trap."
        ),
        side_effects={"elira_sablewake_rumor_active": True},
    ),

    CrossRailEvent(
        id="damon_sablewake_reached_triggers_faction_watch",
        trigger_flag="sablewake_reached",
        trigger_value=True,
        source_pov="damon",
        target_pov="elira",
        effect_type=RailEffect.FACTION_ALERT,
        description="A Reaveborne-blooded man arrived in Sablewake with an archer and an injured cleric.",
        narrative_hint=(
            "Elira overhears courtesy-house staff whispering about a dangerous arrival. "
            "The description matches someone she's seen before."
        ),
        side_effects={"damon_arrival_known_to_black_tide": True},
    ),

    CrossRailEvent(
        id="elira_lower_access_reached_shared_objective",
        trigger_flag="elira_reached_lower_access",
        trigger_value=True,
        source_pov="elira",
        target_pov="damon",
        effect_type=RailEffect.LOCATION_CHANGE,
        description="The lower access has been breached from the social side. A path is open — briefly.",
        narrative_hint=(
            "Carrow detects a shift in the old prayer-lines beneath the harbor. "
            "Something below has been disturbed. The window won't stay open long."
        ),
        side_effects={"lower_access_breached": True, "convergence_window_open": True},
    ),
]


class CrossRailEngine:
    def __init__(self):
        self.events = {e.id: e for e in CROSSRAIL_EVENTS}
        self.fired_log: list[str] = []

    def check_and_fire(self, game_flags) -> list[CrossRailEvent]:
        """
        Scan all unfired events. Fire any whose trigger_flag matches.
        Apply side effects. Return newly fired events.
        """
        newly_fired = []

        for event in self.events.values():
            if event.fired:
                continue
            current_value = game_flags.get(event.trigger_flag)
            if current_value == event.trigger_value:
                event.fired = True
                self.fired_log.append(event.id)
                # Apply side effects to flags
                for k, v in event.side_effects.items():
                    game_flags.set(k, v)
                newly_fired.append(event)

        return newly_fired

    def get_narrative_hints(self, pov: str, game_flags) -> list[str]:
        """
        Return narrative hints visible to a given POV based on fired events.
        Used to inject world-awareness into LLM prompts.
        """
        hints = []
        for event in self.events.values():
            if not event.fired:
                continue
            if event.target_pov != pov:
                continue
            hints.append(event.narrative_hint)
        return hints

    def summary(self) -> list[dict]:
        return [
            {
                "id": e.id,
                "fired": e.fired,
                "source": e.source_pov,
                "target": e.target_pov,
                "effect": e.effect_type.value,
                "description": e.description,
            }
            for e in self.events.values()
        ]


# Singleton
_crossrail: Optional[CrossRailEngine] = None


def get_crossrail() -> CrossRailEngine:
    global _crossrail
    if _crossrail is None:
        _crossrail = CrossRailEngine()
    return _crossrail
