"""Build / refresh embedding index for hybrid retrieval."""
from __future__ import annotations

from typing import Any

from director_bot.canon.db import CanonDB
from director_bot.canon.embed import embed_text


def _digest_blob(d: dict) -> str:
    parts = [
        d.get("situation"), d.get("decision"), d.get("rationale"),
        d.get("director"), d.get("phase"),
        " ".join(d.get("tags") or []),
    ]
    return " | ".join(str(p) for p in parts if p)


def _moment_blob(m: dict) -> str:
    dlg = m.get("dialogue") or []
    dlg_txt = " ".join(
        f"{d.get('character', '')}: {d.get('text', '')}"
        if isinstance(d, dict) else str(d)
        for d in dlg
    )
    parts = [
        m.get("scale"), m.get("subject"), m.get("location"),
        m.get("time_of_day"), m.get("action_text"), m.get("mood"),
        m.get("move"), m.get("angle"),
        " ".join(m.get("characters") or []), dlg_txt,
    ]
    return " | ".join(str(p) for p in parts if p)


def _card_blob(c: dict) -> str:
    parts = [
        c.get("slugline"), c.get("title"), c.get("what_happens"),
        c.get("relationship_delta"), c.get("plot_function"),
        c.get("emotional_spine"), c.get("structural_beat"),
        " ".join(c.get("characters") or []),
        " ".join(c.get("tags") or []),
    ]
    return " | ".join(str(p) for p in parts if p)


def reindex(db: CanonDB) -> dict[str, int]:
    """Recompute embeddings for digests, moments, and scene cards."""
    counts = {"digest": 0, "moment": 0, "card": 0}
    for d in db.list_digests():
        if d.get("id") is None:
            continue
        blob = _digest_blob(d)
        db.upsert_embedding("digest", int(d["id"]), blob, embed_text(blob))
        counts["digest"] += 1
    for m in db.all_shot_moments():
        if m.get("id") is None:
            continue
        blob = _moment_blob(m)
        db.upsert_embedding("moment", int(m["id"]), blob, embed_text(blob))
        counts["moment"] += 1
    for c in db.all_scene_cards():
        if c.get("id") is None:
            continue
        blob = _card_blob(c)
        db.upsert_embedding("card", int(c["id"]), blob, embed_text(blob))
        counts["card"] += 1
    db.emit("embeddings_reindexed", counts)
    return counts


def ensure_indexed(db: CanonDB) -> dict[str, Any]:
    """Reindex if empty; return status."""
    digests = db.embeddings_of_type("digest")
    if digests:
        return {"status": "ready", "digest_vectors": len(digests)}
    counts = reindex(db)
    return {"status": "built", **counts}
