"""Agreement metrics: do later auto-decisions honor prior human overrides?"""
from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from director_bot.canon.db import CanonDB


def agreement_metrics(db: CanonDB, project_id: int) -> dict[str, Any]:
    """Compare human_override decisions to later non-human choices in same phase.

    A later decision "agrees" if its chosen_action is token-set-similar (>=70)
    to the most recent prior human override in that phase.
    """
    rows = db.decisions_for_project(project_id)
    human_by_phase: dict[str, str] = {}
    checked = 0
    agreeing = 0
    details: list[dict[str, Any]] = []

    for row in rows:
        phase = str(row.get("phase") or "")
        method = str(row.get("equilibrium_method") or "")
        action = str(row.get("chosen_action") or "")
        if method == "human_override":
            human_by_phase[phase] = action
            continue
        if phase not in human_by_phase:
            continue
        prior = human_by_phase[phase]
        score = float(fuzz.token_set_ratio(prior, action))
        checked += 1
        ok = score >= 70.0
        if ok:
            agreeing += 1
        details.append({
            "decision_id": row.get("id"),
            "phase": phase,
            "score": score / 100.0,
            "agrees": ok,
            "human": prior[:120],
            "auto": action[:120],
        })

    rate = (agreeing / checked) if checked else None
    return {
        "project_id": project_id,
        "overrides_seen": sum(
            1 for r in rows
            if r.get("equilibrium_method") == "human_override"
        ),
        "checked": checked,
        "agreeing": agreeing,
        "agreement_rate": rate,
        "details": details,
    }
