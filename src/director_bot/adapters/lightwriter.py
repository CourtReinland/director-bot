"""Adapter: LightWriter cards / Fountain handoff (file-based, no repo edits)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def cards_from_lightwriter_export(data: dict[str, Any] | list) -> list[dict[str, Any]]:
    """Normalize a LightWriter card export into canon scene_card dicts.

    Accepts either:
      - list of card objects
      - { "cards": [...] } or { "scenes": [...] }
    """
    if isinstance(data, list):
        raw = data
    else:
        raw = data.get("cards") or data.get("scenes") or data.get("scene_cards") or []
    cards: list[dict[str, Any]] = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            continue
        cards.append({
            "idx": int(c.get("idx", c.get("index", i))),
            "slugline": str(c.get("slugline") or c.get("heading") or ""),
            "title": str(c.get("title") or c.get("name") or f"Card {i}"),
            "what_happens": str(
                c.get("what_happens") or c.get("summary") or c.get("body") or ""
            ),
            "relationship_delta": str(c.get("relationship_delta") or c.get("relationships") or ""),
            "plot_function": str(c.get("plot_function") or c.get("plot") or ""),
            "emotional_spine": str(c.get("emotional_spine") or c.get("emotion") or ""),
            "characters": list(c.get("characters") or []),
            "structural_beat": str(c.get("structural_beat") or c.get("beat") or ""),
            "act": c.get("act"),
            "page_estimate": c.get("page_estimate") or c.get("pages"),
            "tags": list(c.get("tags") or []),
            "meta": {"lightwriter": True, **(c.get("meta") or {})},
        })
    return cards


def load_lightwriter_cards(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path).expanduser().resolve()
    data = json.loads(p.read_text(encoding="utf-8"))
    return cards_from_lightwriter_export(data)


def fountain_handoff_package(
    *,
    title: str,
    fountain_text: str,
    cards: Optional[list[dict[str, Any]]] = None,
    cast: Optional[list[str]] = None,
    style_bible: str = "",
    decision_hashes: Optional[list[str]] = None,
    genre: str = "",
    logline: str = "",
    frameworks: Optional[list[str]] = None,
    decision_summaries: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Package for handoff into writing/production tools (v2)."""
    return {
        "format": "director-bot/lightwriter-handoff/v2",
        "title": title,
        "genre": genre,
        "logline": logline,
        "fountain": fountain_text,
        "scene_cards": list(cards or []),
        "cast_lock": list(cast or []),
        "style_bible": style_bible,
        "frameworks": list(frameworks or []),
        "decision_ledger_tip": (decision_hashes or [None])[-1] if decision_hashes else None,
        "decision_hashes": list(decision_hashes or []),
        "decision_summaries": list(decision_summaries or []),
        "import_hints": {
            "cards": "Import scene_cards into LightWriter Cards view.",
            "fountain": "Open sibling .fountain or paste fountain field.",
            "cast_lock": "Apply cast_lock so rewrites cannot invent names.",
        },
    }


def write_lightwriter_handoff(package: dict[str, Any], path: Path | str) -> Path:
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Also write .fountain sibling if present
    if package.get("fountain"):
        fp = p.with_suffix(".fountain")
        fp.write_text(str(package["fountain"]), encoding="utf-8")
    return p
