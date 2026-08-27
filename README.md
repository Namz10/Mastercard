# Mastercard — AegisLoop (GFF 2026)

Identify, Generate, and Defend as **one closed-loop** lab. Problem statement: [`MC_PS.md`](MC_PS.md). Landscape: [`HACKATHON_RESEARCH.md`](Docs/HACKATHON_RESEARCH.md).

**Run the product:** [`./run.sh`](run.sh) (Postgres + pgvector, seed, Identify, API).

**Start here for implementation:** [`walkthrough.md`](walkthrough.md)

**Planning is locked.** [`Docs/LOCKED.md`](Docs/LOCKED.md) · Phase 1a: [`Docs/plans/04-phase-1-provider-baseline-identify.md`](Docs/plans/04-phase-1-provider-baseline-identify.md)

| Plan | File |
|---|---|
| Defects and fork winners | [`Docs/plans/00-correct-planning-defects.md`](Docs/plans/00-correct-planning-defects.md) |
| Identify + catalog | [`Docs/plans/01-identify-catalog-lock.md`](Docs/plans/01-identify-catalog-lock.md) |
| Generate, Defend, loop | [`Docs/plans/02-generate-defend-loop-lock.md`](Docs/plans/02-generate-defend-loop-lock.md) |
| Platform, demo, build order | [`Docs/plans/03-platform-demo-build-lock.md`](Docs/plans/03-platform-demo-build-lock.md) |
| Phase 1a (OmniRoute, pgvector, Identify) | [`Docs/plans/04-phase-1-provider-baseline-identify.md`](Docs/plans/04-phase-1-provider-baseline-identify.md) |

`./run.sh` is the single product entrypoint. It reads `.env` (without shell-sourcing it), requires live Tavily + OmniRoute configuration, starts Postgres/pgvector, runs every product gate, then serves FastAPI. Catalog and embeddings live in **Postgres + pgvector** (no Qdrant). 29 seed AttackSpec rows cover T01–T24.

```bash
./run.sh                 # live e2e, then API on :8000
./run.sh --check         # live e2e, then exit
./run.sh --down          # stop Postgres
```

Required `.env`: `IDENTIFY_LIVE_SEARCH=true`, `TAVILY_API_KEY`,
`AEGIS_LLM_PROFILE=omniroute`, `AEGIS_LLM_BASE_URL`,
`AEGIS_LLM_MODEL`, `AEGIS_LLM_API_KEY`, and `DATABASE_URL`.
OmniRoute must already be listening at the configured URL.
