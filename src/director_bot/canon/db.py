"""SQLite persistence for canon + project state + merkle decision ledger.

One database at $DIRECTOR_BOT_HOME/director.db. JSON columns are
transparently encoded/decoded. Append-only `events` + `decisions` tables
provide audit trails.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    year INTEGER,
    directors TEXT NOT NULL DEFAULT '[]',
    genres TEXT NOT NULL DEFAULT '[]',
    medium TEXT NOT NULL DEFAULT 'film',
    tier TEXT NOT NULL DEFAULT 'UNRANKED',
    theme TEXT NOT NULL DEFAULT '',
    logline TEXT NOT NULL DEFAULT '',
    plot_summary TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scene_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id),
    idx INTEGER NOT NULL,
    slugline TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    what_happens TEXT NOT NULL DEFAULT '',
    relationship_delta TEXT NOT NULL DEFAULT '',
    plot_function TEXT NOT NULL DEFAULT '',
    emotional_spine TEXT NOT NULL DEFAULT '',
    characters TEXT NOT NULL DEFAULT '[]',
    structural_beat TEXT NOT NULL DEFAULT '',
    act INTEGER,
    page_estimate REAL,
    tags TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS shot_moments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id),
    scene_card_id INTEGER REFERENCES scene_cards(id),
    idx INTEGER NOT NULL,
    start_s REAL NOT NULL DEFAULT 0,
    end_s REAL NOT NULL DEFAULT 0,
    scale TEXT NOT NULL DEFAULT 'MS',
    subject TEXT NOT NULL DEFAULT '',
    angle TEXT NOT NULL DEFAULT 'EYE LEVEL',
    move TEXT NOT NULL DEFAULT 'STATIC',
    int_ext TEXT NOT NULL DEFAULT 'EXT.',
    location TEXT NOT NULL DEFAULT '',
    time_of_day TEXT NOT NULL DEFAULT 'DAY',
    action_text TEXT NOT NULL DEFAULT '',
    characters TEXT NOT NULL DEFAULT '[]',
    mood TEXT NOT NULL DEFAULT '',
    dialogue TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5,
    keyframes TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS decision_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    scene_card_id INTEGER REFERENCES scene_cards(id),
    shot_moment_id INTEGER REFERENCES shot_moments(id),
    situation TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    director TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    phase TEXT NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'intake',
    genre TEXT NOT NULL DEFAULT '',
    logline TEXT NOT NULL DEFAULT '',
    medium TEXT NOT NULL DEFAULT 'film',
    series_slug TEXT NOT NULL DEFAULT '',
    markers TEXT NOT NULL DEFAULT '{}',
    working_memory TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    phase TEXT NOT NULL DEFAULT '',
    situation TEXT NOT NULL DEFAULT '',
    candidates TEXT NOT NULL DEFAULT '[]',
    chosen_id TEXT NOT NULL DEFAULT '',
    chosen_action TEXT NOT NULL DEFAULT '',
    equilibrium_method TEXT NOT NULL DEFAULT 'weighted_pareto',
    creativity_alpha REAL NOT NULL DEFAULT 0.25,
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    scores TEXT NOT NULL DEFAULT '{}',
    parent_hash TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    text_blob TEXT NOT NULL DEFAULT '',
    vector TEXT NOT NULL DEFAULT '[]',
    dim INTEGER NOT NULL DEFAULT 384,
    updated_at TEXT NOT NULL,
    UNIQUE(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS project_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    idx INTEGER NOT NULL,
    slugline TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    what_happens TEXT NOT NULL DEFAULT '',
    relationship_delta TEXT NOT NULL DEFAULT '',
    plot_function TEXT NOT NULL DEFAULT '',
    emotional_spine TEXT NOT NULL DEFAULT '',
    characters TEXT NOT NULL DEFAULT '[]',
    structural_beat TEXT NOT NULL DEFAULT '',
    act INTEGER,
    page_estimate REAL,
    tags TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_project_id INTEGER NOT NULL REFERENCES projects(id),
    number INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    logline TEXT NOT NULL DEFAULT '',
    child_project_id INTEGER REFERENCES projects(id),
    arc_notes TEXT NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '{}',
    UNIQUE(series_project_id, number)
);

CREATE TABLE IF NOT EXISTS motifs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_project_id INTEGER NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'visual',
    description TEXT NOT NULL DEFAULT '',
    first_episode INTEGER,
    payoff_episode INTEGER,
    status TEXT NOT NULL DEFAULT 'planted',
    tags TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS motif_beats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motif_id INTEGER NOT NULL REFERENCES motifs(id),
    episode_number INTEGER NOT NULL,
    beat TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_scene_cards_work ON scene_cards(work_id, idx);
CREATE INDEX IF NOT EXISTS idx_shot_moments_work ON shot_moments(work_id, idx);
CREATE INDEX IF NOT EXISTS idx_shot_moments_scene ON shot_moments(scene_card_id);
CREATE INDEX IF NOT EXISTS idx_digests_work ON decision_digests(work_id);
CREATE INDEX IF NOT EXISTS idx_works_tier ON works(tier);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id, id);
CREATE INDEX IF NOT EXISTS idx_embeddings_type ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_project_cards ON project_cards(project_id, idx);
CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_project_id, number);
CREATE INDEX IF NOT EXISTS idx_motifs_series ON motifs(series_project_id);
CREATE INDEX IF NOT EXISTS idx_motif_beats ON motif_beats(motif_id, episode_number);
"""

