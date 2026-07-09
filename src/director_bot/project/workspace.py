"""Project workspace: scene cards, series episodes, handoff packages."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from director_bot.adapters.lightwriter import (
    cards_from_lightwriter_export,
    fountain_handoff_package,
    write_lightwriter_handoff,
)
from director_bot.adapters.script2screen import (
    build_sts_manifest_stub,
    write_sts_handoff,
)
from director_bot.canon.db import CanonDB
from director_bot import config


def import_cards_file(
    db: CanonDB,
    project_id: int,
    path: Path | str,
    *,
    replace: bool = True,
) -> list[int]:
    p = Path(path).expanduser().resolve()
    data = json.loads(p.read_text(encoding="utf-8"))
    cards = cards_from_lightwriter_export(data)
    if replace:
        return db.replace_project_cards(project_id, cards)
    return [db.add_project_card(project_id, c) for c in cards]


def cards_to_fountain_stub(
    title: str,
    cards: list[dict[str, Any]],
    logline: str = "",
) -> str:
    """Deterministic Fountain sketch from scene cards (board → pages seed)."""
    lines = [f"Title: {title}", "Credit: Written by", "Author: Director-bot", ""]
    if logline:
        lines += ["=", logline, "", ""]
    for c in sorted(cards, key=lambda x: int(x.get("idx", 0))):
        slug = (c.get("slugline") or "EXT. UNKNOWN - DAY").strip()
        if not slug.startswith(("INT", "EXT", ".")):
            slug = f".{slug}" if slug.startswith(".") else slug
        lines.append(slug)
        lines.append("")
        body = c.get("what_happens") or c.get("title") or ""
        if body:
            lines.append(str(body))
            lines.append("")
        chars = c.get("characters") or []
        if chars and c.get("emotional_spine"):
            # optional placeholder line for first character
            name = str(chars[0]).upper()
            lines.append(name)
            lines.append(f"({c.get('emotional_spine')})")
            lines.append("...")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_project_handoffs(
    db: CanonDB,
    project_id: int,
    *,
    out_dir: Optional[Path | str] = None,
) -> dict[str, str]:
    """Write LightWriter + STS handoff packages for a project."""
    proj = db.get_project(project_id)
    if proj is None:
        raise ValueError(f"no project {project_id}")
    cards = db.project_cards(project_id)
    decisions = db.decisions_for_project(project_id)
    hashes = [str(d.get("content_hash") or "") for d in decisions if d.get("content_hash")]
    tip = hashes[-1] if hashes else ""

    title = str(proj.get("title") or proj.get("slug") or "untitled")
    fountain = cards_to_fountain_stub(title, cards, logline=str(proj.get("logline") or ""))
    cast: list[str] = []
    for c in cards:
        for name in c.get("characters") or []:
            n = str(name).upper()
            if n and n not in cast:
                cast.append(n)

    root = Path(out_dir) if out_dir else config.project_dir(str(proj.get("slug")))
    root.mkdir(parents=True, exist_ok=True)

    decision_summaries = [
        {
            "id": d.get("id"),
            "phase": d.get("phase"),
            "action": d.get("chosen_action"),
            "method": d.get("equilibrium_method"),
            "hash": d.get("content_hash"),
        }
        for d in decisions
    ]
    # Lightweight shot list from decision actions (director intent → STS prompts)
    shot_list = [
        {
            "idx": i,
            "action_text": str(d.get("chosen_action") or ""),
            "phase": d.get("phase"),
            "hash": d.get("content_hash"),
        }
        for i, d in enumerate(decisions)
        if d.get("chosen_action")
    ]

    lw = fountain_handoff_package(
        title=title,
        fountain_text=fountain,
        cards=cards,
        cast=cast,
        style_bible=str((proj.get("markers") or {}).get("style_bible") or ""),
        decision_hashes=hashes,
        genre=str(proj.get("genre") or ""),
        logline=str(proj.get("logline") or ""),
        frameworks=list((proj.get("markers") or {}).get("frameworks") or []),
        decision_summaries=decision_summaries,
    )
    lw_path = write_lightwriter_handoff(lw, root / "lightwriter_handoff.json")

    man = build_sts_manifest_stub(
        title=title,
        episode=str((proj.get("markers") or {}).get("episode") or "Ep1"),
        characters=[{"name": n, "visual_prompt": ""} for n in cast],
        style_ref=str((proj.get("markers") or {}).get("style_ref") or ""),
        notes=str(proj.get("logline") or ""),
        decision_hash=tip,
        scene_cards=cards,
        shot_list=shot_list,
        decision_ledger=decision_summaries,
        genre=str(proj.get("genre") or ""),
        logline=str(proj.get("logline") or ""),
        style_bible=str((proj.get("markers") or {}).get("style_bible") or ""),
    )
    sts_path = write_sts_handoff(man, root / "sts", fountain_text=fountain)

    # also dump cards json
    cards_path = root / "scene_cards.json"
    cards_path.write_text(
        json.dumps({"cards": cards}, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "lightwriter": str(lw_path),
        "sts": str(sts_path),
        "cards": str(cards_path),
        "root": str(root),
    }


def create_series_with_episodes(
    db: CanonDB,
    series_title: str,
    episode_titles: list[str],
    *,
    genre: str = "",
    logline: str = "",
) -> dict[str, Any]:
    """Create a series project + child episode projects + episode rows."""
    series_id = db.create_project(
        series_title,
        genre=genre,
        logline=logline,
        medium="series",
    )
    series = db.get_project(series_id)
    series_slug = str(series.get("slug") if series else series_title)
    db.update_project(series_id, phase="series_arc", series_slug=series_slug)

    episode_ids: list[dict[str, Any]] = []
    for i, etitle in enumerate(episode_titles, start=1):
        child_id = db.create_project(
            etitle,
            genre=genre,
            logline="",
            medium="episode",
            series_slug=series_slug,
        )
        db.update_project(
            child_id,
            markers={"episode": f"Ep{i}", "series_project_id": series_id},
        )
        eid = db.add_episode(
            series_id, i, title=etitle, child_project_id=child_id,
            arc_notes="",
        )
        episode_ids.append({
            "episode_row_id": eid,
            "number": i,
            "project_id": child_id,
            "title": etitle,
        })
    return {
        "series_project_id": series_id,
        "series_slug": series_slug,
        "episodes": episode_ids,
    }
