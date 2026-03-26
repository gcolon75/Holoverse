# Vaelrune

A chapter-based, consequence-heavy text RPG.  
Coded systems handle state and dice. The LLM handles tone, narration, and dialogue.

**Rule of Ash: No rewinds. No retcons. No undoing consequences.**

---

## Setup

```bash
# 1. Clone
git clone https://github.com/gcolon75/Holoverse.git
cd Holoverse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key (narration requires this)
export ANTHROPIC_API_KEY=your_key_here   # Mac/Linux
set ANTHROPIC_API_KEY=your_key_here      # Windows CMD
$env:ANTHROPIC_API_KEY="your_key_here"  # Windows PowerShell

# 4. Run
python main.py
```

Without the API key the engine still runs — no narration, mechanical output only.

---

## Commands

| Command | Description |
|---|---|
| `status` | Full character sheet |
| `inv` | Inventory |
| `party` | Party overview |
| `flags` | All quest flags |
| `quests` | Quest log |
| `quests <quest_id>` | Quest detail + notes |
| `log` | Recent event log |
| `location` | Current location data |
| `travel <destination_id>` | Travel with encounter resolution |
| `inspect <item_id>` | Item detail |
| `npc <npc_id>` | NPC record |
| `faction <faction_id>` | Faction record |
| `chapters` | Chapter map, both rails |
| `crossrail` | Cross-rail event status |
| `pov` | Current POV / rail positions |
| `switch elira` | Activate and switch to Elira's rail |
| `roll <stat> <dc>` | Manual skill check |
| `roll <stat> <dc> adv/dis` | With advantage or disadvantage |
| `fight` | Test combat |
| `save` | Checkpoint save |
| `quit` | Save and exit |

Or just type what you want to do:
```
move toward the harbor
examine the bronze tablet  
bluff the door warden
invoke claimant authority
investigate the courtesy mark
```

---

## Project Structure

```
vaelrune/
├── main.py
├── requirements.txt
├── .gitignore
│
├── engine/
│   ├── rules.py          # D20, checks, damage — dice never touch the LLM
│   ├── combat.py         # Turn combat resolution
│   ├── inventory.py      # Items + relic logic
│   ├── status.py         # Status effects registry
│   ├── world.py          # NPC + faction data loader
│   ├── chapter.py        # Chapter registry, POV switch logic
│   ├── crossrail.py      # Cross-rail event bus (Damon ↔ Elira world echoes)
│   └── scene.py          # Scene engine, encounter tables, scripted beats, travel
│
├── game/
│   ├── state.py          # Master game state
│   ├── loop.py           # Main game loop
│   ├── quest.py          # Quest tracking + append-only event log
│   └── save_load.py      # JSON save/load, checkpoint system
│
├── llm/
│   ├── client.py         # Anthropic SDK wrapper (streaming)
│   ├── prompts.py        # System prompt + turn payload builder
│   └── parser.py         # Intent parser, DC table, stat mapping
│
├── ui/
│   ├── display.py        # Rich terminal UI — POV themes, HP bars, panels
│   └── input.py          # Input handling
│
└── data/
    ├── npcs.json          # 11 NPCs — trust, hostility, knows, wants, agendas
    ├── factions.json      # 7 factions — attitudes, reactions, hidden agendas
    ├── locations.json     # All locations with atmosphere, connections, access
    └── saves/             # Player save files (gitignored)
```

---

## Architecture

```
Player input
    ↓
Intent parser (llm/parser.py)
    ↓
Rules engine (engine/rules.py) — rolls dice, resolves checks
    ↓
State update (game/state.py) — HP, flags, inventory, statuses
    ↓
Crossrail tick (engine/crossrail.py) — world echo events
    ↓
Quest tick (game/quest.py) — quest stage advancement
    ↓
Event log (game/quest.py) — append-only record
    ↓
LLM narration (llm/client.py) — receives structured result, returns prose + 4 suggestions
    ↓
Save (game/save_load.py)
```

The LLM never rolls dice or modifies state. It receives facts and makes them matter.

---

## Current Story Position

**Damon** — Claimant verified at Saint Vaelor. HP 6/12. Moving west with Kest and Carrow.  
Next: Reach Sablewake. Acquire a courtesy mark. Enter the Gilded Vice. Reach the Western Node.

**Elira** — In Sablewake (rail inactive until switched). Has the ring and the token.  
Next: Understand what the ring opens. Stay ahead of Saervan.

**Convergence gate** — Both rails in Sablewake + Western Node located = rails can cross.

---

## Phase Roadmap

| Phase | Status | What |
|---|---|---|
| 1 | ✅ | Engine, state, save/load, terminal UI |
| 2 | ✅ | LLM wiring — narration, intent parser, streaming |
| 3 | ✅ | Rich UI, NPC/faction data layer, world engine |
| 4 | ✅ | Elira rail, chapter engine, crossrail event bus |
| 5 | ✅ | Scene engine, encounter tables, quest system, event log |
| 6 | 🔲 | Tauri desktop wrapper, persistent UI, sound design |
| 7 | 🔲 | Full campaign content pass, act 2 scripting |
