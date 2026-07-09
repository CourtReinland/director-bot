"""MentalProcesses: phase state machine for the director's behavioral modes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from director_bot.contracts.schemas import PHASES, ProjectPhase


# Allowed transitions — director may not skip straight to previs from intake.
def default_transitions() -> dict[str, set[str]]:
    return {
        ProjectPhase.INTAKE.value: {
            ProjectPhase.BREAK_STORY.value,
            ProjectPhase.SERIES_ARC.value,
        },
        ProjectPhase.BREAK_STORY.value: {
            ProjectPhase.WRITE.value,
            ProjectPhase.INTAKE.value,
            ProjectPhase.SERIES_ARC.value,
        },
        ProjectPhase.WRITE.value: {
            ProjectPhase.SHOTLIST.value,
            ProjectPhase.BREAK_STORY.value,
        },
        ProjectPhase.SHOTLIST.value: {
            ProjectPhase.PREVIS.value,
            ProjectPhase.WRITE.value,
        },
        ProjectPhase.PREVIS.value: {
            ProjectPhase.DAILIES.value,
            ProjectPhase.SHOTLIST.value,
        },
        ProjectPhase.DAILIES.value: {
            ProjectPhase.CUT.value,
            ProjectPhase.PREVIS.value,
            ProjectPhase.SHOTLIST.value,
        },
        ProjectPhase.CUT.value: {
            ProjectPhase.DAILIES.value,
            ProjectPhase.SERIES_ARC.value,
            ProjectPhase.INTAKE.value,  # next episode / next short
        },
        ProjectPhase.SERIES_ARC.value: {
            ProjectPhase.BREAK_STORY.value,
            ProjectPhase.INTAKE.value,
        },
    }


PROCESS_BLURBS: dict[str, str] = {
    ProjectPhase.INTAKE.value: (
        "Receive the brief. Clarify genre, theme, logline, constraints. "
        "Refuse to invent coverage before the story spine is clear."
    ),
    ProjectPhase.BREAK_STORY.value: (
        "Break the story into scene cards. Protect structure beats. "
        "Argue for cuts that serve theme over decoration."
    ),
    ProjectPhase.WRITE.value: (
        "Pages and dialogue. Cast lock. Subtext over speechifying. "
        "Use LightWriter as the writing surface when available."
    ),
    ProjectPhase.SHOTLIST.value: (
        "Translate cards into shot decisions using canon digests. "
        "Justify every choice with evidence or deliberate divergence."
    ),
    ProjectPhase.PREVIS.value: (
        "Describe / generate previz. Continuity blocks. "
        "Script2Screen package readiness."
    ),
    ProjectPhase.DAILIES.value: (
        "Critique generated material against intention. "
        "Re-prompt or re-decide where agreement fails."
    ),
    ProjectPhase.CUT.value: (
        "Pace, trim, emotional rhythm. Prefer cut on emotion, not coverage."
    ),
    ProjectPhase.SERIES_ARC.value: (
        "Season / web-series spine. Recurring motifs, character arcs across episodes."
    ),
}


@dataclass
class MentalProcess:
    name: str
    blurb: str

    @classmethod
    def for_phase(cls, phase: str | ProjectPhase) -> MentalProcess:
        name = phase.value if isinstance(phase, ProjectPhase) else str(phase)
        if name not in PHASES:
            raise ValueError(f"unknown phase: {name}")
        return cls(name=name, blurb=PROCESS_BLURBS[name])


class ProcessMachine:
    """Finite state machine over ProjectPhase."""

    def __init__(
        self,
        phase: str | ProjectPhase = ProjectPhase.INTAKE,
        transitions: Optional[dict[str, set[str]]] = None,
    ) -> None:
        name = phase.value if isinstance(phase, ProjectPhase) else str(phase)
        if name not in PHASES:
            raise ValueError(f"unknown phase: {name}")
        self.phase = name
        self.transitions = transitions or default_transitions()

    @property
    def process(self) -> MentalProcess:
        return MentalProcess.for_phase(self.phase)

    def can_transition(self, target: str | ProjectPhase) -> bool:
        t = target.value if isinstance(target, ProjectPhase) else str(target)
        return t in self.transitions.get(self.phase, set())

    def transition(self, target: str | ProjectPhase) -> str:
        t = target.value if isinstance(target, ProjectPhase) else str(target)
        if t not in PHASES:
            raise ValueError(f"unknown phase: {t}")
        if not self.can_transition(t):
            allowed = sorted(self.transitions.get(self.phase, set()))
            raise ValueError(
                f"illegal transition {self.phase!r} → {t!r}; allowed: {allowed}"
            )
        self.phase = t
        return self.phase

    def allowed(self) -> list[str]:
        return sorted(self.transitions.get(self.phase, set()))
