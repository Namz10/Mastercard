# Plan 03 — Platform, demo, safety, and build order (locked)

**Status:** LOCKED.

**Depends on:** [`00-correct-planning-defects.md`](00-correct-planning-defects.md), [`01-identify-catalog-lock.md`](01-identify-catalog-lock.md), [`02-generate-defend-loop-lock.md`](02-generate-defend-loop-lock.md).

**SSOT:** MC_PS submission = public GitHub `TeamName`, `TeamName.docx`, **working web prototype** that shows the closed loop. HACKATHON_RESEARCH §6.3 UI screens; §6.4 feasibility (latency, HITL, ethics, explainability). V1_MASTERPLAN §3.2 layout and §12 ops, except where Plan 00 overrode forks.

---

## 1. Product and repo

| Item | Lock |
|---|---|
| UI product name | AegisLoop |
| GitHub / Kaggle repo name | **TeamName** — **BLOCKER:** freeze the string before making the repo public. Architecture does not depend on it |
| Layout | `apps/web` (Next.js App Router, Tailwind, shadcn/ui), `apps/api` (FastAPI), `packages/{agents,catalog,osint,sim,features,models,policy,eval}`, `data/`, `models/`, `docker-compose.yml`, `Makefile` |
| Package manager | `uv` with lockfile (or Poetry if the team already standardized — pick **uv** unless a lockfile exists) |
| Orchestration | LangGraph supervisor + subgraphs `identify_graph`, `generate_graph`, `defend_graph`, `evolve_graph`. **Deterministic** supervisor (if Identify done → Generate → Defend → Evolve). LLM router only if chat-to-run-lab is added |
| Checkpointer | `langgraph-checkpoint-postgres` |
| Jobs | ARQ + Redis (sim/train 2–10 min) |
| Auth | None or basic demo login — do not spend days |

---

## 2. `LabState` (minimum)

```text
run_id, generation
catalog_ids[], pending_specs[]
sim_config, ledger_uri, graph_snapshot_uri
model_version, metrics{}, miss_ids[]
human_approved: bool
errors[]
```

Checkpoint after every node. Demo uses one `thread_id` so judges can replay.

---

## 3. Docker Compose

**Always on:** `web`, `api`, `worker`, `postgres`, `redis`, `qdrant`.

**Optional profiles:** `ollama`; Langfuse + extra stores **only if RAM allows**. Target **16 GB**. Do not start Neo4j + Langfuse + Ollama 70B together.

Commands: `make up` / `make seed` / `make demo`.

**Seed job:** load YAML catalog; optional Kaggle download of calibrators via `.env` token **not committed**; fit SDV GaussianCopula priors → `data/priors.json`.

---

## 4. Environment

`.env.example`:

- `GROQ_API_KEY` — Scout/Extractor/GapAnalyst (Llama 3.3 70B class structured JSON)
- `TAVILY_API_KEY` — live Identify only
- `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`
- `KAGGLE_USERNAME` / `KAGGLE_KEY` optional
- `IDENTIFY_LIVE_SEARCH=false` default
- `GREYNOISE_API_KEY` optional
- `OSINT_EXTRACTOR=tavily|trafilatura|firecrawl`

Embeddings always local (`sentence-transformers`). Ollama fallback for offline (`llama3.2` / `qwen2.5`). Do not require paid GPT-4o as the only path.

---

## 5. API surface (minimum for the six-click demo)

REST + SSE from FastAPI. Worker owns long jobs.

| Endpoint (logical) | Role |
|---|---|
| `GET /health` | Compose check |
| `GET /catalog` | Atlas rows for threat map |
| `POST /identify/run` | Start identify_graph (fixtures or live) |
| `POST /hitl/{id}/decision` | approve / reject / reject_unsafe / edit |
| `POST /sim/run` | population generation |
| `POST /sim/canary` | `canary_mode` pin |
| `GET /sim/{run_id}/stream` | SSE ledger / graph |
| `POST /score` | AuthGate + Brake (sync, fast) |
| `GET /metrics` | HoldoutVault / generation table |
| `POST /loop/retrain` | Loop M |
| `GET /loop/arms-race` | evasion vs generation on HoldoutVault |

