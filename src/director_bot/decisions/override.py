"""Human overrides land on the merkle ledger and can mint new digests."""
from __future__ import annotations

from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.canon.index import reindex
from director_bot.contracts.schemas import CandidateAction, CriteriaScores
from director_bot.decisions.ledger import commit_decision


def human_override(
    db: CanonDB,
    *,
    project_id: int,
    action: str,
    situation: str = "",
    phase: str = "",
    rationale: str = "",
    mint_digest: bool = False,
    work_id: Optional[int] = None,
    director: str = "human",
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Commit a human-authored decision as the chosen action.

    Optionally mint a DecisionDigest so future retrieval can learn from it.
    """
    proj = db.get_project(project_id)
    if proj is None:
        raise ValueError(f"no project {project_id}")
    phase_v = phase or str(proj.get("phase") or "shotlist")
    sit = situation or f"Human override in phase {phase_v}"
    chosen = CandidateAction(
        id="human-override",
        action=action,
        style_source="human",
        scores=CriteriaScores(
            genre_craft=0.85,
            style_match=0.8,
            continuity=0.9,
            originality=0.55,
            feasibility=0.95,
            emotion=0.85,
        ),
        evidence_ids=[],
        notes=rationale or "human override",
    )
    record = commit_decision(
        db,
        project_id=project_id,
        phase=phase_v,
        situation=sit,
        candidates=[chosen],
        chosen=chosen,
        equilibrium_method="human_override",
        creativity_alpha=0.0,
        evidence_ids=[],
        scores={"source": "human", "rationale": rationale},
    )

    digest_id = None
    if mint_digest:
        dig = {
            "work_id": work_id,
            "situation": sit,
            "decision": action,
            "rationale": rationale or "Minted from human override on a live project.",
            "director": director,
            "tags": list(tags or ["human-override"]),
            "phase": phase_v,
            "meta": {
                "project_id": project_id,
                "decision_id": record.id,
                "content_hash": record.content_hash,
            },
        }
        digest_id = db.add_digest(dig)
        reindex(db)

    # remember in project working memory snapshot
    mem = list(proj.get("working_memory") or [])
    mem.append({
        "kind": "decision",
        "content": f"Human override: {action}",
        "ts": record.created_at,
        "meta": {"hash": record.content_hash, "digest_id": digest_id},
    })
    db.update_project(project_id, working_memory=mem)

    return {
        "decision": record,
        "digest_id": digest_id,
    }
