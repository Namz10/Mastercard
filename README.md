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

Default Identify uses fixtures (`IDENTIFY_LIVE_SEARCH=false`). LLM default is OmniRoute at `http://127.0.0.1:20128/v1`. Catalog and embeddings live in **Postgres + pgvector** (no Qdrant). 29 seed AttackSpec rows cover T01–T24.

```bash
./run.sh                 # API on :8000
./run.sh --validate      # seed + Identify + pytest
make validate-all        # same gates via Make
```
