# AegisLoop walkthrough

Handoff guide for **Attack (Generate)** and **Defend** teams. Identify + catalog + handoff layers are implemented through FinalIdentify steps 0–11.

**Planning SSOT:** [`Docs/LOCKED.md`](Docs/LOCKED.md) · **Identify runbook:** [`Docs/Identify Docs/FinalIdentify.md`](Docs/Identify%20Docs/FinalIdentify.md) · **Generate (built):** [`Docs/plans/08-generate-world-build.md`](Docs/plans/08-generate-world-build.md) · **Defend (next build):** [`Docs/plans/02-defend-build.md`](Docs/plans/02-defend-build.md) · Plan 02 architecture lock: [`Docs/plans/02-generate-defend-loop-lock.md`](Docs/plans/02-generate-defend-loop-lock.md)

---

## 1. What exists today

```
Identify (done)          Generate (Plan 08 done)         Defend (next: Plan 12)
─────────────────        ─────────────────────────       ─────────────────────
Scout → … → HITL         quiet world + injectors         packages/policy/ coverage
                         train.parquet + sidecar         v0 rules (row engine in 12)
                         POST /generate/*                AuthGate/Brake not built yet
                           ↑                               ↑
                    KillChain Atlas (Postgres)      features_expected
                    data/catalog/seed.yaml          data/rules/v0_rules.yaml
```

| Layer | Status | Your job next |
|-------|--------|----------------|
| **Catalog / Atlas** | 29 seed rows, all T01–T24 | Add rows via YAML + `make seed` |
| **Identify graph** | Fixtures + OmniRoute + Postgres pgvector | Optional: live Tavily |
| **Generate handoff** | Injector **stubs** + API | Build real world sim + ledger |
| **Defend handoff** | v0 rules + coverage map | AuthGate, Brake, scoring loop |

---

## 2. First-time setup (everyone)

```bash
cd /path/to/Mastercard
make install                 # .venv + deps (uv sync, or pip fallback)
make dev                     # Postgres → seed → API on :8000

# live product (Tavily + OmniRoute required)
./run.sh --check             # live gates, then exit
./run.sh                     # live gates, then API on :8000

# piecewise (same as make dev, without auto-reload grouping)
make up
make seed
make api
```

**Offline verify:** `make validate-all`. **Live product:** `./run.sh --check`.

**Live Tavily + OmniRoute + pgvector:** `make validate-all-live` — requires `TAVILY_API_KEY` and `AEGIS_LLM_API_KEY`.

---

## 3. Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `DATABASE_URL` | `postgresql://aegisloop:aegisloop@localhost:5432/aegisloop` | Atlas + pgvector |
| `TAVILY_API_KEY` | — | Live OSINT search/extract |
| `AEGIS_LLM_PROFILE` | `omniroute` | `omniroute` (default) or `groq` |
| `AEGIS_LLM_BASE_URL` | `http://127.0.0.1:20128/v1` | OpenAI-compatible base |
| `AEGIS_LLM_MODEL` | `auto` | OmniRoute router model |
| `AEGIS_LLM_API_KEY` | — | OmniRoute (or Groq if profile=groq) |
| `IDENTIFY_LIVE_SEARCH` | `false` (code); `true` in `.env.example` | `true` = live collectors + Tavily; `false` = fixtures (CI) |
| `IDENTIFY_MAX_DOCS` | `0` | Max URLs after curator (`0` = unlimited) |
| `IDENTIFY_MAX_HITL` | `0` | Max HITL rows staged per run (`0` = unlimited) |
| `IDENTIFY_MAX_CANDIDATES` | `0` | Scout pool cap before curator (`0` = unlimited) |
| `IDENTIFY_TAVILY_MAX_CALLS_PER_RUN` | `12` | Tavily query budget per run |
| `IDENTIFY_CURATOR_ENABLED` | `true` | LLM rank before extract (tier fallback if off/unconfigured) |
| `OSINT_EXTRACTOR` | `tavily` | `trafilatura` or `firecrawl` fallback |
| `HF_TOKEN` | — | Optional Hugging Face download |
| `GREYNOISE_API_KEY` | — | Optional network-footprint corroboration |

