"""Adapter: Scripty pass rows → canon Work bundle.

Can ingest:
  1. A JSON file produced by `scripty export-canon`
  2. Live Scripty Database rows when scripty is importable / SCRIPTY_HOME set
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.canon.import_export import import_work_bundle


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def scripty_pass_to_bundle(
    *,
    project: dict[str, Any],
    pass_row: dict[str, Any],
    shots: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    dialogue: list[dict[str, Any]],
    tier: str = "UNRANKED",
    directors: Optional[list[str]] = None,
    genres: Optional[list[str]] = None,
    theme: str = "",
    logline: str = "",
    plot_summary: str = "",
) -> dict[str, Any]:
    """Convert Scripty projection rows into a canon import bundle."""
    title = str(project.get("name") or project.get("slug") or "untitled")
    slug = _slugify(str(project.get("slug") or title))
    pid = project.get("id")
    pass_id = pass_row.get("id")
    pass_num = pass_row.get("number")

    # Dialogue by shot_id
    dlg_by_shot: dict[Any, list[dict[str, str]]] = {}
    for line in dialogue:
        sid = line.get("shot_id")
        dlg_by_shot.setdefault(sid, []).append({
            "character": str(line.get("character") or ""),
            "text": str(line.get("text") or ""),
            "parenthetical": str(line.get("parenthetical") or ""),
        })

    scene_cards = []
    for sc in scenes:
        slugline = (
            f"{sc.get('int_ext', 'EXT.')} "
            f"{str(sc.get('location') or 'UNKNOWN').upper()} - "
            f"{sc.get('time_of_day', 'DAY')}"
        )
        chars: list[str] = []
        shot_ids = sc.get("shot_ids") or []
        for sh in shots:
            if sh.get("id") in shot_ids or sh.get("idx") in shot_ids:
                for c in sh.get("characters") or []:
                    name = c if isinstance(c, str) else str(c)
                    if name and name not in chars:
                        chars.append(name)
        scene_cards.append({
            "idx": int(sc.get("idx", 0)),
            "slugline": slugline,
            "title": str(sc.get("location") or f"Scene {sc.get('idx', 0)}"),
            "what_happens": str(sc.get("synopsis") or ""),
            "relationship_delta": "",
            "plot_function": "",
            "emotional_spine": "",
            "characters": chars,
            "structural_beat": "",
            "act": None,
            "tags": [],
            "meta": {"scripty_scene_id": sc.get("id")},
        })

    # Map shot → scene idx via scene shot_ids when possible
    shot_id_to_scene_idx: dict[Any, int] = {}
    for sc in scenes:
        idx = int(sc.get("idx", 0))
        for sid in sc.get("shot_ids") or []:
            shot_id_to_scene_idx[sid] = idx

    shot_moments = []
    digests = []
    for sh in shots:
        chars = sh.get("characters") or []
        char_names = [
            c if isinstance(c, str) else str(c.get("name", c))
            for c in chars
        ]
        scene_idx = shot_id_to_scene_idx.get(sh.get("id"))
        if scene_idx is None:
            # fallback: match location
            for sc in scenes:
                if sc.get("location") == sh.get("location"):
                    scene_idx = int(sc.get("idx", 0))
                    break
        moment = {
            "idx": int(sh.get("idx", 0)),
            "scene_idx": scene_idx,
            "start_s": float(sh.get("start_s", 0)),
            "end_s": float(sh.get("end_s", 0)),
            "scale": sh.get("scale") or "MS",
            "subject": sh.get("subject") or "",
            "angle": sh.get("angle") or "EYE LEVEL",
            "move": sh.get("move") or "STATIC",
            "int_ext": sh.get("int_ext") or "EXT.",
            "location": sh.get("location") or "",
            "time_of_day": sh.get("time_of_day") or "DAY",
            "action_text": sh.get("action_text") or "",
            "characters": char_names,
            "mood": sh.get("mood") or "",
            "dialogue": dlg_by_shot.get(sh.get("id"), []),
            "confidence": float(sh.get("confidence", 0.5)),
            "keyframes": sh.get("keyframes") or [],
            "meta": {"scripty_shot_id": sh.get("id")},
        }
        shot_moments.append(moment)

        # Auto-digest from labeled shot (human can refine later)
        digests.append({
            "shot_idx": int(sh.get("idx", 0)),
            "scene_idx": scene_idx,
            "situation": (
                f"{moment['int_ext']} {moment['location']} - {moment['time_of_day']}: "
                f"{moment['action_text'] or moment['subject']}"
            ),
            "decision": (
                f"Shot as {moment['scale']} {moment['subject']} "
                f"({moment['angle']}, {moment['move']})"
            ),
            "rationale": moment["mood"] or "Labeled by Scripty supervision pass.",
            "director": (directors or [""])[0] if directors else "",
            "tags": [moment["scale"], moment["move"]],
            "phase": "shotlist",
        })

    return {
        "work": {
            "slug": slug,
            "title": title,
            "year": None,
            "directors": list(directors or []),
            "genres": list(genres or []),
            "medium": "film",
            "tier": tier,
            "theme": theme,
            "logline": logline,
            "plot_summary": plot_summary,
            "source": f"scripty:project:{pid}:pass:{pass_id}:n{pass_num}",
            "meta": {
                "scripty_project_id": pid,
                "scripty_pass_id": pass_id,
                "video_path": project.get("video_path"),
            },
        },
        "scene_cards": scene_cards,
        "shot_moments": shot_moments,
        "decision_digests": digests,
    }


def import_scripty_bundle_file(
    db: CanonDB,
    path: Path | str,
    *,
    replace_children: bool = True,
) -> int:
    p = Path(path).expanduser().resolve()
    bundle = json.loads(p.read_text(encoding="utf-8"))
    if "work" not in bundle and "project" in bundle:
        # Raw export-canon envelope
        bundle = scripty_pass_to_bundle(
            project=bundle["project"],
            pass_row=bundle["pass"],
            shots=bundle.get("shots") or [],
            scenes=bundle.get("scenes") or [],
            dialogue=bundle.get("dialogue") or [],
            tier=bundle.get("tier") or "UNRANKED",
            directors=bundle.get("directors"),
            genres=bundle.get("genres"),
            theme=bundle.get("theme") or "",
            logline=bundle.get("logline") or "",
            plot_summary=bundle.get("plot_summary") or "",
        )
    return import_work_bundle(db, bundle, replace_children=replace_children)


def try_load_scripty_db(scripty_db_path: Optional[Path | str] = None):
    """Best-effort open of a Scripty Database. Returns None if unavailable."""
    try:
        from scripty.core.db import Database  # type: ignore
        from scripty.core import config as sconfig  # type: ignore
    except ImportError:
        return None
    path = Path(scripty_db_path) if scripty_db_path else sconfig.db_path()
    if not Path(path).is_file():
        return None
    return Database(path)


def export_from_live_scripty(
    scripty_db,
    project_id: int,
    pass_id: Optional[int] = None,
    **meta: Any,
) -> dict[str, Any]:
    """Pull rows from a live Scripty DB and build a canon bundle."""
    project = scripty_db.get_project(project_id)
    if project is None:
        raise ValueError(f"no scripty project {project_id}")
    if pass_id is None:
        # latest complete pass
        # Scripty may not expose list_passes — probe via SQL-ish helpers
        if hasattr(scripty_db, "passes_for_project"):
            passes = scripty_db.passes_for_project(project_id)
        else:
            # fallback: try increasing ids is not available — require pass_id
            raise ValueError("pass_id required when passes_for_project is unavailable")
        complete = [p for p in passes if p.get("status") == "complete"]
        if not complete:
            raise ValueError("no complete passes")
        pass_row = complete[-1]
        pass_id = int(pass_row["id"])
    else:
        pass_row = scripty_db.get_pass(pass_id)
        if pass_row is None:
            raise ValueError(f"no pass {pass_id}")

    shots = scripty_db.shots_for_pass(pass_id)
    scenes = scripty_db.scenes_for_pass(pass_id)
    dialogue = scripty_db.dialogue_for_pass(pass_id)
    return scripty_pass_to_bundle(
        project=project,
        pass_row=pass_row,
        shots=shots,
        scenes=scenes,
        dialogue=dialogue,
        **meta,
    )
