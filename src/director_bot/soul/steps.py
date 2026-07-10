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

    def meet_prompt(self, topic: str) -> dict[str, str]:
        """Exact system/user messages that would be sent to the brain."""
        from director_bot.soul.trace import build_meet_prompt

        process = self.process.process
        return build_meet_prompt(
            system=self.soul.system_preamble(),
            process_name=process.name,
            process_blurb=process.blurb,
            memory_text=self.memory.format_for_prompt(),
            topic=topic,
        )

    def speak_about(self, topic: str) -> str:
        prompts = self.meet_prompt(topic)
        brain = self.brain
        if hasattr(brain, "with_context"):
            brain = brain.with_context(  # type: ignore[assignment]
                kind="meet",
                project_id=self.project_id,
                phase=self.process.phase,
            )
        reply = brain.complete(prompts["system"], prompts["user"])
        self.memory.append("speech", reply)
        self.persist_memory()
        return reply

    def _meet_view_base(self, topic: str, prompts: dict[str, str]) -> dict[str, Any]:
        from director_bot.soul.trace import _char_stats

        process = self.process.process
        return {
            "kind": "meet",
            "live": True,
            "brain": getattr(self.brain, "name", "unknown"),
            "project_id": self.project_id,
            "phase": self.process.phase,
            "system": prompts["system"],
            "user": prompts["user"],
            "stats": _char_stats(prompts["system"], prompts["user"]),
            "sections": {
                "soul_name": self.soul.name,
                "soul_core": self.soul.core,
                "soul_taste": self.soul.taste,
                "soul_process_notes": self.soul.process_notes,
                "process_name": process.name,
                "process_blurb": process.blurb,
                "working_memory": self.memory.to_list(),
                "working_memory_text": self.memory.format_for_prompt(),
                "topic": topic,
            },
        }

    def _context_brain(self) -> Any:
        brain = self.brain
        if hasattr(brain, "with_context"):
            return brain.with_context(  # type: ignore[return-value]
                kind="meet",
                project_id=self.project_id,
                phase=self.process.phase,
            )
        return brain

    def speak_about_traced(self, topic: str) -> dict[str, Any]:
        """Meet + return full model view (system/user/response) for training."""
        prompts = self.meet_prompt(topic)
        brain = self._context_brain()
        reply = brain.complete(prompts["system"], prompts["user"])
        self.memory.append("speech", reply)
        self.persist_memory()
        view = self._meet_view_base(topic, prompts)
        view["brain"] = getattr(brain, "name", "unknown")
        view["response"] = reply
        view["streamed"] = False
        return view

    def speak_about_stream(self, topic: str):
        """Yield SSE-friendly event dicts: meta → token* → done|error.

        Records the full response via TracingBrain.stream when available.
        """
        from director_bot.soul.brain import stream_text

        prompts = self.meet_prompt(topic)
        brain = self._context_brain()
        base = self._meet_view_base(topic, prompts)
        base["brain"] = getattr(brain, "name", "unknown")
        base["streamed"] = True
        base["response"] = ""
        yield {"event": "meta", "data": base}

        parts: list[str] = []
        try:
            for delta in stream_text(brain, prompts["system"], prompts["user"]):
                parts.append(delta)
                yield {"event": "token", "data": {"t": delta}}
            reply = "".join(parts)
            self.memory.append("speech", reply)
            self.persist_memory()
            done = dict(base)
            done["response"] = reply
            done["sections"] = {
                **base["sections"],
                "working_memory": self.memory.to_list(),
                "working_memory_text": self.memory.format_for_prompt(),
            }
            yield {"event": "done", "data": done}
        except Exception as exc:
            yield {
                "event": "error",
                "data": {
                    "message": str(exc),
                    "partial": "".join(parts),
                    "system": prompts["system"],
                    "user": prompts["user"],
                },
            }




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
