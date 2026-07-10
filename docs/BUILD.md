# Building the macOS desktop app

Director-bot's desktop shell is an Electron app (`desktop/`) that spawns the Python backend (`director-bot serve`) on a free localhost port, waits for `/api/health`, and opens the dashboard — including **Model View** (exact system/user messages the brain receives) — in a native window.

## Prerequisites

- **Node.js** (with `npm`)
- **Python 3.11+** venv with director-bot installed:

  ```bash
  cd /Users/blue/Projects/director-bot
  python3.11 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev,web]"
  ```

  Confirm `.venv/bin/director-bot` exists — that is the default backend the shell launches.

## Install & run (dev)

```bash
cd desktop
npm install
bash build/gen_icon.sh   # optional: icon.png for packaging
npm start                # headed app
npm run smoke            # headless boot check → SMOKE OK
```

| Script | What it does |
| --- | --- |
| `npm start` | Launch Electron + spawn `director-bot serve` |
| `npm run smoke` | Spawn backend, poll health, print `SMOKE OK`, exit |
| `npm run pack` | Unsigned `.app` via electron-builder |

## Data directory

The shell defaults `DIRECTOR_BOT_HOME` to `~/.director-bot` if unset — same DB as the CLI. Override to sandbox:

```bash
DIRECTOR_BOT_HOME=/tmp/dbot-sandbox npm start
```

Backend binary override:

```bash
DIRECTOR_BOT_BACKEND_BIN=/path/to/director-bot npm start
```

## Gatekeeper (unsigned)

The app is **unsigned** (`identity: null`). On first launch: Right-click → Open, or:

```bash
xattr -dr com.apple.quarantine desktop/dist/mac-arm64/Director-bot.app
```

## Model View (training)

The dashboard's primary pane surfaces:

1. **System** — soul preamble (meet) or craft-scorer system (decide)
2. **User** — assembled user message / score JSON payload
3. **Response** — live reply or dry-run provisional equilibrium
4. **Retrieval / sections** — canon hits, working memory, candidates
5. **Brain traces** — process-local ring of every `complete()` this session

Dry-run **Preview context** never calls a paid model. **Stream meet** uses SSE (`/api/soul/meet/stream`) so tokens paint as they arrive; every call is dual-written to SQLite `brain_traces` (survives restarts).
## Standalone package (frozen backend + DMG)

No local venv required on the target machine:

```bash
# 1) Freeze Python backend (PyInstaller onedir)
bash packaging/build_backend.sh
# -> packaging/dist/director-bot-backend/director-bot-backend

# 2) One-shot: freeze + electron-builder dmg
bash packaging/build_standalone.sh
# -> desktop/dist/mac-arm64/Director-bot.app
# -> desktop/dist/Director-bot-*.dmg
```

Dev launches still use `.venv/bin/director-bot`. Packaged apps use the frozen binary under `Contents/Resources/backend/`.

## Dual embedder

```bash
export DIRECTOR_BOT_PROVIDER=xai
export XAI_API_KEY=...
export OPENAI_API_KEY=...          # auto-selected for embeddings
# export DIRECTOR_BOT_EMBED_PROVIDER=hash   # force offline
director-bot doctor                # shows embedder + dual_key note
```

## Troubleshooting

- `backend binary not found` → `pip install -e ".[web]"` in the project venv
- Backend exits immediately → run `director-bot serve` alone and fix import/errors
- Empty traces → only live `complete()` calls are logged; mock decide skips scorer LLM
- Packaged app missing backend → run `bash packaging/build_backend.sh` before `npm run pack`
