"""
game/loop.py
Main game loop — Phase 2: LLM wired in.
Engine resolves mechanics. LLM narrates results and suggests actions.
"""

from game.state import GameState, build_initial_state
from game.save_load import save, load, save_exists, checkpoint
from engine.rules import skill_check
from engine.combat import CombatEngine, Combatant
from engine.world import get_world
from engine.chapter import get_chapter_engine, SwitchTrigger
from engine.crossrail import get_crossrail
from llm.client import narrate_streaming, is_configured
from llm.prompts import SYSTEM_PROMPT, build_turn_payload, build_scene_intro_payload
from llm.parser import parse_intent, get_default_check
from ui.display import Display, console
from ui.input import get_input, parse_command


class GameLoop:
    def __init__(self):
        self.state: GameState = None
        self.display = Display()
        self.running = False
        self.llm_enabled = False
        self.last_suggestions: list[str] = []

    def start(self):
        self.display.title_card()

        if is_configured():
            self.llm_enabled = True
            self.display.print_info("LLM narration: ENABLED")
        else:
            self.display.print_info("LLM narration: DISABLED (set ANTHROPIC_API_KEY to enable)")

        if save_exists():
            choice = get_input("Save file found. [L]oad or [N]ew game? ").strip().lower()
            if choice == "l":
                self.state = load()
                self.display.print_info("Save loaded.")
            else:
                self.state = build_initial_state()
                save(self.state)
                self.display.print_info("New game started.")
        else:
            self.state = build_initial_state()
            save(self.state)
            self.display.print_info("New game started.")

        if self.llm_enabled:
            self._stream_scene_intro()

        self.running = True
        self.loop()

    def loop(self):
        while self.running:
            self.display.render_scene(self.state)
            self._show_suggestions()

            raw_input = get_input("\n> ")
            if not raw_input:
                continue

            # Expand numbered shortcut
            if raw_input.strip() in ("1", "2", "3", "4"):
                idx = int(raw_input.strip()) - 1
                if 0 <= idx < len(self.last_suggestions):
                    raw_input = self.last_suggestions[idx]
                    self.display.print_info(f"-> {raw_input}")

            cmd, args = parse_command(raw_input)

            META = {"quit", "exit", "save", "help", "status", "inv",
                    "inventory", "party", "flags", "fight", "inspect",
                    "npc", "faction", "roll", "check",
                    "pov", "switch", "chapters", "crossrail"}
            if cmd in META:
                self.handle_meta_command(cmd, args)
            else:
                self.handle_action(raw_input)

    # -------------------------------------------------------------------------
    # Core turn
    # -------------------------------------------------------------------------

    def handle_action(self, raw_input: str):
        state = self.state
        active = state.get_active_character()
        if not active:
            self.display.print_error("No active character.")
            return

        intent = parse_intent(raw_input)

        if intent.category == "unknown" and not self.llm_enabled:
            self.display.print_error(
                f"Unknown action: '{raw_input}'. "
                "Try: move, examine, talk, attack, hide, investigate, invoke, use, rest"
            )
            return

        # Resolve check
        stat, dc = get_default_check(intent)
        dc = self._adjust_dc(intent, dc)
        modifier = active.stat_modifier(stat)
        result = skill_check(modifier, dc)

        roll_result_str = str(result)
        outcome_summary = (
            f"{active.name} attempted to {intent.verb} ({intent.category}). "
            f"{stat.upper()} check vs DC {dc}. "
            f"{result.outcome.value.upper().replace('_', ' ')}."
        )

        self.display.render_roll(result, stat, active.name)
        self._apply_consequences(intent, result, active)

        state.advance_turn()

        # Tick crossrail — check if any flags triggered world events
        crossrail = get_crossrail()
        fired = crossrail.check_and_fire(state.flags)
        if fired:
            for event in fired:
                state.crossrail_fired.append(event.id)
                self.display.print_info(f"[World] {event.description}")

        # Check pending POV switch
        if state.has_pending_switch():
            rail = state.rails.get(state.active_pov)
            if rail and rail.pending_switch_to:
                self._execute_pov_switch(rail.pending_switch_to, rail.last_switch_trigger)

        save(state)

        if self.llm_enabled:
            payload = build_turn_payload(
                state=state,
                player_input=raw_input,
                intent=intent.to_dict(),
                roll_result_str=roll_result_str,
                outcome_summary=outcome_summary,
            )
            self._stream_narration(payload)
        else:
            console.print(f"\n[dim]{outcome_summary}[/]\n")

    def _adjust_dc(self, intent, base_dc: int) -> int:
        state = self.state
        if intent.category == "invoke":
            active = state.get_active_character()
            if active and not active.inventory.has("succession_signet"):
                base_dc += 4
        if intent.category == "social":
            carrow = state.get_character("carrow")
            if carrow and carrow.flags.get("trust_level") == "trust_damaged":
                base_dc += 2
        return base_dc

    def _apply_consequences(self, intent, result, character):
        from engine.rules import Outcome
        if intent.category == "hide" and not result.passed():
            character.flags["last_hide_failed"] = True
        if intent.category == "invoke" and result.passed():
            character.flags["last_invocation_successful"] = True
            self.display.print_info("Authority acknowledged.")
        if result.outcome == Outcome.CRITICAL_FAILURE:
            character.flags["last_action_critical_fail"] = True

    # -------------------------------------------------------------------------
    # LLM streaming
    # -------------------------------------------------------------------------

    def _stream_narration(self, payload: str):
        console.print()
        full_text = ""
        try:
            for chunk in narrate_streaming(SYSTEM_PROMPT, payload):
                console.print(chunk, end="", highlight=False)
                full_text += chunk
            console.print("\n")
        except Exception as e:
            self.display.print_error(f"LLM error: {e}")
            return
        self._extract_suggestions(full_text)

    def _stream_scene_intro(self):
        payload = build_scene_intro_payload(self.state)
        console.print()
        full_text = ""
        try:
            for chunk in narrate_streaming(SYSTEM_PROMPT, payload):
                console.print(chunk, end="", highlight=False)
                full_text += chunk
            console.print("\n")
        except Exception as e:
            self.display.print_error(f"LLM scene intro error: {e}")
            return
        self._extract_suggestions(full_text)

    def _extract_suggestions(self, text: str):
        import re
        matches = re.findall(r"^\s*[1-4][.)]\s*(.+)", text, re.MULTILINE)
        self.last_suggestions = [m.strip() for m in matches] if matches else []

    def _show_suggestions(self):
        if self.last_suggestions:
            console.print("[dim]--- Suggested Actions ---[/]")
            for i, s in enumerate(self.last_suggestions, 1):
                console.print(f"  [dim cyan]{i}.[/] {s}")
            console.print()

    # -------------------------------------------------------------------------
    # Meta commands
    # -------------------------------------------------------------------------

    def handle_meta_command(self, cmd: str, args: list[str]):
        state = self.state
        active = state.get_active_character()

        if cmd in ("quit", "exit"):
            save(state)
            self.display.print_info("Game saved. Goodbye.")
            self.running = False
        elif cmd == "save":
            checkpoint(state)
            self.display.print_info("Checkpoint saved.")
        elif cmd == "help":
            self.display.print_help()
        elif cmd == "status":
            self.display.render_character_sheet(active)
        elif cmd in ("inventory", "inv"):
            self.display.render_inventory(active)
        elif cmd == "party":
            for cid in ["damon", "kest", "carrow"]:
                char = state.get_character(cid)
                if char:
                    self.display.render_character_brief(char)
        elif cmd == "flags":
            self.display.render_flags(state.flags)
        elif cmd == "fight":
            self._run_test_combat()
        elif cmd == "inspect":
            if args:
                item_id = "_".join(args)
                item = active.inventory.get(item_id)
                if item:
                    self.display.render_item(item)
                else:
                    self.display.print_error(f"No item '{item_id}' in inventory.")
            else:
                self.display.print_error("Usage: inspect <item_id>")
        elif cmd == "npc":
            if args:
                npc_id = "_".join(args)
                world = get_world()
                npc = world.get_npc(npc_id)
                if npc:
                    self.display.render_npc_panel(npc)
                else:
                    self.display.print_error(f"No NPC '{npc_id}'.")
            else:
                self.display.print_error("Usage: npc <npc_id>")
        elif cmd == "faction":
            if args:
                faction_id = "_".join(args)
                world = get_world()
                faction = world.get_faction(faction_id)
                if faction:
                    from rich.panel import Panel
                    pov = state.active_pov
                    summary = world.build_faction_summary(faction_id, pov)
                    console.print(Panel(
                        f"[bold]{faction["name"]}[/]
"
                        f"[dim]{faction.get("description","")}[/]

"
                        f"{summary}

"
                        f"[dim]Hidden agenda:[/] {faction.get("hidden_agenda","unknown")}",
                        border_style="dim yellow", padding=(0,2),
                    ))
                else:
                    self.display.print_error(f"No faction '{faction_id}'.")
            else:
                self.display.print_error("Usage: faction <faction_id>")
        elif cmd in ("roll", "check"):
            self._handle_roll(args, active)
        elif cmd == "pov":
            self._handle_pov_command(args)
        elif cmd == "switch":
            self._handle_switch_command(args)
        elif cmd == "chapters":
            self._handle_chapters_command()
        elif cmd == "crossrail":
            self._handle_crossrail_command()

    def _handle_roll(self, args, character):
        if len(args) < 2:
            self.display.print_error("Usage: roll <stat> <dc> [adv|dis]")
            return
        stat = args[0].lower()
        try:
            dc = int(args[1])
        except ValueError:
            self.display.print_error("DC must be a number.")
            return
        advantage = len(args) > 2 and args[2].lower() == "adv"
        disadvantage = len(args) > 2 and args[2].lower() == "dis"
        active = self.state.get_active_character()
        modifier = active.stat_modifier(stat)
        result = skill_check(modifier, dc, advantage, disadvantage)
        self.display.render_roll(result, stat, active.name)
        self.state.advance_turn()
        save(self.state)

    def _execute_pov_switch(self, new_pov: str, trigger: str = "manual"):
        """Execute a POV switch with chapter card display."""
        state = self.state
        old_pov = state.active_pov
        state.switch_pov(new_pov, trigger)
        chapter_def = get_chapter_engine().get(state.chapter)
        title = chapter_def.title if chapter_def else state.chapter
        self.display.chapter_card(state.chapter, new_pov, title)
        self.display.print_info(f"POV switched: {old_pov.upper()} → {new_pov.upper()} [{trigger}]")
        if self.llm_enabled:
            self._stream_scene_intro()
        save(state)

    def _handle_pov_command(self, args: list[str]):
        """Manual POV switch — gated behind rail activation."""
        state = self.state
        if not args:
            console.print(f"Current POV: [bold]{state.active_pov.upper()}[/]")
            for pov, rail in state.rails.items():
                console.print(f"  {pov}: chapter={rail.current_chapter} turns={rail.turns_on_this_rail}")
            return
        target = args[0].lower()
        if target not in ("damon", "elira"):
            self.display.print_error("POV must be 'damon' or 'elira'.")
            return
        if target == state.active_pov:
            self.display.print_error(f"Already on {target}.")
            return
        if target == "elira" and not state.flags.get("elira_rail_active"):
            self.display.print_error(
                "Elira's rail is not yet active. "
                "Use 'switch elira' to activate it at the current story point."
            )
            return
        self._execute_pov_switch(target, "manual")

    def _handle_switch_command(self, args: list[str]):
        """Activate Elira's rail or force a strong-beat switch."""
        state = self.state
        if args and args[0].lower() == "elira":
            if state.flags.get("elira_rail_active"):
                self._execute_pov_switch("elira", "manual")
            else:
                state.flags.set("elira_rail_active", True)
                state.characters["elira"].flags["rail_active"] = True
                self.display.print_info("Elira's rail activated.")
                self._execute_pov_switch("elira", "forced")
        else:
            self.display.print_error("Usage: switch elira")

    def _handle_chapters_command(self):
        """Display chapter map."""
        engine = get_chapter_engine()
        from rich.table import Table
        from rich import box
        table = Table(title="Chapter Map", box=box.SIMPLE_HEAD)
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("POV")
        table.add_column("Title")
        table.add_column("Done")
        for cid, c in engine.registry.items():
            done_str = "[green]✓[/]" if c.completed else "[dim]·[/]"
            pov_color = "steel_blue" if c.pov == "damon" else "gold1"
            table.add_row(cid, f"[{pov_color}]{c.pov}[/]", c.title, done_str)
        console.print(table)

    def _handle_crossrail_command(self):
        """Show crossrail event status."""
        crossrail = get_crossrail()
        from rich.table import Table
        from rich import box
        table = Table(title="Cross-Rail Events", box=box.SIMPLE_HEAD)
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Src")
        table.add_column("→ Tgt")
        table.add_column("Effect", style="dim")
        table.add_column("Fired")
        for e in crossrail.events.values():
            fired_str = "[green]✓[/]" if e.fired else "[dim]·[/]"
            table.add_row(
                e.id[:30], e.source_pov, e.target_pov,
                e.effect_type.value, fired_str,
            )
        console.print(table)

    def _run_test_combat(self):
        damon = self.state.get_character("damon")
        engine = CombatEngine()
        engine.add_combatant(Combatant(
            id="damon", name="Damon Reaveborne",
            hp=damon.hp, max_hp=damon.max_hp, ac=damon.effective_ac(),
            attack_modifier=damon.stat_modifier("str") + 2,
            damage_dice="1d8", damage_bonus=damon.stat_modifier("str"),
            is_player=True,
        ))
        engine.add_combatant(Combatant(
            id="hollow_shade", name="Hollow Shade",
            hp=8, max_hp=8, ac=11, attack_modifier=1, damage_dice="1d6",
        ))
        engine.start(["damon", "hollow_shade"])
        self.display.print_info("\n--- TEST COMBAT ---\n")
        rounds = 0
        while not engine.is_over() and rounds < 20:
            for attacker_id in engine.turn_order:
                if engine.is_over():
                    break
                defenders = [c for c in engine.turn_order if c != attacker_id]
                if defenders:
                    r = engine.resolve_attack(attacker_id, defenders[0])
                    self.display.render_combat_round(r, engine.combatants)
            engine.advance_round()
            rounds += 1
        if engine.log.victor:
            self.display.print_info(f"\nVictor: {engine.combatants[engine.log.victor].name}")
        damon_c = engine.combatants.get("damon")
        if damon_c:
            damon.hp = damon_c.hp
            save(self.state)
            self.display.print_info(f"Damon HP: {damon.hp}/{damon.max_hp}")
