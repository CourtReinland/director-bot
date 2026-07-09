"""FastAPI dashboard — board, decisions, canon lookup, arc overview."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from director_bot import config
from director_bot.canon.db import CanonDB

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DecideBody(BaseModel):
    summary: str
    project_id: Optional[int] = None
    genre: str = ""
    phase: str = "shotlist"
    alpha: Optional[float] = None


class MotifBody(BaseModel):
    name: str
    kind: str = "visual"
    description: str = ""
    first_episode: Optional[int] = 1
    payoff_episode: Optional[int] = None


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
    app = FastAPI(title="Director-bot", version="0.3.0")

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
        return {
            "ok": True,
            "version": __version__,
            "provider": config.default_provider(),
            "embedder": emb.name,
            "works": len(database.list_works()),
            "projects": len(database.list_projects()),
        }

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
        return out

    @app.get("/api/projects/{project_id}/chain")
    def chain(project_id: int) -> dict:
        from director_bot.decisions.ledger import verify_chain
        from director_bot.decisions.agreement import agreement_metrics
        return {
            "verify": verify_chain(database, project_id),
            "agreement": agreement_metrics(database, project_id),
            "decisions": database.decisions_for_project(project_id),
        }

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
        try:
            phase = ProjectPhase(payload.phase)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        situation = SituationContext(
            phase=phase, genre=payload.genre, summary=payload.summary,
        )
        result = decide(
            database, situation,
            project_id=payload.project_id,
            creativity_alpha=payload.alpha,
            commit=True,
        )
        chosen = result["chosen"]
        rec = result.get("decision")
        return {
            "chosen_id": chosen.id,
            "chosen_action": chosen.action,
            "style_source": chosen.style_source,
            "creativity_alpha": result["creativity_alpha"],
            "brain": result.get("brain"),
            "decision_id": getattr(rec, "id", None),
            "content_hash": getattr(rec, "content_hash", None),
            "equilibrium": result.get("equilibrium"),
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
