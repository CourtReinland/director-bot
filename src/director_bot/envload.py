"""Load `.env` without requiring python-dotenv.

Supports both `KEY=value` and shell-style `export KEY=value`.
Never logs secret values. Does not override already-set env vars.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_LINE = re.compile(
    r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$"
)


def _strip_value(raw: str) -> str:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v.strip()


def load_env_file(path: Path | str) -> list[str]:
    """Load env file; return list of keys set (not values)."""
    p = Path(path).expanduser()
    if not p.is_file():
        return []
    set_keys: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE.match(s)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2)
        if key in os.environ and os.environ[key] != "":
            continue  # already set wins
        os.environ[key] = _strip_value(raw_val)
        set_keys.append(key)
    return set_keys


def load_default_env() -> list[str]:
    """Search common locations for a director-bot .env."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",  # repo root
        Path.home() / ".director-bot" / ".env",
    ]
    loaded: list[str] = []
    seen: set[Path] = set()
    for c in candidates:
        try:
            rp = c.resolve()
        except OSError:
            continue
        if rp in seen or not rp.is_file():
            continue
        seen.add(rp)
        loaded.extend(load_env_file(rp))
    return loaded


# Auto-load on import so CLI/brain/embeddings see keys immediately.
# Skip during pytest so unit tests stay offline/deterministic unless they opt in.
import os as _os
if not _os.environ.get("PYTEST_CURRENT_TEST") and _os.environ.get(
    "DIRECTOR_BOT_SKIP_DOTENV", ""
).lower() not in ("1", "true", "yes"):
    _AUTO = load_default_env()
else:
    _AUTO = []
