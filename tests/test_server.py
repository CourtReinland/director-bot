"""Dashboard API smoke tests."""
from pathlib import Path

import pytest

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from director_bot.server.app import create_app  # noqa: E402


def test_dashboard_api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    monkeypatch.setenv("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Dash", genre="thriller", logline="test")
    client = TestClient(create_app(db))
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["ok"] is True
    assert client.get("/api/works").status_code == 200
    assert client.get(f"/api/projects/{pid}").status_code == 200
    r = client.post("/api/decide", json={
        "summary": "interrogation silence reverse",
        "project_id": pid,
        "genre": "thriller",
        "phase": "shotlist",
    })
    assert r.status_code == 200
    assert r.json()["chosen_action"]
    assert client.get("/").status_code == 200
