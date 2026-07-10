"""Embeddings: pure-Python hash vectors + optional OpenAI/xAI API providers.

Store contract is always `list[float]` in the embeddings table. Provider is
selected by DIRECTOR_BOT_EMBED_PROVIDER (hash|openai|xai|auto).
xAI does not currently document a public /v1/embeddings route; when
provider=xai we try it and fall back to hash on failure. OpenAI embeddings
are used when provider=openai or auto+OPENAI_API_KEY.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from typing import Iterable, Optional, Protocol, Sequence, runtime_checkable

DIM_HASH = 384
_TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _ngrams(tokens: Sequence[str], n: int = 2) -> Iterable[str]:
    for t in tokens:
        yield t
    if n >= 2:
        for i in range(len(tokens) - 1):
            yield f"{tokens[i]}_{tokens[i + 1]}"


def embed_hash(text: str, dim: int = DIM_HASH) -> list[float]:
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
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# Back-compat name used across the codebase.
def embed_text(text: str, dim: int = DIM_HASH) -> list[float]:
    return get_embedder().embed(text)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    # Allow different dims only via zero
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    if len(a) != len(b):
        # pad shorter with zeros conceptually by truncating to min
        aa, bb = a[:n], b[:n]
    else:
        aa, bb = a, b
    dot = sum(x * y for x, y in zip(aa, bb))
    na = math.sqrt(sum(x * x for x in aa)) or 1.0
    nb = math.sqrt(sum(y * y for y in bb)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def hybrid_score(fuzz_01: float, cosine_01: float,
                 w_fuzz: float = 0.45, w_vec: float = 0.55) -> float:
    cos_unit = (cosine_01 + 1.0) / 2.0
    return w_fuzz * float(fuzz_01) + w_vec * cos_unit


def l2_normalize(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(v) * float(v) for v in vec)) or 1.0
    return [float(v) / norm for v in vec]


@runtime_checkable
class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    name = "hash"
    dim = DIM_HASH

    def embed(self, text: str) -> list[float]:
        return embed_hash(text, self.dim)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class OpenAICompatEmbedder:
    """OpenAI-compatible POST /v1/embeddings (OpenAI or experimental xAI)."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        base_url: str,
        model: str,
        dim: int = 1536,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim
        self._fallback = HashEmbedder()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # empty strings → hash zeros
        clean = [t if (t or "").strip() else " " for t in texts]
        url = f"{self.base_url}/embeddings"
        body = {"model": self.model, "input": clean}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                json.JSONDecodeError) as exc:
            # Silent fall back for offline/tests; caller can inspect name.
            if os.environ.get("DIRECTOR_BOT_EMBED_STRICT", "").lower() in (
                "1", "true", "yes",
            ):
                raise RuntimeError(f"{self.name} embeddings failed: {exc}") from exc
            return self._fallback.embed_many(texts)

        items = payload.get("data") or []
        # sort by index if present
        items = sorted(items, key=lambda x: int(x.get("index", 0)))
        out: list[list[float]] = []
        for i, item in enumerate(items):
            vec = item.get("embedding") or []
            if not vec:
                out.append(self._fallback.embed(texts[i] if i < len(texts) else ""))
            else:
                out.append(l2_normalize(vec))
                self.dim = len(out[-1])
        while len(out) < len(texts):
            out.append(self._fallback.embed(texts[len(out)]))
        return out

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]


_EMBEDDER: Optional[Embedder] = None


def _select_provider() -> str:
    forced = os.environ.get("DIRECTOR_BOT_EMBED_PROVIDER", "").strip().lower()
    if forced in ("hash", "openai", "xai", "auto"):
        return forced
    return "auto"


def _auto_embed_provider() -> str:
    """Pick embedder when DIRECTOR_BOT_EMBED_PROVIDER is auto/unset.

    Dual-key policy (training-friendly retrieval):
    - OPENAI_API_KEY present → OpenAI embeddings (even if chat is xAI)
    - else XAI_API_KEY + DIRECTOR_BOT_EMBED_TRY_XAI=1 → experimental xAI
    - else hash (offline)

    This lets you run `DIRECTOR_BOT_PROVIDER=xai` for Grok chat while using
    OpenAI `text-embedding-3-small` for hybrid canon lookup.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("XAI_API_KEY"):
        prefer = os.environ.get("DIRECTOR_BOT_EMBED_TRY_XAI", "").lower()
        if prefer in ("1", "true", "yes"):
            return "xai"
    return "hash"


def get_embedder(provider: Optional[str] = None, *, force_reload: bool = False) -> Embedder:
    """Return process-wide embedder (cached)."""
    global _EMBEDDER
    if _EMBEDDER is not None and not force_reload and provider is None:
        return _EMBEDDER

    # ensure .env loaded
    try:
        from director_bot import envload  # noqa: F401
    except Exception:
        pass

    name = (provider or _select_provider()).lower()
    if name == "auto":
        name = _auto_embed_provider()

    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            emb: Embedder = HashEmbedder()
        else:
            emb = OpenAICompatEmbedder(
                name="openai",
                api_key=key,
                base_url=os.environ.get(
                    "OPENAI_BASE_URL", "https://api.openai.com/v1"
                ),
                model=os.environ.get(
                    "DIRECTOR_BOT_EMBED_MODEL", "text-embedding-3-small"
                ),
            )
    elif name == "xai":
        key = os.environ.get("XAI_API_KEY", "")
        if not key:
            emb = HashEmbedder()
        else:
            emb = OpenAICompatEmbedder(
                name="xai",
                api_key=key,
                base_url=os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1"),
                model=os.environ.get(
                    "DIRECTOR_BOT_EMBED_MODEL", "grok-embedding-small"
                ),
            )
    else:
        emb = HashEmbedder()

    if provider is None:
        _EMBEDDER = emb
    return emb


def reset_embedder() -> None:
    global _EMBEDDER
    _EMBEDDER = None
