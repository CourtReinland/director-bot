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
    scene_cards: Optional[list[dict[str, Any]]] = None,
    shot_list: Optional[list[dict[str, Any]]] = None,
    decision_ledger: Optional[list[dict[str, Any]]] = None,
    genre: str = "",
    logline: str = "",
    style_bible: str = "",
) -> dict[str, Any]:
    """STS-oriented handoff manifest (file-based; no STS source edits).

    v2 adds scene_cards, optional shot_list, and a decision_ledger slice so
    Script2Screen (or a human operator) can prefill wizard steps without
    re-deriving director intent.
    """
    return {
        "format": "director-bot/script2screen-handoff/v2",
        "title": title,
        "episode": episode,
        "genre": genre,
        "logline": logline,
        "fountain_path": fountain_path,
        "characters": list(characters or []),
        "style_ref": style_ref,
        "style_bible": style_bible,
        "aspect_ratio": aspect_ratio,
        "notes": notes,
        "director_decision_hash": decision_hash,
        "scene_cards": list(scene_cards or []),
        "shot_list": list(shot_list or []),
        "decision_ledger": list(decision_ledger or []),
        "wizard_hints": {
            "step_script": "Use fountain_path or paste fountain sibling.",
            "step_characters": "characters[] — name + optional visual_prompt.",
            "step_style": "style_ref / style_bible for global treatment.",
            "step_prompts": "shot_list[] action_text can seed still/motion prompts.",
        },
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
