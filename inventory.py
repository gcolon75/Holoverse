"""
engine/inventory.py
Item definitions, relic logic, and inventory management.
Items are structured objects with explicit properties — not just strings.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ItemType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    RELIC = "relic"
    KEY_ITEM = "key_item"
    DOCUMENT = "document"
    CONSUMABLE = "consumable"
    GEAR = "gear"
    TOKEN = "token"


@dataclass
class Item:
    id: str
    name: str
    type: ItemType
    description: str
    tags: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    consumed: bool = False
    owner: Optional[str] = None

    def is_available(self) -> bool:
        return not self.consumed


# --- Item Registry ---

ITEM_REGISTRY: dict[str, Item] = {
    "longsword": Item(
        id="longsword",
        name="Longsword",
        type=ItemType.WEAPON,
        description="Standard military longsword. Well-maintained.",
        tags=["melee", "weapon"],
        properties={"damage_dice": "1d8", "attack_modifier": 2},
    ),
    "anchor_shard": Item(
        id="anchor_shard",
        name="Anchor Shard",
        type=ItemType.RELIC,
        description=(
            "A command-fragment from a Hollow-binding. Cold to the touch. "
            "It hums faintly near corrupted systems."
        ),
        tags=["hollow", "command_fragment", "dangerous", "relic"],
        properties={
            "stored_echo_slots": 1,
            "stored_echo_current": 0,   # Cistern echo was spent at Saint Vaelor
            "can_trace_corruption": True,
            "can_expose_false_prayer_lines": True,
            "can_interfere_lesser_bound": True,
            "entity_size_restriction": "lesser_only",  # NOT for Malrec-tier entities
            "backlash_risk": "high",
        },
    ),
    "succession_signet": Item(
        id="succession_signet",
        name="Hidden Imperial Succession Signet",
        type=ItemType.KEY_ITEM,
        description=(
            "Blood-keyed to the Reaveborne line. Opens claimant structures, "
            "activates old witness protocols, and proves bloodline authority to "
            "systems that still obey the First Tide inheritance laws."
        ),
        tags=["bloodline", "claimant", "key_item", "occult_key"],
        properties={
            "blood_keyed_to": "damon",
            "opens_claimant_structures": True,
            "activates_witness_protocols": True,
            "faction_recognition": ["saint_vaelor", "iverian_old_law", "veiled_throne"],
        },
    ),
    "veiled_throne_packet": Item(
        id="veiled_throne_packet",
        name="Veiled Throne Packet",
        type=ItemType.DOCUMENT,
        description=(
            "A sealed packet of coded letters, payment routes, shipping exemptions, "
            "Black Tide references, and custody clues. Not just lore — this is an "
            "active investigation substrate."
        ),
        tags=["document", "clue_bundle", "veiled_throne", "black_tide_adjacent"],
        properties={
            "contains_coded_letters": True,
            "contains_payment_routes": True,
            "contains_custody_clues": True,
            "unlocked_cross_references": [],  # Fills as player investigates
        },
    ),
    "malrec_tablet": Item(
        id="malrec_tablet",
        name="Malrec's Bronze Tablet",
        type=ItemType.KEY_ITEM,
        description=(
            "A bronze tablet recovered from the Lower Witness Vault. "
            "It confirms the Western Node's location, reveals the displaced witness, "
            "and ties the western custody network to the non-royal courtesy path. "
            "It also explicitly states Damon must never reach the Western Node."
        ),
        tags=["document", "relic", "key_item", "western_node", "malrec"],
        properties={
            "reveals_western_node": True,
            "western_node_location": "sablewake_gilded_vice",
            "confirms_secondary_witness_displacement": True,
            "is_bridge_item_to_act_2": True,
        },
    ),
    "high_empress_letter": Item(
        id="high_empress_letter",
        name="Letter of the High Empress",
        type=ItemType.DOCUMENT,
        description=(
            "A formal letter from the High Empress. Now read and integrated into "
            "the witness record at Saint Vaelor."
        ),
        tags=["document", "imperial", "succession"],
        properties={"read": True, "integrated_into_witness_record": True},
    ),
    "sealed_bronze_casket": Item(
        id="sealed_bronze_casket",
        name="Sealed Bronze Casket",
        type=ItemType.KEY_ITEM,
        description="The casket recovered from the Tide Chapel sanctum. Now opened and empty.",
        tags=["container", "opened"],
        properties={"opened": True, "contents_retrieved": True},
    ),
    "silver_black_vial": Item(
        id="silver_black_vial",
        name="Sealed Silver-Black Vial",
        type=ItemType.CONSUMABLE,
        description=(
            "Contained a bound witness-memory of the High Empress recording Damon "
            "as the concealed continuation under First Tide inheritance. Consumed at "
            "Saint Vaelor — the memory has been witnessed and cannot be unwound."
        ),
        tags=["consumable", "witness_memory", "imperial"],
        properties={"bound_memory_type": "high_empress_succession_record"},
        consumed=True,
    ),
    # --- Elira items ---
    "black_tide_courtesy_token": Item(
        id="black_tide_courtesy_token",
        name="Black Tide Courtesy Token",
        type=ItemType.TOKEN,
        description=(
            "A courtesy marker from the Black Tide network. Small. "
            "Enormous plot leverage — opens doors in western courtesy-custody systems."
        ),
        tags=["token", "black_tide", "courtesy_mark", "western_access"],
        properties={
            "grants_courtesy_recognition": True,
            "network": "black_tide",
            "access_tier": "standard_courtesy",
        },
    ),
    "dark_stone_ring": Item(
        id="dark_stone_ring",
        name="Dark-Stone Ring",
        type=ItemType.KEY_ITEM,
        description=(
            "Stolen from Lord Saervan at The Gilded Vice. Dark stone, cold, "
            "likely tied to the western custody system. The ring that led Elira west."
        ),
        tags=["ring", "saervan", "black_tide_adjacent", "western_custody"],
        properties={
            "original_owner": "saervan",
            "tied_to_western_custody": True,
            "purpose_unknown": True,
        },
    ),
}


class Inventory:
    def __init__(self, owner_id: str):
        self.owner_id = owner_id
        self.items: dict[str, Item] = {}

    def add(self, item_id: str) -> Item:
        import copy
        if item_id not in ITEM_REGISTRY:
            raise ValueError(f"Unknown item: {item_id}")
        item = copy.deepcopy(ITEM_REGISTRY[item_id])
        item.owner = self.owner_id
        self.items[item_id] = item
        return item

    def remove(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False

    def has(self, item_id: str) -> bool:
        return item_id in self.items and self.items[item_id].is_available()

    def get(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)

    def use_relic_echo(self, item_id: str) -> bool:
        """Consume one stored echo from a relic. Returns True if successful."""
        item = self.get(item_id)
        if not item:
            return False
        current = item.properties.get("stored_echo_current", 0)
        if current <= 0:
            return False
        item.properties["stored_echo_current"] -= 1
        return True

    def list_ids(self) -> list[str]:
        return [k for k, v in self.items.items() if v.is_available()]

    def to_dict(self) -> dict:
        return {k: {
            "id": v.id,
            "name": v.name,
            "type": v.type.value,
            "consumed": v.consumed,
            "properties": v.properties,
            "tags": v.tags,
        } for k, v in self.items.items()}
