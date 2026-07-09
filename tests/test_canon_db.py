"""Canon DB + seed + lookup."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.import_export import export_work_bundle, import_work_bundle
from director_bot.canon.query import lookup_digests, lookup_moments
from director_bot.canon.seed import seed_demo_canon


def test_seed_and_list(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    ids = seed_demo_canon(db)
    assert len(ids) == 2
    works = db.list_works(tier="S")
    assert len(works) == 2
    assert db.scene_cards_for_work(ids[0])
    assert db.shot_moments_for_work(ids[0])
    assert db.list_digests(work_id=ids[0])


def test_import_export_roundtrip(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    wid = import_work_bundle(db, {
        "work": {
            "slug": "rt-test",
            "title": "Roundtrip",
            "tier": "A",
            "directors": ["X"],
            "genres": ["drama"],
        },
        "scene_cards": [{"idx": 0, "slugline": "EXT. ROAD - DAY",
                         "what_happens": "A car passes."}],
        "shot_moments": [{"idx": 0, "scene_idx": 0, "scale": "WS",
                          "subject": "ROAD", "action_text": "Car passes."}],
        "decision_digests": [{
            "shot_idx": 0, "scene_idx": 0,
            "situation": "establishing road",
            "decision": "wide static",
            "rationale": "geography first",
        }],
    })
    bundle = export_work_bundle(db, wid)
    assert bundle["work"]["title"] == "Roundtrip"
    assert len(bundle["scene_cards"]) == 1
    assert len(bundle["shot_moments"]) == 1
    assert len(bundle["decision_digests"]) == 1


def test_lookup_digests(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    hits = lookup_digests(
        db,
        "interrogation silence withhold reverse angle power",
        k=3,
    )
    assert hits
    assert hits[0]["score"] > 0.15
    # Fincher digest should rank for interrogation query
    top_text = (hits[0].get("decision") or "") + (hits[0].get("situation") or "")
    assert any(
        w in top_text.lower()
        for w in ("reverse", "mcu", "silence", "suspect", "push")
    )


def test_lookup_moments(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    hits = lookup_moments(db, "doorway farewell hotel corridor dawn", k=3, tier="S")
    assert hits
