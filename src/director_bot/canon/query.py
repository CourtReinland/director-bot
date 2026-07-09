"""Lookup helpers over the canon (hybrid: rapidfuzz + hashed embeddings)."""
from __future__ import annotations

from typing import Any, Optional

from rapidfuzz import fuzz

from director_bot.canon.db import CanonDB
from director_bot.canon.embed import cosine, get_embedder, hybrid_score
from director_bot.canon.index import ensure_indexed


def filter_works(
    db: CanonDB,
    *,
    tier: Optional[str] = None,
    genre: Optional[str] = None,
    director: Optional[str] = None,
) -> list[dict]:
    works = db.list_works(tier=tier, genre=genre)
    if director:
        d = director.lower()
        works = [
            w for w in works
            if any(d in str(x).lower() for x in (w.get("directors") or []))
        ]
    return works


def _fuzz(query: str, blob: str) -> float:
    if not query.strip() or not blob.strip():
        return 0.0
    return float(fuzz.token_set_ratio(query, blob)) / 100.0


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


def _digest_blob(d: dict) -> str:
    parts = [
        d.get("situation"), d.get("decision"), d.get("rationale"),
        d.get("director"), d.get("phase"),
        " ".join(d.get("tags") or []),
    ]
    return " | ".join(str(p) for p in parts if p)


def _vec_map(db: CanonDB, entity_type: str) -> dict[int, list[float]]:
    out: dict[int, list[float]] = {}
    for row in db.embeddings_of_type(entity_type):
        vec = row.get("vector") or []
        if isinstance(vec, list) and vec:
            out[int(row["entity_id"])] = [float(x) for x in vec]
    return out


def lookup_moments(
    db: CanonDB,
    query: str,
    *,
    k: int = 8,
    tier: Optional[str] = None,
    genre: Optional[str] = None,
    min_score: float = 0.12,
    hybrid: bool = True,
) -> list[dict[str, Any]]:
    """Return top-k shot moments with work metadata and similarity score."""
    ensure_indexed(db) if hybrid else None
    qvec = get_embedder().embed(query) if hybrid else []
    vmap = _vec_map(db, "moment") if hybrid else {}

    allowed_ids: Optional[set[int]] = None
    if tier or genre:
        works = filter_works(db, tier=tier, genre=genre)
        allowed_ids = {int(w["id"]) for w in works}
        if not allowed_ids:
            return []

    work_cache: dict[int, dict] = {}
    scored: list[tuple[float, dict]] = []
    for m in db.all_shot_moments():
        wid = int(m["work_id"])
        if allowed_ids is not None and wid not in allowed_ids:
            continue
        blob = _moment_blob(m)
        f = _fuzz(query, blob)
        if hybrid and m.get("id") is not None and int(m["id"]) in vmap:
            c = cosine(qvec, vmap[int(m["id"])])
            score = hybrid_score(f, c)
        else:
            score = f
        if score < min_score:
            continue
        if wid not in work_cache:
            work_cache[wid] = db.get_work(wid) or {}
        scored.append((score, {
            **m, "work": work_cache[wid], "score": score, "fuzz": f,
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]


def lookup_cards(
    db: CanonDB,
    query: str,
    *,
    k: int = 8,
    tier: Optional[str] = None,
    genre: Optional[str] = None,
    min_score: float = 0.12,
    hybrid: bool = True,
) -> list[dict[str, Any]]:
    ensure_indexed(db) if hybrid else None
    qvec = get_embedder().embed(query) if hybrid else []
    vmap = _vec_map(db, "card") if hybrid else {}

    works_by_id: dict[int, dict] = {}
    for w in filter_works(db, tier=tier, genre=genre) if (tier or genre) else db.list_works():
        works_by_id[int(w["id"])] = w
    allowed_ids: Optional[set[int]] = set(works_by_id) if (tier or genre) else None

    scored: list[tuple[float, dict]] = []
    for w in (works_by_id.values() if works_by_id else db.list_works()):
        wid = int(w["id"])
        if allowed_ids is not None and wid not in allowed_ids:
            continue
        for c in db.scene_cards_for_work(wid):
            blob = _card_blob(c)
            f = _fuzz(query, blob)
            if hybrid and c.get("id") is not None and int(c["id"]) in vmap:
                score = hybrid_score(f, cosine(qvec, vmap[int(c["id"])]))
            else:
                score = f
            if score < min_score:
                continue
            scored.append((score, {**c, "work": w, "score": score, "fuzz": f}))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]


def lookup_digests(
    db: CanonDB,
    query: str,
    *,
    k: int = 8,
    director: Optional[str] = None,
    phase: Optional[str] = None,
    min_score: float = 0.12,
    hybrid: bool = True,
) -> list[dict[str, Any]]:
    ensure_indexed(db) if hybrid else None
    qvec = get_embedder().embed(query) if hybrid else []
    vmap = _vec_map(db, "digest") if hybrid else {}

    digests = db.list_digests()
    if director:
        d = director.lower()
        digests = [x for x in digests if d in str(x.get("director", "")).lower()]
    if phase:
        digests = [x for x in digests if x.get("phase") == phase]

    scored: list[tuple[float, dict]] = []
    for dig in digests:
        blob = _digest_blob(dig)
        f = _fuzz(query, blob)
        if hybrid and dig.get("id") is not None and int(dig["id"]) in vmap:
            score = hybrid_score(f, cosine(qvec, vmap[int(dig["id"])]))
        else:
            score = f
        if score < min_score:
            continue
        work = db.get_work(int(dig["work_id"])) if dig.get("work_id") else None
        scored.append((score, {
            **dig, "work": work, "score": score, "fuzz": f,
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]
