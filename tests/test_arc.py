"""Series arc / motif planner."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.project.arc import (
    add_motif,
    apply_plan_cards,
    arc_report,
    mark_payoff,
    plan_episode_spine,
    record_beat,
)
from director_bot.project.workspace import create_series_with_episodes


def test_arc_planner(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    db = CanonDB(tmp_path / "t.db")
    series = create_series_with_episodes(
        db, "Motif Show", ["Ep1", "Ep2", "Ep3"], genre="thriller",
    )
    sid = series["series_project_id"]
    mid = add_motif(
        db, sid, name="Closed File", kind="visual",
        description="Unopened dossier on the desk",
        first_episode=1, payoff_episode=3,
    )
    record_beat(db, mid, 1, "Plant: file appears in wide")
    record_beat(db, mid, 2, "Develop: hand hovers, does not open")
    plan = plan_episode_spine(db, sid, 3, logline_hint="The file opens.")
    assert plan["must_payoff"]
    assert plan["suggested_cards"]
    child = series["episodes"][2]["project_id"]
    ids = apply_plan_cards(db, child, plan)
    assert ids
    mark_payoff(db, mid, 3, notes="Opened in CU")
    rep = arc_report(db, sid)
    assert rep["stats"]["paid_off"] == 1
    assert rep["stats"]["open_loops"] == 0
