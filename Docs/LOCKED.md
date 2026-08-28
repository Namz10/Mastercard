# LOCKED — AegisLoop planning spine

**These plans supersede competing architecture forks** in `V1_MASTERPLAN.md`, `ARCHITECTURE.md`, `decisions.md` Part B, `identify_pipeline_implementation_2025ee2b.plan.md`, and informal Identify drafts.

**Problem-statement SSOT (never overridden):** [`MC_PS.md`](MC_PS.md), then [`HACKATHON_RESEARCH.md`](HACKATHON_RESEARCH.md).

| File | What it locks |
|---|---|
| [`plans/00-correct-planning-defects.md`](plans/00-correct-planning-defects.md) | Defects, fork winners, naming, status enum, canary vs HoldoutVault |
| [`plans/01-identify-catalog-lock.md`](plans/01-identify-catalog-lock.md) | AttackSpec, T01–T24, OSINT, identify_graph, simulatable_signals |
| [`plans/02-generate-defend-loop-lock.md`](plans/02-generate-defend-loop-lock.md) | Defend **architecture**: loops names, HoldoutVault protocol, Cat 4 offline, no LLM on auth. **Do not implement v1 from this file** |
| [`plans/02-defend-build.md`](plans/02-defend-build.md) | **Defend SSOT (Plan 12):** train/split artifacts, GBDT, row-value rules, Brake, Loop M, Phase 0 Generate HTTP/`fidelity.pass`/live honesty. Overrides Plan 02/03 where 12 lists |
| [`plans/03-platform-demo-build-lock.md`](plans/03-platform-demo-build-lock.md) | Repo, demo, safety, platform build order. **SDV priors sentence superseded by Plan 08**. **Defend code:** Plan 12, not LangGraph `defend_graph` in v1 |
| [`plans/08-generate-world-build.md`](plans/08-generate-world-build.md) | **Generate SSOT:** quiet world, four injectors, Parquet allowlist, population/canary, WorldCalibrator. Overrides Plan 02/03 only where 08 lists |

[`plans/07-generate-benign-world-injectors.md`](plans/07-generate-benign-world-injectors.md) is **superseded**. Do not implement from 07.

Process detail for Identify still lives in patched [`Updated Identify Phase.md`](Updated%20Identify%20Phase.md). [`Identify Phase.md`](Identify%20Phase.md) is **superseded**.

**Do not reopen:** LLM-on-ledger, LLM-on-authorization, dark-web Identify, two taxonomies, Canary Vault as a name, AutoGluon as the live scorer, parallel Identify swarms, Cat 4 on the public API.

**Still unset (not architecture):** Kaggle/GitHub TeamName; verified holdout download URLs; optional overnight AutoGluon host.

Identify is implemented through Plan 03 step 1 + Phase 1a. **Generate (Plan 08 phases A–G) is implemented and sign-off green.** **Next implementation:** [`plans/02-defend-build.md`](plans/02-defend-build.md) Phase 0 then A–E. Do not implement Defend from Plan 02 architecture prose. Plan 11 UI after AuthGate/Brake exist.
