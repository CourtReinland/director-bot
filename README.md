# Director-bot

Embodied AI film director. Uses a **canon** of S-tier labeled films and decision digests, an OpenSouls-inspired **soul** (personality + process FSM), hybrid **vector + fuzzy retrieval**, and a **merkle decision ledger** with multi-criteria equilibrium. Orchestrates **Scripty**, **LightWriter**, and **Script2Screen** via thin file-based adapters.

```
brief → soul phases → hybrid canon lookup → decide (ledger) → tool handoffs → film
```

**Repo:** https://github.com/CourtReinland/director-bot  

## Quick start

```bash
cd /Users/blue/Projects/director-bot
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,web]"

# Optional: .env in repo root (gitignored). Supports `export KEY=value`.
#   export DIRECTOR_BOT_PROVIDER=xai
#   export XAI_API_KEY=...

director-bot doctor        # shows provider + embedder + which env keys exist
director-bot demo          # seed + project + decide + handoffs
director-bot short --genre thriller --title "The File" --style "David Fincher"
director-bot serve         # dashboard http://127.0.0.1:8790/
director-bot soul meet "pitch me a cold open" --project 1
director-bot canon lookup "interrogation silence withhold reverse"
```

### Desktop app (macOS)

Persistent Electron shell — same pattern as Scripty. Spawns the backend and opens the dashboard in a native window:

```bash
cd desktop && npm install && npm start
# headless check:
npm run smoke   # → SMOKE OK
```

See [`docs/BUILD.md`](docs/BUILD.md). Data stays in `~/.director-bot` (shared with CLI).

### Model View (training)

The dashboard opens on **Model View**: the exact system + user messages the brain receives, plus retrieval hits, candidates, score payloads, and a **durable brain_traces** log (SQLite).

- **Preview context** — dry-run, no tokens  
- **Stream meet** — SSE tokens as they arrive (`POST /api/soul/meet/stream`)  
- **Traces** — click any past call (survives app restarts)  

## CLI map

| Command | Purpose |
|---------|---------|
| `demo` | Seed + project + decide + verify + handoffs |
| `short` | Vertical slice pipeline for a short film |
| `doctor` | Paths / health / embedding counts |
| `canon seed` | Multi-genre pocket S/A corpus + reindex |
| `canon import FILE` | Import work bundle or Scripty export |
| `canon import-dir DIR` | Bulk import `*.json` |
| `canon tier ID S` | Set work tier |
| `canon annotate ID --theme …` | Patch work metadata |
| `canon digest ID --situation … --decision …` | Hand-authored digest |
| `canon reindex` | Rebuild hashed embeddings |
| `canon lookup QUERY` | Hybrid digest/moment/card search |
| `project create` | New production project |
| `project series TITLE -e Ep1 -e Ep2` | Series + episode projects |
| `project cards-import` | LightWriter-style cards → board |
| `project export` | LightWriter + STS handoff packages |
| `decide run` / `decide chain` | Decision engine + merkle verify |
| `soul meet` / `soul cycle` | Embodied creative meeting |

Alias: `dbot`.

## Scripty pipe

```bash
scripty export-canon 1 -o /tmp/wooded.json \
  --tier S --director "David Fincher" --genre thriller
director-bot canon import /tmp/wooded.json
```

## Live LLM brain + embeddings (optional)

Defaults to **mock** / **hash** offline. Keys from `.env` or the environment:

```bash
export DIRECTOR_BOT_PROVIDER=xai          # or anthropic | openai | mock
export XAI_API_KEY=...
# export OPENAI_API_KEY=...               # for OpenAI chat and/or embeddings
# export DIRECTOR_BOT_EMBED_PROVIDER=hash # hash | openai | xai | auto
pip install -e ".[web,anthropic]"         # dashboard + Claude optional
```

When non-mock, `decide` can re-score candidates via the brain before equilibrium.
xAI does not currently ship a stable public embeddings route; default embedder stays **hash** unless you set `DIRECTOR_BOT_EMBED_PROVIDER=openai` (or try `xai` with `DIRECTOR_BOT_EMBED_TRY_XAI=1`).

## Soul files

- `soul/static/core.md` — identity  
- `soul/static/taste.md` — gravity wells  
- `soul/static/process_notes.md` — phase discipline  

`DIRECTOR_BOT_SOUL_DIR` overrides the directory.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `DIRECTOR_BOT_HOME` | `~/.director-bot` | Data root |
| `DIRECTOR_BOT_DB` | `$HOME/director.db` | SQLite path |
| `DIRECTOR_BOT_SOUL_DIR` | repo `soul/static` | Personality markdown |
| `DIRECTOR_BOT_PROVIDER` | auto → `mock` | `mock` / `anthropic` / `openai` / `xai` |
| `DIRECTOR_BOT_TEXT_MODEL` | provider default | Model id |
| `DIRECTOR_BOT_EMBED_PROVIDER` | `auto` | `hash` / `openai` / `xai` / `auto` |
| *(auto embed)* | — | If `OPENAI_API_KEY` set → OpenAI embeddings even when chat is xAI |

## Related tools

| Repo | Role |
|------|------|
| [scripty](https://github.com/CourtReinland/scripty) | Label films → **export-canon** |
| [lightwriter](https://github.com/CourtReinland/lightwriter) | Pages & scene cards |
| [script2screen](https://github.com/CourtReinland/script2screen) | Resolve timeline realization |
| [opensouls](https://github.com/opensouls/opensouls) | Inspiration (WorkingMemory / processes) |

## Tests

```bash
python -m pytest -q
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Status

**v0.6.0** — dual embed (XAI chat + OpenAI embed), inline board edit, trace search, 50+ seed pockets, packaging/DMG scripts; plus stream meet + durable traces.