Never commit `.env`. Keys stay server-side only.

---

## 4. Repo map (where to edit)

```
apps/api/                 FastAPI app + routes
  routes/catalog.py       Threat map / Atlas list
  routes/identify.py      Identify run + HITL
  routes/generate.py      Population + canary (Attack team)
  routes/defend.py        Coverage map + Loop I (Defend team)
  seed.py                 YAML → Postgres

packages/catalog/         AttackSpec schema + queries
  models.py               Pydantic AttackSpec (SSOT type)
  loader.py               Load data/catalog/seed.yaml
  query.py                list_generate_eligible, get_spec_by_vector_id
  features.py             features_expected derivation
  campaigns.py            FinCEN canary campaign pin

packages/sim/             Generate / Attack (extend here)
  injectors.py            Read catalog → ledger event stub
  runner.py               population + canary_mode

packages/policy/          Defend (extend here)
  rules.py                Load data/rules/v0_rules.yaml
  loop_i.py               Draft rule from catalog card
  coverage.py             Loop C — 24× coverage map

packages/agents/          Identify graph (mostly stable)
packages/osint/           Tavily, allowlist, pgvector chunks

data/catalog/seed.yaml    30 catalog rows — handoff source of truth
data/rules/v0_rules.yaml  v0 if-then rules
data/osint/fixtures/      Airplane-mode articles

scripts/validate_all_live.py   Full live integration script
```

---

## 5. Shared contract: `AttackSpec`

Every team reads/writes the same row shape (`packages/catalog/models.py`).

**Statuses:** `proposed` → HITL approve → `open` → `generating` / `defending` → `solved` (Defend miss keeps `open`).

**Generate handoff fields (Attack team must respect):**

| Field | Role |
|-------|------|
| `generate_mode` | `generate` = injector runs; `name_only` = catalog only |
| `simulator.injector_id` | `graph_mule` \| `identity_trajectory` \| `app_session` \| `doc_beneficiary` |
| `simulatable_signals` | Validated per injector — see `packages/catalog/schemas.py` |
| `canary_eligible` | Only when confirmed + tier ≤2 + valid generate signals |
| `features_expected` | Auth-plane columns Defend should fire — see §8 |

**Load / validate YAML without DB:**

```bash
python -c "from packages.catalog.loader import load_catalog_yaml, catalog_summary; print(catalog_summary(load_catalog_yaml()))"
```

**Reseed Postgres after YAML edits:**

```bash
make seed
```

---

## 6. Running the API

```bash
make dev                       # recommended: Postgres + seed + API (uses .venv)
# → http://localhost:8000
# → http://localhost:8000/docs  (OpenAPI)

# or step by step
make up
make seed
make api
```

All `make` Python targets use `.venv/bin/python`. Do not run bare `uvicorn` from a global install.

---

## 7. API quick reference

### Catalog / threat map

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/catalog` | All Atlas rows |
| GET | `/catalog/threat-map` | 24 techniques × chips |

### Identify + HITL

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/identify/config` | Env / key booleans |
| POST | `/identify/run` | Run full identify graph |
| GET | `/identify/hitl` | `proposed` queue |
| POST | `/identify/approve/{vector_id}` | Approve → `open` |
| POST | `/identify/reject/{vector_id}` | Reject |
| POST | `/identify/decision/{vector_id}` | approve / reject / edit |

