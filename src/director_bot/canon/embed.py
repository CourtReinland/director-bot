"""Pure-Python bag-of-hashed-ngrams embeddings (no torch / no network).

Stable offline vectors for hybrid retrieval. Swap later for real embedding
APIs without changing the storage contract (list[float] JSON columns).
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Sequence

DIM = 384
_TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _ngrams(tokens: Sequence[str], n: int = 2) -> Iterable[str]:
    for t in tokens:
        yield t
    if n >= 2:
        for i in range(len(tokens) - 1):
            yield f"{tokens[i]}_{tokens[i + 1]}"


def embed_text(text: str, dim: int = DIM) -> list[float]:
    """Hashing trick embedding, L2-normalized. Empty text → zero vector."""
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim
    vec = [0.0] * dim
    for gram in _ngrams(tokens):
        h = hash(gram)
        idx = h % dim
        sign = 1.0 if (h & 1) == 0 else -1.0
        vec[idx] += sign
    # mild TF dampening
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    # already unit-ish, but re-normalize for safety
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def hybrid_score(fuzz_01: float, cosine_01: float,
                 w_fuzz: float = 0.45, w_vec: float = 0.55) -> float:
    """Combine rapidfuzz (0..1) with cosine mapped to 0..1."""
    cos_unit = (cosine_01 + 1.0) / 2.0  # -1..1 → 0..1
    return w_fuzz * float(fuzz_01) + w_vec * cos_unit
