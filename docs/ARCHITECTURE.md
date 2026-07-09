# Director-bot Architecture

Embodied AI film director: **canon** (S-tier decision corpus) + **soul** (personality & process) + **decisions** (multi-criteria equilibrium + merkle ledger) + **adapters** (scripty / lightwriter / script2screen).

## Layout

```
director-bot/
├── soul/static/          # hot-editable personality (core, taste, process)
├── src/director_bot/
│   ├── contracts/        # shared schemas (SceneCard, Work, DecisionRecord, …)
│   ├── canon/            # SQLite corpus + query + seed
│   ├── soul/             # WorkingMemory, MentalProcesses, cognitive steps
│   ├── decisions/        # equilibrium + merkle ledger + decide()
│   ├── adapters/         # thin file-based tool hooks
│   ├── config.py
│   └── cli.py
├── tests/
└── docs/
```

## Data flow

```
Scripty (label film)
    │ export-canon JSON
    ▼
Canon DB  ◄── hand seed / LightWriter cards
    │ retrieve digests & moments
    ▼
Director soul (phase FSM)
    │ propose candidates + α creativity blend
    ▼
Equilibrium (weighted Pareto)
    │ commit
    ▼
Merkle decision ledger
    │ handoff packages
    ▼
LightWriter / Script2Screen (later)
```

## Contracts

- **Work** — film/episode with tier, genre, directors, theme, logline
- **SceneCard** — LightWriter-aligned: what happens, relationship delta, plot function, beat
- **ShotMoment** — Scripty-aligned labels + dialogue
- **DecisionDigest** — historical "in situation X, chose Y because Z"
- **DecisionRecord** — live project choice with `parent_hash` + `content_hash`

## Soul (OpenSouls-inspired, not forked)

| Concept | Implementation |
|---------|----------------|
| Static memories | `soul/static/*.md` |
| WorkingMemory | append-only entries, persisted on project |
| MentalProcesses | `ProcessMachine` over `ProjectPhase` |
| cognitiveSteps | `run_cognitive_cycle` → perceive → decide → remember |
| TextBrain | Protocol + `MockBrain` offline twin |

## Decision engine

1. Embed situation as text blob (v1: rapidfuzz retrieval; swap for vectors later)
2. Propose historical candidates from digests/moments + one creative candidate
3. Optional hybrid via `blend_creativity(α)`
4. `pick_equilibrium` — criterion floor → Pareto front → weighted score
5. `commit_decision` — hash chain on `decisions` table

Criteria: `genre_craft`, `style_match`, `continuity`, `originality`, `feasibility`, `emotion`.

## Adapters

File-based only. No edits to LightWriter or Script2Screen required.

- `scripty` — pass rows / export-canon JSON → work bundle
- `lightwriter` — cards JSON + fountain handoff package
- `script2screen` — STS handoff stub manifest

## Storage

`$DIRECTOR_BOT_HOME` (default `~/.director-bot`):

- `director.db` — works, cards, shots, digests, projects, decisions, events
- `projects/<slug>/` — workspace files

## Offline-first

All tests run without API keys. Provider selection defaults to `mock` unless credentials resolve.
