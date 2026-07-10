"""Inline board cards + trace search filters + scaled corpus size."""
from pathlib import Path

import pytest

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import SEED_BUNDLES, seed_demo_canon
from director_bot.canon.seed_extra import EXTRA_BUNDLES
from director_bot.canon.seed_scale import SCALE_BUNDLES
from director_bot.soul.trace import get_trace_store


def test_corpus_scale_counts():
    total = len(SEED_BUNDLES) + len(EXTRA_BUNDLES) + len(SCALE_BUNDLES)
    digests = sum(
        len(b.get("decision_digests") or [])
        for b in SEED_BUNDLES + EXTRA_BUNDLES + SCALE_BUNDLES
    )
    assert total >= 50
    assert digests >= 50


def test_project_card_crud(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    pid = db.create_project("Cards", genre="drama")
    cid = db.add_project_card(pid, {
        "idx": 0,
        "slugline": "INT. ROOM - DAY",
        "title": "Open",
        "what_happens": "They enter.",
        "tags": ["enter"],
    })
    row = db.get_project_card(cid)
    assert row and row["title"] == "Open"
    updated = db.update_project_card(cid, title="Revised", what_happens="They pause.")
    assert updated["title"] == "Revised"
    assert db.delete_project_card(cid) is True
    assert db.get_project_card(cid) is None


def test_brain_trace_search(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    store = get_trace_store()
    store.clear()
    store.bind_db(db)
    store.record(
        kind="meet", system="soul core", user="pitch cold open silence",
        response="hold the reverse", brain="mock", project_id=1,
    )
    store.record(
        kind="score", system="scorer", user="situation cars",
        response="[]", brain="mock", project_id=2,
    )
    hits = db.list_brain_traces(q="silence", n=20)
    assert len(hits) == 1
    assert "silence" in hits[0]["user"]
    meets = db.list_brain_traces(kind="meet", n=20)
    assert all(h["kind"] == "meet" for h in meets)
    assert db.count_brain_traces(q="silence") == 1
    store.bind_db(None)


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from director_bot.server.app import create_app  # noqa: E402


def test_card_and_trace_api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    monkeypatch.setenv("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
    get_trace_store().clear()
    db = CanonDB(tmp_path / "t.db")
    # lighter seed for speed in API test
    from director_bot.canon.import_export import import_work_bundle
    from director_bot.canon.index import reindex
    import_work_bundle(db, SEED_BUNDLES[0], reindex_after=False)
    reindex(db)
    pid = db.create_project("API Board", genre="thriller")
    client = TestClient(create_app(db))

    r = client.post(f"/api/projects/{pid}/cards", json={
        "slugline": "INT. LAB - NIGHT",
        "title": "Lab",
        "what_happens": "Something glows.",
        "tags": ["lab"],
    })
    assert r.status_code == 200
    cid = r.json()["id"]
    p = client.patch(f"/api/cards/{cid}", json={"title": "Lab revised"})
    assert p.status_code == 200
    assert p.json()["title"] == "Lab revised"

    meet = client.post("/api/soul/meet", json={
        "message": "unique-search-token-xyz",
        "project_id": pid,
    })
    assert meet.status_code == 200
    tr = client.get("/api/brain/traces", params={"q": "unique-search-token-xyz"})
    assert tr.status_code == 200
    assert tr.json()["count"] >= 1

    d = client.delete(f"/api/cards/{cid}")
    assert d.status_code == 200
    assert d.json()["ok"] is True
