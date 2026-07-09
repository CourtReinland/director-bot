"""Multi-criteria equilibrium (practical stand-in for Nash-style stability).

Players = criteria (genre_craft, style_match, continuity, originality,
feasibility, emotion). A candidate is preferred when no unilateral
criterion swap would improve the weighted vector without collapsing others
below a floor — approximated via weighted sum + Pareto dominance filter.
"""
from __future__ import annotations

from typing import Iterable, Optional

from director_bot.config import DEFAULT_CRITERIA_WEIGHTS
from director_bot.contracts.schemas import (
    CRITERIA,
    CandidateAction,
    CriteriaScores,
)


def score_candidate(
    scores: CriteriaScores | dict[str, float],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Normalized weighted sum in [0, ~1] if component scores are 0..1."""
    w = weights or DEFAULT_CRITERIA_WEIGHTS
    d = scores.as_dict() if isinstance(scores, CriteriaScores) else dict(scores)
    total_w = sum(max(float(w.get(c, 0.0)), 0.0) for c in CRITERIA) or 1.0
    raw = sum(float(d.get(c, 0.0)) * max(float(w.get(c, 0.0)), 0.0) for c in CRITERIA)
    return raw / total_w


def _dominates(a: dict[str, float], b: dict[str, float],
               eps: float = 1e-9) -> bool:
    """True if a is >= b on all criteria and > on at least one."""
    ge_all = all(a.get(c, 0.0) + eps >= b.get(c, 0.0) for c in CRITERIA)
    gt_one = any(a.get(c, 0.0) > b.get(c, 0.0) + eps for c in CRITERIA)
    return ge_all and gt_one


def pareto_front(candidates: Iterable[CandidateAction]) -> list[CandidateAction]:
    items = list(candidates)
    if not items:
        return []
    front: list[CandidateAction] = []
    for c in items:
        cd = c.scores.as_dict()
        dominated = False
        for other in items:
            if other is c:
                continue
            if _dominates(other.scores.as_dict(), cd):
                dominated = True
                break
        if not dominated:
            front.append(c)
    return front or items


def pick_equilibrium(
    candidates: list[CandidateAction],
    *,
    weights: Optional[dict[str, float]] = None,
    floor: float = 0.25,
) -> tuple[CandidateAction, dict]:
    """Pick stable choice from candidates.

    1. Drop candidates that fail any criterion floor (if any remain).
    2. Restrict to Pareto front.
    3. Maximize weighted score among survivors.
    """
    if not candidates:
        raise ValueError("no candidates to equilibrate")

    def ok(c: CandidateAction) -> bool:
        d = c.scores.as_dict()
        return all(float(d.get(k, 0.0)) >= floor for k in CRITERIA)

    viable = [c for c in candidates if ok(c)]
    pool = viable if viable else list(candidates)
    front = pareto_front(pool)

    best = max(front, key=lambda c: score_candidate(c.scores, weights))
    report = {
        "method": "weighted_pareto",
        "n_candidates": len(candidates),
        "n_viable": len(viable),
        "n_pareto": len(front),
        "floor": floor,
        "chosen_id": best.id,
        "chosen_score": score_candidate(best.scores, weights),
        "weights": dict(weights or DEFAULT_CRITERIA_WEIGHTS),
        "front_ids": [c.id for c in front],
    }
    return best, report


def blend_creativity(
    historical: CandidateAction,
    creative: CandidateAction,
    alpha: float,
    *,
    weights: Optional[dict[str, float]] = None,
) -> CandidateAction:
    """Blend two candidates: α toward creative, (1-α) historical.

    Scores are linearly mixed; action text prefers creative when α >= 0.5.
    """
    a = max(0.0, min(1.0, float(alpha)))
    hd = historical.scores.as_dict()
    cd = creative.scores.as_dict()
    mixed = CriteriaScores.from_dict({
        k: (1 - a) * hd.get(k, 0.0) + a * cd.get(k, 0.0) for k in CRITERIA
    })
    action = creative.action if a >= 0.5 else historical.action
    if 0.2 < a < 0.8:
        action = (
            f"{historical.action.rstrip('.')} — with creative inflection: "
            f"{creative.action}"
        )
    return CandidateAction(
        id=f"hybrid-{historical.id}-{creative.id}",
        action=action,
        style_source=f"hybrid:a={a:.2f}",
        scores=mixed,
        evidence_ids=list(dict.fromkeys(
            list(historical.evidence_ids) + list(creative.evidence_ids)
        )),
        notes=(
            f"blend α={a:.2f}; hist_score={score_candidate(historical.scores, weights):.3f}; "
            f"creative_score={score_candidate(creative.scores, weights):.3f}"
        ),
    )