### Attack / Generate

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/generate/eligible` | Rows with `generate_mode=generate`, status open/generating |
| GET | `/generate/canary-eligible` | Canary rows + campaign defs |
| POST | `/generate/population` | One injector run from catalog row |
| POST | `/generate/canary` | Pin FinCEN campaign or single vector |

**Population example:**

```bash
curl -s -X POST http://localhost:8000/generate/population \
  -H 'Content-Type: application/json' \
  -d '{"vector_id":"t13-upi-impersonation-app","run_id":"attack-test-1"}' | python -m json.tool
```

**Canary (FinCEN FIN-2024-Alert004 chain T09→T11→T13→T02):**

```bash
curl -s -X POST http://localhost:8000/generate/canary \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id":"fincen-fin-2024-alert004","run_id":"canary-1"}' | python -m json.tool
```

### Defend

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/defend/coverage-map` | Loop C — 24 techniques × rule status |
| GET | `/defend/scout-topics` | Gap cells → Scout topic hints |
| GET | `/defend/rules/v0` | Live v0 rule list |
| POST | `/defend/loop-i/draft/{vector_id}` | Draft rule or named gap from card |
| POST | `/defend/miss/{vector_id}` | Miss → keep status `open` |

**Coverage map:**

```bash
curl -s http://localhost:8000/defend/coverage-map | python -m json.tool
```

**Loop I draft for T13:**

```bash
curl -s -X POST http://localhost:8000/defend/loop-i/draft/t13-upi-impersonation-app | python -m json.tool
```

---

## 8. Attack team (Generate)

### What you consume

Query Postgres via `packages/catalog/query.py`:

```python
from apps.api.db import SessionLocal
from packages.catalog.query import list_generate_eligible, get_spec_by_vector_id

db = SessionLocal()
specs = list_generate_eligible(db)  # status open|generating, generate_mode=generate
spec = get_spec_by_vector_id(db, "t13-upi-impersonation-app")
# spec.simulator.injector_id, spec.simulatable_signals
```

### Two modes (Plan 02 §5)

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Population** | Default sim | Sample open rows; injector reads `simulatable_signals` |
| **canary_mode** | API / UI pin | All params from one `canary_eligible` row or FinCEN campaign |

Campaign definition: `packages/catalog/campaigns.py` (`fincen-fin-2024-alert004`).

### Injectors (current = stubs)

| `injector_id` | Category | Signals model |
|---------------|----------|---------------|
| `graph_mule` | Cat 1 mule graph | `fan_in_1h`, `fan_out_ttl_hours`, `smurf_cap_ratio`, `hop_rails`, … |
| `identity_trajectory` | Cat 2 KYC/seasoning | `seasoning_days`, `liveness_score`, `device_hash_shift`, … |
| `app_session` | Cat 3 APP/coercion | `call_active_flag`, `copy_paste_payee_flag`, `new_payee`, … |
| `doc_beneficiary` | Cat 5 BEC | `beneficiary_changed`, `gstin_checksum_ok`, … |

**Stub today:** `packages/sim/injectors.py` emits one `gff.txn.v1` ledger event with `features_auth` mapped from signals.

**Your build order (Plan 02):**

1. Benign ShadowRail world (customers, payees, circadian spend)
2. Real injector engines in `packages/sim/` (not LLM-generated edge lists for mules)
3. Parquet ledger partitioned by `run_id` / `generation`
4. Fidelity gate (KS/PSI vs priors)
5. Wire population sampler to weight by rail/family

### Python without API

```python
from apps.api.db import SessionLocal
from packages.sim.runner import run_population, run_canary

db = SessionLocal()
pop = run_population(db, vector_id="t13-upi-impersonation-app")
canary = run_canary(db, campaign_id="fincen-fin-2024-alert004")
db.close()
```

### Do not

- Require Identify to run injectors (handoff is catalog-only)
- Row-copy Kaggle/production data
- Put GSTIN + 3DS + VPA + chat embeddings on every ledger row
- Build Cat 4 Loop A on the live API path (offline only)

---

## 9. Defend team

### What you consume

Same Atlas rows. Focus on:

