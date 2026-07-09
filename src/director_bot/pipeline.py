"""Vertical-slice orchestration: brief → board → decide → handoffs."""
from __future__ import annotations

from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.canon.query import lookup_cards
from director_bot.canon.seed import seed_demo_canon
from director_bot.contracts.schemas import ProjectPhase, SceneCard, SituationContext
from director_bot.decisions.engine import decide
from director_bot.decisions.ledger import verify_chain
from director_bot.project.workspace import export_project_handoffs
from director_bot.soul.steps import DirectorMind


def run_short_pipeline(
    db: CanonDB,
    *,
    title: str,
    genre: str,
    logline: str,
    situation: str,
    style_refs: Optional[list[str]] = None,
    seed: bool = True,
) -> dict[str, Any]:
    """Offline-friendly short-film vertical slice.

    1. Optionally seed canon
    2. Create project + seed board from nearest canon cards
    3. Advance phases intake → shotlist
    4. Commit a shot decision
    5. Export handoffs
    """
    seeded: list[int] = []
    if seed and not db.list_works():
        seeded = seed_demo_canon(db)
    elif seed:
        # ensure embeddings exist even if works already present
        from director_bot.canon.index import ensure_indexed
        ensure_indexed(db)

    pid = db.create_project(title, genre=genre, logline=logline, medium="short")
    # board from nearest cards
    hits = lookup_cards(db, f"{genre} {logline} {situation}", k=3, genre=genre or None)
    if not hits:
        hits = lookup_cards(db, situation or logline or genre, k=3)
    cards = []
    for i, h in enumerate(hits or []):
        cards.append({
            "idx": i,
            "slugline": h.get("slugline") or "EXT. UNKNOWN - DAY",
            "title": h.get("title") or f"Card {i}",
            "what_happens": h.get("what_happens") or "",
            "relationship_delta": h.get("relationship_delta") or "",
            "plot_function": h.get("plot_function") or "",
            "emotional_spine": h.get("emotional_spine") or "",
            "characters": h.get("characters") or [],
            "structural_beat": h.get("structural_beat") or "",
            "act": h.get("act"),
            "tags": h.get("tags") or [],
            "meta": {"from_canon_work": (h.get("work") or {}).get("slug")},
        })
    if not cards:
        cards = [{
            "idx": 0,
            "slugline": "EXT. LOCATION - DAY",
            "title": "Open",
            "what_happens": situation or logline,
            "characters": [],
            "structural_beat": "Set-Up",
            "act": 1,
        }]
    db.replace_project_cards(pid, cards)

    mind = DirectorMind.create(db, project_id=pid)
    for step in ("break_story", "write", "shotlist"):
        mind.set_phase(step)

    first = cards[0]
    scene = SceneCard(
        idx=int(first.get("idx", 0)),
        slugline=str(first.get("slugline") or ""),
        title=str(first.get("title") or ""),
        what_happens=str(first.get("what_happens") or ""),
        relationship_delta=str(first.get("relationship_delta") or ""),
        plot_function=str(first.get("plot_function") or ""),
        emotional_spine=str(first.get("emotional_spine") or ""),
        characters=list(first.get("characters") or []),
        structural_beat=str(first.get("structural_beat") or ""),
    )
    ctx = SituationContext(
        phase=ProjectPhase.SHOTLIST,
        genre=genre,
        logline=logline,
        summary=situation or logline,
        scene_card=scene,
        style_refs=list(style_refs or []),
    )
    result = decide(db, ctx, project_id=pid, commit=True)
    chain = verify_chain(db, pid)
    handoffs = export_project_handoffs(db, pid)
    return {
        "project_id": pid,
        "seeded_works": seeded,
        "cards": len(cards),
        "chosen": result["chosen"].action,
        "decision_hash": getattr(result.get("decision"), "content_hash", None),
        "chain": chain,
        "handoffs": handoffs,
        "brain": result.get("brain"),
    }