Browser is **not trusted:** it may request drafts and display candidates; promotion, thresholds, and model swap are **server-side**.

Cat 4 `query_automl` is **not** a public route.

OpenAPI is the screenshot source for the `.docx`.

---

## 6. RedBlue Console — six clicks (locked demo script)

Judges must see the loop, not a CSV classifier.

1. **Threat map** — 24 techniques in 5 columns; chips `proposed/open/generating/defending/solved/rejected*`; `confidence_level` badges; `source_tier` chips; evidence spans from local KB.
2. **Run Identify** — fixture FinCEN/RBI article → Scout/Extractor propose 1–3 vectors → HITL Approve (`open`).
3. **Simulate generation N** — world ticks; live ledger + mule graph (react-force-graph or Cytoscape). Fidelity badge.
4. **Decisioning** — score stream, SHAP-style reason codes, **Brake action** (not binary only). APP vs ATO actions distinguishable.
5. **Arms race** — red evasion vs blue PR-AUC / recall **on HoldoutVault (frozen G-test)** across generations. Static blue vs looped blue.
6. **Retrain from misses** — Loop M once; new `model_version`; metrics delta; genuine FPR must not explode.

**Extra tabs (not extra clicks):** HITL queue; analyst copilot (LLM summarizes a case **from reason codes**, is not the detector); coverage map for Loop C.

Charts: Recharts/ECharts. Optional React Flow for LangGraph steps if time.

**Primary UI is Next.js.** Streamlit is a 4-hour backup only, not the submission UI.

---

## 7. Demo resilience (plan the failures)

| Failure | Fallback |
|---|---|
| LLM down | Precomputed Identify results in Postgres |
| Sim too slow | Pre-baked Parquet generation 3 + live scoring only |
| Train too slow | Ship `models/v*.txt` + “replay metrics” |
| No internet | `IDENTIFY_LIVE_SEARCH=false`, Ollama or recorded traces, fixtures |

A winning demo is **resilient**, not maximally live.

---

## 8. Observability and quality

- `structlog` with `run_id` on every line
- Optional Langfuse OSS profile
- `ruff`, `pytest`, `mypy` on `packages/catalog` and `packages/sim` at minimum
- Pandera on ledger batches
- Pydantic models at API, agents, catalog

Skip v1: Kafka, Snowflake, Feast, Elasticsearch, Neo4j, MinIO (unless Parquet must look S3-shaped). MLflow local optional; `metrics.json` is enough.

---

## 9. Safety, dual-use, `SECURITY.md`

MUST:

1. No live rails, real customers, real VPA/PAN/Aadhaar payloads.
2. No images, audio, APKs, outbound phishing.
3. ShadowRail: allowlisted model endpoints; LLM keys **server-side**; spend caps.
4. All generator inputs (KB, misses, demo text) treated as **untrusted**. Output = schema. Verifier is code.
5. Cat 4 offline, not in the public prototype API.
6. Loop cannot promote without HoldoutVault + human (demo auto-click once is explicit theater).
7. Public repo: capability-limited dialogues; capability card; CI grep for live bank URLs and ID-shaped strings.
8. Identify may be exhaustive; Generate is **capability-limited**.
9. Scout never uses dark-web / jailbreak-as-a-service query terms.
10. Unauthenticated generate endpoints, keys in the browser, unbounded LLM spend — **disallowed**.

---

## 10. Over-agenting — do not build

From ARCHITECTURE §13, now binding:

- Identify swarm that browses the open web
- Cat 1 as a ReAct graph builder
- Cat 5 document “crew” inventing letterheads
- Defend agent that chats AutoGluon hyperparameters
- LLM wrapper around every verifier
- Cat 3 victim with tools (leaks the detector)
- Orchestrator LLM that freely reorders Identify / Generate / Defend

LLMs stay where the problem is **strategic**: identity trajectories, multi-turn social engineering under a resistance policy, Cat 4 patches, Identify extraction against a local/allowlisted corpus. Everywhere else LangGraph’s value is checkpoints, interrupts, structured tools, and evaluator-optimizer edges.

---

