# Director-bot

Embodied AI film director. Uses a **canon** of S-tier labeled films and decision digests, an OpenSouls-inspired **soul** (personality + process FSM), and a **merkle decision ledger** with multi-criteria equilibrium. Orchestrates **Scripty**, **LightWriter**, and **Script2Screen** via thin adapters (those repos stay independent).

```
brief → soul phases → canon lookup → decide (ledger) → tool handoffs → film
```

## Quick start

```bash
cd /Users/blue/Projects/director-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Fully offline demo: seed canon, create project, one justified decision
director-bot demo

# Creative meeting (mock brain)
director-bot soul meet "pitch me a cold open for a two-hander thriller" --project 1

# Lookup what S-tier directors did in a situation
director-bot canon lookup "interrogation silence withhold reverse"

# Explicit decision
director-bot decide run "Suspect is silent; detective has a closed file" \
  --project 1 --genre thriller --phase shotlist
```

## CLI map

| Command | Purpose |
|---------|---------|
| `director-bot demo` | Seed + project + decide + verify chain |
| `director-bot doctor` | Paths / health |
| `director-bot canon seed` | Load pocket S-tier corpus |
| `director-bot canon import FILE` | Import work bundle or Scripty export |
| `director-bot canon list` | List works |
| `director-bot canon lookup QUERY` | Digest/moment/card retrieval |
| `director-bot project create TITLE` | New production project |
| `director-bot project phase ID TARGET` | Legal phase transition |
| `director-bot decide run SUMMARY` | Full decision pass |
| `director-bot decide chain ID` | Verify merkle chain |
| `director-bot soul show` | Print soul preamble |
| `director-bot soul meet MSG` | Talk to the director |
| `director-bot soul cycle SUMMARY` | Perceive → decide → remember |

Alias: `dbot` → same entry point.

## Scripty pipe

From the Scripty repo (after a complete pass):

```bash
scripty export-canon 1 -o /tmp/wooded.json \
  --tier S --director "David Fincher" --genre thriller \
  --theme "…" --logline "…"

director-bot canon import /tmp/wooded.json
```

## Soul files

Edit without reinstalling:

- `soul/static/core.md` — identity & non-negotiables  
- `soul/static/taste.md` — gravity wells & distrusts  
- `soul/static/process_notes.md` — phase discipline  

Override directory with `DIRECTOR_BOT_SOUL_DIR`.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `DIRECTOR_BOT_HOME` | `~/.director-bot` | Data root |
| `DIRECTOR_BOT_DB` | `$HOME/director.db` | SQLite path |
| `DIRECTOR_BOT_SOUL_DIR` | repo `soul/static` | Personality markdown |
| `DIRECTOR_BOT_PROVIDER` | auto → `mock` | Brain provider |

## Related tools

| Repo | Role |
|------|------|
| [scripty](https://github.com/CourtReinland/scripty) | Label films → shots/scripts → **export-canon** |
| [lightwriter](https://github.com/CourtReinland/lightwriter) | Pages & scene cards |
| [script2screen](https://github.com/CourtReinland/script2screen) | Realize timeline in Resolve |
| [opensouls](https://github.com/opensouls/opensouls) | Inspiration for WorkingMemory / MentalProcesses |

## Tests

```bash
source .venv/bin/activate
python -m pytest -q
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Status

v0.1.0 — monorepo scaffold: contracts, canon DB, soul, decision engine, adapters, Scripty export pipe. Next: richer corpus curation UI, vector retrieval, live LLM brain, tighter LightWriter/STS file contracts as those tools stabilize.
