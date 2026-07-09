"""Frozen shared schemas: works, scene cards, shot moments, decisions.

Aligns with LightWriter scene cards and Scripty shot vocabulary so
interchange is lossless at the field level we care about.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #

class WorkTier(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    UNRANKED = "UNRANKED"


class ProjectPhase(str, Enum):
    """MentalProcess modes for the director soul."""
    INTAKE = "intake"
    BREAK_STORY = "break_story"
    WRITE = "write"
    SHOTLIST = "shotlist"
    PREVIS = "previs"
    DAILIES = "dailies"
    CUT = "cut"
    SERIES_ARC = "series_arc"


TIERS = tuple(t.value for t in WorkTier)
PHASES = tuple(p.value for p in ProjectPhase)

# Multi-criteria "players" for equilibrium scoring.
CRITERIA = (
    "genre_craft",
    "style_match",
    "continuity",
    "originality",
    "feasibility",
    "emotion",
)


# --------------------------------------------------------------------------- #
# Canon entities
# --------------------------------------------------------------------------- #

@dataclass
class Work:
    """A film, episode, or series entry in the S-tier canon."""
    id: Optional[int] = None
    slug: str = ""
    title: str = ""
    year: Optional[int] = None
    directors: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    medium: str = "film"           # film | tv | web | short
    tier: WorkTier = WorkTier.UNRANKED
    theme: str = ""
    logline: str = ""
    plot_summary: str = ""
    source: str = ""               # e.g. "scripty:project:3:pass:1"
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_row(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "year": self.year,
            "directors": list(self.directors),
            "genres": list(self.genres),
            "medium": self.medium,
            "tier": self.tier.value if isinstance(self.tier, WorkTier) else self.tier,
            "theme": self.theme,
            "logline": self.logline,
            "plot_summary": self.plot_summary,
            "source": self.source,
            "meta": dict(self.meta),
        }


@dataclass
class SceneCard:
    """LightWriter-compatible scene card — lingua franca for story structure."""
    id: Optional[int] = None
    work_id: Optional[int] = None
    idx: int = 0
    slugline: str = ""             # EXT. WOODED ROAD - NIGHT
    title: str = ""                # short card title
    what_happens: str = ""         # literal action
    relationship_delta: str = ""   # who people are / how bonds shift
    plot_function: str = ""        # how this advances the plot
    emotional_spine: str = ""
    characters: list[str] = field(default_factory=list)
    structural_beat: str = ""      # e.g. "Catalyst", "Midpoint"
    act: Optional[int] = None
    page_estimate: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def situation_blob(self) -> str:
        """Text used for retrieval / embedding proxies."""
        parts = [
            self.slugline, self.title, self.what_happens,
            self.relationship_delta, self.plot_function,
            self.emotional_spine, self.structural_beat,
            " ".join(self.characters), " ".join(self.tags),
        ]
        return " | ".join(p for p in parts if p)


@dataclass
class ShotMoment:
    """Scripty-shaped labeled shot + optional decision digest link."""
    id: Optional[int] = None
    work_id: Optional[int] = None
    scene_card_id: Optional[int] = None
    idx: int = 0
    start_s: float = 0.0
    end_s: float = 0.0
    scale: str = "MS"
    subject: str = ""
    angle: str = "EYE LEVEL"
    move: str = "STATIC"
    int_ext: str = "EXT."
    location: str = ""
    time_of_day: str = "DAY"
    action_text: str = ""
    characters: list[str] = field(default_factory=list)
    mood: str = ""
    dialogue: list[dict[str, str]] = field(default_factory=list)
    # e.g. [{"character": "MARA", "text": "...", "parenthetical": ""}]
    confidence: float = 0.5
    keyframes: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def label(self) -> str:
        subject = (self.subject or "UNKNOWN").upper()
        return f"{self.scale} {subject}"

    def situation_blob(self) -> str:
        dlg = " ".join(
            f"{d.get('character', '')}: {d.get('text', '')}" for d in self.dialogue
        )
        parts = [
            self.label(), self.location, self.time_of_day, self.action_text,
            self.mood, self.move, self.angle, " ".join(self.characters), dlg,
        ]
        return " | ".join(p for p in parts if p)


@dataclass
class DecisionDigest:
    """Historical director choice extracted from a canon moment."""
    id: Optional[int] = None
    work_id: Optional[int] = None
    scene_card_id: Optional[int] = None
    shot_moment_id: Optional[int] = None
    situation: str = ""            # free-text circumstance
    decision: str = ""             # what was chosen
    rationale: str = ""
    director: str = ""
    tags: list[str] = field(default_factory=list)
    phase: str = ""                # optional ProjectPhase value
    meta: dict[str, Any] = field(default_factory=dict)

    def situation_blob(self) -> str:
        return " | ".join(
            p for p in (self.situation, self.decision, self.rationale,
                        self.director, " ".join(self.tags), self.phase)
            if p
        )


# --------------------------------------------------------------------------- #
# Live project / decision engine
# --------------------------------------------------------------------------- #

@dataclass
class SituationContext:
    """What the director faces at a decision point."""
    phase: ProjectPhase = ProjectPhase.SHOTLIST
    project_slug: str = ""
    genre: str = ""
    logline: str = ""
    scene_card: Optional[SceneCard] = None
    summary: str = ""              # free-text situation
    constraints: list[str] = field(default_factory=list)
    style_refs: list[str] = field(default_factory=list)  # director names / works
    markers: dict[str, Any] = field(default_factory=dict)

    def blob(self) -> str:
        card_blob = self.scene_card.situation_blob() if self.scene_card else ""
        parts = [
            self.phase.value if isinstance(self.phase, ProjectPhase) else str(self.phase),
            self.genre, self.logline, self.summary, card_blob,
            " ".join(self.constraints), " ".join(self.style_refs),
        ]
        return " | ".join(p for p in parts if p)


@dataclass
class CriteriaScores:
    genre_craft: float = 0.0
    style_match: float = 0.0
    continuity: float = 0.0
    originality: float = 0.0
    feasibility: float = 0.0
    emotion: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {c: float(getattr(self, c)) for c in CRITERIA}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CriteriaScores:
        kwargs = {c: float(data.get(c, 0.0)) for c in CRITERIA}
        return cls(**kwargs)


@dataclass
class CandidateAction:
    """One proposed choice in a decision round."""
    id: str = ""
    action: str = ""
    style_source: str = ""         # "historical:Fincher" | "creative" | "hybrid"
    scores: CriteriaScores = field(default_factory=CriteriaScores)
    evidence_ids: list[int] = field(default_factory=list)  # DecisionDigest ids
    notes: str = ""


@dataclass
class DecisionRecord:
    """Append-only justified decision (merkle-linked)."""
    id: Optional[int] = None
    project_id: Optional[int] = None
    phase: str = ""
    situation: str = ""
    candidates: list[CandidateAction] = field(default_factory=list)
    chosen_id: str = ""
    chosen_action: str = ""
    equilibrium_method: str = "weighted_pareto"
    creativity_alpha: float = 0.25
    evidence_ids: list[int] = field(default_factory=list)
    scores: dict[str, Any] = field(default_factory=dict)
    parent_hash: str = ""
    content_hash: str = ""
    created_at: str = ""

    def payload_for_hash(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "situation": self.situation,
            "candidates": [
                {
                    "id": c.id,
                    "action": c.action,
                    "style_source": c.style_source,
                    "scores": c.scores.as_dict(),
                    "evidence_ids": list(c.evidence_ids),
                    "notes": c.notes,
                }
                for c in self.candidates
            ],
            "chosen_id": self.chosen_id,
            "chosen_action": self.chosen_action,
            "equilibrium_method": self.equilibrium_method,
            "creativity_alpha": self.creativity_alpha,
            "evidence_ids": list(self.evidence_ids),
            "scores": dict(self.scores),
            "parent_hash": self.parent_hash,
        }


@dataclass
class ProjectState:
    """Where the director is in the production process."""
    id: Optional[int] = None
    slug: str = ""
    title: str = ""
    phase: ProjectPhase = ProjectPhase.INTAKE
    genre: str = ""
    logline: str = ""
    markers: dict[str, Any] = field(default_factory=dict)
    working_memory: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def content_hash(payload: dict[str, Any], parent_hash: str = "") -> str:
    """SHA-256 of canonical JSON (sorted keys) chained to parent."""
    body = {"parent_hash": parent_hash, "payload": payload}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def situation_text(obj: Any) -> str:
    if hasattr(obj, "situation_blob"):
        return obj.situation_blob()
    if hasattr(obj, "blob"):
        return obj.blob()
    return str(obj)


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj
