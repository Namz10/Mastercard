# V1 Masterplan — Mastercard AI Defense Lab

**Product name (working):** `AegisLoop` — a closed-loop red/blue multi-agent system that **identifies** emerging GenAI-powered payment fraud, **generates** high-fidelity simulations, and **defends** with a low-false-positive detector that retrains on its own misses.

**This document is the build contract.** It follows the problem statement word-for-word: one end-to-end red-teaming AI system, three pillars, one feedback loop, a runnable repo, a `.docx` walkthrough, and a presentable web prototype.

Companion docs: `MC_PS.md` (the brief), `HACKATHON_RESEARCH.md` (why this exists).

---

## 0. Non-negotiables from the problem statement

| Brief requirement | How this plan meets it |
|-------------------|------------------------|
| Identify novel emerging GenAI-powered **payment** fraud | Allowlisted OSINT + structured taxonomy across rails/channels/social-engineering surfaces |
| Breadth **and** depth, grounded in real payments | Attack catalog with rail, kill-chain stage, failed control, features, citation |
| Generate / simulate **at scale**, **high fidelity** | Calibrated world model + typed attack injectors (not LLM-written ledgers) |
| Defend: detect, **flag**, **mitigate**; max precision/recall/F1/AUC; **low FP** on genuine | Score + policy actions; PR-AUC and FPR@TPR as primary metrics |
| Attacks become training ground; gaps feed new attacks | Co-evolution loop with checkpointed LangGraph state |
| Novelty | Agents + synthetic flywheel + graph features + arms-race UI |
| Live-payments feasibility | Compact on-path scorer (~tens of ms); LLM **off** the authorization path |
| Code + `TeamName.docx` + web UI | Monorepo + FastAPI + Next.js |

**Safety (hackathon-winning and legal):** simulate **synthetic customers and synthetic rails only**. Do not send real phishing, do not clone living people, do not call criminal LLMs, do not scrape the dark web, do not produce exploit payloads. Identify = **public typology research**. Generate = **labeled synthetic events**. Defend = **detection and intervention policy**.

---

## 1. One-sentence architecture

A **LangGraph state machine** runs Identify → Generate → Defend → Gap-analysis → mutate attacks → repeat; **Postgres + Parquet + Qdrant** hold catalog, ledgers, and OSINT; a **deterministic payment world simulator** emits transactions; **LightGBM (+ graph features)** scores them in milliseconds; a **Next.js lab UI** shows the loop.

