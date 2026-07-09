# Roadmap

## Done (v0.1 → v0.2)

- [x] Monorepo: contracts, canon DB, soul, decisions, adapters
- [x] Scripty `export-canon` pipe
- [x] Merkle decision ledger + multi-criteria equilibrium
- [x] Hybrid retrieval (fuzz + hashed embeddings)
- [x] Live brain seam (mock / anthropic / openai / xai)
- [x] Curation CLI (tier, annotate, digest, bulk import)
- [x] Project cards + series episodes + handoff export
- [x] Vertical-slice `short` pipeline
- [x] Human override → ledger (+ optional digest mint)

## Next

- [ ] Real embedding API option (e.g. xAI / OpenAI embeddings) behind same store
- [ ] Interactive TUI / light dashboard for board + decision chain
- [ ] Deeper LightWriter IPC when that API stabilizes (still file-based for now)
- [ ] Script2Screen wizard prefill from STS handoff (when STS accepts it)
- [ ] Multi-episode arc planner (motif tracking across `episodes`)
- [ ] Agreement metrics: human overrides vs prior auto choices (Scripty-style curve)
- [ ] Corpus scale: 50–100 hand-curated S-tier scene pockets by genre
- [ ] Optional packaging as macOS app shell (after CLI is battle-tested)

## Non-goals (near term)

- Fine-tuning a foundation model on scripts
- Editing LightWriter / Script2Screen source from this repo
- Full game-theoretic Nash solvers per beat
