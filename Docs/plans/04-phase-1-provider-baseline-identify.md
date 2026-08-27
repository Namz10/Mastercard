# Phase 1 — OmniRoute, Postgres+pgvector, Baseline Repair, Identify

**Parent:** `AegisLoop Master Implementation Plan`

**Quality-gate result:** first draft was **NO-GO**. This file is the amended execution plan. Work **1a** to completion before 1b or any later phase.

**Scope 1a:** Reproducible install, **Postgres as the only datastore** (relational + vectors via **pgvector**), OmniRoute as primary LLM endpoint, Identify correctness, golden fixtures, **unmocked Librarian**, `./run.sh` end-to-end.

**Scope 1b (after 1a is green):** Knowledge-base tools, LangGraph checkpoint/interrupt HITL, frozen Identify evaluation corpus.

This phase does not implement payment simulation, fraud scoring, or the web application.

## 0. Pinned decisions

1. **OmniRoute contract.** Default `AEGIS_LLM_PROFILE=omniroute` with `AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1` and `AEGIS_LLM_MODEL=auto`. Groq is an explicit opt-in profile only. Do not silently pick another model or provider on 404.
2. **Postgres only (no Qdrant).** Catalog rows, HITL, OSINT chunks, and catalog-dedup embeddings live in the same Postgres instance with the `vector` extension. Image: `pgvector/pgvector:pg16`. Python: `pgvector`. Qdrant is retired from compose, CI, env, and Identify.
3. **Single status authority.** One `transition_atlas_status()` with a legal transition matrix.
4. **Offline extraction.** Weak or unknown articles **abstain** (no proposal). Never default to T13. Fixture mode never substitutes FinCEN text for unrelated URLs.
5. **Real product path.** `make validate-all`, `./run.sh`, and Identify Librarian persist to Postgres. Do not patch `merge_proposed_spec`. Deterministic rule extraction when OmniRoute is down is a **product fallback**, not a test mock. HTTP client unit tests may use an in-process transport to cover status codes without a paid provider.
6. **1a exit is honest and small.** Blocking: clean-clone `./run.sh` / `make validate-all` against real Postgres+pgvector, OmniRoute transport tests, opt-in `live_llm`. Not blocking in 1a: KB tools, LangGraph checkpointer, frozen eval corpus, 95%/80% mutation scores.
7. **Repro first.** `uv.lock` + GitHub Actions with **Postgres+pgvector only** (no Qdrant). `.env.example` defaults `IDENTIFY_LIVE_SEARCH=false` and documents `AEGIS_LLM_*`.

## 1. Completion standard (1a)

Phase 1a is complete only when:

- a clean clone installs and passes offline validation with **one** Docker service: Postgres (pgvector);
- OmniRoute is the default LLM endpoint; Groq is not selected unless explicitly configured;
- deterministic extraction still works when OmniRoute is absent (abstain if the article is weak);
- Identify proposals are schema-valid, source-traceable, stored in Postgres, and abstain on weak input;
- FinCEN fixture substitution, illegal status jumps, and unwired catalog dedup are gone;
- catalog cosine dedup queries **pgvector**, not an in-memory-only store;
- REST HITL revalidates every edit with Pydantic;
- `./run.sh` brings up Postgres, seeds Atlas + embeddings, runs Identify, and starts the API;
- golden fixtures cover schema, safety, source attribution, and abstention;
- commands and evidence are recorded in `Docs/reports/`.

Phase 1b is complete when KB tools, checkpointed HITL, and the frozen eval corpus have their own tests and evidence. Do not claim “Identify finished” after 1a alone.

## 2. Required execution cycle for every implementation slice

1. Confirm the behavioral contract and files in scope.
2. Add tests that fail for the missing behavior.
3. Implement the smallest cohesive change.
4. Run targeted tests, Ruff, and mypy for touched modules.
5. Run the complete offline regression suite against real Postgres.
6. Run a defect-first `/code-review`. Record findings; this is not a CI gate.
7. Fix every confirmed blocking finding and add a regression test for each defect.
8. Repeat targeted tests and the full offline suite.
9. Append commands, outcomes, and residual risks to the phase evidence report.

## 3. Pre-existing defects 1a must inventory (Slice A)

| Defect | Location |
|--------|----------|
| No `uv.lock`, no `.github/workflows`, `make install` uses pip | `Makefile`, `pyproject.toml` |
| `make up` sleeps 3s; extra Qdrant service | `Makefile`, `docker-compose.yml` |
| `.env.example` sets `IDENTIFY_LIVE_SEARCH=true`; Groq-only vars | `.env.example` |
| Groq-only LLM stack; 404 model fallback; `.env` file key parse | `packages/agents/llm.py` |
| FinCEN body used for any offline non-fixture URL | `packages/agents/nodes/extractor.py::_body_for_url` |
| Weak input defaults to T13 | `rule_based_extract` else-branch |
| LLM overlay filled from rule skeleton | `enrich_groq_extract` |
| Duplicate unguarded status writers | `query.set_atlas_status`, `librarian_db.set_atlas_status` |
| HITL edit skips `AttackSpec.model_validate` | `apps/api/routes/identify.py::hitl_decision` |
| `AttackSpec.status` default `open` | `packages/catalog/models.py` |
| Catalog cosine dedup unwired / memory-only | `max_catalog_similarity` |
| Merge by first `open` `technique_id` | `find_merge_target` |
| Confidence: two tier-≤3 URLs can confirm without two orgs each at ≤3 | `tier_scorer.score_spec_sources` |
| `validate-all` patches `merge_proposed_spec` | `Makefile` |
| Second vector DB (Qdrant) for a workload Postgres can hold | `vector_store.py`, compose |

