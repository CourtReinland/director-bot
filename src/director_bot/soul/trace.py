"""Model-facing context assembly + brain call traces.

Training regimen depends on seeing *exactly* what the model sees:
system preamble, user message, retrieval hits, score payload, and replies.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.canon.query import lookup_cards, lookup_digests, lookup_moments
from director_bot.config import DEFAULT_CRITERIA_WEIGHTS, PHASE_CREATIVITY
from director_bot.contracts.schemas import (
    CandidateAction,
    ProjectPhase,
    SituationContext,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _char_stats(system: str, user: str) -> dict[str, int]:
    return {
        "system_chars": len(system),
        "user_chars": len(user),
        "total_chars": len(system) + len(user),
        # rough token estimate (~4 chars/token for English prose)
        "approx_tokens": max(1, (len(system) + len(user) + 3) // 4),
    }


# --------------------------------------------------------------------------- #
# Ring buffer + optional SQLite persistence
# --------------------------------------------------------------------------- #

class BrainTraceStore:
    """Process-local ring of recent complete() calls, dual-written to SQLite
    when a CanonDB is bound (durable training history).
    """

    def __init__(self, max_n: int = 80) -> None:
        self._max = max_n
        self._lock = threading.Lock()
        self._calls: deque[dict[str, Any]] = deque(maxlen=max_n)
        self._db: Optional[CanonDB] = None

    def bind_db(self, db: Optional[CanonDB]) -> None:
        """Attach durable storage. Pass None to unbind."""
        self._db = db

    @property
    def db(self) -> Optional[CanonDB]:
        return self._db

    def clear(self) -> None:
        with self._lock:
            self._calls.clear()

    def record(
        self,
        *,
        kind: str,
        system: str,
        user: str,
        response: str,
        brain: str,
        project_id: Optional[int] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4())[:12],
            "ts": _now(),
            "kind": kind,
            "brain": brain,
            "project_id": project_id,
            "system": system,
            "user": user,
            "response": response,
            "stats": _char_stats(system, user),
            "meta": dict(meta or {}),
            "persisted": False,
        }
        with self._lock:
            self._calls.appendleft(entry)
        db = self._db
        if db is not None:
            try:
                db_id = db.insert_brain_trace({
                    "public_id": entry["id"],
                    "ts": entry["ts"],
                    "kind": entry["kind"],
                    "brain": entry["brain"],
                    "project_id": entry["project_id"],
                    "system": entry["system"],
                    "user": entry["user"],
                    "response": entry["response"],
                    "stats": entry["stats"],
                    "meta": entry["meta"],
                })
                entry["db_id"] = db_id
                entry["persisted"] = True
            except Exception:
                # Never break generation if persistence fails
                entry["persisted"] = False
        return entry

    def list(
        self,
        *,
        n: int = 40,
        project_id: Optional[int] = None,
        kind: Optional[str] = None,
        q: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        brain: Optional[str] = None,
        offset: int = 0,
        prefer_db: bool = True,
    ) -> list[dict[str, Any]]:
        db = self._db
        if prefer_db and db is not None:
            try:
                rows = db.list_brain_traces(
                    n=n, project_id=project_id, kind=kind, q=q,
                    since=since, until=until, brain=brain, offset=offset,
                )
                # Return even if empty so filters aren't masked by ring fallback
                if q or since or until or brain or offset or project_id or kind:
                    return rows
                if rows:
                    return rows
            except Exception:
                pass
        with self._lock:
            items = list(self._calls)
        if project_id is not None:
            items = [c for c in items if c.get("project_id") == project_id]
        if kind:
            items = [c for c in items if c.get("kind") == kind]
        if brain:
            items = [c for c in items if c.get("brain") == brain]
        if q and q.strip():
            ql = q.strip().lower()
            items = [
                c for c in items
                if ql in (c.get("system") or "").lower()
                or ql in (c.get("user") or "").lower()
                or ql in (c.get("response") or "").lower()
                or ql in (c.get("kind") or "").lower()
            ]
        if since:
            items = [c for c in items if (c.get("ts") or "") >= since]
        if until:
            items = [c for c in items if (c.get("ts") or "") <= until]
        return items[offset: offset + max(1, n)]

    def count(
        self,
        *,
        project_id: Optional[int] = None,
        kind: Optional[str] = None,
        q: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        brain: Optional[str] = None,
    ) -> int:
        db = self._db
        if db is not None:
            try:
                return db.count_brain_traces(
                    project_id=project_id, kind=kind, q=q,
                    since=since, until=until, brain=brain,
                )
            except Exception:
                pass
        return len(self.list(
            n=500, project_id=project_id, kind=kind, q=q,
            since=since, until=until, brain=brain, prefer_db=False,
        ))

    def get(self, call_id: str) -> Optional[dict[str, Any]]:
        db = self._db
        if db is not None:
            try:
                hit = db.get_brain_trace(call_id)
                if hit:
                    return hit
            except Exception:
                pass
        with self._lock:
            for c in self._calls:
                if c.get("id") == call_id or str(c.get("db_id")) == str(call_id):
                    return c
        return None


_STORE = BrainTraceStore()


def get_trace_store() -> BrainTraceStore:
    return _STORE


class TracingBrain:
    """Decorator brain that logs every complete()/stream() into the ring + DB."""

    def __init__(
        self,
        inner: Any,
        *,
        store: Optional[BrainTraceStore] = None,
        default_kind: str = "complete",
        project_id: Optional[int] = None,
    ) -> None:
        self.inner = inner
        self.store = store or get_trace_store()
        self.default_kind = default_kind
        self.project_id = project_id
        self.kind_override: Optional[str] = None
        self.meta: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return getattr(self.inner, "name", "unknown")

    def with_context(
        self,
        *,
        kind: Optional[str] = None,
        project_id: Optional[int] = None,
        **meta: Any,
    ) -> TracingBrain:
        """Return a shallow clone with call-context for the next complete()."""
        clone = TracingBrain(
            self.inner,
            store=self.store,
            default_kind=kind or self.default_kind,
            project_id=project_id if project_id is not None else self.project_id,
        )
        clone.meta = dict(meta)
        return clone

    def complete(self, system: str, user: str) -> str:
        kind = self.kind_override or self.default_kind
        response = self.inner.complete(system, user)
        self.store.record(
            kind=kind,
            system=system,
            user=user,
            response=response,
            brain=self.name,
            project_id=self.project_id,
            meta=self.meta,
        )
        return response

    def stream(self, system: str, user: str):
        """Yield text deltas; record full response when the stream ends."""
        from director_bot.soul.brain import stream_text

        kind = self.kind_override or self.default_kind
        parts: list[str] = []
        try:
            for delta in stream_text(self.inner, system, user):
                parts.append(delta)
                yield delta
        finally:
            # Record even if consumer stops early mid-stream
            self.store.record(
                kind=kind,
                system=system,
                user=user,
                response="".join(parts),
                brain=self.name,
                project_id=self.project_id,
                meta={**self.meta, "streamed": True},
            )


# Scorer prompt constants (must match brain.score_candidates_with_brain)
SCORE_SYSTEM = (
    "You are a film craft scorer. Return ONLY valid JSON array. "
    "Each item: {\"id\": str, \"scores\": {criteria: 0..1 floats}, "
    "\"notes\": str}. Score honestly; historical craft high on genre/"
    "continuity; creative high on originality."
)


def build_score_payload(
    situation: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "situation": situation,
        "candidates": [
            {
                "id": c.get("id"),
                "action": c.get("action"),
                "style_source": c.get("style_source"),
            }
            for c in candidates
        ],
        "criteria": [
            "genre_craft", "style_match", "continuity",
            "originality", "feasibility", "emotion",
        ],
    }


def build_meet_prompt(
    *,
    system: str,
    process_name: str,
    process_blurb: str,
    memory_text: str,
    topic: str,
) -> dict[str, str]:
    user = (
        f"Current mental process: {process_name}\n"
        f"Process guidance: {process_blurb}\n\n"
        f"Working memory:\n{memory_text}\n\n"
        f"Human / situation:\n{topic}\n\n"
        "Respond in character as the director. Be decisive. "
        "Cite craft principles. Do not skip process."
    )
    return {"system": system, "user": user}


def preview_meet(
    db: CanonDB,
    *,
    topic: str,
    project_id: Optional[int] = None,
    phase: Optional[str] = None,
) -> dict[str, Any]:
    """Assemble the exact meet prompt without calling the brain."""
    from director_bot.soul.brain import get_brain
    from director_bot.soul.steps import DirectorMind

    mind = DirectorMind.create(db, project_id=project_id)
    if phase:
        try:
            mind.process.phase = phase  # type: ignore[assignment]
        except Exception:
            pass
    system = mind.soul.system_preamble()
    process = mind.process.process
    memory_text = mind.memory.format_for_prompt()
    prompts = build_meet_prompt(
        system=system,
        process_name=process.name,
        process_blurb=process.blurb,
        memory_text=memory_text,
        topic=topic,
    )
    brain = get_brain()
    return {
        "kind": "meet",
        "live": False,
        "brain": brain.name,
        "project_id": project_id,
        "phase": mind.process.phase,
        "system": prompts["system"],
        "user": prompts["user"],
        "stats": _char_stats(prompts["system"], prompts["user"]),
        "sections": {
            "soul_name": mind.soul.name,
            "soul_core": mind.soul.core,
            "soul_taste": mind.soul.taste,
            "soul_process_notes": mind.soul.process_notes,
            "process_name": process.name,
            "process_blurb": process.blurb,
            "working_memory": mind.memory.to_list(),
            "working_memory_text": memory_text,
            "topic": topic,
        },
        "would_call_llm": brain.name != "mock",
        "note": (
            "This is a dry-run of the exact system+user messages "
            "speak_about() sends to the brain."
        ),
    }


def preview_decide(
    db: CanonDB,
    *,
    summary: str,
    genre: str = "",
    phase: str = "shotlist",
    project_id: Optional[int] = None,
    style_refs: Optional[list[str]] = None,
    alpha: Optional[float] = None,
    k: int = 5,
) -> dict[str, Any]:
    """Assemble retrieval + candidates + score prompt without committing."""
    from director_bot.decisions.engine import propose_candidates
    from director_bot.decisions.equilibrium import pick_equilibrium, score_candidate
    from director_bot.soul.brain import get_brain
    from director_bot.soul.loader import load_soul

    try:
        phase_enum = ProjectPhase(phase)
    except ValueError:
        phase_enum = ProjectPhase.SHOTLIST
        phase = phase_enum.value

    situation = SituationContext(
        phase=phase_enum,
        genre=genre,
        summary=summary,
        style_refs=list(style_refs or []),
    )
    if project_id is not None:
        proj = db.get_project(project_id)
        if proj:
            situation.project_slug = str(proj.get("slug") or "")
            situation.genre = situation.genre or str(proj.get("genre") or "")
            situation.logline = situation.logline or str(proj.get("logline") or "")

    situation_blob = situation.blob()
    creativity = (
        alpha if alpha is not None
        else PHASE_CREATIVITY.get(phase, 0.3)
    )
    weights = DEFAULT_CRITERIA_WEIGHTS

    digests = lookup_digests(db, situation_blob, k=max(k, 8))
    moments = lookup_moments(db, situation_blob, k=max(2, k // 2), genre=genre or None, tier="S")
    cards = lookup_cards(db, situation_blob, k=4)

    candidates = propose_candidates(db, situation, k=k)
    cand_dicts = [
        {
            "id": c.id,
            "action": c.action,
            "style_source": c.style_source,
            "scores": c.scores.as_dict(),
            "evidence_ids": list(c.evidence_ids),
            "notes": c.notes,
            "weighted": score_candidate(c.scores, weights),
        }
        for c in candidates
    ]

    # provisional equilibrium without brain re-score
    chosen, report = pick_equilibrium(candidates, weights=weights)

    score_payload = build_score_payload(
        situation_blob,
        [{"id": c.id, "action": c.action, "style_source": c.style_source}
         for c in candidates],
    )
    score_user = json.dumps(score_payload, indent=2)

    brain = get_brain()
    soul = load_soul()

    return {
        "kind": "decide",
        "live": False,
        "brain": brain.name,
        "project_id": project_id,
        "phase": phase,
        "creativity_alpha": creativity,
        "situation_blob": situation_blob,
        "situation": {
            "phase": phase,
            "genre": situation.genre,
            "logline": situation.logline,
            "summary": situation.summary,
            "style_refs": list(situation.style_refs),
            "project_slug": situation.project_slug,
        },
        "retrieval": {
            "query": situation_blob,
            "digests": digests[:8],
            "moments": moments[:6],
            "cards": cards[:4],
        },
        "candidates": cand_dicts,
        "provisional_chosen": {
            "id": chosen.id,
            "action": chosen.action,
            "style_source": chosen.style_source,
        },
        "provisional_equilibrium": report,
        "score_prompt": {
            "system": SCORE_SYSTEM,
            "user": score_user,
            "stats": _char_stats(SCORE_SYSTEM, score_user),
            "will_send": brain.name != "mock",
            "note": (
                "Brain re-score runs only when provider != mock. "
                "Mock skips this LLM call and uses deterministic scores."
            ),
        },
        "soul_preamble_chars": len(soul.system_preamble()),
        "soul_note": (
            "Decide() does not send the full soul preamble to the scorer; "
            "scoring uses SCORE_SYSTEM only. Soul preamble is used in meet/speak."
        ),
        "stats": _char_stats(SCORE_SYSTEM, score_user),
        "would_call_llm": brain.name != "mock",
    }


def glass_box_decision(db: CanonDB, decision_id: int) -> Optional[dict[str, Any]]:
    """Reconstruct a stored decision for training inspection."""
    row = db.get_decision(decision_id)
    if not row:
        return None
    situation = str(row.get("situation") or "")
    digests = lookup_digests(db, situation, k=6) if situation else []
    moments = lookup_moments(db, situation, k=4) if situation else []
    return {
        "kind": "decision_glass",
        "decision": row,
        "retrieval_replay": {
            "query": situation,
            "digests": digests,
            "moments": moments,
            "note": "Re-queried with stored situation blob (index may have changed).",
        },
    }


def serialize_candidate(c: CandidateAction) -> dict[str, Any]:
    return {
        "id": c.id,
        "action": c.action,
        "style_source": c.style_source,
        "scores": c.scores.as_dict(),
        "evidence_ids": list(c.evidence_ids),
        "notes": c.notes,
    }
