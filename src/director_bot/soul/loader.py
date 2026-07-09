"""Load static soul markdown (hot-editable personality files)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from director_bot import config


@dataclass
class SoulBlueprint:
    name: str
    core: str
    taste: str = ""
    process_notes: str = ""
    files: dict[str, Path] = field(default_factory=dict)

    def system_preamble(self) -> str:
        parts = [f"# Soul: {self.name}", "", self.core.strip()]
        if self.taste.strip():
            parts += ["", "## Taste", self.taste.strip()]
        if self.process_notes.strip():
            parts += ["", "## Process", self.process_notes.strip()]
        return "\n".join(parts)


def _read(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def load_soul(
    soul_dir: Optional[Path | str] = None,
    name: str = "Director",
) -> SoulBlueprint:
    root = Path(soul_dir) if soul_dir else config.SOUL_STATIC_DIR
    core_p = root / "core.md"
    taste_p = root / "taste.md"
    process_p = root / "process_notes.md"
    core = _read(core_p)
    if not core.strip():
        core = (
            f"You are {name}, an embodied film director. "
            "You make decisive creative choices backed by craft evidence. "
            "You refuse to skip story structure for empty spectacle."
        )
    return SoulBlueprint(
        name=name,
        core=core,
        taste=_read(taste_p),
        process_notes=_read(process_p),
        files={"core": core_p, "taste": taste_p, "process_notes": process_p},
    )
