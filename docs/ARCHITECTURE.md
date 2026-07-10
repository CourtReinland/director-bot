# Director-bot Architecture (v0.4)

Embodied AI film director: **canon** + **soul** + **decisions** + **adapters** + **project workspace** + **model view**.

## Layout

```
director-bot/
├── soul/static/                 # hot-editable personality
├── desktop/                     # Electron shell (Scripty-style)
├── src/director_bot/
│   ├── contracts/               # shared schemas
│   ├── canon/                   # SQLite corpus, hybrid query, embed, seed
│   ├── soul/                    # WorkingMemory, processes, brain, trace
│   ├── decisions/               # equilibrium + merkle ledger + decide()
│   ├── project/                 # cards, series, handoffs
│   ├── adapters/                # scripty / lightwriter / script2screen
│   ├── server/                  # FastAPI + static dashboard
│   ├── pipeline.py              # vertical-slice short orchestration
│   ├── config.py
│   └── cli.py
└── tests/
```

## Model View (training regimen)

Every brain `complete(system, user)` is wrapped by `TracingBrain` and logged to a process-local ring (`soul/trace.py`). The dashboard **Model View** pane shows:

| Surface | Meet | Decide |
|---------|------|--------|
| System | soul preamble (`core`+`taste`+`process_notes`) | craft scorer system |
| User | process + working memory + topic | JSON score payload |
| Side | memory sections | retrieval digests/moments + candidates |
| Traces | live ring `/api/brain/traces` | same |

Dry-run: `POST /api/model-view/meet|decide` assembles context without calling the LLM.
Live: `POST /api/soul/meet` returns system/user/response; `POST /api/decide` embeds `model_view`.

### Streaming meet (SSE)

`POST /api/soul/meet/stream` yields Server-Sent Events:

```
event: meta   → full model view (system, user, sections; response empty)
event: token  → {"t": "<delta>"}  (many)
event: done   → full model view with final response + updated memory
event: error  → {"message", "partial", ...}
```

Brains implement optional `stream(system, user) -> Iterator[str]`. Mock chunks deterministically; OpenAI-compat and Anthropic use native streams.

### Durable traces

`brain_traces` SQLite table (dual-written from `BrainTraceStore` when a DB is bound by the server/CLI). List via `GET /api/brain/traces` (`source: sqlite`). Process ring remains a hot cache.

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
