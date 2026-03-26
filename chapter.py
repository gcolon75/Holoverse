"""
engine/chapter.py
Chapter definitions, transition rules, and POV switch logic.

Core rule from the handoff:
  POV switches happen only at strong chapter beats:
  injury, revelation, betrayal, or cliffhanger.
  Do NOT merge the rails early just because the plot smells related.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SwitchTrigger(Enum):
    INJURY          = "injury"
    REVELATION      = "revelation"
    BETRAYAL        = "betrayal"
    CLIFFHANGER     = "cliffhanger"
    OBJECTIVE_COMPLETE = "objective_complete"
    FORCED          = "forced"       # GM/developer override


@dataclass
class ChapterDef:
    id: str
    pov: str                          # "damon" or "elira"
    title: str
    location: str
    opening_goal: str
    summary: str
    prerequisite_flags: dict = field(default_factory=dict)   # flags that must be true to unlock
    completion_flags: dict = field(default_factory=dict)     # flags set when chapter ends
    unlocks_chapters: list[str] = field(default_factory=list)
    switch_trigger: Optional[SwitchTrigger] = None
    completed: bool = False


# ---
# Chapter registry — seeded from handoff + live continuation
# ---

CHAPTER_REGISTRY: dict[str, ChapterDef] = {

    # --- DAMON RAIL ---

    "damon_ch1_quiet_lanterns": ChapterDef(
        id="damon_ch1_quiet_lanterns",
        pov="damon",
        title="House of Quiet Lanterns",
        location="quiet_lanterns_inn",
        opening_goal="Answer the summons. Learn who shaped the exile.",
        summary=(
            "Damon answered a secret summons, met allied watchers, learned the "
            "Veiled Throne shaped his exile, fought a Hollow-bound sea entity, "
            "and gained the Anchor Shard."
        ),
        completion_flags={"anchor_shard_obtained": True},
        unlocks_chapters=["damon_ch2_tide_chapel"],
        switch_trigger=SwitchTrigger.REVELATION,
        completed=True,
    ),

    "damon_ch2_tide_chapel": ChapterDef(
        id="damon_ch2_tide_chapel",
        pov="damon",
        title="Tide Chapel / The Casket",
        location="tide_chapel_sanctum",
        opening_goal="Open the blood-keyed sanctum. Find the casket.",
        summary=(
            "Damon opened a blood-keyed sanctum, escaped Lady Merrow Vale, "
            "and recovered the Sealed Bronze Casket containing proof of his "
            "imperial succession claim."
        ),
        prerequisite_flags={"anchor_shard_obtained": True},
        completion_flags={"high_empress_letter_read": True},
        unlocks_chapters=["elira_ch1_gilded_vice", "damon_ch3_western_cliffs"],
        switch_trigger=SwitchTrigger.REVELATION,
        completed=True,
    ),

    "damon_ch3_western_cliffs": ChapterDef(
        id="damon_ch3_western_cliffs",
        pov="damon",
        title="Western Cliffs",
        location="western_cliffs",
        opening_goal="Investigate the western road. Assess the rogue.",
        summary=(
            "Damon crossed paths with Elira and Kest. Social tension, bluffing, "
            "misdirection. Damon let Elira go — marking her as a future problem."
        ),
        prerequisite_flags={"high_empress_letter_read": True},
        completion_flags={"elira_crossed_damons_path": True},
        unlocks_chapters=["damon_ch4_saint_vaelor"],
        switch_trigger=SwitchTrigger.CLIFFHANGER,
        completed=True,
    ),

    "damon_ch4_saint_vaelor": ChapterDef(
        id="damon_ch4_saint_vaelor",
        pov="damon",
        title="Saint Vaelor",
        location="saint_vaelor_sanctum",
        opening_goal="Enter the sanctum. Complete the claimant proof.",
        summary=(
            "Damon reached the renewal chamber, declared authority by blood and signet, "
            "witnessed the High Empress succession record, completed the claimant imprint, "
            "destroyed a hostile registry remnant, and recovered Malrec's bronze tablet. "
            "Western Node located: Sablewake, beneath The Gilded Vice."
        ),
        prerequisite_flags={"elira_crossed_damons_path": True},
        completion_flags={
            "claimant_verified_at_saint_vaelor": True,
            "malrec_betrayal_confirmed": True,
            "western_node_located": True,
        },
        unlocks_chapters=["damon_ch5_road_to_sablewake"],
        switch_trigger=SwitchTrigger.REVELATION,
        completed=True,
    ),

    "damon_ch5_road_to_sablewake": ChapterDef(
        id="damon_ch5_road_to_sablewake",
        pov="damon",
        title="The Road to Sablewake",
        location="saint_vaelor_outer_ridge",
        opening_goal="Travel to Sablewake. Acquire or fabricate a courtesy mark.",
        summary="Damon moves away from Saint Vaelor with Kest and Carrow, heading west.",
        prerequisite_flags={"western_node_located": True},
        completion_flags={"sablewake_reached": True},
        unlocks_chapters=["damon_ch6_sablewake_arrival"],
        switch_trigger=SwitchTrigger.OBJECTIVE_COMPLETE,
        completed=False,
    ),

    "damon_ch6_sablewake_arrival": ChapterDef(
        id="damon_ch6_sablewake_arrival",
        pov="damon",
        title="Sablewake",
        location="sablewake_harbor",
        opening_goal="Navigate the city. Find access to The Gilded Vice's lower level.",
        summary="",
        prerequisite_flags={"sablewake_reached": True},
        completion_flags={"gilded_vice_infiltrated": True},
        unlocks_chapters=["damon_ch7_western_node"],
        switch_trigger=SwitchTrigger.CLIFFHANGER,
        completed=False,
    ),

    "damon_ch7_western_node": ChapterDef(
        id="damon_ch7_western_node",
        pov="damon",
        title="The Western Node",
        location="gilded_vice_lower_access",
        opening_goal="Reach the Western Node. Repair the broken succession.",
        summary="",
        prerequisite_flags={"gilded_vice_infiltrated": True},
        completion_flags={"western_node_accessed": True},
        switch_trigger=SwitchTrigger.REVELATION,
        completed=False,
    ),

    # --- ELIRA RAIL ---

    "elira_ch1_gilded_vice": ChapterDef(
        id="elira_ch1_gilded_vice",
        pov="elira",
        title="The Gilded Vice",
        location="gilded_vice_main_floor",
        opening_goal="Win big. Get out. Don't get caught.",
        summary=(
            "Elira won heavily at The Gilded Vice, attracted Lord Saervan's attention, "
            "gained a Black Tide Courtesy Token, and stole Saervan's dark-stone ring."
        ),
        completion_flags={
            "elira_has_courtesy_token": True,
            "elira_has_saervan_ring": True,
        },
        unlocks_chapters=["elira_ch2_western_road"],
        switch_trigger=SwitchTrigger.CLIFFHANGER,
        completed=True,
    ),

    "elira_ch2_western_road": ChapterDef(
        id="elira_ch2_western_road",
        pov="elira",
        title="The Western Road",
        location="western_road_coastal",
        opening_goal="Follow the ring west. Stay ahead of Saervan.",
        summary=(
            "Elira followed the ring west. Crossed paths with Damon and Kest. "
            "Escaped through bluffing and misdirection."
        ),
        prerequisite_flags={"elira_has_saervan_ring": True},
        completion_flags={"elira_crossed_damons_path": True},
        unlocks_chapters=["elira_ch3_sablewake"],
        switch_trigger=SwitchTrigger.INJURY,
        completed=True,
    ),

    "elira_ch3_sablewake": ChapterDef(
        id="elira_ch3_sablewake",
        pov="elira",
        title="Sablewake — The Hard Way",
        location="sablewake_dockside",
        opening_goal="Reach Sablewake. Understand what the ring actually opens.",
        summary="",
        prerequisite_flags={"elira_crossed_damons_path": True},
        completion_flags={"elira_in_sablewake": True},
        unlocks_chapters=["elira_ch4_gilded_vice_return"],
        switch_trigger=SwitchTrigger.REVELATION,
        completed=False,
    ),

    "elira_ch4_gilded_vice_return": ChapterDef(
        id="elira_ch4_gilded_vice_return",
        pov="elira",
        title="Return to the Vice",
        location="gilded_vice_main_floor",
        opening_goal="Use the token. Get below. Find what Saervan is protecting.",
        summary="",
        prerequisite_flags={"elira_in_sablewake": True},
        completion_flags={"elira_reached_lower_access": True},
        switch_trigger=SwitchTrigger.CLIFFHANGER,
        completed=False,
    ),
}


class ChapterEngine:
    """
    Manages chapter state, transitions, and POV switching.
    The rails stay separate until the story earns the merge.
    """

    def __init__(self):
        self.registry = CHAPTER_REGISTRY

    def get(self, chapter_id: str) -> Optional[ChapterDef]:
        return self.registry.get(chapter_id)

    def get_current(self, chapter_id: str) -> Optional[ChapterDef]:
        return self.get(chapter_id)

    def complete_chapter(self, chapter_id: str, game_flags) -> list[str]:
        """
        Mark a chapter complete, apply its completion flags, return unlocked chapters.
        """
        chapter = self.get(chapter_id)
        if not chapter:
            return []

        chapter.completed = True

        for flag_key, flag_val in chapter.completion_flags.items():
            game_flags.set(flag_key, flag_val)

        return chapter.unlocks_chapters

    def available_chapters(self, pov: str, game_flags) -> list[ChapterDef]:
        """Return chapters available for a given POV based on current flags."""
        available = []
        for chapter in self.registry.values():
            if chapter.pov != pov:
                continue
            if chapter.completed:
                continue
            prereqs_met = all(
                game_flags.get(k) == v
                for k, v in chapter.prerequisite_flags.items()
            )
            if prereqs_met:
                available.append(chapter)
        return available

    def should_switch_pov(
        self,
        current_pov: str,
        trigger: SwitchTrigger,
        game_flags,
    ) -> Optional[str]:
        """
        Given a trigger event, determine if a POV switch is warranted.
        Returns the new POV id, or None if no switch.

        Core rule: do NOT switch just because it's convenient.
        Only switch on strong beats.
        """
        strong_triggers = {
            SwitchTrigger.INJURY,
            SwitchTrigger.REVELATION,
            SwitchTrigger.BETRAYAL,
            SwitchTrigger.CLIFFHANGER,
            SwitchTrigger.FORCED,
        }

        if trigger not in strong_triggers:
            return None

        # Only switch if the other rail has available chapters
        other_pov = "elira" if current_pov == "damon" else "damon"
        available = self.available_chapters(other_pov, game_flags)

        # Don't switch to Elira until she's been activated
        if other_pov == "elira" and not game_flags.get("elira_rail_active"):
            return None

        return other_pov if available else None

    def check_convergence(self, game_flags) -> bool:
        """
        Returns True if conditions are met for the rails to start converging.
        This is a hard gate — don't merge early.
        """
        return (
            game_flags.get("claimant_verified_at_saint_vaelor")
            and game_flags.get("elira_in_sablewake")
            and game_flags.get("western_node_located")
        )

    def to_dict(self) -> dict:
        return {
            cid: {
                "id": c.id,
                "pov": c.pov,
                "title": c.title,
                "completed": c.completed,
                "location": c.location,
                "goal": c.opening_goal,
            }
            for cid, c in self.registry.items()
        }


# Singleton
_engine: Optional[ChapterEngine] = None


def get_chapter_engine() -> ChapterEngine:
    global _engine
    if _engine is None:
        _engine = ChapterEngine()
    return _engine
