"""
game/quest.py
Quest tracking and persistent event log.

Quests are structured objective chains with stages.
The log is append-only — Rule of Ash applies here too.
Nothing gets removed. Everything that happened is recorded.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class QuestStatus(Enum):
    LOCKED      = "locked"       # prereqs not met
    ACTIVE      = "active"       # in progress
    COMPLETE    = "complete"     # finished successfully
    FAILED      = "failed"       # permanently failed
    SUSPENDED   = "suspended"    # paused — can resume


@dataclass
class QuestStage:
    id: str
    description: str
    completed: bool = False
    failed: bool = False
    completion_flag: Optional[str] = None   # flag set when this stage completes
    failure_flag: Optional[str] = None


@dataclass
class Quest:
    id: str
    title: str
    pov: str                                # "damon", "elira", or "shared"
    description: str
    status: QuestStatus = QuestStatus.LOCKED
    stages: list[QuestStage] = field(default_factory=list)
    prerequisite_flags: dict = field(default_factory=dict)
    completion_flags: dict = field(default_factory=dict)
    failure_flags: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)  # accumulated intel/clues

    def current_stage(self) -> Optional[QuestStage]:
        for stage in self.stages:
            if not stage.completed and not stage.failed:
                return stage
        return None

    def advance(self) -> Optional[QuestStage]:
        current = self.current_stage()
        if current:
            current.completed = True
        return self.current_stage()

    def is_done(self) -> bool:
        return self.status in (QuestStatus.COMPLETE, QuestStatus.FAILED)

    def add_note(self, note: str):
        self.notes.append(note)


# ---------------------------------------------------------------------------
# Quest registry — seeded from handoff + live state
# ---------------------------------------------------------------------------

def build_quest_registry() -> dict[str, Quest]:
    return {

        # --- DAMON MAIN QUEST ---

        "damon_main_succession": Quest(
            id="damon_main_succession",
            pov="damon",
            title="Repair the Broken Succession",
            description=(
                "Malrec split the proof. Saint Vaelor verified the claim. "
                "The Western Node beneath The Gilded Vice in Sablewake is the repair point. "
                "Reach it. Complete it. Before hostile factions lock it down."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="reach_sablewake",
                    description="Travel from Saint Vaelor to Sablewake.",
                    completion_flag="sablewake_reached",
                ),
                QuestStage(
                    id="acquire_courtesy_mark",
                    description="Obtain or fabricate a courtesy mark for the lower Vice.",
                    completion_flag="courtesy_mark_obtained",
                ),
                QuestStage(
                    id="infiltrate_gilded_vice",
                    description="Enter The Gilded Vice and reach the lower access.",
                    completion_flag="gilded_vice_infiltrated",
                ),
                QuestStage(
                    id="access_western_node",
                    description="Reach the Western Node chamber. Complete the succession repair.",
                    completion_flag="western_node_accessed",
                ),
            ],
            prerequisite_flags={"claimant_verified_at_saint_vaelor": True},
            completion_flags={"western_node_accessed": True},
            notes=[
                "The tablet explicitly states Damon must never reach the Node — Malrec's proxy will act.",
                "Claimant override exists but is loud. Every faction in Sablewake will know.",
                "Courtesy mark is cleaner. Elira's token is genuine — if she can be found.",
            ],
        ),

        "damon_threat_malrec_proxy": Quest(
            id="damon_threat_malrec_proxy",
            pov="damon",
            title="Identify Malrec's Proxy",
            description=(
                "Malrec is sealed and buried. But the bronze tablet confirms he has a living agent "
                "in Sablewake operating through the Black Tide network. That agent will move to "
                "block the Node before Damon can reach it."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="find_proxy_trace",
                    description="Find evidence of the proxy's presence in Sablewake.",
                    completion_flag="malrec_proxy_trace_found",
                ),
                QuestStage(
                    id="identify_proxy",
                    description="Identify who the proxy is.",
                    completion_flag="malrec_proxy_identified",
                ),
                QuestStage(
                    id="neutralize_proxy",
                    description="Neutralize the proxy before they can lock down the Node.",
                    completion_flag="malrec_proxy_neutralized",
                ),
            ],
            prerequisite_flags={"malrec_betrayal_confirmed": True},
            notes=[
                "The proxy has access to the Black Tide upper layer.",
                "Saervan reports to someone. That someone may be the proxy.",
            ],
        ),

        "damon_party_carrow": Quest(
            id="damon_party_carrow",
            pov="damon",
            title="Carrow's Hidden Knowledge",
            description=(
                "Carrow knows something about the Western Node access ritual he has not shared. "
                "Trust is damaged. Whatever he's withholding may be essential."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="restore_carrow_trust",
                    description="Restore enough trust for Carrow to speak plainly.",
                    completion_flag="carrow_trust_restored",
                ),
                QuestStage(
                    id="learn_carrow_secret",
                    description="Learn what Carrow has been withholding about the Node.",
                    completion_flag="carrow_secret_revealed",
                ),
            ],
            notes=[
                "Carrow is injured. Treat the wound. It may open the conversation.",
                "The scripted beat on the road will surface if trust is not restored in time.",
            ],
        ),

        "damon_kest_loyalty": Quest(
            id="damon_kest_loyalty",
            pov="damon",
            title="Kest Wants the Truth",
            description=(
                "Kest is suspicious and blunt. He has followed this far on operational trust. "
                "He wants a real answer before walking into Sablewake."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="answer_kest",
                    description="Give Kest an honest account of what you are and what you're doing.",
                    completion_flag="kest_confrontation_done",
                ),
            ],
            notes=[
                "How Damon answers affects Kest's trust for the rest of the campaign.",
                "This beats as a scripted scene on the road to Sablewake.",
            ],
        ),

        # --- ELIRA MAIN QUEST ---

        "elira_main_ring": Quest(
            id="elira_main_ring",
            pov="elira",
            title="What the Ring Actually Opens",
            description=(
                "The dark-stone ring Elira stole from Saervan is not just valuable. "
                "It is a custody key to the lower Vice. Saervan wants it back desperately. "
                "Understanding what it opens — and deciding what to do with that power — "
                "is Elira's central arc."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="reach_sablewake",
                    description="Reach Sablewake ahead of Saervan's people.",
                    completion_flag="elira_in_sablewake",
                ),
                QuestStage(
                    id="understand_ring",
                    description="Determine what the ring actually unlocks.",
                    completion_flag="elira_understands_ring_purpose",
                ),
                QuestStage(
                    id="decide_ring_fate",
                    description="Use it, sell it, destroy it, or give it to someone who needs it.",
                    completion_flag="elira_ring_decision_made",
                ),
            ],
            prerequisite_flags={"elira_has_saervan_ring": True},
            notes=[
                "The ring is Saervan's personal custody key. Without it he cannot open the Node from his side.",
                "Elira can use it herself — but that puts her inside Black Tide custody law.",
                "Damon needs access to the lower Vice. The ring is a path.",
            ],
        ),

        "elira_threat_saervan": Quest(
            id="elira_threat_saervan",
            pov="elira",
            title="Stay Ahead of Saervan",
            description=(
                "Lord Saervan is patient, urbane, and hunting her. "
                "He wants the ring. He is not above making the problem disappear quietly."
            ),
            status=QuestStatus.ACTIVE,
            stages=[
                QuestStage(
                    id="evade_initial_pursuit",
                    description="Reach Sablewake without being caught.",
                    completion_flag="elira_in_sablewake",
                ),
                QuestStage(
                    id="navigate_sablewake_heat",
                    description="Move through Sablewake without Saervan's people catching up.",
                    completion_flag="elira_sablewake_heat_managed",
                ),
            ],
            notes=[
                "Saervan's outriders are faster than Elira on open road.",
                "In the city, social cover matters more than speed.",
                "The courtesy token is her best protection — but it also puts her in the system.",
            ],
        ),

        # --- SHARED / CONVERGENCE ---

        "shared_convergence": Quest(
            id="shared_convergence",
            pov="shared",
            title="The Convergence",
            description=(
                "Damon needs the Node. Elira has the ring that opens it from the inside. "
                "Neither knows the other is in Sablewake yet. "
                "When the rails cross, this quest activates."
            ),
            status=QuestStatus.LOCKED,
            stages=[
                QuestStage(
                    id="rails_cross",
                    description="Damon and Elira become aware of each other in Sablewake.",
                    completion_flag="rails_converged_sablewake",
                ),
                QuestStage(
                    id="negotiation",
                    description="Negotiate terms. Alliance, tension, or conflict.",
                    completion_flag="convergence_terms_set",
                ),
                QuestStage(
                    id="joint_approach",
                    description="Enter the lower Vice together — or separately with shared stakes.",
                    completion_flag="joint_approach_executed",
                ),
            ],
            prerequisite_flags={
                "sablewake_reached": True,
                "elira_in_sablewake": True,
            },
            notes=[
                "Damon let Elira go on the cliffs. She remembers.",
                "Elira has the ring. Damon has the claimant mark. Neither path is clean without the other.",
            ],
        ),
    }


# ---------------------------------------------------------------------------
# Quest manager
# ---------------------------------------------------------------------------

class QuestManager:
    def __init__(self):
        self.quests: dict[str, Quest] = build_quest_registry()

    def get(self, quest_id: str) -> Optional[Quest]:
        return self.quests.get(quest_id)

    def active_quests(self, pov: str) -> list[Quest]:
        return [
            q for q in self.quests.values()
            if q.status == QuestStatus.ACTIVE and q.pov in (pov, "shared")
        ]

    def tick(self, game_flags) -> list[Quest]:
        """
        Check all quests against current flags.
        Unlock locked quests whose prereqs are met.
        Complete active quests whose completion flags are set.
        Returns list of quests that changed state this tick.
        """
        changed = []

        for quest in self.quests.values():
            if quest.status == QuestStatus.LOCKED:
                prereqs_met = all(
                    game_flags.get(k) == v
                    for k, v in quest.prerequisite_flags.items()
                )
                if prereqs_met:
                    quest.status = QuestStatus.ACTIVE
                    changed.append(quest)

            elif quest.status == QuestStatus.ACTIVE:
                # Advance stages
                for stage in quest.stages:
                    if not stage.completed and stage.completion_flag:
                        if game_flags.get(stage.completion_flag):
                            stage.completed = True

                # Check full completion
                if quest.completion_flags:
                    all_done = all(
                        game_flags.get(k) == v
                        for k, v in quest.completion_flags.items()
                    )
                    if all_done:
                        quest.status = QuestStatus.COMPLETE
                        changed.append(quest)

                # Check failure
                if quest.failure_flags:
                    failed = all(
                        game_flags.get(k) == v
                        for k, v in quest.failure_flags.items()
                    )
                    if failed:
                        quest.status = QuestStatus.FAILED
                        changed.append(quest)

        return changed

    def to_dict(self) -> dict:
        return {
            qid: {
                "id": q.id,
                "title": q.title,
                "pov": q.pov,
                "status": q.status.value,
                "stages": [
                    {"id": s.id, "completed": s.completed, "failed": s.failed}
                    for s in q.stages
                ],
                "notes": q.notes,
            }
            for qid, q in self.quests.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestManager":
        manager = cls()
        for qid, qd in data.items():
            if qid in manager.quests:
                q = manager.quests[qid]
                q.status = QuestStatus(qd["status"])
                q.notes = qd.get("notes", q.notes)
                for i, sd in enumerate(qd.get("stages", [])):
                    if i < len(q.stages):
                        q.stages[i].completed = sd["completed"]
                        q.stages[i].failed = sd["failed"]
        return manager


# ---------------------------------------------------------------------------
# Event log — append-only, Rule of Ash
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    turn: int
    pov: str
    location: str
    event_type: str     # "action", "encounter", "beat", "quest", "crossrail", "combat"
    summary: str
    mechanical: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventLog:
    def __init__(self):
        self.entries: list[LogEntry] = []

    def record(
        self,
        turn: int,
        pov: str,
        location: str,
        event_type: str,
        summary: str,
        mechanical: dict = None,
    ):
        entry = LogEntry(
            turn=turn,
            pov=pov,
            location=location,
            event_type=event_type,
            summary=summary,
            mechanical=mechanical or {},
        )
        self.entries.append(entry)

    def recent(self, n: int = 10) -> list[LogEntry]:
        return self.entries[-n:]

    def by_pov(self, pov: str) -> list[LogEntry]:
        return [e for e in self.entries if e.pov == pov]

    def by_type(self, event_type: str) -> list[LogEntry]:
        return [e for e in self.entries if e.event_type == event_type]

    def to_list(self) -> list[dict]:
        return [
            {
                "turn": e.turn,
                "pov": e.pov,
                "location": e.location,
                "type": e.event_type,
                "summary": e.summary,
                "mechanical": e.mechanical,
                "timestamp": e.timestamp,
            }
            for e in self.entries
        ]

    @classmethod
    def from_list(cls, data: list[dict]) -> "EventLog":
        log = cls()
        for d in data:
            log.entries.append(LogEntry(
                turn=d["turn"],
                pov=d["pov"],
                location=d["location"],
                event_type=d["type"],
                summary=d["summary"],
                mechanical=d.get("mechanical", {}),
                timestamp=d.get("timestamp", ""),
            ))
        return log
