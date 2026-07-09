# Director-bot Architecture (v0.2)

Embodied AI film director: **canon** + **soul** + **decisions** + **adapters** + **project workspace**.

## Layout

```
director-bot/
├── soul/static/                 # hot-editable personality
├── src/director_bot/
│   ├── contracts/               # shared schemas
│   ├── canon/                   # SQLite corpus, hybrid query, embed, seed
│   ├── soul/                    # WorkingMemory, processes, brain providers
│   ├── decisions/               # equilibrium + merkle ledger + decide()
│   ├── project/                 # cards, series, handoffs
│   ├── adapters/                # scripty / lightwriter / script2screen
│   ├── pipeline.py              # vertical-slice short orchestration
│   ├── config.py
│   └── cli.py
└── tests/
```

## Data flow

```
Scripty export-canon JSON ──┐
Hand seed / curated digests ┼─► Canon DB + hashed embeddings
LightWriter cards JSON ─────┘         │
                                      ▼ hybrid lookup
Director soul (phase FSM) ──► propose → (optional LLM score) → equilibrium
                                      │
                                      ▼ merkle commit
Project workspace ──► LightWriter handoff + STS handoff packages
```

## Hybrid retrieval

1. **rapidfuzz** token-set ratio on text blobs  
2. **Hashed n-gram embeddings** (384-d, pure Python, L2-normalized)  
3. **hybrid_score** = 0.45·fuzz + 0.55·((cos+1)/2)  

`canon reindex` rebuilds the `embeddings` table. Import/seed auto-reindex.

## Decision engine

Criteria players: genre_craft, style_match, continuity, originality, feasibility, emotion.

1. Retrieve digests + moments  
2. Propose historical candidates + creative candidate  
3. Blend with phase α  
4. Optional brain re-score (skipped for mock)  
5. Floor → Pareto → weighted pick  
6. Merkle `parent_hash` / `content_hash` commit  

## Soul

| OpenSouls concept | Here |
|-------------------|------|
| staticMemories | `soul/static/*.md` |
| WorkingMemory | append-only, persisted on project |
| MentalProcesses | `ProcessMachine` over `ProjectPhase` |
| cognitiveSteps | `run_cognitive_cycle` |
| TextBrain | mock / anthropic / openai / xai |

## Project workspace

- `project_cards` — live board (LightWriter-compatible fields)  
- `episodes` — series → child projects  
- `export_project_handoffs` — fountain + LW package + STS stub  

## Storage

`$DIRECTOR_BOT_HOME/director.db` tables: works, scene_cards, shot_moments, decision_digests, embeddings, projects, project_cards, episodes, decisions, events.

## Offline-first

All tests pass with `DIRECTOR_BOT_PROVIDER=mock` and no API keys.
