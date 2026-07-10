"""FastAPI dashboard — board, decisions, model view (training), arc, SSE meet."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field

from director_bot import config
from director_bot.canon.db import CanonDB
from director_bot.soul.trace import get_trace_store

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DecideBody(BaseModel):
    summary: str
    project_id: Optional[int] = None
    genre: str = ""
    phase: str = "shotlist"
    alpha: Optional[float] = None
    style_refs: list[str] = Field(default_factory=list)
    commit: bool = True


class MotifBody(BaseModel):
    name: str
    kind: str = "visual"
    description: str = ""
    first_episode: Optional[int] = 1
    payoff_episode: Optional[int] = None


class MeetBody(BaseModel):
    message: str
    project_id: Optional[int] = None
    preview_only: bool = False


class PreviewDecideBody(BaseModel):
    summary: str
    project_id: Optional[int] = None
    genre: str = ""
    phase: str = "shotlist"
    alpha: Optional[float] = None
    style_refs: list[str] = Field(default_factory=list)
    k: int = 5


class PreviewMeetBody(BaseModel):
    topic: str
    project_id: Optional[int] = None
    phase: Optional[str] = None


class CardBody(BaseModel):
    idx: Optional[int] = None
    slugline: str = ""
    title: str = ""
    what_happens: str = ""
    relationship_delta: str = ""
    plot_function: str = ""
    emotional_spine: str = ""
    characters: list[str] = Field(default_factory=list)
    structural_beat: str = ""
    act: Optional[int] = None
    page_estimate: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class CardPatch(BaseModel):
    idx: Optional[int] = None
    slugline: Optional[str] = None
    title: Optional[str] = None
    what_happens: Optional[str] = None
    relationship_delta: Optional[str] = None
    plot_function: Optional[str] = None
    emotional_spine: Optional[str] = None
    characters: Optional[list[str]] = None
    structural_beat: Optional[str] = None
    act: Optional[int] = None
    page_estimate: Optional[float] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict[str, Any]] = None


def create_app(db: Optional[CanonDB] = None):
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import HTMLResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError(
            "Dashboard requires fastapi+uvicorn. Install: pip install -e '.[web]'"
        ) from exc

    database = db or CanonDB(config.db_path())
    # Durable training log: every complete()/stream() dual-writes to this DB
    get_trace_store().bind_db(database)
    app = FastAPI(title="Director-bot", version="0.6.0")

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> Any:
        index_path = STATIC_DIR / "index.html"
        if index_path.is_file():
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Director-bot</h1><p>static/index.html missing</p>")

    @app.get("/api/health")
    def health() -> dict:
        from director_bot import __version__
        from director_bot.canon.embed import get_embedder
        emb = get_embedder()
        store = get_trace_store()
        return {
            "ok": True,
            "version": __version__,
            "provider": config.default_provider(),
            "embedder": emb.name,
            "works": len(database.list_works()),
            "projects": len(database.list_projects()),
            "brain_traces": store.count(),
            "home": str(config.home()),
            "db": str(config.db_path()),
        }

    # ------------------------------------------------------------------ soul
    @app.get("/api/soul")
    def soul_payload() -> dict:
        from director_bot.soul.loader import load_soul
        soul = load_soul()
        preamble = soul.system_preamble()
        return {
            "name": soul.name,
            "core": soul.core,
            "taste": soul.taste,
            "process_notes": soul.process_notes,
            "system_preamble": preamble,
            "files": {k: str(v) for k, v in soul.files.items()},
            "stats": {
                "preamble_chars": len(preamble),
                "approx_tokens": max(1, (len(preamble) + 3) // 4),
            },
        }

    # -------------------------------------------------------------- model view
    @app.post("/api/model-view/meet")
    def model_view_meet(payload: PreviewMeetBody) -> dict:
        from director_bot.soul.trace import preview_meet
        return preview_meet(
            database,
            topic=payload.topic,
            project_id=payload.project_id,
            phase=payload.phase,
        )

    @app.post("/api/model-view/decide")
    def model_view_decide(payload: PreviewDecideBody) -> dict:
        from director_bot.soul.trace import preview_decide
        return preview_decide(
            database,
            summary=payload.summary,
            genre=payload.genre,
            phase=payload.phase,
            project_id=payload.project_id,
            style_refs=payload.style_refs,
            alpha=payload.alpha,
            k=payload.k,
        )

    @app.get("/api/brain/traces")
    def brain_traces(
        n: int = Query(40, ge=1, le=200),
        project_id: Optional[int] = None,
        kind: Optional[str] = None,
        q: Optional[str] = Query(None, description="Full-text on system/user/response"),
        since: Optional[str] = Query(None, description="ISO ts lower bound"),
        until: Optional[str] = Query(None, description="ISO ts upper bound"),
        brain: Optional[str] = None,
        offset: int = Query(0, ge=0),
    ) -> dict:
        store = get_trace_store()
        filters = dict(
            project_id=project_id, kind=kind, q=q,
            since=since, until=until, brain=brain,
        )
        traces = store.list(n=n, offset=offset, **filters)
        return {
            "traces": traces,
            "count": store.count(**filters),
            "offset": offset,
            "n": n,
            "source": "sqlite" if store.db is not None else "memory",
            "filters": {k: v for k, v in filters.items() if v is not None},
        }

    @app.get("/api/brain/traces/{trace_id}")
    def brain_trace(trace_id: str) -> dict:
        hit = get_trace_store().get(trace_id)
        if not hit:
            raise HTTPException(
                404,
                "trace not found (check public_id or db id; ring is process-local)",
            )
        return hit

    # ------------------------------------------------------------------ meet
    @app.post("/api/soul/meet")
    def soul_meet(payload: MeetBody) -> dict:
        from director_bot.soul.steps import DirectorMind
        from director_bot.soul.trace import preview_meet

        if payload.preview_only:
            return preview_meet(
                database,
                topic=payload.message,
                project_id=payload.project_id,
            )
        mind = DirectorMind.create(database, project_id=payload.project_id)
        mind.perceive(payload.message)
        return mind.speak_about_traced(payload.message)

    @app.post("/api/soul/meet/stream")
    def soul_meet_stream(payload: MeetBody) -> Any:
        """SSE stream: meta → token* → done|error. Tokens appear as they arrive."""
        from fastapi.responses import StreamingResponse
        from director_bot.soul.steps import DirectorMind
        from director_bot.soul.trace import preview_meet

        if payload.preview_only:
            view = preview_meet(
                database,
                topic=payload.message,
                project_id=payload.project_id,
            )

            def preview_events() -> Iterator[str]:
                yield _sse("meta", view)
                yield _sse("done", view)

            return StreamingResponse(
                preview_events(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        mind = DirectorMind.create(database, project_id=payload.project_id)
        mind.perceive(payload.message)

        def event_stream() -> Iterator[str]:
            for item in mind.speak_about_stream(payload.message):
                yield _sse(item["event"], item["data"])

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ---------------------------------------------------------------- works /
    @app.get("/api/works")
    def works(tier: Optional[str] = None, genre: Optional[str] = None) -> list:
        return database.list_works(tier=tier, genre=genre)

    @app.get("/api/projects")
    def projects() -> list:
        return database.list_projects()

    @app.get("/api/projects/{project_id}")
    def project(project_id: int) -> dict:
        p = database.get_project(project_id)
        if not p:
            raise HTTPException(404, "project not found")
        out = dict(p)
        out["cards"] = database.project_cards(project_id)
        out["decisions"] = database.decisions_for_project(project_id)
        # Training surface: working memory as the model would read it
        from director_bot.soul.memory import WorkingMemory
        wm = WorkingMemory.from_list(p.get("working_memory"))
        out["working_memory_text"] = wm.format_for_prompt()
        out["working_memory_entries"] = wm.to_list()
        return out

    @app.get("/api/projects/{project_id}/cards")
    def list_cards(project_id: int) -> list:
        if not database.get_project(project_id):
            raise HTTPException(404, "project not found")
        return database.project_cards(project_id)

    @app.post("/api/projects/{project_id}/cards")
    def create_card(project_id: int, payload: CardBody) -> dict:
        if not database.get_project(project_id):
            raise HTTPException(404, "project not found")
        data = payload.model_dump()
        if data.get("idx") is None:
            existing = database.project_cards(project_id)
            data["idx"] = len(existing)
        cid = database.add_project_card(project_id, data)
        card = database.get_project_card(cid)
        return card or {"id": cid}

    @app.patch("/api/cards/{card_id}")
    def patch_card(card_id: int, payload: CardPatch) -> dict:
        fields = {k: v for k, v in payload.model_dump().items() if v is not None}
        card = database.update_project_card(card_id, **fields)
        if not card:
            raise HTTPException(404, "card not found")
        return card

    @app.delete("/api/cards/{card_id}")
    def delete_card(card_id: int) -> dict:
        if not database.delete_project_card(card_id):
            raise HTTPException(404, "card not found")
        return {"ok": True, "id": card_id}

    @app.get("/api/projects/{project_id}/chain")
    def chain(project_id: int) -> dict:
        from director_bot.decisions.ledger import verify_chain
        from director_bot.decisions.agreement import agreement_metrics
        return {
            "verify": verify_chain(database, project_id),
            "agreement": agreement_metrics(database, project_id),
            "decisions": database.decisions_for_project(project_id),
        }

    @app.get("/api/decisions/{decision_id}")
    def decision_detail(decision_id: int) -> dict:
        from director_bot.soul.trace import glass_box_decision
        hit = glass_box_decision(database, decision_id)
        if not hit:
            raise HTTPException(404, "decision not found")
        return hit

    @app.get("/api/lookup")
    def lookup(
        q: str = Query(..., min_length=1),
        kind: str = Query("digest"),
        k: int = Query(8, ge=1, le=30),
    ) -> list:
        from director_bot.canon.query import (
            lookup_cards, lookup_digests, lookup_moments,
        )
        kind_l = kind.lower()
        if kind_l == "moment":
            return lookup_moments(database, q, k=k)
        if kind_l == "card":
            return lookup_cards(database, q, k=k)
        return lookup_digests(database, q, k=k)

    @app.post("/api/decide")
    def api_decide(payload: DecideBody) -> dict:
        from director_bot.contracts.schemas import ProjectPhase, SituationContext
        from director_bot.decisions.engine import decide
        from director_bot.soul.trace import serialize_candidate
        try:
            phase = ProjectPhase(payload.phase)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        situation = SituationContext(
            phase=phase,
            genre=payload.genre,
            summary=payload.summary,
            style_refs=list(payload.style_refs or []),
        )
        result = decide(
            database, situation,
            project_id=payload.project_id,
            creativity_alpha=payload.alpha,
            commit=payload.commit,
        )
        chosen = result["chosen"]
        rec = result.get("decision")
        return {
            "chosen_id": chosen.id,
            "chosen_action": chosen.action,
            "style_source": chosen.style_source,
            "creativity_alpha": result["creativity_alpha"],
            "brain": result.get("brain"),
            "brain_scored": result.get("brain_scored"),
            "decision_id": getattr(rec, "id", None),
            "content_hash": getattr(rec, "content_hash", None),
            "equilibrium": result.get("equilibrium"),
            "situation": result.get("situation"),
            "candidates": [serialize_candidate(c) for c in result.get("candidates") or []],
            "model_view": result.get("model_view"),
        }

    @app.get("/api/series/{series_id}/arc")
    def series_arc(series_id: int) -> dict:
        from director_bot.project.arc import arc_report
        return arc_report(database, series_id)

    @app.post("/api/series/{series_id}/motifs")
    def create_motif(series_id: int, payload: MotifBody) -> dict:
        from director_bot.project.arc import add_motif
        mid = add_motif(
            database, series_id,
            name=payload.name, kind=payload.kind,
            description=payload.description,
            first_episode=payload.first_episode,
            payoff_episode=payload.payoff_episode,
        )
        return database.get_motif(mid) or {"id": mid}

    @app.get("/api/series/{series_id}/plan/{episode_number}")
    def plan_ep(series_id: int, episode_number: int,
                hint: str = "") -> dict:
        from director_bot.project.arc import plan_episode_spine
        return plan_episode_spine(
            database, series_id, episode_number, logline_hint=hint,
        )

    return app


def _sse(event: str, data: Any) -> str:
    """Format one Server-Sent Event (JSON data payload)."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
