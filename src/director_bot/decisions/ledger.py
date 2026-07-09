"""Merkle-linked append-only decision ledger."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.contracts.schemas import (
    CandidateAction,
    CriteriaScores,
    DecisionRecord,
    content_hash,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidates_to_json(candidates: list[CandidateAction]) -> list[dict]:
    return [
        {
            "id": c.id,
            "action": c.action,
            "style_source": c.style_source,
            "scores": c.scores.as_dict(),
            "evidence_ids": list(c.evidence_ids),
            "notes": c.notes,
        }
        for c in candidates
    ]


def commit_decision(
    db: CanonDB,
    *,
    project_id: Optional[int],
    phase: str,
    situation: str,
    candidates: list[CandidateAction],
    chosen: CandidateAction,
    equilibrium_method: str = "weighted_pareto",
    creativity_alpha: float = 0.25,
    evidence_ids: Optional[list[int]] = None,
    scores: Optional[dict[str, Any]] = None,
) -> DecisionRecord:
    """Hash-chain a decision onto the project's ledger and persist it."""
    parent = db.latest_decision_hash(project_id)
    record = DecisionRecord(
        project_id=project_id,
        phase=phase,
        situation=situation,
        candidates=list(candidates),
        chosen_id=chosen.id,
        chosen_action=chosen.action,
        equilibrium_method=equilibrium_method,
        creativity_alpha=creativity_alpha,
        evidence_ids=list(evidence_ids if evidence_ids is not None
                          else chosen.evidence_ids),
        scores=dict(scores or {}),
        parent_hash=parent,
        created_at=_now(),
    )
    record.content_hash = content_hash(record.payload_for_hash(), parent)

    did = db.append_decision({
        "project_id": project_id,
        "phase": phase,
        "situation": situation,
        "candidates": _candidates_to_json(candidates),
        "chosen_id": chosen.id,
        "chosen_action": chosen.action,
        "equilibrium_method": equilibrium_method,
        "creativity_alpha": creativity_alpha,
        "evidence_ids": record.evidence_ids,
        "scores": record.scores,
        "parent_hash": record.parent_hash,
        "content_hash": record.content_hash,
        "created_at": record.created_at,
    })
    record.id = did
    return record


def verify_chain(db: CanonDB, project_id: int) -> dict[str, Any]:
    """Recompute hashes; report first break if any."""
    rows = db.decisions_for_project(project_id)
    prev = ""
    for i, row in enumerate(rows):
        candidates_raw = row.get("candidates") or []
        candidates: list[CandidateAction] = []
        for c in candidates_raw:
            if not isinstance(c, dict):
                continue
            sc = c.get("scores") or {}
            candidates.append(CandidateAction(
                id=str(c.get("id", "")),
                action=str(c.get("action", "")),
                style_source=str(c.get("style_source", "")),
                scores=CriteriaScores.from_dict(sc if isinstance(sc, dict) else {}),
                evidence_ids=list(c.get("evidence_ids") or []),
                notes=str(c.get("notes", "")),
            ))
        probe = DecisionRecord(
            phase=str(row.get("phase", "")),
            situation=str(row.get("situation", "")),
            candidates=candidates,
            chosen_id=str(row.get("chosen_id", "")),
            chosen_action=str(row.get("chosen_action", "")),
            equilibrium_method=str(row.get("equilibrium_method", "")),
            creativity_alpha=float(row.get("creativity_alpha", 0.25)),
            evidence_ids=list(row.get("evidence_ids") or []),
            scores=dict(row.get("scores") or {}),
            parent_hash=str(row.get("parent_hash", "")),
        )
        expected_parent = prev
        actual_parent = str(row.get("parent_hash", ""))
        if actual_parent != expected_parent:
            return {
                "ok": False,
                "index": i,
                "id": row.get("id"),
                "reason": "parent_hash_mismatch",
                "expected_parent": expected_parent,
                "actual_parent": actual_parent,
            }
        expected_hash = content_hash(probe.payload_for_hash(), actual_parent)
        actual_hash = str(row.get("content_hash", ""))
        if expected_hash != actual_hash:
            return {
                "ok": False,
                "index": i,
                "id": row.get("id"),
                "reason": "content_hash_mismatch",
                "expected": expected_hash,
                "actual": actual_hash,
            }
        prev = actual_hash
    return {"ok": True, "length": len(rows), "tip": prev}
