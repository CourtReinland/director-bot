#!/usr/bin/env bash
# One-command self-contained build for Director-bot.
#
# Produces a macOS .app + .dmg with frozen Python backend (no local venv needed):
#   1. Freeze backend with PyInstaller  -> packaging/dist/director-bot-backend/
#   2. electron-builder packages extraResources + ad-hoc signs
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

echo "==> [1/2] Freezing backend (PyInstaller onedir)"
bash "$ROOT/packaging/build_backend.sh"

if [ ! -x "$ROOT/packaging/dist/director-bot-backend/director-bot-backend" ]; then
  echo "error: frozen backend missing" >&2
  exit 1
fi

echo "==> [2/2] Packaging Electron app (electron-builder --mac dmg)"
(
  cd "$ROOT/desktop"
  npm install >/dev/null 2>&1 || true
  bash build/gen_icon.sh 2>/dev/null || true
  npm run dist:standalone
)

echo
echo "==> Build complete. Artifacts under desktop/dist:"
DIST="$ROOT/desktop/dist"
if [ -d "$DIST" ]; then
  find "$DIST" -maxdepth 2 -name '*.app' -print 2>/dev/null | while read -r appPath; do
    size=$(du -sh "$appPath" 2>/dev/null | cut -f1)
    echo "  APP: $appPath  ($size)"
  done
  find "$DIST" -maxdepth 1 -name '*.dmg' -print 2>/dev/null | while read -r dmgPath; do
    size=$(du -sh "$dmgPath" 2>/dev/null | cut -f1)
    echo "  DMG: $dmgPath  ($size)"
  done
else
  echo "  (warning: $DIST not found)" >&2
fi
