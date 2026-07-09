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
pip install -e ".[dev]"

director-bot demo          # seed + project + decide + handoffs
director-bot short --genre thriller --title "The File" --style "David Fincher"
director-bot soul meet "pitch me a cold open" --project 1
director-bot canon lookup "interrogation silence withhold reverse"
```

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

## Live LLM brain (optional)

Defaults to **mock** offline. Set a provider when keys exist:

```bash
export DIRECTOR_BOT_PROVIDER=xai          # or anthropic | openai
export XAI_API_KEY=...
# export ANTHROPIC_API_KEY=...
# export OPENAI_API_KEY=...
pip install -e ".[anthropic]"             # only needed for Claude
```

When non-mock, `decide` can re-score candidates via the brain before equilibrium.

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

**v0.2.0** — hybrid retrieval, live brain seam, curation CLI, project cards/series, vertical-slice `short` pipeline, multi-genre seed corpus, handoff export.
