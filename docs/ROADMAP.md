# Roadmap

## Done (v0.1 → v0.6)

- [x] Monorepo: contracts, canon DB, soul, decisions, adapters
- [x] Scripty `export-canon` pipe
- [x] Merkle decision ledger + multi-criteria equilibrium
- [x] Hybrid retrieval (fuzz + hashed embeddings)
- [x] Live brain seam (mock / anthropic / openai / xai)
- [x] Curation CLI (tier, annotate, digest, bulk import)
- [x] Project cards + series episodes + handoff export
- [x] Vertical-slice `short` pipeline
- [x] Human override → ledger (+ optional digest mint)
- [x] Agreement metrics (overrides vs later auto choices)
- [x] `.env` loader (`export KEY=` and `KEY=`) — never committed
- [x] Embedder provider seam (`hash` / `openai` / experimental `xai`)
- [x] FastAPI dashboard (`director-bot serve`)
- [x] Multi-episode arc planner (motifs, plants/payoffs, plan-ep)
- [x] Expanded seed corpus (multi-genre S/A pockets)
- [x] Deeper LightWriter / STS handoff packages (v2)
- [x] **Model View** — exact system/user/response + retrieval for training regimen
- [x] Brain trace ring (`/api/brain/traces`) on every `complete()`
- [x] Dry-run context preview (meet + decide) without spending tokens
- [x] Elegant multi-pane dashboard (rail nav, glass-box decide)
- [x] macOS Electron desktop shell (`desktop/`, Scripty-style)
- [x] **SSE stream meet** (`POST /api/soul/meet/stream`) — tokens as they arrive
- [x] **Durable brain_traces** table in SQLite (survives restarts)
- [x] Mock/OpenAI/xAI/Anthropic `stream()` implementations

- [x] Dual-key embed auto: OPENAI embed when present (even if chat is xAI)
- [x] Inline board card create/edit/delete in dashboard
- [x] Trace search / filter (q, kind, since, brain) API + Model View UI
- [x] Corpus scale: 50+ scene pockets (`seed_scale.py`)
- [x] Packaging scripts: frozen PyInstaller backend + Electron DMG path

## Next

- [ ] Live Scripty DB import button when scripty is installed
- [ ] Script2Screen wizard auto-prefill once STS documents an import path
- [ ] Real embedding model eval (hash vs API) on held-out situations
- [ ] Trace analytics (agreement vs overrides over time)
- [ ] SSE stream for decide score calls (not only meet)

## Non-goals (near term)

- Fine-tuning a foundation model on scripts
- Editing LightWriter / Script2Screen source from this repo
- Full game-theoretic Nash solvers per beat