Hermes is **not** the orchestrator. Nous Hermes Agent (2026) is a **personal assistant runtime** (Telegram/CLI, self-writing skills). You need a **product with typed state, HITL, retries, and a demoable graph**. That is [LangGraph](https://github.com/langchain-ai/langgraph). Optional later: copy Hermes’ *skill markdown* idea for attack playbooks — as **files you version in git**, not as the runtime.

---

## 2. Overall workflow (the closed loop)

```
                    ┌─────────────────────────────────────────────┐
                    │              HUMAN GATE (HITL)              │
                    │  approve new vectors / go-live a model      │
                    └──────────────────────┬──────────────────────┘
                                           │
┌──────────┐   OSINT    ┌────────────┐     │     ┌─────────────┐
│ Sources  │───────────▶│ IDENTIFY   │─────┴────▶│ Attack      │
│ RSS/API  │            │ crew       │           │ Catalog     │
└──────────┘            └────────────┘           │ (Pydantic)  │
                                                 └──────┬──────┘
                                                        │ specs
                                                 ┌──────▼──────┐
                     calibrators (PaySim etc.)──▶│ GENERATE    │
                                                 │ World+Inject│
                                                 └──────┬──────┘
                                                        │ Parquet ledger
                                                 ┌──────▼──────┐
                                                 │ DEFEND      │
                                                 │ feat→score  │
                                                 │ →policy     │
                                                 └──────┬──────┘
                                                        │ misses + metrics
                                                 ┌──────▼──────┐
                                                 │ CO-EVOLVE   │
                                                 │ mutate spec │
                                                 │ retrain     │
                                                 └──────┬──────┘
                                                        └──▶ next generation
```

### 2.1 Happy-path demo (what judges click)

1. Open **Threat map** — 20+ approved vectors across card, A2A/UPI-like, onboarding, ATO, BEC, mule.
2. Click **Run Identify** — agent ingests a FinCEN/RBI-style alert, proposes 1–3 new vectors, waits for Approve.
3. Click **Simulate generation N** — world ticks; live ledger + mule graph stream in the UI.
4. **Scores** appear with SHAP-style reasons and a **mitigation** (approve / step-up / hold / decline / notify).
5. **Arms race** chart: red evasion vs blue PR-AUC across generations.
6. Click **Retrain from misses** — new model version, metrics delta, still low FPR on holdout genuine.

If that six-step story works, you have satisfied Identify, Generate, Defend, and the feedback loop.

### 2.2 Batch vs online (feasibility story)

| Path | Latency budget | What runs |
|------|----------------|-----------|
| **Offline lab** (Identify, sim, train, LLM case writeup) | seconds–minutes | LangGraph, Groq/Ollama, Optuna |
| **Online decisioning** (prototype of live payments) | **target ≤ 50 ms** model, **≤ 300 ms** end-to-end like Mastercard DI | LightGBM + precomputed graph stats, no LLM |

Never put an LLM on the authorization hot path. Mastercard’s public DI story is tens of milliseconds. Judges will smell a 2-second GPT score.

---

## 3. System architecture

### 3.1 Logical components

```
[Next.js Lab UI]
        │  REST + SSE
[FastAPI Gateway]
        │
        ├── LangGraph App (orchestrator + agents)
        ├── Simulation Engine (SimPy + NetworkX)
        ├── Feature Service (pure Python, deterministic)
        ├── Model Registry (MLflow local / filesystem)
        ├── Policy Engine (rules + score thresholds)
        └── Job Worker (ARQ + Redis)  ← long sims & training
        │
        ├── PostgreSQL     catalog, runs, scores, LangGraph checkpoints
        ├── DuckDB/Parquet analytical txns
        ├── Qdrant         OSINT embeddings
        └── Redis          queues, SSE fan-out
```

### 3.2 Recommended repo layout

```
TeamName/
  apps/web/                 Next.js UI
  apps/api/                 FastAPI
  packages/agents/          LangGraph graphs, tools, prompts
  packages/catalog/         Pydantic AttackSpec, seed taxonomy
  packages/osint/           allowlisted fetchers (no open crawl)
  packages/sim/             world, agents, injectors, fidelity metrics
  packages/features/        feature engineering (shared train/serve)
  packages/models/          train, eval, export (LightGBM)
  packages/policy/          mitigation mapping
  packages/eval/            metrics, reports for .docx
  data/                     parquet, catalogs (git-lfs or download script)
  models/                   versioned .txt / .onnx
  docker-compose.yml
  Makefile
  README.md
```

---

## 4. Multi-agent design (who does what)

### 4.1 Framework choice (decision, not a bake-off)

| Option | Verdict for *this* hackathon |
|--------|------------------------------|
| **LangGraph** | **Use as the spine.** Stateful graph, cycles (co-evolution), Postgres checkpointer, human interrupt, streaming to UI, Python+TS, used in production finance orgs. |
| **PydanticAI** | **Use inside nodes** for structured `AttackSpec` extraction (typed, validated). Not the whole app. |
| **CrewAI** | Fast roles; weaker durable state. Skip unless you are prototyping Identify in a weekend spike, then port to LangGraph. |
| **AutoGen / AG2** | Chatty research debates. Optional one-off for Identify brainstorm; do not orchestrate the lab. |
| **OpenAI Agents SDK** | Clean handoffs but vendor-shaped. Avoid lock-in; Groq/Ollama matter for cost. |
| **Hermes Agent** | Wrong abstraction (install-and-talk personal agent). **Do not build the product on it.** Optional: Agent Skills markdown format for playbooks. |
| **LangChain Deep Agents (2026)** | Optional later for Identify subagents; v1 stay on explicit LangGraph nodes so you can debug on stage. |

**Orchestration pattern:** one **supervisor graph** with subgraphs `identify_graph`, `generate_graph`, `defend_graph`, `evolve_graph`. Shared `LabState` (TypedDict / Pydantic).

### 4.2 Agents (roles)

Keep the cast small. Many agents = flaky demo.

| Agent | Pillar | LLM? | Job |
|-------|--------|------|-----|
| **Scout** | Identify | Yes | Query allowlisted search/RSS; return URLs + snippets |
| **Extractor** | Identify | Yes + Pydantic | Turn article → candidate `AttackSpec` JSON |
| **Grounder** | Identify | Light LLM + rules | Reject vectors that are not *payments* or not *GenAI-powered*; require rail + failed control |
| **Librarian** | Identify | No | Dedup vs catalog (embedding + canonical id); merge depth |
| **WorldSim** | Generate | No | Tick accounts, devices, merchants, clocks |
| **Injector** | Generate | No (params may come from LLM) | Apply approved attack programs to the world |
| **FidelityCritic** | Generate | Optional | Compare sim stats vs calibrator datasets; fail job if drift too high |
| **FeatureBuilder** | Defend | No | Point-in-time features, no leakage |
| **Scorer** | Defend | No | LightGBM probability |
| **Explainer** | Defend | Optional | SHAP → short reason codes; LLM only polishes analyst text |
| **Policy** | Defend | No | Map score + red flags → action |
| **GapAnalyst** | Loop | Yes | Cluster misses; propose spec mutations |
| **Trainer** | Loop | No | Retrain/calibrate; write model version |
| **Supervisor** | All | Routing LLM or rules | Advance the graph; enforce HITL |

**v1 routing:** Supervisor can be **deterministic** (if Identify done → Generate → Defend → Evolve). Use an LLM router only if you add chat-to-run-lab. Deterministic supervisor = fewer on-stage failures.

### 4.3 `LabState` (minimum fields)

```text
run_id, generation
catalog_ids[], pending_specs[]
sim_config, ledger_uri, graph_snapshot_uri
model_version, metrics{}, miss_ids[]
human_approved: bool
errors[]
```

Checkpoint after every node (`langgraph-checkpoint-postgres`).

---

## 5. Where the LLM goes vs what stays deterministic

This is the most important engineering choice in the project.

### 5.1 LLM **on** (offline, bounded, structured)

- Scout queries and source summaries
- Extractor → **JSON AttackSpec only** (schema + retry on validation fail)
- GapAnalyst hypotheses (“increase seasoning days”, “switch cash-out to crypto MCC”)
- Analyst case narrative in the UI
- `.docx` draft sections (you still edit)

Use **structured outputs** (Pydantic / JSON schema). Temperature ≤ 0.2 for extractors. Cite `source_url`.

### 5.2 Deterministic **always** (no LLM)

- Payment **ledger** (amounts, timestamps, balances, graph edges)
- RNG (seeded `numpy` / `pcg64`)
- Feature math, aggregations, graph metrics
- Model train/predict
- Thresholds and policy
- Metrics (AUC, F1, FPR)
- Dedup keys, ISO-like field validation
- Docker/build

If an LLM writes a transaction amount, **fidelity is dead** and judges will not trust the detector.

### 5.3 Hybrid (LLM proposes, code executes)

Attack **parameters** (e.g. `mule_fan_in=12`, `voice_clone_flag=true` as a **simulated signal**, not real audio) may be proposed by GapAnalyst, then **clamped** by a schema (`min/max`, allowed rails). Injector code is the source of truth.

---

## 6. Identify pillar — emerging-attack intake (not “scrape the internet”)

The brief says **research and map**. Unrestricted scraping is brittle, often ToS-illegal, and will pull junk. **Allowlisted collection + structured extraction** is how you get breadth *and* citations.

### 6.1 Source allowlist (v1)

Fetch **only** these classes:

| Class | Examples | Method |
|-------|----------|--------|
| Regulator alerts | [FinCEN news](https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial), FTC, FBI IC3, RBI press, FCA, ECB card-fraud notes | Official RSS/HTML **allowlist** |
| Industry research | Wipro, Feedzai, BNY, Amazon payments blog, Deloitte Insights | Tavily **domain-filtered** search or saved HTML |
| Academic | [arXiv:2410.09066](https://arxiv.org/abs/2410.09066), arXiv `cs.CR` query `payment fraud generative` | arXiv API |
| News (optional) | Reuters/FT/BBC on deepfake payments | Tavily with `include_domains` |

**Do not:** dark-web forums, paste sites, unrestricted Google scrape, credentialed bank portals, headless browsers against Cloudflare for fun.

### 6.2 Tooling (free / freemium)

| Job | Use | Why |
|-----|-----|-----|
| Search | **[Tavily](https://tavily.com)** Search + Extract (`langchain-tavily`) | Built for agents; domain filter; extract clean text; free tier |
| Fallback search | DuckDuckGo `ddgs` or official RSSHub | Zero cost if Tavily quota dies |
| Fetch | `httpx` + `trafilatura` | Best open-source article text extraction |
| RSS | `feedparser` | FinCEN/FTC/arXiv |
| Crawl a **single** allowlisted site | Tavily Crawl/Map **or** skip | Prefer Extract on known URLs |
| Embed | `sentence-transformers` `BAAI/bge-small-en-v1.5` (local, free) | Dedup + RAG |
| Vector store | **Qdrant** (Docker, OSS) | Filters on `source_type`, `date` |
| Structured extract | LLM (Groq Llama 3.3 70B or local Qwen2.5) + Pydantic | Catalog rows |

**Tavily Research API** (structured `output_schema`) is useful for a weekly “what’s new in GenAI payment fraud” job. Still **validate** with Grounder rules.

### 6.3 AttackSpec schema (this is your diversity score)

Every vector **must** fill:

```text
id, title, one_liner
genai_modality: text | voice | video | document | bot | poisoning | mixed
rail: card_cnp | card_cp | a2a_rtp | upi_like | ach | wire | crypto_offramp | onboarding
lifecycle: kyc | auth | initiation | authorization | settlement | cashout
social_surface: email | sms | voice | video_call | in_app | merchant
failed_control: liveness | voice_bio | otp | static_kyc | velocity_rule | human_callback | ...
is_authorized_push: bool          # APP/scam vs stolen credential
entities: victim, mule, merchant, device, ...
simulator: injector_id + param_schema
features_expected: [device_mismatch, new_payee, fan_in, ...]
citations: [url]
novelty_notes
status: proposed | approved | rejected
```

Seed the catalog **by hand** from `HACKATHON_RESEARCH.md` (25–40 vectors) **before** the agent runs. Agents add *more*. A catalog that starts empty will look thin on stage.

**Diversity target for v1:** ≥ 8 families × ≥ 2 variants:

1. Synthetic ID / deepfake KYC  
2. Voice-clone ATO / call-center  
3. APP / impersonation scam (India-relevant)  
4. BEC / deepfake CFO (commercial)  
5. CNP / bot + stolen or synthetic card  
6. Mule / funnel cash-out  
7. Seasoned synthetic bust-out  
8. Detector probing / poisoning (Amazon risk — simulate **label noise**, do not attack third parties)

### 6.4 Grounder rules (deterministic quality bar)

Reject if any of: no payment rail; “GenAI” only as buzzword; no failed control; duplicate cosine > 0.92 to existing title+rail; describes malware/exploit steps (store as **high-level typology only**).

---

## 7. Generate pillar — simulation (fidelity first)

### 7.1 Design principle

Two layers:

1. **World model** — population of customers, merchants, devices, accounts, payee graphs, circadian spend. Calibrated to **public synthetic** datasets.  
2. **Attack programs** — discrete, testable injectors keyed by `injector_id`. They **perturb** the world (new device, new payee, burst, mule fan-in, “liveness_glitch=true” as a **feature flag**, not a real deepfake file).

This matches Wipro’s “synthetic fraud scenarios” and the brief’s “closely resemble real payment data.”

### 7.2 What to use (and what not to)

| Need | Choose | Skip / why |
|------|--------|------------|
| Discrete-event clock | **SimPy** | Mesa is more ABM-UI; SimPy is faster for ledgers |
| Entity graph | **NetworkX** in sim; export JSON for UI | Neo4j Community is extra Docker RAM; add only if graph demo is the star |
| Tabular resemblance | **SDV** (GaussianCopula first; CTGAN if you have GPU time) | Don’t CTGAN the whole ledger every demo |
| Card-like calibrator | **Sparkov** (Kaggle “Credit Card Transactions Fraud Detection”) | Richer fields than PCA-only European set |
| A2A / mobile-money calibrator | **PaySim** ([Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) / [GitHub](https://github.com/EdgarLopezPhD/PaySim)) | Maps to UPI-like P2P + cash-out |
| Bank payments calibrator | **BankSim** | Smaller; good for MCC/age |
| E-comm + device | **IEEE-CIS** (Kaggle) | Optional; anonymized; heavy; TOS |
| AML graph extra | **Tide** generator ([paper 2026](https://arxiv.org/abs/2603.01863) / related GitHub) | Nice for mule graphs if time |
| IBM TabFormer / IBM SDS | Optional if downloadable without paid IBM Z packaging | Don’t block v1 on it |
| Real bank data | **Never** | Privacy + disqualification risk |

**Do not** use PaySim/Sparkov **as the product**. They lack GenAI typology labels (voice clone, APP, deepfake KYC). Use them to **fit amount/time/MCC/device priors**, then **your** simulator emits the labeled GenAI attacks.

### 7.3 Ledger schema (aim at live-payments look)

Think **authorization message + identity + device + graph**, not `amount, class`.

Suggested columns (synthetic, no real PAN):

```text
txn_id, event_time, rail, msg_type
payer_id, payee_id, merchant_id, mcc, channel
amount, currency, country_payer, country_payee
device_id, ip_country, is_new_device, is_new_payee
auth_method: pin | otp | biometric | none
is_customer_authorized   # True for APP
kyc_level, account_age_days, seasoning_txn_count
graph: payer_degree, payee_fan_in_1h, shared_device_cluster
signals (simulated, not real media):
  voice_match_score, liveness_score, doc_consistency, deepfake_tool_flag
label_fraud, label_family, attack_id, generation
```

Store **Parquet partitioned by run_id/generation** (PyArrow). Register views in **DuckDB** for the API.

### 7.4 Injector examples (programs, not prompts)

- `app_impersonation`: victim pays **new** payee (mule) after `social_pressure=high`; amounts in “urgent” tail; `is_customer_authorized=true`; device may be **normal** (hard case).  
- `synth_kyc_mule`: new account, doc/liveness anomalies, inbound many small credits, outbound crypto/gambling MCC (FinCEN red flags).  
- `voice_ato`: new device + failed/skipped MFA + velocity vs profile.  
- `cnp_bot`: many cards, many MCCs, short inter-arrival, device clustering.  
- `bec_wire`: commercial payer, new beneficiary, amount in 5–6 figures, callback_skipped.

Scale = **repeat with RNG**, not LLM loops.

### 7.5 Fidelity checks (you will be scored on this)

Run after each sim (SDMetrics / SDV quality + custom):

- KS or PSI on amount, hour-of-week vs Sparkov/PaySim  
- Fraud rate in a realistic band (e.g. 0.1–2% depending on rail)  
- Graph: mule `fan-in` vs genuine payees  
- No future leakage (features at time t use only ≤ t)

Fail the Generate node if PSI > threshold. Show this badge in the UI (“fidelity: pass”).

### 7.6 Streaming for the demo

Worker writes batches to Redis Stream or just **SSE from FastAPI** reading Parquet as it lands. Kafka is overkill for a hackathon.

---

## 8. Defend pillar — detect, flag, mitigate

### 8.1 Problem formulation (matches the brief)

- **Primary:** binary fraud at **authorization / payment-initiation** time.  
- **Secondary:** `label_family` (for analyst UI, not required for approve/decline).  
- **Output:** `score ∈ [0,1]`, `reason_codes[]`, `action`.

Actions (mitigation, not just classify):

| Action | When |
|--------|------|
| `approve` | score < T_low |
| `step_up` | MFA / liveness / biometric |
| `hold` | APP / new payee / high amount (RBI-style cooling analog) |
| `notify` | customer push |
| `decline` | high stolen-credential score |
| `case` | queue for analyst |

APP should **prefer hold/notify/step-up** over blind decline (customer *meant* to pay). Stolen CNP can decline. This is live-payments literacy.

### 8.2 Model stack (peak for the time you have)

**v1 production detector (build this first):**

- **LightGBM** (or XGBoost) on tabular + **graph feature preprocessor** (degrees, shared devices, 1h/24h velocity, payee age).  
- Imbalance: `scale_pos_weight` + **PR-AUC** as Optuna objective (not Accuracy).  
- Time-based split (train past, test future generations **and** a frozen genuine holdout).  
- **SHAP** (`shap` TreeExplainer) for reason codes.  
- Export: native `.txt` or **ONNX** via `onnxmltools` for a latency story.

Why not a huge GNN as v1: PyG/DGL R-GCN is the *Mastercard-like* story, but trees + graph features often match GNN quality on fraud graphs and stay in **milliseconds on CPU**. Literature (IEEE-CIS SageMaker DGL, Elliptic hybrids, Tide GFP+LightGBM) supports **trees with graph features** as the strong baseline.

**v1.5 if time:**

- LightGBM + **sequence** features (last-k amounts)  
- Optional **GraphSAGE** on a sampled ego-graph for mule-heavy families; **blend** scores  
- Isolation Forest / **PyOD** as unsupervised complement for novel generation-0 attacks  

**Do not v1:** fine-tune an LLM as the classifier; LSTM on raw ledger without features; AutoGluon 4-hour fits on a laptop during the demo.

### 8.3 “Train a model for each attack” — do this instead of AutoResearch

**Do not** run Sakana-style AI Scientist / open-ended AutoResearch per typology. It will not finish, will not be reproducible, and is not how issuers deploy.

**Do:**

| Layer | What |
|-------|------|
| **One global scorer** | All families; features include signals that differ by family |
| **Family adapters (optional)** | Separate LightGBM for `APP` vs `CNP` vs `ATO` if PR-AUC gain is real; route by rail/channel **not** by leaked label |
| **HPO** | **Optuna** TPE, 30–80 trials, PR-AUC, early stop |
| **AutoML assist (optional)** | [FLAML](https://github.com/microsoft/FLAML) or LightAutoML **offline** to find a strong baseline, then **lock** a single recipe for the demo |
| **Per-attack eval** | Always report recall/precision **by `label_family`** — this is how you prove diversity of defense, without 20 models |
| **Retrain trigger** | Co-evolve: append misses + new injected rows; refit; compare to previous model on **same** holdout genuine (FP must not explode) |

That *is* co-evolutionary AI (Kurshan et al.), at hackathon scale.

### 8.4 Metrics (put on the dashboard and in the .docx)

Must-haves from the brief:

- ROC-AUC, **PR-AUC**, F1, precision, recall  
- **FPR** on genuine, **FNR** on fraud  
- **FPR @ 90% / 95% recall** (issuer-shaped)  
- Per-family recall  
- **Cost sketch:** missed fraud $ vs false decline $ (even made-up unit costs)  
- Latency p50/p95 of `score()`  
- After loop: evasion rate of red injector vs generation  

Imbalance: **never lead with Accuracy**.

### 8.5 Explainability and SAR-ish text

- Deterministic reason codes from top SHAP + FinCEN-style flags.  
- LLM **only** turns codes into a paragraph (“Case Summary Agent” analog). Hallucination risk → grounded in codes only.

---

## 9. Co-evolution loop (the novelty slot)

```
for g in generations:
    simulate(world, catalog, params_g)
    score with model_{g-1}
    metrics_g, misses_g
    GapAnalyst → mutated params / new approved specs (HITL if new family)
    Trainer → model_g on ledger_0..g  (or replay buffer of hard negatives)
```

**Red mutation (deterministic core):**

- Genetic / random search on **numeric params** (seasoning days, mule count, amount quantile, new-device rate) to **maximize miss rate** under current model, subject to fidelity constraints.  
- Start with **nevergrad** or a 20-line evolutionary loop. No GPU.

**Red mutation (LLM assist):** propose *which* param to touch; code runs the search.

Show **generation vs recall** and **generation vs FPR** — if FPR stays flat while recall recovers, you win the narrative.

**Poisoning family:** optionally inject a fraction of **mislabeled** genuine as fraud in train and show a **robustness** training flag (downweight / filter). That covers Amazon’s data-poisoning bullet without attacking anyone.

---

## 10. Data stores and data structures

| Store | Holds | Why this not that |
|-------|--------|-------------------|
| **PostgreSQL 16** | Attack catalog, run metadata, model registry pointers, users, HITL decisions, **LangGraph checkpoints** | Source of truth; ACID; `langgraph-checkpoint-postgres` |
| **Parquet + DuckDB** | Transactions, features, scores | Columnar, cheap, demo-friendly; DuckDB SQL from API |
| **Qdrant** | OSINT chunks + embeddings + payload `{url, date, source}` | RAG/dedup; OSS Docker |
| **Redis 7** | ARQ jobs, SSE pubsub, rate limits | Sim/train can run 2–10 min |
| **Filesystem `models/`** | LightGBM + `metrics.json` + `features.json` | MLflow local tracking optional (`mlflow` OSS) |
| **NetworkX pickle / graphml** | Snapshot per run for UI | Avoid Neo4j until needed |
| **Git** | Seed catalog YAML, injector code, prompts | Catalog-as-code |

**Pydantic models everywhere** (API, agents, catalog). **Pandera** on ledger batches (schema tests).

Skip for v1: Kafka, Snowflake, Feast, Elasticsearch, Neo4j, MinIO (unless you already know them). Add **MinIO** only if Parquet must be S3-shaped for a “network” story.

**IDs:** ULIDs for runs/txns. Never real cards; `pan_token = hash(synthetic)`.

---

## 11. Application, UI, jobs, observability

| Layer | Pick | Notes |
|-------|------|--------|
| API | **FastAPI** + Pydantic v2 | SSE for live sim; OpenAPI for the .docx screenshots |
| UI | **Next.js (App Router) + Tailwind + shadcn/ui** | More “presentable” than Streamlit; Streamlit only as 4-hour backup |
| Charts | Recharts / ECharts | Arms race, PR curve |
| Graph viz | **react-force-graph** or Cytoscape.js | Mule networks |
| Flow viz | React Flow | LangGraph steps |
| Worker | **ARQ** (async Redis) or Celery | ARQ is lighter with FastAPI |
| Auth | None or basic demo login | Don’t waste time |
| Observability | **Langfuse** OSS (optional compose profile) | Trace agent nodes; skip if RAM tight |
| Logging | `structlog` | `run_id` on every line |
| Experiment tracking | MLflow local or just `metrics.json` | |
| Lint/test | `ruff`, `pytest`, `mypy` on packages/catalog/sim | |

**LLM runtime (cost):**

1. **Groq** free tier — Llama 3.3 70B / Llama 4-class if available — structured JSON  
2. Fallback **Ollama** — `llama3.2` or `qwen2.5` for offline demo  
3. Embeddings always local (`sentence-transformers`)

Do not require GPT-4o paid as the only path.

---

## 12. How to run the whole thing smoothly

### 12.1 Docker Compose (yes)

Services:

```text
web          # Next.js
api          # FastAPI
worker       # ARQ
postgres
redis
qdrant
# optional profiles:
ollama
langfuse + postgres/clickhouse  # only if you have RAM (≥16 GB comfortable without this)
```

`make up` / `make seed` / `make demo`.

**Seed job:** load YAML catalog, download Sparkov/PaySim via a script (Kaggle API token in `.env`, **not** committed), fit SDV copula, write `data/priors.json`.

**Resource reality:** target **16 GB RAM**. Keep Qdrant and Postgres modest. Don’t start Neo4j+Langfuse+Ollama 70B together.

### 12.2 Config

`.env.example`: `GROQ_API_KEY`, `TAVILY_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `KAGGLE_USERNAME` (optional).

Feature flags: `IDENTIFY_LIVE_SEARCH=false` for airplane-mode demo (use cached OSINT fixtures).

### 12.3 Reproducibility (judges clone GitHub)

- Pinned `uv.lock` or `poetry.lock`  
- `python -m packages.sim --seed 42 --n 50000`  
- `python -m packages.models.train`  
- README: 10-minute path **without** Tavily (fixtures)

### 12.4 Demo failure modes (plan them)

| Failure | Fallback |
|---------|----------|
| LLM down | Precomputed Identify results in Postgres |
| Sim too slow | Pre-baked Parquet generation 3 + live scoring only |
| Train too slow | Ship `models/v3.txt`; button “replay metrics” |
| No internet | `IDENTIFY_LIVE_SEARCH=false`, Ollama or recorded traces |

A winning demo is **resilient**, not maximally live.

---

## 13. Technology radar (locked v1 vs later)

### Locked for v1 (do not reopen)

LangGraph, Pydantic v2, FastAPI, Next.js, Postgres, Redis, Qdrant, DuckDB/Parquet, SimPy, NetworkX, LightGBM, Optuna, SHAP, sentence-transformers, Docker Compose, Groq+Ollama, Tavily allowlisted, SDV copula, Sparkov+PaySim calibrators, ARQ, Trafilatura.

### Explicitly rejected for v1

Hermes-as-orchestrator, CrewAI-as-spine, Kafka, Neo4j-required, unrestricted scrapy, FraudGPT, real deepfake media generation, LLM-written ledgers, one model per attack via AutoResearch, Streamlit-as-only-UI (backup only), SageMaker.

### If ahead of schedule

ONNX Runtime scoring, GraphSAGE blend, Langfuse, React Flow supervisor map, Tide AML graphs, family-specific models, MinIO, Playwright e2e of the six-click demo.

---

## 14. Mapping to evaluation criteria

| Criterion | Mechanism in this plan |
|-----------|------------------------|
| Diversity of attacks | Seed 25–40 specs + Identify agent + 8 families |
| Fidelity of simulation | Calibrators + PSI/KS gate + realistic APP vs CNP |
| Detection efficacy | PR-AUC, FPR@recall, per-family, latency |
| Novelty | Multi-agent lab + co-evolution + graph features + policy actions |
| Real-world feasibility | 50 ms scorer, hold vs decline, HITL, no LLM on-path, India APP hold analog |

---

## 15. Build sequence (so you actually finish)

**Week-shaped, compress as needed:**

1. **Catalog YAML + Pydantic + empty UI taxonomy page** (diversity visible on day 1).  
2. **World sim + 3 injectors** (APP, mule, CNP) + Parquet + DuckDB API.  
3. **Features + LightGBM + metrics dashboard.**  
4. **Policy actions + SHAP reasons.**  
5. **LangGraph Identify** on **fixture articles** (FinCEN text in repo).  
6. **Tavily allowlist** + Qdrant + HITL approve.  
7. **Co-evolve** param search + retrain + arms-race chart.  
8. **Polish UI**, seed 20+ vectors, write `TeamName.docx`, record backup demo.  
9. Compose, README, public GitHub `TeamName`, Luma/Kaggle names.

Do **not** start with agent framework yak-shaving. Start with **ledger + detector + 8 families**. Agents wrap a working lab.

---

## 16. LLM/provider cheat sheet (free-first)

| Provider | Role | Cost |
|----------|------|------|
| Groq | Scout/Extractor/GapAnalyst | Free tier, fast |
| Ollama | Offline fallback | Free, local GPU/CPU |
| Tavily | Search/extract | Free tier |
| Kaggle | Sparkov/PaySim/IEEE-CIS | Free |
| Hugging Face | bge-small, optional models | Free |
| Langfuse cloud | Optional traces | Free hobby |

---

## 17. What “peak at each task” means (checklist)

- Identify: citations on every vector; reject non-payment; breadth across rails.  
- Generate: seeded, calibrated, labeled, fidelity badge.  
- Defend: PR-AUC + FPR, per-family, actions, SHAP.  
- Loop: generation table in UI.  
- Feasibility: latency number on the score API.  
- Engineering: `make demo`, Docker, fixtures, no secrets in git.  
- Ethics: synthetic only; high-level typologies; no criminal tooling.

---

## 18. Naming the loop in judge language

> We built a closed-loop red-team/blue-team lab. Identify agents map GenAI payment attacks from regulator-grade sources into a typed catalog. A deterministic simulator, calibrated on public payment synthetics, recreates those attacks at ledger fidelity. A millisecond-class gradient-boosted scorer with graph features detects and **mitigates** them. Misses retrain the defender and mutate the next attack generation. The LLM never writes the money movement and never sits on the authorization path.

That is the problem statement, operationalized.

---

## 19. Immediate next actions (when you say “build”)

1. Freeze team name → repo `TeamName`.  
2. Implement `AttackSpec` + seed catalog from research doc.  
3. Scaffold `docker-compose` + FastAPI health + Next.js shell with the five screens (map, simulate, decisioning, arms race, analyst).  
4. Implement WorldSim + one APP injector + LightGBM on that ledger.  
5. Only then wire LangGraph Identify.

This masterplan is v1. Change injectors and models; do not change the **LLM-off-ledger** and **closed-loop** rules unless the brief changes.