Do not read `.env` or secret values.

## 4. Phase 1a ordered spine

### Slice C — Reproducible install (Postgres+pgvector only)

- Add `uv.lock`, `uv sync`, fix `Makefile` `install`.
- Compose: `pgvector/pgvector:pg16`; `CREATE EXTENSION vector` on init; health-based `make up` (`--wait`); drop `sleep 3`; **remove Qdrant**.
- Tables: `osint_chunks` and `catalog_embeddings` with `vector(384)`.
- `.env.example`: `IDENTIFY_LIVE_SEARCH=false`, `AEGIS_LLM_*`, `DATABASE_URL`; no `QDRANT_*`.
- GitHub Actions: Postgres+pgvector service container only.
- `./run.sh`: install (if needed), start Postgres, seed Atlas + embeddings, run Identify, start API, smoke `/health` `/ready` `/identify/run`.

**Exit:** contributor runs `./run.sh` from README without Qdrant. CI and Make use the same Postgres.

### Slice D — Active documentation (with Slice C)

- README / walkthrough: pgvector, OmniRoute, `./run.sh`, 29 seed rows.
- Plan 03 §4: `AEGIS_LLM_*` primary; `DATABASE_URL`; drop `QDRANT_URL` as required.
- Mark historical Qdrant/Groq docs as superseded for Identify storage/LLM.

### Slice B — Provider-neutral LLM client

Reimplement under `packages/agents/llm/` (axolotl **shape only**, no import). Profile `omniroute` → `:20128/v1`.

**Must migrate:** `extract_from_document`, extractor, `identify_config`, `AgentSettings`, `scripts/validate_all_live.py`.

**Forbidden:** `.env` file key parse in LLM code; Groq names on generic paths; silent model fallback on 404; mixing `GROQ_*` and `AEGIS_LLM_*` without error.

**Transport tests:** in-process HTTP matrix (200/4xx/5xx/timeout/malformed/redaction/loopback). Opt-in `pytest -m live_llm` against a running OmniRoute.

When OmniRoute is down: **abstain or rule extract**, never invent T13 from empty articles.

### Slice F — Scout / fetch provenance (P0)

- Fixture lookup keyed by URL only; RBI must not receive FinCEN body.
- Per-document failures observable.

### Slice G — Extraction abstention (P0)

- Remove T13 default.
- Do not overlay a full `rule_based_extract` skeleton onto LLM JSON.
- Scout `source_url` remains authoritative.

### Slice E — Status and schema (P0)

- `transition_atlas_status()` used by Identify, Defend, policy.
- HITL edit runs `AttackSpec.model_validate`.
- New extractions default `status=proposed`. Defend miss `defending → open` remains legal.

### Slice I — Confidence (P0)

- Confirmed iff one source tier 1–2, **or** ≥2 independent organizations **each** with a source tier ≤3.

### Slice H — Dedup (P0, pgvector)

- `preload_catalog_embeddings` on seed writes `catalog_embeddings`.
- Grounder/librarian call `max_catalog_similarity` (SQL cosine).
- `find_merge_target`: exact match, then vector ≥ 0.92. Not “first open technique_id”.

### Slice L — API safety

- `/ready` booleans + profile/model names, never keys.
- Redact secrets in errors/logs.

### Slice K (1a) — REST HITL + Postgres

- Field-level diff vs nearest catalog row.
- Transactions; no Librarian mocks.

### Golden fixtures + final 1a

- Provenance, abstain, unsafe reject, schema-valid persist, T01–T24 seed retained.
- `make validate-all` and `./run.sh` **without** patching Librarian.

## 5. Phase 1b (after 1a)

- Slice J: `kb_search` / `kb_get_chunk` / `upsert_taxonomy` on the **same** pgvector tables.
- Slice K remainder: LangGraph interrupt + Postgres checkpointer.
- Slice M: frozen eval corpus; coverage/mutation **targets**.

## 6. Blocking commands (1a)

- `./run.sh` (or `make up seed` + Identify + API smoke)
- Ruff + mypy on touched modules
- pytest including transport tests and unmocked Librarian
- `make validate-all` on a clean clone with Postgres up
- Evidence in `Docs/reports/`

## 7. Explicit defer (not 1a)

- KB search APIs, LangGraph interrupt, frozen eval corpus
- Blocking 95%/80% coverage/mutation
- Production GreyNoise/Shadowserver
- Web UI, payment simulation, fraud scoring, Redis/ARQ
- **Qdrant** (do not reintroduce)

## 8. Go / no-go

**GO (1a)** when `./run.sh` and clean-clone `make validate-all` pass on real Postgres+pgvector, OmniRoute is default, Librarian is unmocked, and P0 defects are gone.

**NO-GO** if Qdrant is still required, Groq is the default provider, pytest/validate-all only pass with mocked Librarian, weak input invents T13, unrelated URLs get FinCEN text, secrets leak, or illegal status transitions remain.
