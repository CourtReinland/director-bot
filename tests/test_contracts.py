"""Schema helpers."""
from director_bot.contracts.schemas import (
    CandidateAction,
    CriteriaScores,
    DecisionRecord,
    SceneCard,
    content_hash,
)


def test_content_hash_stable():
    a = content_hash({"x": 1, "y": [2, 3]}, parent_hash="")
    b = content_hash({"y": [2, 3], "x": 1}, parent_hash="")
    assert a == b
    c = content_hash({"x": 1, "y": [2, 3]}, parent_hash="abc")
    assert c != a


def test_scene_card_blob():
    card = SceneCard(
        slugline="INT. ROOM - NIGHT",
        what_happens="A door closes.",
        characters=["MARA"],
    )
    blob = card.situation_blob()
    assert "INT. ROOM" in blob
    assert "MARA" in blob


def test_decision_payload():
    rec = DecisionRecord(
        phase="shotlist",
        situation="test",
        candidates=[CandidateAction(id="a", action="hold MCU",
                                    scores=CriteriaScores(emotion=0.9))],
        chosen_id="a",
        chosen_action="hold MCU",
        parent_hash="",
    )
    h = content_hash(rec.payload_for_hash(), "")
    assert len(h) == 64