_JSON_COLS = {
    "works": {"directors", "genres", "meta"},
    "scene_cards": {"characters", "tags", "meta"},
    "shot_moments": {"characters", "dialogue", "keyframes", "meta"},
    "decision_digests": {"tags", "meta"},
    "projects": {"markers", "working_memory"},
    "decisions": {"candidates", "evidence_ids", "scores"},
    "events": {"payload"},
    "embeddings": {"vector"},
    "project_cards": {"characters", "tags", "meta"},
    "episodes": {"meta"},
    "motifs": {"tags", "meta"},
    "motif_beats": {"meta"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


class CanonDB:
    """Thread-safe SQLite wrapper for canon + project + decision ledger."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after v0.1 without breaking old DBs."""
        cols = {
            r[1]
            for r in self._conn.execute("PRAGMA table_info(projects)").fetchall()
        }
        if "medium" not in cols:
            self._conn.execute(
                "ALTER TABLE projects ADD COLUMN medium TEXT NOT NULL DEFAULT 'film'"
            )
        if "series_slug" not in cols:
            self._conn.execute(
                "ALTER TABLE projects ADD COLUMN series_slug TEXT NOT NULL DEFAULT ''"
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- encoding ------------------------------------------------------------ #

    def _encode(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        cols = _JSON_COLS.get(table, set())
        out = dict(row)
        for k in cols:
            if k in out and not isinstance(out[k], str):
                out[k] = json.dumps(out[k] if out[k] is not None else (
                    {} if k in ("meta", "markers", "scores", "payload") else []
                ))
        return out

    def _decode(self, table: str, row: Optional[sqlite3.Row]) -> Optional[dict]:
        if row is None:
            return None
        d = dict(row)
        for k in _JSON_COLS.get(table, set()):
            if k in d and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except json.JSONDecodeError:
                    pass
        return d

    def _decode_many(self, table: str, rows: list) -> list[dict]:
        return [self._decode(table, r) for r in rows]  # type: ignore[misc]

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (ts, type, payload) VALUES (?, ?, ?)",
                (_now(), event_type, json.dumps(payload or {})),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    # -- works --------------------------------------------------------------- #

    def upsert_work(self, data: dict[str, Any]) -> int:
        """Insert or update by slug. Returns work id."""
        slug = data.get("slug") or _slugify(data.get("title", "untitled"))
        existing = self.work_by_slug(slug)
        row = {
            "slug": slug,
            "title": data.get("title") or slug,
            "year": data.get("year"),
            "directors": data.get("directors") or [],
            "genres": data.get("genres") or [],
            "medium": data.get("medium") or "film",
            "tier": data.get("tier") or "UNRANKED",
            "theme": data.get("theme") or "",
            "logline": data.get("logline") or "",
            "plot_summary": data.get("plot_summary") or "",
            "source": data.get("source") or "",
            "meta": data.get("meta") or {},
        }
        with self._lock:
            if existing:
                enc = self._encode("works", row)
                self._conn.execute(
                    """UPDATE works SET title=?, year=?, directors=?, genres=?,
                       medium=?, tier=?, theme=?, logline=?, plot_summary=?,
                       source=?, meta=? WHERE id=?""",
                    (enc["title"], enc["year"], enc["directors"], enc["genres"],
                     enc["medium"], enc["tier"], enc["theme"], enc["logline"],
                     enc["plot_summary"], enc["source"], enc["meta"],
                     existing["id"]),
                )
                self._conn.commit()
                wid = int(existing["id"])
                self.emit("work_updated", {"id": wid, "slug": slug})
                return wid
            enc = self._encode("works", {**row, "created_at": _now()})
            cur = self._conn.execute(
                """INSERT INTO works
                   (slug, title, year, directors, genres, medium, tier, theme,
                    logline, plot_summary, source, meta, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enc["slug"], enc["title"], enc["year"], enc["directors"],
                 enc["genres"], enc["medium"], enc["tier"], enc["theme"],
                 enc["logline"], enc["plot_summary"], enc["source"],
                 enc["meta"], enc["created_at"]),
            )
            self._conn.commit()
            wid = int(cur.lastrowid)
            self.emit("work_created", {"id": wid, "slug": slug})
            return wid

    def work_by_slug(self, slug: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM works WHERE slug = ?", (slug,)
            ).fetchone()
        return self._decode("works", row)

    def get_work(self, work_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM works WHERE id = ?", (work_id,)
            ).fetchone()
        return self._decode("works", row)

    def list_works(self, tier: Optional[str] = None,
                   genre: Optional[str] = None) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM works ORDER BY tier, title"
            ).fetchall()
        works = self._decode_many("works", rows)
        if tier:
            works = [w for w in works if w.get("tier") == tier]
        if genre:
            g = genre.lower()
            works = [
                w for w in works
                if any(g in str(x).lower() for x in (w.get("genres") or []))
            ]
        return works

    # -- scene cards --------------------------------------------------------- #

    def add_scene_card(self, work_id: int, data: dict[str, Any]) -> int:
        row = {
            "work_id": work_id,
            "idx": int(data.get("idx", 0)),
            "slugline": data.get("slugline") or "",
            "title": data.get("title") or "",
            "what_happens": data.get("what_happens") or "",
            "relationship_delta": data.get("relationship_delta") or "",
            "plot_function": data.get("plot_function") or "",
            "emotional_spine": data.get("emotional_spine") or "",
            "characters": data.get("characters") or [],
            "structural_beat": data.get("structural_beat") or "",
            "act": data.get("act"),
            "page_estimate": data.get("page_estimate"),
            "tags": data.get("tags") or [],
            "meta": data.get("meta") or {},
        }
        enc = self._encode("scene_cards", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO scene_cards
                   (work_id, idx, slugline, title, what_happens, relationship_delta,
                    plot_function, emotional_spine, characters, structural_beat,
                    act, page_estimate, tags, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enc["work_id"], enc["idx"], enc["slugline"], enc["title"],
                 enc["what_happens"], enc["relationship_delta"],
                 enc["plot_function"], enc["emotional_spine"], enc["characters"],
                 enc["structural_beat"], enc["act"], enc["page_estimate"],
                 enc["tags"], enc["meta"]),
            )
            self._conn.commit()
            cid = int(cur.lastrowid)
        self.emit("scene_card_added", {"id": cid, "work_id": work_id})
        return cid

    def scene_cards_for_work(self, work_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM scene_cards WHERE work_id = ? ORDER BY idx",
                (work_id,),
            ).fetchall()
        return self._decode_many("scene_cards", rows)

    def clear_work_children(self, work_id: int) -> None:
        """Remove cards/shots/digests for a work (for re-import)."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM decision_digests WHERE work_id = ?", (work_id,)
            )
            self._conn.execute(
                "DELETE FROM shot_moments WHERE work_id = ?", (work_id,)
            )
            self._conn.execute(
                "DELETE FROM scene_cards WHERE work_id = ?", (work_id,)
            )
            self._conn.commit()
        self.emit("work_children_cleared", {"work_id": work_id})

    # -- shot moments -------------------------------------------------------- #

    def add_shot_moment(self, work_id: int, data: dict[str, Any],
                        scene_card_id: Optional[int] = None) -> int:
        row = {
            "work_id": work_id,
            "scene_card_id": scene_card_id or data.get("scene_card_id"),
            "idx": int(data.get("idx", 0)),
            "start_s": float(data.get("start_s", 0)),
            "end_s": float(data.get("end_s", 0)),
            "scale": data.get("scale") or "MS",
            "subject": data.get("subject") or "",
            "angle": data.get("angle") or "EYE LEVEL",
            "move": data.get("move") or "STATIC",
            "int_ext": data.get("int_ext") or "EXT.",
            "location": data.get("location") or "",
            "time_of_day": data.get("time_of_day") or "DAY",
            "action_text": data.get("action_text") or "",
            "characters": data.get("characters") or [],
            "mood": data.get("mood") or "",
            "dialogue": data.get("dialogue") or [],
            "confidence": float(data.get("confidence", 0.5)),
            "keyframes": data.get("keyframes") or [],
            "meta": data.get("meta") or {},
        }
        enc = self._encode("shot_moments", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO shot_moments
                   (work_id, scene_card_id, idx, start_s, end_s, scale, subject,
                    angle, move, int_ext, location, time_of_day, action_text,
                    characters, mood, dialogue, confidence, keyframes, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enc["work_id"], enc["scene_card_id"], enc["idx"],
                 enc["start_s"], enc["end_s"], enc["scale"], enc["subject"],
                 enc["angle"], enc["move"], enc["int_ext"], enc["location"],
                 enc["time_of_day"], enc["action_text"], enc["characters"],
                 enc["mood"], enc["dialogue"], enc["confidence"],
                 enc["keyframes"], enc["meta"]),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def shot_moments_for_work(self, work_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM shot_moments WHERE work_id = ? ORDER BY idx",
                (work_id,),
            ).fetchall()
        return self._decode_many("shot_moments", rows)

    def all_shot_moments(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM shot_moments ORDER BY work_id, idx"
            ).fetchall()
        return self._decode_many("shot_moments", rows)

    # -- decision digests (historical) --------------------------------------- #

    def add_digest(self, data: dict[str, Any]) -> int:
        row = {
            "work_id": data.get("work_id"),
            "scene_card_id": data.get("scene_card_id"),
            "shot_moment_id": data.get("shot_moment_id"),
            "situation": data.get("situation") or "",
            "decision": data.get("decision") or "",
            "rationale": data.get("rationale") or "",
            "director": data.get("director") or "",
            "tags": data.get("tags") or [],
            "phase": data.get("phase") or "",
            "meta": data.get("meta") or {},
        }
        enc = self._encode("decision_digests", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO decision_digests
                   (work_id, scene_card_id, shot_moment_id, situation, decision,
                    rationale, director, tags, phase, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (enc["work_id"], enc["scene_card_id"], enc["shot_moment_id"],
                 enc["situation"], enc["decision"], enc["rationale"],
                 enc["director"], enc["tags"], enc["phase"], enc["meta"]),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_digests(self, work_id: Optional[int] = None) -> list[dict]:
        with self._lock:
            if work_id is not None:
                rows = self._conn.execute(
                    "SELECT * FROM decision_digests WHERE work_id = ?",
                    (work_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM decision_digests"
                ).fetchall()
        return self._decode_many("decision_digests", rows)

    # -- projects ------------------------------------------------------------ #

    def create_project(self, title: str, slug: Optional[str] = None,
                       genre: str = "", logline: str = "",
                       medium: str = "film",
                       series_slug: str = "") -> int:
        s = slug or _slugify(title)
        now = _now()
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO projects
                   (slug, title, phase, genre, logline, medium, series_slug,
                    markers, working_memory, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (s, title, "intake", genre, logline, medium or "film",
                 series_slug or "", "{}", "[]", now, now),
            )
            self._conn.commit()
            pid = int(cur.lastrowid)
        self.emit("project_created", {"id": pid, "slug": s, "medium": medium})
        return pid

    def get_project(self, project_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return self._decode("projects", row)

    def project_by_slug(self, slug: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE slug = ?", (slug,)
            ).fetchone()
        return self._decode("projects", row)

    def list_projects(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        return self._decode_many("projects", rows)

    def update_project(self, project_id: int, **fields: Any) -> None:
        allowed = {
            "title", "phase", "genre", "logline", "markers", "working_memory",
            "medium", "series_slug",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = _now()
        enc = self._encode("projects", updates)
        sets = ", ".join(f"{k}=?" for k in enc)
        vals = list(enc.values()) + [project_id]
        with self._lock:
            self._conn.execute(
                f"UPDATE projects SET {sets} WHERE id = ?", vals
            )
            self._conn.commit()
        self.emit("project_updated", {"id": project_id, **{
            k: updates[k] for k in updates if k != "updated_at"
        }})

    # -- decision ledger ----------------------------------------------------- #

    def latest_decision_hash(self, project_id: Optional[int] = None) -> str:
        with self._lock:
            if project_id is None:
                row = self._conn.execute(
                    "SELECT content_hash FROM decisions ORDER BY id DESC LIMIT 1"
                ).fetchone()
            else:
                row = self._conn.execute(
                    """SELECT content_hash FROM decisions
                       WHERE project_id = ? ORDER BY id DESC LIMIT 1""",
                    (project_id,),
                ).fetchone()
        return str(row["content_hash"]) if row else ""

    def append_decision(self, data: dict[str, Any]) -> int:
        row = {
            "project_id": data.get("project_id"),
            "phase": data.get("phase") or "",
            "situation": data.get("situation") or "",
            "candidates": data.get("candidates") or [],
            "chosen_id": data.get("chosen_id") or "",
            "chosen_action": data.get("chosen_action") or "",
            "equilibrium_method": data.get("equilibrium_method") or "weighted_pareto",
            "creativity_alpha": float(data.get("creativity_alpha", 0.25)),
            "evidence_ids": data.get("evidence_ids") or [],
            "scores": data.get("scores") or {},
            "parent_hash": data.get("parent_hash") or "",
            "content_hash": data.get("content_hash") or "",
            "created_at": data.get("created_at") or _now(),
        }
        enc = self._encode("decisions", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO decisions
                   (project_id, phase, situation, candidates, chosen_id,
                    chosen_action, equilibrium_method, creativity_alpha,
                    evidence_ids, scores, parent_hash, content_hash, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enc["project_id"], enc["phase"], enc["situation"],
                 enc["candidates"], enc["chosen_id"], enc["chosen_action"],
                 enc["equilibrium_method"], enc["creativity_alpha"],
                 enc["evidence_ids"], enc["scores"], enc["parent_hash"],
                 enc["content_hash"], enc["created_at"]),
            )
            self._conn.commit()
            did = int(cur.lastrowid)
        self.emit("decision_committed", {
            "id": did, "content_hash": row["content_hash"],
            "chosen_id": row["chosen_id"],
        })
        return did

    def decisions_for_project(self, project_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM decisions WHERE project_id = ? ORDER BY id",
                (project_id,),
            ).fetchall()
        return self._decode_many("decisions", rows)

    def get_decision(self, decision_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM decisions WHERE id = ?", (decision_id,)
            ).fetchone()
        return self._decode("decisions", row)

    def update_work(self, work_id: int, **fields: Any) -> None:
        allowed = {
            "title", "year", "directors", "genres", "medium", "tier",
            "theme", "logline", "plot_summary", "source", "meta", "slug",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        enc = self._encode("works", updates)
        sets = ", ".join(f"{k}=?" for k in enc)
        vals = list(enc.values()) + [work_id]
        with self._lock:
            self._conn.execute(f"UPDATE works SET {sets} WHERE id = ?", vals)
            self._conn.commit()
        self.emit("work_patched", {"id": work_id, **{
            k: updates[k] for k in updates
        }})

    def update_digest(self, digest_id: int, **fields: Any) -> None:
        allowed = {
            "situation", "decision", "rationale", "director", "tags",
            "phase", "meta", "work_id", "scene_card_id", "shot_moment_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        enc = self._encode("decision_digests", updates)
        sets = ", ".join(f"{k}=?" for k in enc)
        vals = list(enc.values()) + [digest_id]
        with self._lock:
            self._conn.execute(
                f"UPDATE decision_digests SET {sets} WHERE id = ?", vals
            )
            self._conn.commit()
        self.emit("digest_patched", {"id": digest_id})

    def get_digest(self, digest_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM decision_digests WHERE id = ?", (digest_id,)
            ).fetchone()
        return self._decode("decision_digests", row)

    def all_scene_cards(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM scene_cards ORDER BY work_id, idx"
            ).fetchall()
        return self._decode_many("scene_cards", rows)

    # -- embeddings ---------------------------------------------------------- #

    def upsert_embedding(self, entity_type: str, entity_id: int,
                         text_blob: str, vector: list[float]) -> None:
        now = _now()
        enc_vec = json.dumps(vector)
        with self._lock:
            self._conn.execute(
                """INSERT INTO embeddings
                   (entity_type, entity_id, text_blob, vector, dim, updated_at)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                     text_blob=excluded.text_blob,
                     vector=excluded.vector,
                     dim=excluded.dim,
                     updated_at=excluded.updated_at""",
                (entity_type, entity_id, text_blob, enc_vec, len(vector), now),
            )
            self._conn.commit()

    def embeddings_of_type(self, entity_type: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM embeddings WHERE entity_type = ?",
                (entity_type,),
            ).fetchall()
        return self._decode_many("embeddings", rows)

    def clear_embeddings(self, entity_type: Optional[str] = None) -> int:
        with self._lock:
            if entity_type:
                cur = self._conn.execute(
                    "DELETE FROM embeddings WHERE entity_type = ?",
                    (entity_type,),
                )
            else:
                cur = self._conn.execute("DELETE FROM embeddings")
            self._conn.commit()
            return int(cur.rowcount)

    # -- project cards ------------------------------------------------------- #

    def add_project_card(self, project_id: int, data: dict[str, Any]) -> int:
        row = {
            "project_id": project_id,
            "idx": int(data.get("idx", 0)),
            "slugline": data.get("slugline") or "",
            "title": data.get("title") or "",
            "what_happens": data.get("what_happens") or "",
            "relationship_delta": data.get("relationship_delta") or "",
            "plot_function": data.get("plot_function") or "",
            "emotional_spine": data.get("emotional_spine") or "",
            "characters": data.get("characters") or [],
            "structural_beat": data.get("structural_beat") or "",
            "act": data.get("act"),
            "page_estimate": data.get("page_estimate"),
            "tags": data.get("tags") or [],
            "meta": data.get("meta") or {},
        }
        enc = self._encode("project_cards", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO project_cards
                   (project_id, idx, slugline, title, what_happens,
                    relationship_delta, plot_function, emotional_spine,
                    characters, structural_beat, act, page_estimate, tags, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enc["project_id"], enc["idx"], enc["slugline"], enc["title"],
                 enc["what_happens"], enc["relationship_delta"],
                 enc["plot_function"], enc["emotional_spine"], enc["characters"],
                 enc["structural_beat"], enc["act"], enc["page_estimate"],
                 enc["tags"], enc["meta"]),
            )
            self._conn.commit()
            cid = int(cur.lastrowid)
        self.emit("project_card_added", {"id": cid, "project_id": project_id})
        return cid

    def project_cards(self, project_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM project_cards WHERE project_id = ? ORDER BY idx",
                (project_id,),
            ).fetchall()
        return self._decode_many("project_cards", rows)

    def clear_project_cards(self, project_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM project_cards WHERE project_id = ?", (project_id,)
            )
            self._conn.commit()

    def replace_project_cards(self, project_id: int,
                              cards: list[dict[str, Any]]) -> list[int]:
        self.clear_project_cards(project_id)
        return [self.add_project_card(project_id, c) for c in cards]

    # -- episodes (series) --------------------------------------------------- #

    def add_episode(self, series_project_id: int, number: int,
                    title: str = "", logline: str = "",
                    arc_notes: str = "",
                    child_project_id: Optional[int] = None) -> int:
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO episodes
                   (series_project_id, number, title, logline, child_project_id,
                    arc_notes, meta)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(series_project_id, number) DO UPDATE SET
                     title=excluded.title,
                     logline=excluded.logline,
                     arc_notes=excluded.arc_notes,
                     child_project_id=COALESCE(excluded.child_project_id,
                                              episodes.child_project_id)""",
                (series_project_id, number, title, logline, child_project_id,
                 arc_notes, "{}"),
            )
            self._conn.commit()
            # fetch id
            row = self._conn.execute(
                """SELECT id FROM episodes
                   WHERE series_project_id = ? AND number = ?""",
                (series_project_id, number),
            ).fetchone()
            eid = int(row["id"] if row else cur.lastrowid)
        self.emit("episode_upserted", {
            "id": eid, "series_project_id": series_project_id, "number": number,
        })
        return eid

    def episodes_for_series(self, series_project_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM episodes WHERE series_project_id = ?
                   ORDER BY number""",
                (series_project_id,),
            ).fetchall()
        return self._decode_many("episodes", rows)

    def update_episode(self, series_project_id: int, number: int,
                       **fields: Any) -> None:
        allowed = {"title", "logline", "arc_notes", "child_project_id", "meta"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        enc = self._encode("episodes", updates)
        sets = ", ".join(f"{k}=?" for k in enc)
        vals = list(enc.values()) + [series_project_id, number]
        with self._lock:
            self._conn.execute(
                f"""UPDATE episodes SET {sets}
                    WHERE series_project_id = ? AND number = ?""",
                vals,
            )
            self._conn.commit()

    # -- motifs (series arc) ------------------------------------------------- #

    def add_motif(self, series_project_id: int, data: dict[str, Any]) -> int:
        row = {
            "series_project_id": series_project_id,
            "name": data.get("name") or "unnamed",
            "kind": data.get("kind") or "visual",
            "description": data.get("description") or "",
            "first_episode": data.get("first_episode"),
            "payoff_episode": data.get("payoff_episode"),
            "status": data.get("status") or "planted",
            "tags": data.get("tags") or [],
            "meta": data.get("meta") or {},
        }
        enc = self._encode("motifs", row)
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO motifs
                   (series_project_id, name, kind, description, first_episode,
                    payoff_episode, status, tags, meta)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (enc["series_project_id"], enc["name"], enc["kind"],
                 enc["description"], enc["first_episode"], enc["payoff_episode"],
                 enc["status"], enc["tags"], enc["meta"]),
            )
            self._conn.commit()
            mid = int(cur.lastrowid)
        self.emit("motif_added", {"id": mid, "series_project_id": series_project_id})
        return mid

    def motifs_for_series(self, series_project_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM motifs WHERE series_project_id = ? ORDER BY id",
                (series_project_id,),
            ).fetchall()
        return self._decode_many("motifs", rows)

    def update_motif(self, motif_id: int, **fields: Any) -> None:
        allowed = {
            "name", "kind", "description", "first_episode", "payoff_episode",
            "status", "tags", "meta",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        enc = self._encode("motifs", updates)
        sets = ", ".join(f"{k}=?" for k in enc)
        vals = list(enc.values()) + [motif_id]
        with self._lock:
            self._conn.execute(f"UPDATE motifs SET {sets} WHERE id = ?", vals)
            self._conn.commit()

    def add_motif_beat(self, motif_id: int, episode_number: int,
                       beat: str, notes: str = "") -> int:
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO motif_beats
                   (motif_id, episode_number, beat, notes, meta)
                   VALUES (?,?,?,?,?)""",
                (motif_id, episode_number, beat, notes, "{}"),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def motif_beats(self, motif_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM motif_beats WHERE motif_id = ?
                   ORDER BY episode_number, id""",
                (motif_id,),
            ).fetchall()
        return self._decode_many("motif_beats", rows)

    def get_motif(self, motif_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM motifs WHERE id = ?", (motif_id,)
            ).fetchone()
        return self._decode("motifs", row)
