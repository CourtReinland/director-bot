"""Build / refresh embedding index for hybrid retrieval."""
from __future__ import annotations

from typing import Any

from director_bot.canon.db import CanonDB
from director_bot.canon.embed import get_embedder


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


def reindex(db: CanonDB, *, batch_size: int = 32) -> dict[str, int | str]:
    """Recompute embeddings for digests, moments, and scene cards."""
    emb = get_embedder()
    counts: dict[str, int | str] = {
        "digest": 0, "moment": 0, "card": 0, "provider": emb.name,
    }

    def _flush(entity_type: str, batch: list[tuple[int, str]]) -> None:
        if not batch:
            return
        vectors = emb.embed_many([b for _, b in batch])
        for (eid, blob), vec in zip(batch, vectors):
            db.upsert_embedding(entity_type, eid, blob, vec)

    batch: list[tuple[int, str]] = []
    for d in db.list_digests():
        if d.get("id") is None:
            continue
        batch.append((int(d["id"]), _digest_blob(d)))
        if len(batch) >= batch_size:
            _flush("digest", batch)
            counts["digest"] = int(counts["digest"]) + len(batch)
            batch = []
    if batch:
        counts["digest"] = int(counts["digest"]) + len(batch)
        _flush("digest", batch)
        batch = []

    for m in db.all_shot_moments():
        if m.get("id") is None:
            continue
        batch.append((int(m["id"]), _moment_blob(m)))
        if len(batch) >= batch_size:
            _flush("moment", batch)
            counts["moment"] = int(counts["moment"]) + len(batch)
            batch = []
    if batch:
        counts["moment"] = int(counts["moment"]) + len(batch)
        _flush("moment", batch)
        batch = []

    for c in db.all_scene_cards():
        if c.get("id") is None:
            continue
        batch.append((int(c["id"]), _card_blob(c)))
        if len(batch) >= batch_size:
            _flush("card", batch)
            counts["card"] = int(counts["card"]) + len(batch)
            batch = []
    if batch:
        counts["card"] = int(counts["card"]) + len(batch)
        _flush("card", batch)

    db.emit("embeddings_reindexed", dict(counts))
    return counts


def ensure_indexed(db: CanonDB) -> dict[str, Any]:
    """Reindex if empty; return status."""
    digests = db.embeddings_of_type("digest")
    if digests:
        return {"status": "ready", "digest_vectors": len(digests)}
    counts = reindex(db)
    return {"status": "built", **counts}
