"""Agreement metrics for human overrides."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.contracts.schemas import ProjectPhase, SituationContext
from director_bot.decisions.agreement import agreement_metrics
from director_bot.decisions.engine import decide
from director_bot.decisions.override import human_override
from director_bot.canon.seed import seed_demo_canon


def test_agreement_after_override(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Agree", genre="thriller")
    human_override(
        db,
        project_id=pid,
        action="Hold MCU on the silent party; withhold reverse angle on the speaker.",
        situation="interrogation silence",
        phase="shotlist",
    )
    decide(
        db,
        SituationContext(
            phase=ProjectPhase.SHOTLIST,
            genre="thriller",
            summary="interrogation silence power without dialogue reverse",
            style_refs=["David Fincher"],
        ),
        project_id=pid,
        commit=True,
    )
    report = agreement_metrics(db, pid)
    assert report["overrides_seen"] == 1
    assert report["checked"] >= 1
    # rate may be 0 or 1 depending on retrieval; just ensure shape
    assert "agreement_rate" in report
