"""Vertical-slice short pipeline."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.pipeline import run_short_pipeline


def test_short_pipeline(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    db = CanonDB(tmp_path / "t.db")
    result = run_short_pipeline(
        db,
        title="Pipeline Test",
        genre="thriller",
        logline="A detective and a silence.",
        situation="interrogation power without dialogue",
        style_refs=["David Fincher"],
        seed=True,
    )
    assert result["project_id"]
    assert result["chosen"]
    assert result["chain"]["ok"] is True
    assert result["handoffs"]["root"]
