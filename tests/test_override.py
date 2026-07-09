"""Human override ledger path."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.decisions.ledger import verify_chain
from director_bot.decisions.override import human_override


def test_human_override_mints_digest(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Override Film", genre="thriller")
    result = human_override(
        db,
        project_id=pid,
        action="Hold a dirty single on the detective's hands, not the face.",
        situation="Interrogation; face coverage feels on-the-nose.",
        rationale="Hands tell the lie.",
        mint_digest=True,
        director="Court",
        tags=["hands", "interrogation"],
    )
    assert result["decision"].content_hash
    assert result["digest_id"] is not None
    assert verify_chain(db, pid)["ok"] is True
    dig = db.get_digest(int(result["digest_id"]))
    assert "hands" in dig["decision"].lower() or "Hands" in dig["rationale"]