- `features_expected` — which auth columns should fire for this attack
- `economic_class` — APP vs ATO vs mule vs BEC (different Brake actions)
- `control_bypassed` — which control failed (for Loop I drafts)

Derived automatically in extractor path via `packages/catalog/features.py`. Seed YAML also sets them explicitly.

**Auth feature examples:** `call_active_flag`, `copy_paste_payee_flag`, `is_new_payee`, `fan_in_1h`, `beneficiary_changed`, `liveness_score`, …

### v0 rules

File: `data/rules/v0_rules.yaml`  
Loader: `packages/policy/rules.py`

Kinds: `hard_flag` | `nudge` | `calm_down`

Example live rule:

```yaml
id: call-and-paste-new-payee
kind: hard_flag
applies_to: APP
when:
  call_active_flag: true
  copy_paste_payee_flag: true
  is_new_payee: true
```

### Loop I — catalog → draft rule

`POST /defend/loop-i/draft/{vector_id}` or:

```python
from packages.catalog.query import get_spec_by_vector_id
from packages.policy.loop_i import draft_rule_from_spec

spec = get_spec_by_vector_id(db, "t13-upi-impersonation-app")
draft = draft_rule_from_spec(spec)
# draft_rule.id == "call-and-paste-new-payee" OR coverage_status == "named_gap"
```

**Named gaps (by design — no fake live rule):** T07 BIN testing, T06 without merchant nodes, Cat 4 T20–T23, deepfake video at payment time, live crypto cash-out.

### Loop C — coverage map

`GET /defend/coverage-map` returns 24 cells with:

| `coverage_status` | Meaning |
|-------------------|---------|
| `live_rule` | v0 rule matches `features_expected` |
| `draft_rule` | Loop I template applies, not yet promoted |
| `named_gap` | Not observable at auth — catalog only |
| `case_only` | Case tab / investigation plane |
| `empty` | No catalog row for technique |

Empty / gap cells include `scout_topic_hint` for the Identify team’s next collection run.

### Miss path

Defend miss → `POST /defend/miss/{vector_id}` sets status **`open`** (not `solved`). Generate oversamples; loop retrains.

### Your build order (Plan 02 §6)

1. Score `features_auth` from Attack ledger (rules → LightGBM → Brake)
2. Implement Brake actions: `allow | notify | step_up | hold | decline | mule_credit_restrict`
3. SHAP → reason codes (no LLM on hot path)
4. CaseScore plane (optional LLM) — not on authorization path
5. HoldoutVault for promotion (not `canary_mode`)

Reference: [`Docs/defense_architecture.md`](Docs/defense_architecture.md), [`Docs/feedback-loop.md`](Docs/feedback-loop.md)

### Do not

- Call Identify graph from Defend
- Concatenate sentence embeddings into AuthGate
- Mark catalog `solved` on a single miss
- Invent live rules for named-gap techniques

---

## 10. End-to-end demo script (teams together)

```bash
# 1. Infrastructure
make dev

# 2. Identify → proposed (live or fixtures)
curl -s -X POST http://localhost:8000/identify/run \
  -H 'Content-Type: application/json' \
  -d '{"run_id":"demo-1","topic":"deepfake UPI payment fraud"}' | python -m json.tool

# 3. HITL approve (pick vector_id from response / hitl queue)
curl -s -X POST http://localhost:8000/identify/approve/identify-... 

# 4. Attack — population
curl -s -X POST http://localhost:8000/generate/population \
  -d '{"vector_id":"t13-upi-impersonation-app"}' | python -m json.tool

# 5. Attack — canary campaign
curl -s -X POST http://localhost:8000/generate/canary \
  -d '{"campaign_id":"fincen-fin-2024-alert004"}' | python -m json.tool

# 6. Defend — coverage + draft rule
curl -s http://localhost:8000/defend/coverage-map | python -m json.tool
curl -s -X POST http://localhost:8000/defend/loop-i/draft/t13-upi-impersonation-app | python -m json.tool

# 7. Simulated miss
curl -s -X POST http://localhost:8000/defend/miss/t13-upi-impersonation-app
```

