"""Adapter: Script2Screen handoff package (file-based, no repo edits)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def build_sts_manifest_stub(
    *,
    title: str,
    episode: str = "Ep1",
    fountain_path: Optional[str] = None,
    characters: Optional[list[dict[str, Any]]] = None,
    style_ref: str = "",
    aspect_ratio: str = "widescreen_16_9",
    notes: str = "",
    decision_hash: str = "",
) -> dict[str, Any]:
    """Minimal STS-oriented manifest the director can emit for later import.

    Script2Screen's full schema may evolve; this stub matches the spirit of
    LightWriter's STS handoff docs without coupling to STS internals.
    """
    return {
        "format": "director-bot/script2screen-handoff/v1",
        "title": title,
        "episode": episode,
        "fountain_path": fountain_path,
        "characters": list(characters or []),
        "style_ref": style_ref,
        "aspect_ratio": aspect_ratio,
        "notes": notes,
        "director_decision_hash": decision_hash,
        "provider_hints": {
            "image": None,
            "video": None,
            "voice": None,
        },
    }


def write_sts_handoff(
    manifest: dict[str, Any],
    out_dir: Path | str,
    *,
    fountain_text: Optional[str] = None,
) -> Path:
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if fountain_text is not None:
        fp = root / "screenplay.fountain"
        fp.write_text(fountain_text, encoding="utf-8")
        manifest = {**manifest, "fountain_path": str(fp)}
    mp = root / "sts_handoff.json"
    mp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return mp
