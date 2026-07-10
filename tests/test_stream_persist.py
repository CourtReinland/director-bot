"""SSE soul meet stream + durable SQLite brain traces."""
from pathlib import Path

import pytest

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.soul.brain import MockBrain, stream_text
from director_bot.soul.steps import DirectorMind
from director_bot.soul.trace import TracingBrain, get_trace_store


def test_mock_stream_chunks():
    b = MockBrain()
    chunks = list(b.stream("sys", "hello director cold open"))
    assert len(chunks) >= 2
    assert "".join(chunks) == b.complete("sys", "hello director cold open")


def test_tracing_stream_persists(tmp_path: Path):
    store = get_trace_store()
    store.clear()
    db = CanonDB(tmp_path / "t.db")
    store.bind_db(db)

    tb = TracingBrain(MockBrain(), store=store, default_kind="meet", project_id=1)
    parts = list(tb.stream("system soul", "user topic about silence"))
    assert parts
    full = "".join(parts)

    ring = store.list(n=5, prefer_db=False)
    assert ring and ring[0]["response"] == full
    assert ring[0]["meta"].get("streamed") is True

    rows = db.list_brain_traces(n=10)
    assert len(rows) >= 1
    assert rows[0]["system"] == "system soul"
    assert rows[0]["user"] == "user topic about silence"
    assert rows[0]["response"] == full
    assert rows[0]["persisted"] is True
    assert db.count_brain_traces() >= 1
    hit = db.get_brain_trace(rows[0]["id"])
    assert hit and hit["response"] == full

    store.bind_db(None)


def test_speak_about_stream_events(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    store = get_trace_store()
    store.clear()
    db = CanonDB(tmp_path / "t.db")
    store.bind_db(db)
    seed_demo_canon(db)
    pid = db.create_project("Stream", genre="thriller")
    mind = DirectorMind.create(db, project_id=pid)
    mind.perceive("setup")

    events = list(mind.speak_about_stream("pitch the cold open"))
    kinds = [e["event"] for e in events]
    assert kinds[0] == "meta"
    assert "token" in kinds
    assert kinds[-1] == "done"
    done = events[-1]["data"]
    assert done["system"]
    assert done["user"]
    assert done["response"]
    assert done["streamed"] is True

    assert store.count() >= 1
    store.bind_db(None)


def test_stream_text_fallback_complete():
    class OnlyComplete:
        name = "only"

        def complete(self, system, user):
            return "whole reply"

    chunks = list(stream_text(OnlyComplete(), "s", "u"))
    assert chunks == ["whole reply"]


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from director_bot.server.app import create_app  # noqa: E402


def test_sse_meet_stream_endpoint(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    monkeypatch.setenv("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
    get_trace_store().clear()
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("SSE", genre="thriller")
    client = TestClient(create_app(db))

    with client.stream(
        "POST",
        "/api/soul/meet/stream",
        json={"message": "what is the theme?", "project_id": pid},
    ) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())

    assert "event: meta" in body
    assert "event: token" in body
    assert "event: done" in body
    assert "mock director" in body.lower() or "Noted" in body

    traces = client.get("/api/brain/traces").json()
    assert traces["count"] >= 1
    assert traces["source"] == "sqlite"
    assert traces["traces"][0]["response"]

    # durable across new store list via same db
    tid = traces["traces"][0]["id"]
    one = client.get(f"/api/brain/traces/{tid}")
    assert one.status_code == 200
    assert one.json()["user"]

    health = client.get("/api/health").json()
    assert health["brain_traces"] >= 1
