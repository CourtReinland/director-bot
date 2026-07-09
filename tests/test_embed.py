"""Hashed embeddings + hybrid score + provider selection."""
from director_bot.canon.embed import (
    HashEmbedder,
    cosine,
    embed_hash,
    get_embedder,
    hybrid_score,
    reset_embedder,
)


def test_embed_similarity():
    a = embed_hash("interrogation silence withhold reverse angle MCU")
    b = embed_hash("silent suspect MCU reverse angle withheld")
    c = embed_hash("slapstick banana peel pie fight comedy")
    assert cosine(a, b) > cosine(a, c)
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6 or all(x == 0 for x in a)


def test_hybrid_range():
    s = hybrid_score(0.8, 0.5)
    assert 0.0 <= s <= 1.0


def test_force_hash_embedder(monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
    reset_embedder()
    emb = get_embedder(force_reload=True)
    assert isinstance(emb, HashEmbedder)
    assert emb.name == "hash"
    reset_embedder()
