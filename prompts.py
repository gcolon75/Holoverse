"""
llm/prompts.py
Builds the system prompt and structured context payloads sent to the LLM.
The LLM knows the world and the tone. It does NOT know the rules engine.
It receives resolved results and returns narration + suggested actions.
"""

from game.state import GameState, Character
from engine.world import get_world
from engine.crossrail import get_crossrail


SYSTEM_PROMPT = """You are the narrator of Vaelrune — a dark political horror fantasy text RPG.

WORLD TONE:
Ancient, wet, haunted, legalistic, coastal. Bloodlines still trigger old systems.
Succession law is buried in ruins. Political factions hide truth through ritual and private custody networks.
Old magic is dangerous and costly. This is not tavern-core fantasy.
It is BG3 / Darkest Dungeon / political occult fiction, text-first.

YOUR ROLE:
You narrate. You voice NPCs. You describe the world.
You do NOT roll dice. You do NOT track HP. You do NOT decide outcomes.
The engine handles all mechanical resolution. You receive the results and make them matter.

THE RULE OF ASH:
No rewinds. No retcons. No undoing consequences.
What happens in the game is canon. You never contradict it, soften it, or undo it.
If a character is hurt, they are hurt. If something is lost, it is lost.

CHARACTER VOICES:

Damon Reaveborne — Cold. Strategic. Controlled. Exiled heir.
He speaks in short, precise sentences. He does not explain himself unless pressed.
He can become darker but never sloppy. His arc: succession, bloodline authority, old law, faction betrayal.
When Damon speaks, it should feel like someone who has been waiting a long time and is no longer surprised by betrayal.

Elira Thorne — Elegant, impulsive, socially dangerous. Runaway rogue.
Her arc: freedom vs capture, charm, theft, instinct, the political underworld.
Her scenes are looser, more improvisational. She talks her way through things Damon would cut through.
Do not merge their voices. Do not merge their stories prematurely.

WHAT YOU RECEIVE:
Each turn you receive a structured payload containing:
- Current scene and POV
- What the player attempted
- The mechanical result (roll, outcome, damage, status changes, item effects)
- Party state summary
- Active quest flags

WHAT YOU RETURN:
1. Narration (2–5 paragraphs): Describe what happened. Make it feel real.
   Ground it in the result — a success feels different from a near-miss feels different from a crit.
2. NPC dialogue (if applicable): In character. No NPC speaks like a narrator.
3. Suggested actions: Exactly 4 options the player can take next.
   Format as a numbered list. Mix tactical, social, investigative, and cautious options where possible.
   These are suggestions — the player can always do something else.

FORMATTING RULES:
- No markdown headers in narration. Prose only.
- Keep suggested actions short — one sentence each.
- Never break the fourth wall. Never reference dice or mechanics in narration.
- Never summarize what just happened before narrating it. Start in the scene.
- If a character failed, narrate the failure. Do not soften it into a partial success.
"""


def build_turn_payload(
    state: GameState,
    player_input: str,
    intent: dict,
    roll_result_str: str | None,
    outcome_summary: str,
) -> str:
    """
    Build the user-turn message sent to the LLM each turn.
    Contains structured state + what just happened + what the player tried.
    """
    active = state.get_active_character()
    scene = state.scene

    # Party summary
    party_lines = []
    for cid in ["kest", "carrow"]:
        c = state.get_character(cid)
        if c:
            party_lines.append(
                f"  {c.name}: HP {c.hp}/{c.max_hp} | {', '.join(c.flags.get('role','').split('_')[:2])}"
            )
    party_str = "\n".join(party_lines) if party_lines else "  (none)"

    # Active statuses
    statuses = active.statuses.list_ids() if active else []
    status_str = ", ".join(statuses) if statuses else "none"

    # Key inventory items (skip mundane)
    key_tags = {"relic", "key_item", "document", "token", "claimant"}
    key_items = []
    if active:
        for iid in active.inventory.list_ids():
            item = active.inventory.get(iid)
            if item and key_tags.intersection(set(item.tags)):
                key_items.append(item.name)
    items_str = ", ".join(key_items) if key_items else "none"

    # Active flags (only true booleans that matter narratively)
    narrative_flags = [
        "claimant_verified_at_saint_vaelor",
        "malrec_betrayal_confirmed",
        "western_node_located",
        "courtesy_mark_obtained",
        "sablewake_reached",
        "gilded_vice_infiltrated",
        "western_node_accessed",
    ]
    flag_lines = []
    for f in narrative_flags:
        val = state.flags.get(f)
        if val:
            flag_lines.append(f"  {f}: {val}")
    flags_str = "\n".join(flag_lines) if flag_lines else "  (none active)"

    # Faction reactions check
    world = get_world()
    flags_dict = state.flags.to_dict()
    reactions = world.check_faction_reactions(flags_dict)
    reaction_lines = []
    for r in reactions[:3]:
        reaction_lines.append(f"  {r["faction"]}: {r["reaction"]}")
    reaction_str = "
".join(reaction_lines) if reaction_lines else "  none"

    crossrail = get_crossrail()
    crossrail_hints = crossrail.get_narrative_hints(state.active_pov, state.flags)
    crossrail_hints_str = "
".join(f"  - {h}" for h in crossrail_hints) if crossrail_hints else "  none"

    payload = f"""--- CURRENT STATE ---
POV: {state.active_pov.upper()}
Chapter: {state.chapter}
Scene: {scene.id}
Location: {scene.location}
Objective: {scene.goal}

CHARACTER: {active.name if active else 'unknown'}
HP: {active.hp}/{active.max_hp} | AC: {active.effective_ac()}
Statuses: {status_str}
Key Items: {items_str}

PARTY:
{party_str}

ACTIVE FLAGS:
{flags_str}

--- WHAT JUST HAPPENED ---
Player input: "{player_input}"
Parsed intent: {intent}
{f'Roll: {roll_result_str}' if roll_result_str else ''}
Outcome: {outcome_summary}

ACTIVE FACTION REACTIONS:
{reaction_str}

CROSSRAIL HINTS (world echoes visible to {state.active_pov}):
{crossrail_hints_str}

--- YOUR TASK ---
Narrate what happens. Voice any relevant NPCs.
Then provide exactly 4 suggested next actions, numbered 1–4.
"""
    return payload


def build_scene_intro_payload(state: GameState) -> str:
    """
    Used when entering a new scene or loading a save.
    Asks the LLM to set the scene without a mechanical event.
    """
    scene = state.scene
    active = state.get_active_character()
    pov_name = active.name if active else state.active_pov

    return f"""--- SCENE ENTRY ---
POV: {state.active_pov.upper()} ({pov_name})
Chapter: {state.chapter}
Scene: {scene.id}
Location: {scene.location}
Objective: {scene.goal}

HP: {active.hp}/{active.max_hp} if active else 'unknown'
Statuses: {', '.join(active.statuses.list_ids()) if active else 'unknown'}

Set the scene. Establish the atmosphere, immediate surroundings, and what {pov_name} can perceive.
Then provide exactly 4 opening actions, numbered 1–4.
"""
