"""Cognitive steps: read → retrieve → propose → equilibrate → commit → speak."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.contracts.schemas import (
    ProjectPhase,
    SceneCard,
    SituationContext,
)
from director_bot.decisions.engine import decide
from director_bot.soul.brain import TextBrain, get_brain
from director_bot.soul.loader import SoulBlueprint, load_soul
from director_bot.soul.memory import WorkingMemory
from director_bot.soul.processes import ProcessMachine


@dataclass
class DirectorMind:
    """The embodied director: soul + memory + phase machine + db handle."""
    db: CanonDB
    soul: SoulBlueprint
    memory: WorkingMemory = field(default_factory=WorkingMemory)
    process: ProcessMachine = field(default_factory=ProcessMachine)
    brain: TextBrain = field(default_factory=get_brain)
    project_id: Optional[int] = None

    @classmethod
    def create(
        cls,
        db: CanonDB,
        *,
        project_id: Optional[int] = None,
        phase: str | ProjectPhase = ProjectPhase.INTAKE,
        soul_dir: Optional[str] = None,
        brain: Optional[TextBrain] = None,
    ) -> DirectorMind:
        soul = load_soul(soul_dir)
        memory = WorkingMemory()
        phase_name = phase.value if isinstance(phase, ProjectPhase) else str(phase)
        if project_id is not None:
            proj = db.get_project(project_id)
            if proj:
                memory = WorkingMemory.from_list(proj.get("working_memory"))
                phase_name = str(proj.get("phase") or phase_name)
        return cls(
            db=db,
            soul=soul,
            memory=memory,
            process=ProcessMachine(phase_name),
            brain=brain or get_brain(),
            project_id=project_id,
        )

    def persist_memory(self) -> None:
        if self.project_id is None:
            return
        self.db.update_project(
            self.project_id,
            working_memory=self.memory.to_list(),
            phase=self.process.phase,
        )

    def set_phase(self, target: str | ProjectPhase) -> str:
        new = self.process.transition(target)
        self.memory.append("note", f"Phase → {new}", meta={"phase": new})
        self.persist_memory()
        return new

    def perceive(self, text: str) -> None:
        self.memory.append("perception", text)

    def speak_about(self, topic: str) -> str:
        system = self.soul.system_preamble()
        process = self.process.process
        user = (
            f"Current mental process: {process.name}\n"
            f"Process guidance: {process.blurb}\n\n"
            f"Working memory:\n{self.memory.format_for_prompt()}\n\n"
            f"Human / situation:\n{topic}\n\n"
            "Respond in character as the director. Be decisive. "
            "Cite craft principles. Do not skip process."
        )
        reply = self.brain.complete(system, user)
        self.memory.append("speech", reply)
        self.persist_memory()
        return reply


def run_cognitive_cycle(
    mind: DirectorMind,
    *,
    summary: str,
    genre: str = "",
    logline: str = "",
    scene_card: Optional[SceneCard] = None,
    style_refs: Optional[list[str]] = None,
    constraints: Optional[list[str]] = None,
    creativity_alpha: Optional[float] = None,
    commit: bool = True,
) -> dict[str, Any]:
    """One full cognitive cycle ending in a ledger decision + speech note."""
    mind.perceive(summary)
    situation = SituationContext(
        phase=ProjectPhase(mind.process.phase),
        project_slug="",
        genre=genre,
        logline=logline,
        scene_card=scene_card,
        summary=summary,
        constraints=list(constraints or []),
        style_refs=list(style_refs or []),
    )
    if mind.project_id is not None:
        proj = mind.db.get_project(mind.project_id)
        if proj:
            situation.project_slug = str(proj.get("slug") or "")
            situation.genre = situation.genre or str(proj.get("genre") or "")
            situation.logline = situation.logline or str(proj.get("logline") or "")

    result = decide(
        mind.db,
        situation,
        project_id=mind.project_id,
        creativity_alpha=creativity_alpha,
        commit=commit,
    )
    chosen = result["chosen"]
    mind.memory.append(
        "decision",
        f"Chose [{chosen.id}]: {chosen.action}",
        meta={
            "style_source": chosen.style_source,
            "hash": getattr(result.get("decision"), "content_hash", None),
        },
    )
    mind.persist_memory()
    result["memory_snapshot"] = mind.memory.recent(5)
    result["phase"] = mind.process.phase
    return result
