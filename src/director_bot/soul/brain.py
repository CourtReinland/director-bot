"""Text brain protocol + mock twin (Scripty-style offline seam)."""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class TextBrain(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class MockBrain:
    """Deterministic offline brain — echoes intent, no network."""

    name = "mock"

    def complete(self, system: str, user: str) -> str:
        # Pull a short directive from the user message for chat demos.
        line = user.strip().splitlines()[0] if user.strip() else "..."
        if len(line) > 200:
            line = line[:200] + "…"
        return (
            f"[mock director] Noted. Phase discipline holds. "
            f"Regarding: {line} — protect theme, cut on emotion, "
            f"justify with canon before novelty."
        )


def get_brain(provider: Optional[str] = None) -> TextBrain:
    from director_bot import config

    name = (provider or config.default_provider()).lower()
    if name == "mock":
        return MockBrain()
    # Real providers can be wired later without changing call sites.
    # Fall back to mock so the monorepo stays offline-first.
    return MockBrain()