---

## 11. Testing commands

| Command | When |
|---------|------|
| `make install` | First clone / after `pyproject.toml` changes |
| `make dev` | Postgres + seed + API (offline local dev) |
| `make setup` | Install + Postgres + seed (no API) |
| `make test` | All pytest |
| `make validate-all` | Offline full stack (no keys) |
| `make validate-all-live` | Tavily + OmniRoute + pgvector + embeddings |
| `make handoff-validate` | Generate + Defend only |
| `pytest tests/test_generate_handoff.py` | Attack handoff |
| `pytest tests/test_defend_handoff.py` | Defend handoff |

---

## 12. OSINT allowlist (Identify — 13 domains)

Regulators: `fincen.gov`, `ftc.gov`, `rbi.org.in`, `treasury.gov`  
Research: `arxiv.org`, `dhs.gov`  
Industry: `feedzai.com`, `wipro.com`, `deloitte.com`, `bny.com`, `paymentservices.amazon.com`  
News: `reuters.com`, `bbc.com`

Live search only returns these domains. Expansion = edit `packages/osint/allowlist.py` + tier table.

---

## 13. Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named 'sqlalchemy'` (or `pydantic`, etc.) | `make install` then use `make api` / `make dev` (not bare `uvicorn`) |
| `No .venv found` | `make install` |
| OmniRoute down | Identify uses fixture rules or abstains; start OmniRoute on :20128 |
| Tavily 0 results | Query too narrow; check allowlist |
| pgvector / extension missing | `docker compose up -d postgres --wait`. If you previously used `postgres:16-alpine`, reset volume: `docker compose down -v` |
| HF model slow first run | Set `HF_TOKEN`; hash embeddings are used if the model cannot load |
| Postgres connection | `docker compose up -d postgres --wait`, check `DATABASE_URL` |
| T13 coverage `case_only` | Reseed; primary row should be `t13-upi-impersonation-app` (canary) |
| Identify uses fixtures | Set `IDENTIFY_LIVE_SEARCH=true` + `TAVILY_API_KEY` |

---

## 14. Not built yet (don’t assume it exists)

- `apps/web` threat-map UI (API only)
- Full ShadowRail simulator / Parquet ledger at scale
- AuthGate LightGBM + Brake scorer
- ARQ worker / Redis jobs
- LangGraph Postgres checkpointer
- HoldoutVault + Loop M retrain
- Neo4j, Streamlit, public Cat 4 API

Attack team owns `packages/sim/` + ledger. Defend team owns scoring + `packages/policy/` promotion gates + model artifacts under `models/` (when added).

---

## 15. Who to ask / what to read

| Topic | Doc |
|-------|-----|
| Problem statement | [`MC_PS.md`](MC_PS.md) |
| Technique census T01–T24 | [`Docs/HACKATHON_RESEARCH.md`](Docs/HACKATHON_RESEARCH.md) §3 |
| AttackSpec schema lock | [`Docs/plans/01-identify-catalog-lock.md`](Docs/plans/01-identify-catalog-lock.md) |
| Generate + Defend design | [`Docs/plans/02-generate-defend-loop-lock.md`](Docs/plans/02-generate-defend-loop-lock.md) |
| Defend rules + loops | [`Docs/defense_architecture.md`](Docs/defense_architecture.md) |
| Demo six-click script | [`Docs/plans/03-platform-demo-build-lock.md`](Docs/plans/03-platform-demo-build-lock.md) §6 |

**Handoff rule:** Identify writes catalog rows; Generate reads `simulatable_signals`; Defend reads `features_expected`. No team should patch another team’s JSON at runtime — extend schema in `packages/catalog/models.py` and seed YAML together.
