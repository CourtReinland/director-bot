# Roadmap

## Done (v0.1 → v0.3)

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
- [x] Light FastAPI dashboard (`director-bot serve`)
- [x] Multi-episode arc planner (motifs, plants/payoffs, plan-ep)
- [x] Expanded seed corpus (multi-genre S/A pockets)
- [x] Deeper LightWriter / STS handoff packages (v2)

## Next

- [ ] Optional OpenAI embeddings when both XAI (chat) + OPENAI (embed) keys present
- [ ] Richer dashboard (edit cards inline, stream soul meet)
- [ ] Live Scripty DB import button when scripty is installed
- [ ] Script2Screen wizard auto-prefill once STS documents an import path
- [ ] Corpus scale toward 50–100 hand-curated scene pockets
- [ ] macOS app shell (after CLI/dashboard battle-tested)
- [ ] Real embedding model eval (hash vs API) on held-out situations

## Non-goals (near term)

- Fine-tuning a foundation model on scripts
- Editing LightWriter / Script2Screen source from this repo
- Full game-theoretic Nash solvers per beat
