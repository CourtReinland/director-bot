"""Decision engine end-to-end."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.contracts.schemas import ProjectPhase, SituationContext
from director_bot.decisions.engine import decide
from director_bot.decisions.ledger import verify_chain


def test_decide_offline(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Engine", genre="thriller")
    situation = SituationContext(
        phase=ProjectPhase.SHOTLIST,
        genre="thriller",
        summary="Two-hander interrogation; show power without dialogue; silence",
        style_refs=["David Fincher"],
    )
    result = decide(db, situation, project_id=pid, commit=True)
    assert result["chosen"].id
    assert result["decision"].content_hash
    assert verify_chain(db, pid)["ok"] is True
    # Should have retrieved something historical when possible
    sources = {c.style_source for c in result["candidates"]}
    assert any(s.startswith("historical") for s in sources) or "creative" in sources
