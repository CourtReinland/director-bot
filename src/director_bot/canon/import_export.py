"""Import/export Work bundles (JSON) between disk and CanonDB."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from director_bot.canon.db import CanonDB


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def import_work_bundle(
    db: CanonDB,
    bundle: dict[str, Any],
    *,
    replace_children: bool = True,
) -> int:
    """Import a full work: meta + scene_cards + shot_moments + digests.

    Bundle shape::

        {
          "work": { title, slug?, year?, directors?, genres?, tier?, ... },
          "scene_cards": [ { idx, slugline, what_happens, ... } ],
          "shot_moments": [ { idx, scene_idx?, scale, ... } ],
          "decision_digests": [ { situation, decision, scene_idx?, shot_idx?, ... } ]
        }
    """
    work_data = dict(bundle.get("work") or {})
    if not work_data.get("title") and not work_data.get("slug"):
        raise ValueError("bundle.work must include title or slug")
    if not work_data.get("slug"):
        work_data["slug"] = _slugify(work_data["title"])

    work_id = db.upsert_work(work_data)
    if replace_children:
        db.clear_work_children(work_id)

    card_id_by_idx: dict[int, int] = {}
    for card in bundle.get("scene_cards") or []:
        cid = db.add_scene_card(work_id, card)
        card_id_by_idx[int(card.get("idx", len(card_id_by_idx)))] = cid

    shot_id_by_idx: dict[int, int] = {}
    for shot in bundle.get("shot_moments") or []:
        scene_card_id: Optional[int] = None
        if "scene_card_id" in shot and shot["scene_card_id"] is not None:
            scene_card_id = int(shot["scene_card_id"])
        elif shot.get("scene_idx") is not None:
            scene_card_id = card_id_by_idx.get(int(shot["scene_idx"]))
        sid = db.add_shot_moment(work_id, shot, scene_card_id=scene_card_id)
        shot_id_by_idx[int(shot.get("idx", len(shot_id_by_idx)))] = sid

    for dig in bundle.get("decision_digests") or []:
        payload = dict(dig)
        payload["work_id"] = work_id
        if payload.get("scene_idx") is not None and not payload.get("scene_card_id"):
            payload["scene_card_id"] = card_id_by_idx.get(int(payload["scene_idx"]))
        if payload.get("shot_idx") is not None and not payload.get("shot_moment_id"):
            payload["shot_moment_id"] = shot_id_by_idx.get(int(payload["shot_idx"]))
        if not payload.get("director"):
            directors = work_data.get("directors") or []
            payload["director"] = directors[0] if directors else ""
        db.add_digest(payload)

    return work_id


def export_work_bundle(db: CanonDB, work_id: int) -> dict[str, Any]:
    work = db.get_work(work_id)
    if work is None:
        raise ValueError(f"no such work: {work_id}")
    cards = db.scene_cards_for_work(work_id)
    shots = db.shot_moments_for_work(work_id)
    digests = db.list_digests(work_id=work_id)
    # strip internal ids from nested export optional — keep them for round-trip
    return {
        "work": {k: v for k, v in work.items() if k != "id"},
        "scene_cards": cards,
        "shot_moments": shots,
        "decision_digests": digests,
    }


def load_bundle_file(path: Path | str) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bundle file must be a JSON object")
    return data


def save_bundle_file(bundle: dict[str, Any], path: Path | str) -> Path:
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str) + "\n",
                 encoding="utf-8")
    return p


def import_bundle_file(db: CanonDB, path: Path | str, **kwargs: Any) -> int:
    return import_work_bundle(db, load_bundle_file(path), **kwargs)
