"""Force offline-friendly defaults for the test suite."""
from __future__ import annotations

import os

# Before any director_bot import side effects matter in collection:
os.environ.setdefault("DIRECTOR_BOT_PROVIDER", "mock")
os.environ.setdefault("DIRECTOR_BOT_EMBED_PROVIDER", "hash")
os.environ.setdefault("DIRECTOR_BOT_SKIP_DOTENV", "1")
