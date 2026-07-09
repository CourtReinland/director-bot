"""Runtime paths and knobs (env-overridable, no secrets)."""
from __future__ import annotations

import os
from pathlib import Path

# Soul markdown: prefer env override, then repo-level soul/static (dev),
# then packaged copy under director_bot/soul/static (installed).
_PKG_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]


def soul_static_dir() -> Path:
    env = os.environ.get("DIRECTOR_BOT_SOUL_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    repo = _REPO_ROOT / "soul" / "static"
    if repo.is_dir() and (repo / "core.md").is_file():
        return repo
    return _PKG_ROOT / "soul" / "static"


# Back-compat alias (resolved at access time via property-like use in callers).
@property  # type: ignore[misc]
def _soul_static_dir_deprecated() -> Path:
    return soul_static_dir()


# Prefer soul_static_dir() at call sites. Constant kept for older imports.
SOUL_STATIC_DIR = soul_static_dir()


def home() -> Path:
    """Root data directory: one SQLite db + project workspaces."""
    raw = os.environ.get("DIRECTOR_BOT_HOME", "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / ".director-bot"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    override = os.environ.get("DIRECTOR_BOT_DB", "").strip()
    if override:
        p = Path(override).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return home() / "director.db"


def project_dir(slug: str) -> Path:
    d = home() / "projects" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_provider() -> str:
    """mock | anthropic | openai | xai — auto mock when no keys."""
    forced = os.environ.get("DIRECTOR_BOT_PROVIDER", "").strip().lower()
    if forced in ("mock", "anthropic", "openai", "xai"):
        return forced
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("XAI_API_KEY"):
        return "xai"
    return "mock"


# Multi-criteria weights (sum need not be 1; normalized at score time).
DEFAULT_CRITERIA_WEIGHTS: dict[str, float] = {
    "genre_craft": 1.0,
    "style_match": 0.9,
    "continuity": 1.1,
    "originality": 0.6,
    "feasibility": 0.8,
    "emotion": 1.0,
}

# Creativity blend α by project phase (0 = pure historical, 1 = pure generative).
PHASE_CREATIVITY: dict[str, float] = {
    "intake": 0.2,
    "break_story": 0.35,
    "write": 0.4,
    "shotlist": 0.25,
    "previs": 0.3,
    "dailies": 0.15,
    "cut": 0.2,
    "series_arc": 0.35,
}
