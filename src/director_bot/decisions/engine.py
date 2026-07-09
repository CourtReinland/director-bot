"""End-to-end decide(): retrieve canon → propose → equilibrate → commit."""
from __future__ import annotations

from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.canon.query import lookup_digests, lookup_moments
from director_bot.config import DEFAULT_CRITERIA_WEIGHTS, PHASE_CREATIVITY
from director_bot.contracts.schemas import (
    CandidateAction,
    CriteriaScores,
    DecisionRecord,
    ProjectPhase,
    SituationContext,
)
from director_bot.decisions.equilibrium import (
    blend_creativity,
    pick_equilibrium,
    score_candidate,
)
from director_bot.decisions.ledger import commit_decision


def _phase_value(phase: ProjectPhase | str) -> str:
    return phase.value if isinstance(phase, ProjectPhase) else str(phase)


def _hist_scores(rank: int, base: float = 0.72) -> CriteriaScores:
    """Deterministic scores from retrieval rank (offline-stable)."""
    decay = max(0.0, 0.12 * rank)
    g = min(1.0, base - decay + 0.08)
    return CriteriaScores(
        genre_craft=min(1.0, g + 0.05),
        style_match=min(1.0, g),
        continuity=min(1.0, 0.7 + 0.05 * (3 - min(rank, 3))),
        originality=max(0.2, 0.45 - 0.05 * rank),
        feasibility=0.85,
        emotion=min(1.0, g + 0.02),
    )


def _creative_scores(seed: str) -> CriteriaScores:
    # Light deterministic jitter from seed length/chars — offline-stable.
    n = sum(ord(c) for c in seed[:32]) if seed else 0
    frac = (n % 100) / 100.0
    return CriteriaScores(
        genre_craft=0.45 + 0.2 * frac,
        style_match=0.35 + 0.15 * frac,
        continuity=0.55,
        originality=0.75 + 0.2 * (1 - frac),
        feasibility=0.65,
        emotion=0.6 + 0.25 * frac,
    )


def propose_candidates(
    db: CanonDB,
    situation: SituationContext,
    *,
    k: int = 5,
) -> list[CandidateAction]:
    """Build historical + creative candidates from canon retrieval."""
    query = situation.blob()
    genre = situation.genre or None
    digests = lookup_digests(db, query, k=k)
    moments = lookup_moments(db, query, k=max(2, k // 2), genre=genre, tier="S")

    candidates: list[CandidateAction] = []
    for i, dig in enumerate(digests):
        director = dig.get("director") or "unknown"
        action = str(dig.get("decision") or "").strip()
        if not action:
            continue
        candidates.append(CandidateAction(
            id=f"hist-digest-{dig.get('id', i)}",
            action=action,
            style_source=f"historical:{director}",
            scores=_hist_scores(i),
            evidence_ids=[int(dig["id"])] if dig.get("id") is not None else [],
            notes=str(dig.get("rationale") or ""),
        ))

    for i, mom in enumerate(moments):
        work = mom.get("work") or {}
        directors = work.get("directors") or []
        director = directors[0] if directors else "canon"
        label = f"{mom.get('scale', 'MS')} {mom.get('subject', '')}".strip()
        action = (
            f"Cover as {label}: {mom.get('action_text') or mom.get('mood') or label}"
        )
        candidates.append(CandidateAction(
            id=f"hist-moment-{mom.get('id', i)}",
            action=action,
            style_source=f"historical:{director}",
            scores=_hist_scores(i + 1, base=0.68),
            evidence_ids=[],
            notes=f"from work {work.get('title', '')}",
        ))

    creative = CandidateAction(
        id="creative-0",
        action=(
            f"Invent a fresh coverage for: {situation.summary or query[:160]}. "
            "Break from retrieved patterns while protecting continuity and emotion."
        ),
        style_source="creative",
        scores=_creative_scores(query),
        evidence_ids=[],
        notes="generative divergence candidate",
    )
    candidates.append(creative)

    # Deduplicate by action text
    seen: set[str] = set()
    unique: list[CandidateAction] = []
    for c in candidates:
        key = c.action.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


def decide(
    db: CanonDB,
    situation: SituationContext,
    *,
    project_id: Optional[int] = None,
    creativity_alpha: Optional[float] = None,
    weights: Optional[dict[str, float]] = None,
    commit: bool = True,
    k: int = 5,
) -> dict[str, Any]:
    """Full decision pass. Returns candidates, chosen, optional ledger record."""
    phase = _phase_value(situation.phase)
    alpha = (
        creativity_alpha
        if creativity_alpha is not None
        else PHASE_CREATIVITY.get(phase, 0.3)
    )
    w = weights or DEFAULT_CRITERIA_WEIGHTS

    raw = propose_candidates(db, situation, k=k)
    if len(raw) < 1:
        # Always have at least a creative fallback.
        raw = [CandidateAction(
            id="fallback",
            action="Hold a medium shot and play the subtext in silence.",
            style_source="creative",
            scores=CriteriaScores(
                genre_craft=0.5, style_match=0.4, continuity=0.7,
                originality=0.6, feasibility=0.9, emotion=0.6,
            ),
        )]

    historical = [c for c in raw if c.style_source.startswith("historical")]
    creative_list = [c for c in raw if c.style_source == "creative"]
    creative = creative_list[0] if creative_list else raw[-1]

    pool = list(raw)
    if historical and alpha > 0:
        best_hist = max(historical, key=lambda c: score_candidate(c.scores, w))
        pool.append(blend_creativity(best_hist, creative, alpha, weights=w))

    chosen, report = pick_equilibrium(pool, weights=w)
    record: Optional[DecisionRecord] = None
    if commit:
        record = commit_decision(
            db,
            project_id=project_id,
            phase=phase,
            situation=situation.blob(),
            candidates=pool,
            chosen=chosen,
            equilibrium_method=report["method"],
            creativity_alpha=alpha,
            evidence_ids=list(chosen.evidence_ids),
            scores=report,
        )

    return {
        "phase": phase,
        "situation": situation.blob(),
        "creativity_alpha": alpha,
        "candidates": pool,
        "chosen": chosen,
        "equilibrium": report,
        "decision": record,
    }
