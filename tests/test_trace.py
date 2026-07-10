"""Model-view assembly + brain trace ring."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.soul.brain import MockBrain, get_brain
from director_bot.soul.steps import DirectorMind
from director_bot.soul.trace import (
    TracingBrain,
    get_trace_store,
    preview_decide,
    preview_meet,
)


def test_tracing_brain_records(monkeypatch):
    store = get_trace_store()
    store.clear()
    tb = TracingBrain(MockBrain(), store=store, default_kind="meet")
    out = tb.complete("sys hello", "user world")
    assert "mock" in out.lower() or "Noted" in out
    traces = store.list(n=5)
    assert len(traces) >= 1
    assert traces[0]["system"] == "sys hello"
    assert traces[0]["user"] == "user world"
    assert traces[0]["kind"] == "meet"
    assert traces[0]["response"]


def test_get_brain_is_traced(monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    b = get_brain()
    assert b.name == "mock"
    assert isinstance(b, TracingBrain) or hasattr(b, "with_context")


def test_preview_meet(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Trace", genre="thriller")
    mind = DirectorMind.create(db, project_id=pid)
    mind.perceive("setup note")
    mind.persist_memory()
    view = preview_meet(db, topic="pitch the cold open", project_id=pid)
    assert view["kind"] == "meet"
    assert view["live"] is False
    assert "Director" in view["system"] or "director" in view["system"].lower()
    assert "Working memory" in view["user"]
    assert "pitch the cold open" in view["user"]
    assert view["stats"]["total_chars"] > 0


def test_preview_decide(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    view = preview_decide(
        db,
        summary="interrogation silence reverse power",
        genre="thriller",
        phase="shotlist",
    )
    assert view["kind"] == "decide"
    assert view["situation_blob"]
    assert view["candidates"]
    assert view["score_prompt"]["system"]
    assert view["score_prompt"]["will_send"] is False  # mock
    assert view["retrieval"]["digests"] is not None


def test_speak_about_traced(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    get_trace_store().clear()
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Meet", genre="thriller")
    mind = DirectorMind.create(db, project_id=pid)
    view = mind.speak_about_traced("what is the theme?")
    assert view["live"] is True
    assert view["system"]
    assert view["user"]
    assert view["response"]
    assert get_trace_store().list(n=1)[0]["kind"] == "meet"
