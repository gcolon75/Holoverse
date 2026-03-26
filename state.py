"""
game/state.py
Master game state. Single source of truth. Everything flows through here.
"""

from dataclasses import dataclass, field
from typing import Optional
from engine.status import StatusManager
from engine.inventory import Inventory


@dataclass
class CharacterStats:
    str: int = 10
    dex: int = 10
    con: int = 10
    int: int = 10
    wis: int = 10
    cha: int = 10


@dataclass
class Character:
    id: str
    name: str
    hp: int
    max_hp: int
    ac: int
    stats: CharacterStats = field(default_factory=CharacterStats)
    statuses: StatusManager = field(default_factory=StatusManager)
    inventory: Inventory = field(default_factory=lambda: Inventory("unknown"))
    flags: dict = field(default_factory=dict)
    relationship_ids: list[str] = field(default_factory=list)
    is_alive: bool = True

    def __post_init__(self):
        self.inventory.owner_id = self.id

    def effective_ac(self) -> int:
        mods = self.statuses.get_all_modifiers()
        return self.ac + mods.get("ac", 0)

    def stat_modifier(self, stat: str) -> int:
        base = getattr(self.stats, stat, 10)
        status_mods = self.statuses.get_all_modifiers()
        total = base + status_mods.get(stat, 0)
        return (total - 10) // 2


@dataclass
class GameFlags:
    # --- Damon rail: completed ---
    damon_exiled: bool = True
    anchor_shard_obtained: bool = True
    high_empress_letter_read: bool = True
    claimant_verified_at_saint_vaelor: bool = True
    malrec_betrayal_confirmed: bool = True
    western_node_located: bool = True
    western_node_location: str = "sablewake_gilded_vice"
    western_node_requires_courtesy_mark: bool = True
    silver_black_vial_consumed: bool = True
    anchor_shard_echo_spent: bool = True
    saint_vaelor_keyed_to_damon: bool = True
    witnessed_high_empress_record: bool = True

    # --- Elira rail: completed ---
    elira_has_courtesy_token: bool = True
    elira_has_saervan_ring: bool = True
    elira_crossed_damons_path: bool = True

    # --- Elira rail: active ---
    elira_rail_active: bool = False
    elira_in_sablewake: bool = False
    elira_reached_lower_access: bool = False

    # --- Damon rail: active ---
    sablewake_reached: bool = False
    gilded_vice_infiltrated: bool = False
    western_node_accessed: bool = False
    courtesy_mark_obtained: bool = False

    # --- Crossrail side effects (set by CrossRailEngine) ---
    black_tide_alert_elevated: bool = False
    saervan_actively_hunting: bool = False
    elira_token_trackable_by_black_tide: bool = True
    saervan_access_key_missing: bool = True
    elira_sablewake_rumor_active: bool = False
    damon_arrival_known_to_black_tide: bool = False
    lower_access_breached: bool = False
    convergence_window_open: bool = False

    def set(self, key: str, value):
        setattr(self, key, value)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class SceneState:
    id: str = "ridge_below_saint_vaelor"
    chapter_id: str = "damon_ch5_road_to_sablewake"
    pov: str = "damon"
    location: str = "saint_vaelor_outer_ridge"
    goal: str = "travel_to_sablewake"
    resolved: bool = False
    description: str = ""
    available_actions: list[str] = field(default_factory=list)


@dataclass
class RailState:
    """Tracks each POV rail's chapter position independently."""
    current_chapter: str = ""
    last_switch_trigger: str = ""
    turns_on_this_rail: int = 0
    pending_switch: bool = False
    pending_switch_to: str = ""


