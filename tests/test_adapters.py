"""Tool adapters (file-based)."""
from pathlib import Path

from director_bot.adapters.lightwriter import (
    cards_from_lightwriter_export,
    fountain_handoff_package,
    write_lightwriter_handoff,
)
from director_bot.adapters.script2screen import build_sts_manifest_stub, write_sts_handoff
from director_bot.adapters.scripty import scripty_pass_to_bundle
from director_bot.canon.db import CanonDB
from director_bot.canon.import_export import import_work_bundle


def test_scripty_pass_to_bundle_import(tmp_path: Path):
    bundle = scripty_pass_to_bundle(
        project={"id": 1, "name": "Wooded Road", "slug": "wooded-road",
                 "video_path": "/tmp/x.mp4"},
        pass_row={"id": 2, "number": 1},
        shots=[{
            "id": 10, "idx": 0, "start_s": 0, "end_s": 3,
            "scale": "MS", "subject": "CAMP FIRE", "angle": "EYE LEVEL",
            "move": "STATIC", "int_ext": "EXT.", "location": "WOODED ROAD",
            "time_of_day": "NIGHT", "action_text": "Fire burns.",
            "characters": ["MARA"], "mood": "cold", "keyframes": [],
            "confidence": 0.8,
        }],
        scenes=[{
            "id": 1, "idx": 0, "int_ext": "EXT.", "location": "WOODED ROAD",
            "time_of_day": "NIGHT", "shot_ids": [10], "synopsis": "Night road.",
        }],
        dialogue=[{
            "shot_id": 10, "character": "MARA", "text": "Don't.",
            "parenthetical": "",
        }],
        tier="S",
        directors=["Test Director"],
        genres=["thriller"],
    )
    assert bundle["work"]["slug"] == "wooded-road"
    assert bundle["shot_moments"][0]["dialogue"][0]["text"] == "Don't."
    db = CanonDB(tmp_path / "t.db")
    wid = import_work_bundle(db, bundle)
    assert db.get_work(wid)["tier"] == "S"


def test_lightwriter_cards():
    cards = cards_from_lightwriter_export({
        "cards": [
            {"title": "Open", "slugline": "EXT. BEACH - DAY",
             "summary": "Waves crash.", "characters": ["A"]},
        ]
    })
    assert cards[0]["what_happens"] == "Waves crash."


def test_handoffs(tmp_path: Path):
    pkg = fountain_handoff_package(
        title="T",
        fountain_text="Title: T\n\nEXT. ROAD - DAY\n\nA car.\n",
        cards=[{"idx": 0, "slugline": "EXT. ROAD - DAY"}],
        cast=["DRIVER"],
    )
    p = write_lightwriter_handoff(pkg, tmp_path / "handoff.json")
    assert p.is_file()
    assert p.with_suffix(".fountain").is_file()

    man = build_sts_manifest_stub(title="T", episode="Ep1", decision_hash="abc")
    mp = write_sts_handoff(man, tmp_path / "sts", fountain_text="Title: T\n")
    assert mp.is_file()
