"""Merkle decision ledger."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.contracts.schemas import CandidateAction, CriteriaScores
from director_bot.decisions.ledger import commit_decision, verify_chain


def _cand(i: str, action: str) -> CandidateAction:
    return CandidateAction(
        id=i,
        action=action,
        style_source="historical:Test",
        scores=CriteriaScores(
            genre_craft=0.8, style_match=0.7, continuity=0.8,
            originality=0.5, feasibility=0.9, emotion=0.75,
        ),
        evidence_ids=[1],
    )


def test_commit_and_verify(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    pid = db.create_project("Chain Test", genre="thriller")
    c1 = _cand("a", "Hold MCU on silence")
    c2 = _cand("b", "Wide master only")
    r1 = commit_decision(
        db, project_id=pid, phase="shotlist", situation="interrogation",
        candidates=[c1, c2], chosen=c1,
    )
    assert r1.content_hash
    assert r1.parent_hash == ""

    c3 = _cand("c", "Push in on eyes")
    r2 = commit_decision(
        db, project_id=pid, phase="shotlist", situation="accusation",
        candidates=[c3], chosen=c3,
    )
    assert r2.parent_hash == r1.content_hash

    report = verify_chain(db, pid)
    assert report["ok"] is True
    assert report["length"] == 2
