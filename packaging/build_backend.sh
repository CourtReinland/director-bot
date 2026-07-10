#!/usr/bin/env bash
# Freeze the Director-bot backend into a self-contained onedir with PyInstaller.
# Output: packaging/dist/director-bot-backend/director-bot-backend
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

if [ ! -x "$PY" ]; then
  echo "error: $PY not found (project venv missing)" >&2
  exit 1
fi

if ! "$PY" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "==> installing pyinstaller into .venv"
  "$PIP" install --quiet pyinstaller
fi

# Ensure web extras present for serve
"$PY" -c "import fastapi, uvicorn" >/dev/null 2>&1 || \
  "$PIP" install --quiet -e ".[web]"

echo "==> running PyInstaller (onedir)"
"$PY" -m PyInstaller --noconfirm --clean --onedir --name director-bot-backend \
  --collect-submodules director_bot \
  --collect-all uvicorn --collect-all fastapi --collect-all starlette \
  --collect-all pydantic --collect-all pydantic_core \
  --collect-all rapidfuzz --collect-all typer --collect-all click \
  --collect-all anyio --collect-all sniffio --collect-all h11 \
  --collect-all httpx --collect-all httpcore --collect-all certifi \
  --collect-all websockets --collect-all watchfiles \
  --collect-all python_multipart --collect-all multipart \
  --add-data "$ROOT/src/director_bot/server/static:director_bot/server/static" \
  --add-data "$ROOT/src/director_bot/soul/static:director_bot/soul/static" \
  --add-data "$ROOT/soul/static:soul/static" \
  --distpath packaging/dist --workpath packaging/build --specpath packaging \
  packaging/backend_entry.py

DIST="$ROOT/packaging/dist/director-bot-backend"
if [ ! -x "$DIST/director-bot-backend" ]; then
  echo "error: expected frozen binary at $DIST/director-bot-backend" >&2
  exit 1
fi

echo "==> ad-hoc codesigning Mach-O in the bundle"
find "$DIST" \( -name '*.so' -o -name '*.dylib' \) -print0 |
  while IFS= read -r -d '' f; do
    codesign --force -s - --timestamp=none "$f" >/dev/null 2>&1 || true
  done
find "$DIST" -type f -perm -u+x -print0 |
  while IFS= read -r -d '' f; do
    if file "$f" | grep -q 'Mach-O'; then
      codesign --force -s - --timestamp=none "$f" >/dev/null 2>&1 || true
    fi
  done
codesign --force -s - --timestamp=none "$DIST/director-bot-backend" >/dev/null 2>&1 || true

echo "==> frozen backend ready: $DIST/director-bot-backend"
