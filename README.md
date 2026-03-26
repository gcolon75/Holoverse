# Vaelrune

A chapter-based, consequence-heavy text RPG. Coded systems handle state and dice. The LLM handles tone, narration, and dialogue.

**Rule of Ash: No rewinds. No retcons. No undoing consequences.**

---

## Setup

```bash
# Clone
git clone https://github.com/gcolon75/Holoverse.git
cd Holoverse

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

---

## Phase 1 — Engine (current)

Terminal-only. No LLM yet. Verifies:
- D20 rolls, skill checks, advantage/disadvantage
- Combat turn resolution
- Status effect application
- Inventory and relic item logic
- State serialization / save-load

**Commands:**
| Command | Description |
|---|---|
| `status` | Character sheet |
| `inv` | Inventory |
| `party` | Party overview |
| `flags` | Quest flags |
| `inspect <item_id>` | Inspect item |
| `roll <stat> <dc>` | Skill check |
| `roll <stat> <dc> adv` | With advantage |
| `fight` | Test combat |
| `save` | Checkpoint |
| `quit` | Save and exit |

---

## Project Structure

```
vaelrune/
├── main.py
├── engine/
│   ├── rules.py        # D20, checks, damage
│   ├── combat.py       # Turn combat
│   ├── inventory.py    # Items + relic logic
│   └── status.py       # Status effects
├── game/
│   ├── state.py        # Master game state
│   ├── loop.py         # Game loop
│   └── save_load.py    # JSON save/load
├── ui/
│   ├── display.py      # Rich terminal UI
│   └── input.py        # Input parsing
├── data/
│   └── saves/          # Save files
└── requirements.txt
```

---

## Phase Roadmap

- **Phase 1** ✅ Engine + state + save/load + terminal UI
- **Phase 2** LLM wiring (Anthropic SDK, narration, intent parsing)
- **Phase 3** Rich UI polish, chapter title cards, POV color themes
- **Phase 4** Elira rail + chapter switching + shared flag system
