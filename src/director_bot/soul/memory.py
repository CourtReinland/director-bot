"""Append-only WorkingMemory (OpenSouls-inspired)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class MemoryEntry:
    kind: str                      # observation | decision | note | perception | speech
    content: str
    ts: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "content": self.content,
            "ts": self.ts,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        return cls(
            kind=str(data.get("kind", "note")),
            content=str(data.get("content", "")),
            ts=str(data.get("ts", "")),
            meta=dict(data.get("meta") or {}),
        )


@dataclass
class WorkingMemory:
    """Immutable-style collection: mutations return a new instance conceptually,
    but we also support in-place append for performance with an export snapshot.
    """
    entries: list[MemoryEntry] = field(default_factory=list)

    def append(self, kind: str, content: str,
               meta: Optional[dict[str, Any]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            kind=kind, content=content, ts=_now(), meta=dict(meta or {})
        )
        self.entries.append(entry)
        return entry

    def extend(self, items: Iterable[MemoryEntry]) -> None:
        self.entries.extend(items)

    def of_kind(self, kind: str) -> list[MemoryEntry]:
        return [e for e in self.entries if e.kind == kind]

    def recent(self, n: int = 12) -> list[MemoryEntry]:
        return self.entries[-n:]

    def format_for_prompt(self, n: int = 16) -> str:
        rows = self.recent(n)
        if not rows:
            return "(working memory empty)"
        lines = []
        for e in rows:
            lines.append(f"[{e.kind} @ {e.ts}] {e.content}")
        return "\n".join(lines)

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.entries]

    @classmethod
    def from_list(cls, data: list[dict[str, Any]] | None) -> WorkingMemory:
        wm = cls()
        for item in data or []:
            if isinstance(item, dict):
                wm.entries.append(MemoryEntry.from_dict(item))
        return wm