@dataclass
class GameState:
    active_pov: str = "damon"
    chapter: str = "damon_ch5_road_to_sablewake"
    scene: SceneState = field(default_factory=SceneState)
    flags: GameFlags = field(default_factory=GameFlags)
    characters: dict[str, Character] = field(default_factory=dict)
    rails: dict[str, RailState] = field(default_factory=lambda: {
        "damon": RailState(current_chapter="damon_ch5_road_to_sablewake"),
        "elira": RailState(current_chapter="elira_ch3_sablewake"),
    })
    turn: int = 0
    in_combat: bool = False
    combat_log: list = field(default_factory=list)
    crossrail_fired: list[str] = field(default_factory=list)

    def get_active_character(self) -> Optional[Character]:
        return self.characters.get(self.active_pov)

    def get_character(self, char_id: str) -> Optional[Character]:
        return self.characters.get(char_id)

    def advance_turn(self):
        self.turn += 1
        rail = self.rails.get(self.active_pov)
        if rail:
            rail.turns_on_this_rail += 1

    def switch_pov(self, new_pov: str, trigger: str = "manual"):
        """Execute a POV switch. Updates active_pov, chapter, scene."""
        from engine.chapter import get_chapter_engine
        self.active_pov = new_pov
        rail = self.rails.get(new_pov)
        if rail:
            self.chapter = rail.current_chapter
            rail.last_switch_trigger = trigger
            rail.turns_on_this_rail = 0
            rail.pending_switch = False

        # Update scene to match new pov/chapter
        engine = get_chapter_engine()
        chapter_def = engine.get(self.chapter)
        if chapter_def:
            self.scene.pov = new_pov
            self.scene.chapter_id = self.chapter
            self.scene.location = chapter_def.location
            self.scene.goal = chapter_def.opening_goal

    def queue_pov_switch(self, to_pov: str, trigger: str):
        """Schedule a switch at end of current scene."""
        rail = self.rails.get(self.active_pov)
        if rail:
            rail.pending_switch = True
            rail.pending_switch_to = to_pov
            rail.last_switch_trigger = trigger

    def has_pending_switch(self) -> bool:
        rail = self.rails.get(self.active_pov)
        return rail.pending_switch if rail else False


def build_initial_state() -> GameState:
    """
    Seed the game state from the Vaelrune handoff doc.
    Damon: mid-Chapter 5, heading to Sablewake.
    Elira: seeded but rail not yet active (activated by player choice or story beat).
    """
    state = GameState()

    # --- Damon ---
    damon = Character(
        id="damon",
        name="Damon Reaveborne",
        hp=6,
        max_hp=12,
        ac=12,
        stats=CharacterStats(str=14, dex=12, con=12, int=16, wis=14, cha=14),
        relationship_ids=["kest", "carrow"],
        flags={
            "is_claimant_verified": True,
            "saint_vaelor_keyed": True,
            "is_exiled_heir": True,
        },
    )
    for status_id in [
        "brine_scald_stabilized", "minor_hollow_echo", "blood_read",
        "tide_marked_clear", "witness_seared", "claimant_imprint_complete",
        "claim_contested", "registry_scored_contained",
        "unlawful_substitution_recorded",
    ]:
        damon.statuses.apply(status_id)

    for item_id in [
        "longsword", "anchor_shard", "succession_signet",
        "veiled_throne_packet", "malrec_tablet", "high_empress_letter",
        "sealed_bronze_casket", "silver_black_vial",
    ]:
        damon.inventory.add(item_id)

    # --- Kest ---
    kest = Character(
        id="kest", name="Kest",
        hp=10, max_hp=10, ac=14,
        stats=CharacterStats(str=12, dex=16, con=14, int=12, wis=13, cha=10),
        flags={"role": "archer_scout", "trust_level": "suspicious_but_reliable"},
    )

    # --- Brother Carrow ---
    carrow = Character(
        id="carrow", name="Brother Carrow",
        hp=5, max_hp=8, ac=11,
        stats=CharacterStats(str=10, dex=10, con=11, int=15, wis=17, cha=12),
        flags={"role": "custodian_liturgical_guide", "trust_level": "trust_damaged", "injured": True},
    )

    # --- Elira — seeded, rail inactive ---
    elira = Character(
        id="elira", name="Elira Thorne",
        hp=9, max_hp=10, ac=13,
        stats=CharacterStats(str=10, dex=16, con=12, int=14, wis=12, cha=17),
        flags={"role": "runaway_rogue", "rail_active": False},
    )
    for item_id in ["black_tide_courtesy_token", "dark_stone_ring"]:
        elira.inventory.add(item_id)

    state.characters = {
        "damon": damon, "kest": kest,
        "carrow": carrow, "elira": elira,
    }

    # Fire initial crossrail events from already-true flags
    from engine.crossrail import get_crossrail
    crossrail = get_crossrail()
    fired = crossrail.check_and_fire(state.flags)
    state.crossrail_fired = [e.id for e in fired]

    return state
