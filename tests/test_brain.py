"""Brain providers (mock path)."""
from director_bot.soul.brain import MockBrain, get_brain, score_candidates_with_brain


def test_mock_brain():
    b = MockBrain()
    out = b.complete("sys", "hello director")
    assert "mock director" in out.lower() or "Noted" in out


def test_get_brain_default_mock(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("DIRECTOR_BOT_PROVIDER", "mock")
    b = get_brain()
    assert b.name == "mock"


def test_score_candidates_mock_returns_empty():
    scored = score_candidates_with_brain(
        MockBrain(),
        "situation",
        [{"id": "a", "action": "hold", "style_source": "creative"}],
    )
    assert scored == []
