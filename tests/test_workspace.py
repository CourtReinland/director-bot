"""Project workspace, series, handoffs."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.project.workspace import (
    cards_to_fountain_stub,
    create_series_with_episodes,
    export_project_handoffs,
    import_cards_file,
)


def test_series_and_export(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    result = create_series_with_episodes(
        db,
        "Night Desk",
        ["Pilot 1 — Pilot", "Episode 2 — The File"],
        genre="thriller",
        logline="A night-shift detective series.",
    )
    assert result["series_project_id"]
    assert len(result["episodes"]) == 2
    eps = db.episodes_for_series(result["series_project_id"])
    assert len(eps) == 2

    pid = result["episodes"][0]["project_id"]
    cards_path = tmp_path / "cards.json"
    cards_path.write_text(
        '{"cards":[{"title":"Open","slugline":"INT. DESK - NIGHT",'
        '"summary":"Phone rings.","characters":["DETECTIVE"]}]}',
        encoding="utf-8",
    )
    ids = import_cards_file(db, pid, cards_path)
    assert len(ids) == 1
    fountain = cards_to_fountain_stub("Pilot", db.project_cards(pid))
    assert "INT. DESK" in fountain
    paths = export_project_handoffs(db, pid, out_dir=tmp_path / "out")
    assert Path(paths["lightwriter"]).is_file()
    assert Path(paths["sts"]).is_file()


def test_curation_tier(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    works = db.list_works()
    wid = int(works[0]["id"])
    db.update_work(wid, tier="A", theme="patched theme")
    w = db.get_work(wid)
    assert w["tier"] == "A"
    assert w["theme"] == "patched theme"
    did = db.add_digest({
        "work_id": wid,
        "situation": "custom sit",
        "decision": "custom choice",
        "rationale": "because",
        "director": "X",
        "tags": ["custom"],
        "phase": "shotlist",
    })
    assert db.get_digest(did)["decision"] == "custom choice"
