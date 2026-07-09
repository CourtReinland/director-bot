"""Hashed embeddings + hybrid score."""
from director_bot.canon.embed import cosine, embed_text, hybrid_score


def test_embed_similarity():
    a = embed_text("interrogation silence withhold reverse angle MCU")
    b = embed_text("silent suspect MCU reverse angle withheld")
    c = embed_text("slapstick banana peel pie fight comedy")
    assert cosine(a, b) > cosine(a, c)
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6 or all(x == 0 for x in a)


def test_hybrid_range():
    s = hybrid_score(0.8, 0.5)
    assert 0.0 <= s <= 1.0