## 11. Single critical path (replaces V1 §15, ARCH §12, and identify-plan sequences)

Do **not** start with agent-framework yak-shaving. Catalog + ledger + detector first; agents wrap a working lab.

| Step | Ship | Gate |
|---|---|---|
| 1 | Pydantic `AttackSpec` + `data/catalog/seed.yaml` (28–36 rows, all T01–T24) + empty threat-map page | Schema validates; map shows 24 IDs |
| 2 | `rail-rules` + benign ShadowRail + `identity_trajectory` + Parquet/DuckDB API | Reserved IDs only; no live rail message types |
| 3 | `graph_mule` + causal PulseFeatures | Leakage test: full-graph AUC must collapse vs `G(t−)` |
| 4 | v0 `rules/` + AuthGate LightGBM + Brake + metrics dashboard | p99 story + policy actions visible; PR-AUC not accuracy |
| 5 | Cat 3 session flags (+ optional templates) + Cat 5 `doc_beneficiary` | Two Cat 3 numbers not mixed; checksum-pass beneficiary change |
| 6 | `identify_graph` on **fixtures** + HITL | `IDENTIFY_LIVE_SEARCH=false`; 1–3 proposed → `open` |
| 7 | Optional Tavily allowlist + Qdrant | Airplane mode still works |
| 8 | `canary_mode` FinCEN-pinned chain | Catch/miss logged per lifecycle stage |
| 9 | Loop A **offline** + LoopGovernor + arms-race on HoldoutVault | Oracle Guard; G-test non-degradation |
| 10 | Polish UI, `TeamName.docx`, `SECURITY.md`, README clone path, public GitHub **TeamName**, Luma/Kaggle names | Six-click script rehearsed with fallbacks |

If ahead of schedule: ONNX Runtime scoring, GraphSAGE blend, Langfuse, React Flow supervisor map, Tide AML graphs, stretch CNP proxy injector, MinIO, Playwright e2e of the six clicks.

---

## 12. Write-up (`TeamName.docx`) structure

Name file `TeamName.docx`. List all members’ full names and Luma/Kaggle emails.

1. Problem: closed loop, APP vs stolen, India UPI + network feasibility
2. Identify: 24/5, tier scoring, corroboration honesty, citations, Atlas schema
3. Generate: PEV pattern, calibrators (honest limits), `canary_mode` vs HoldoutVault
4. Defend: rules → AuthGate → Brake; metrics table; latency
5. Loop: generations, Cat 4 offline, HoldoutVault so the loop cannot grade its own homework
6. Feasibility: 50–300 ms, HITL, synthetic-only ethics, explainability
7. What we did not do: dark web, live honeypots, LLM-on-path, 24 generate pipelines

**Deck one-liners (locked):**

- Generate: *One verification architecture, variable agent thickness — matched to what each fraud type requires for fidelity.*
- Defend: *One AutoML family, two feature views, a policy head — matched to what each rail exposes at payment time.*
- Loop: *The loop cannot grade its own homework.*

---

## 13. README (clone path)

Until code lands, README links [`LOCKED.md`](../LOCKED.md) and `plans/`. After step 1 of the critical path, README must include:

- 10-minute path **without** Tavily (fixtures)
- `make up` / `make seed` / `make demo`
- `python -m packages.sim --seed 42 --n 50000` (or equivalent)
- `python -m packages.models.train`
- No secrets in git

---

## 14. Evaluation criteria mapping

| Criterion | Mechanism |
|---|---|
| Diversity of attacks | Seed all T01–T24 + Identify agent + 5 columns |
| Fidelity of simulation | Calibrators + PSI/KS gate + APP vs CNP/ATO labels |
| Detection efficacy | PR-AUC, FPR@recall, per-family, latency |
| Novelty | Multi-agent lab + co-evolution + graph features + Brake |
| Real-world feasibility | AuthGate latency, hold vs decline, HITL, no LLM on-path, India APP hold analog |

---

## 15. Remaining non-architecture blockers

1. **TeamName** string (Kaggle + GitHub).
2. Holdout URL/license ticks (Plan 02 §10).
3. Optional AutoGluon overnight machine.

No other design questions are open. Implementation starts at §11 step 1.
