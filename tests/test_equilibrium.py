"""Multi-criteria equilibrium."""
from director_bot.contracts.schemas import CandidateAction, CriteriaScores
from director_bot.decisions.equilibrium import (
    blend_creativity,
    pick_equilibrium,
    score_candidate,
)


def test_score_and_pick():
    weak = CandidateAction(
        id="w",
        action="random whip pans",
        scores=CriteriaScores(
            genre_craft=0.2, style_match=0.2, continuity=0.2,
            originality=0.9, feasibility=0.3, emotion=0.2,
        ),
    )
    strong = CandidateAction(
        id="s",
        action="hold MCU on silence",
        scores=CriteriaScores(
            genre_craft=0.9, style_match=0.85, continuity=0.9,
            originality=0.4, feasibility=0.9, emotion=0.9,
        ),
    )
    chosen, report = pick_equilibrium([weak, strong], floor=0.25)
    assert chosen.id == "s"
    assert report["chosen_score"] == score_candidate(strong.scores)


def test_blend():
    h = CandidateAction(
        id="h", action="historical hold",
        scores=CriteriaScores(genre_craft=0.9, style_match=0.9, continuity=0.9,
                              originality=0.3, feasibility=0.9, emotion=0.8),
        evidence_ids=[1],
    )
    c = CandidateAction(
        id="c", action="creative orbit",
        scores=CriteriaScores(genre_craft=0.4, style_match=0.3, continuity=0.5,
                              originality=0.95, feasibility=0.6, emotion=0.7),
    )
    hybrid = blend_creativity(h, c, 0.4)
    assert hybrid.style_source.startswith("hybrid")
    assert 1 in hybrid.evidence_ids
