"""Dashboard API smoke tests — health, model view, meet, decide."""
from pathlib import Path

import pytest

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.soul.trace import get_trace_store


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from director_bot.server.app import create_app  # noqa: E402


def test_dashboard_api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    monkeypatch.setenv("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
    get_trace_store().clear()
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Dash", genre="thriller", logline="test")
    client = TestClient(create_app(db))

    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["ok"] is True

    soul = client.get("/api/soul")
    assert soul.status_code == 200
    assert soul.json()["system_preamble"]

    assert client.get("/api/works").status_code == 200
    p = client.get(f"/api/projects/{pid}")
    assert p.status_code == 200
    assert "working_memory_text" in p.json()

    # Model view dry-run meet
    mv = client.post("/api/model-view/meet", json={
        "topic": "pitch me a cold open",
        "project_id": pid,
        "phase": "shotlist",
    })
    assert mv.status_code == 200
    body = mv.json()
    assert body["kind"] == "meet"
    assert "Working memory" in body["user"]
    assert body["live"] is False

    # Model view dry-run decide
    md = client.post("/api/model-view/decide", json={
        "summary": "interrogation silence reverse",
        "project_id": pid,
        "genre": "thriller",
        "phase": "shotlist",
    })
    assert md.status_code == 200
    assert md.json()["candidates"]
    assert md.json()["score_prompt"]["system"]

    r = client.post("/api/decide", json={
        "summary": "interrogation silence reverse",
        "project_id": pid,
        "genre": "thriller",
        "phase": "shotlist",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["chosen_action"]
    assert data["candidates"]
    assert data["model_view"]["score_prompt"]

    meet = client.post("/api/soul/meet", json={
        "message": "what is the theme of this short?",
        "project_id": pid,
    })
    assert meet.status_code == 200
    m = meet.json()
    assert m["system"]
    assert m["user"]
    assert m["response"]

    traces = client.get("/api/brain/traces")
    assert traces.status_code == 200
    assert traces.json()["count"] >= 1
    assert traces.json()["source"] == "sqlite"

    assert client.get("/").status_code == 200
    html = client.get("/").text
    assert "Model View" in html
    assert "Stream meet" in html
