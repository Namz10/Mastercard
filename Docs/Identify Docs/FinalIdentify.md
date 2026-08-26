# Identify — build steps

> **SSOT:** `[plans/01-identify-catalog-lock.md](../../plans/01-identify-catalog-lock.md)`. **Process contract:** `[Updated Identify Phase.md](Updated%20Identify%20Phase.md)`. **Generate/Defend consumers:** `[plans/02-generate-defend-loop-lock.md](../../plans/02-generate-defend-loop-lock.md)`. **Demo script:** `[plans/03-platform-demo-build-lock.md](../../plans/03-platform-demo-build-lock.md)` §6.

Implementer runbook for the Identify pillar. Each step = what to build, where, and a testable done-when gate. Full T01–T24 census → Plan 01 §2 (do not duplicate here).

**Component names:** KillChain Atlas (store/UI), `AttackSpec` (`packages/catalog/`), `identify_graph` (`packages/agents/`), `packages/osint/`.

```
Scout → Extractor → Grounder → TierScorer → Corroborator → Librarian → [HITL interrupt]
```

---



## Inline reference (keyboard)



### Status enum

`proposed` | `rejected` | `rejected_unsafe` | `open` | `generating` | `defending` | `solved`

- HITL proposes → `proposed`; approve → `open` (not `approved`).
- Defend miss → catalog stays `open` (not `solved`).
- Dual-use fail → `rejected_unsafe`.



### Domain → tier (v1 freeze)


| Domain                     | Tier |
| -------------------------- | ---- |
| fincen.gov                 | 1    |
| ftc.gov                    | 1    |
| rbi.org.in                 | 1    |
| treasury.gov               | 1    |
| arxiv.org                  | 2    |
| dhs.gov                    | 2    |
| feedzai.com                | 3    |
| wipro.com                  | 3    |
| deloitte.com               | 3    |
| bny.com                    | 3    |
| paymentservices.amazon.com | 3    |
| reuters.com                | 4    |
| bbc.com                    | 4    |


Unknown allowlisted domain → default tier **4** until a human edits the table.

### `simulatable_signals` required keys (by `injector_id`)

Generate rejects `generate_mode=generate` rows that fail these. Extra keys allowed.

`graph_mule` (Cat 1 — T01–T06):

- `fan_in_1h` (int ≥ 0)
- `fan_out_ttl_hours` (float > 0)
- `smurf_cap_ratio` (float in (0,1])
- `hop_rails` (list of rail enums)
- `mule_account_age_days` (int ≥ 0)
- `cashout_mcc_or_sink` (str)

`identity_trajectory` (Cat 2 — T08–T12):

- `seasoning_days` (int)
- `seasoning_txn_count` (int)
- `liveness_score` (float 0–1, simulated)
- `doc_consistency` (float 0–1, simulated)
- `device_hash_shift` (bool)
- `kyc_tier` (str)

`app_session` (Cat 3 — T13–T19 session flags):

- `persuasion_labels` (list[str])
- `call_active_flag` (bool)
- `copy_paste_payee_flag` (bool)
- `pause_ms` (int ≥ 0)
- `new_payee` (bool)
- `urgency_pressure` (float 0–1)
- `transcript_ref` (str | null) — optional; templates only in public repo

`doc_beneficiary` (Cat 5 — T24, linked T16/T18):

- `beneficiary_changed` (bool)
- `gstin_checksum_ok` (bool)
- `amount_vs_invoice_delta` (float)
- `lookalike_domain_flag` (bool)

**Cat 4 Loop A** (T20–T22 — not a bulk injector):

- `x_adv` allowlist only: amount jitter, mule payee among owned synthetic accounts, device rotate
- Forbidden: `generator_id`, `persona_id`, full-graph stats, future edges, post-auth transcripts, SHAP/tree dumps



### Env vars


| Flag                   | Default            | Effect                                                                              |
| ---------------------- | ------------------ | ----------------------------------------------------------------------------------- |
| `IDENTIFY_LIVE_SEARCH` | `true`             | Tavily Search + Extract on allowlisted domains                                      |
| `TAVILY_API_KEY`       | required when live | Live collection; fail fast if missing when `IDENTIFY_LIVE_SEARCH=true`              |
| `GREYNOISE_API_KEY`    | optional           | Network-footprint corroboration only (`vector_class=network_footprint`)             |
| `OSINT_EXTRACTOR`      | `tavily`           | Extract fallback: `trafilatura` or `firecrawl` (single-URL, allowlisted hosts only) |


Airplane mode: `IDENTIFY_LIVE_SEARCH=false` → fixtures in `data/osint/fixtures/` only.

---



## Step 0 — Scaffold

**Build:**

- Create `packages/catalog/`, `packages/osint/`, `packages/agents/`, `data/catalog/`, `data/osint/fixtures/`
- Add deps: `pydantic`, `langgraph`, `httpx`, `trafilatura`, `feedparser`, `sentence-transformers`, `qdrant-client`, `pyyaml`
- Minimal `pyproject.toml` or `requirements.txt` so imports resolve

**Files:**

- `packages/catalog/__init__.py`
- `packages/osint/__init__.py`
- `packages/agents/__init__.py`

**Done when:** `python -c "from packages.catalog.models import AttackSpec"` works (stub model OK for this gate).

---



## Step 1 — `AttackSpec` model

**Build:**

- Pydantic v2 `AttackSpec` with all fields from Plan 01 §3
- Enums: `technique_id` (T01–T24), `status`, `generate_mode`, `confidence_level`, `corroboration_type`, `vector_class`, rails, lifecycle stages, economic classes
- Validators:
  - `confidence_level=confirmed` → requires non-empty `source_urls`
  - `generate_mode=generate` → `simulatable_signals` must validate against `simulator.param_schema` / injector contract (Plan 01 §6)
  - `dual_use_rating=high` → only allowed when `generate_mode=name_only` (else reject at load)
- Loader: parse and validate YAML list of rows

**Files:**

- `packages/catalog/models.py`
- `packages/catalog/loader.py`
- `packages/catalog/schemas.py` (injector param schemas, optional split)

**Done when:** invalid row raises; valid row parses; `confirmed` without URLs fails.

---



## Step 2 — Seed catalog

**Build:**

- 28–36 rows; every `technique_id` T01–T24 present at least once
- Transcribe from `Docs/HACKATHON_RESEARCH.md` §3: `source_urls`, pre-filled tiers, `simulatable_signals` per inline table above
- FinCEN / arXiv-backed rows: `status: open`, `confidence_level: confirmed` where cited
- Include `name_only` rows (T07, T19 method, T22, T23, etc.) so the threat map is full on day 1
- Every `generate_mode=generate` row: valid `simulator.injector_id` + `simulatable_signals`
- Set `actor_type` on every row (Plan 01 §11)
- Demo campaign note on primary T13 row: FinCEN FIN-2024-Alert004 chain (T09 → T11 → T13 → T02) in `novelty_notes` or linked `vector_id`s

**Files:**

- `data/catalog/seed.yaml`

**Done when:** loader passes; count ≥ 28; all 24 technique IDs present; zero schema violations on `generate` rows.

---



## Step 3 — Threat map API + UI stub

**Build:**

- `GET /catalog` — list Atlas rows (filter by `status`, `technique_id` optional)
- Threat-map page: 24 technique chips in 5 category columns
- Display per chip: `technique_id`, `name`, `status`, `confidence_level`, `source_tier`, `generate_mode`
- `make seed` (or equivalent) loads `seed.yaml` into Postgres KillChain Atlas table

**Files:**

- `apps/api/routes/catalog.py`
- `apps/web/...` threat-map page (Next.js)
- DB migration / seed script for Atlas table

**Done when:** UI shows 24 technique chips from seed without manual DB inserts.

---



## Step 4 — OSINT fixtures + fetchers

**Build:**

- Fixture text: FinCEN FIN-2024-Alert004 pattern + one RBI-style note
- RSS poll: FinCEN, FTC, arXiv (`packages/osint/rss.py`)
- Extract pipeline: Tavily Extract → `trafilatura` fallback; `OSINT_EXTRACTOR` selects backend (`packages/osint/extract.py`)
- Allowlist + `DOMAIN_TIER` dict (`packages/osint/allowlist.py`)
- Default `IDENTIFY_LIVE_SEARCH=true`: Tavily Search with `include_domains` = allowlist; requires `TAVILY_API_KEY`
- Fallback `IDENTIFY_LIVE_SEARCH=false`: read fixture files only

**Files:**

- `data/osint/fixtures/fincen_alert004.txt`
- `data/osint/fixtures/rbi_note.txt` (or equivalent)
- `packages/osint/rss.py`
- `packages/osint/extract.py`
- `packages/osint/allowlist.py`

**Done when:** live search returns ≥1 allowlisted URL; with `IDENTIFY_LIVE_SEARCH=false`, fixtures load with no API key.

**Safety:** never query dark-web, criminal-market, jailbreak-as-a-service, or exploit-payload terms.

---



## Step 5 — `identify_graph` skeleton

**Build:**

- Linear LangGraph: Scout → Extractor → Grounder → TierScorer → Corroborator → Librarian
- Shared state `TypedDict`: `candidate_urls`, partial `AttackSpec` fields, `hitl_required`, `run_id`
- Nodes stubbed; pass-through compiles and runs on fixtures

**Files:**

- `packages/agents/identify_graph.py`
- `packages/agents/state.py` (optional)

**Done when:** `identify_graph.compile()` succeeds; empty run completes without error on fixtures.

---



## Step 6 — Scout node

**Build:**

- Live: RSS poll + Tavily Search with `include_domains` from allowlist
- Airplane: fixture URLs only from `data/osint/fixtures/`
- Output `candidate_urls[]`: `url`, `source_domain`, `snippet`, `fetched_at`

**Files:**

- `packages/agents/nodes/scout.py` (or inline in `identify_graph.py`)

**Done when:** Scout returns ≥1 URL (live Tavily by default; fixture URLs when `IDENTIFY_LIVE_SEARCH=false`).

---



## Step 7 — Extractor node

**Build:**

- Fetch article body via `packages/osint/extract.py`
- LLM structured output → partial `AttackSpec` (temperature ≤ 0.2, retry on Pydantic validation fail)
- Embed chunk → Qdrant collection `osint_chunks` with model `BAAI/bge-small-en-v1.5`
- Payload: `{url, date, source_type, domain}`

**Files:**

- `packages/agents/nodes/extractor.py`
- Qdrant collection bootstrap (docker or local)

**Done when:** one article (live or fixture) → valid partial `AttackSpec` JSON that passes model validation.

---



## Step 8 — Grounder + TierScorer + Corroborator

**Build:**

- **Grounder** (`packages/agents/grounder.py`): reject if no payment `rail`; GenAI buzzword-only (no `control_bypassed`, no `economic_class`); cosine dedup > 0.92 on `name`+`rail`+`technique_id` embedding; exploit-step / payload / criminal-market how-to
- **TierScorer**: domain table → `source_tier`; independence aggregation → `confidence_level` (Plan 01 §4 confirmation rule)
- **Corroborator** (Plan 01 §5):
  - Set `vector_class` (`network_footprint` vs `human_social`)
  - GreyNoise only for `network_footprint`; never for `human_social`
  - Set `corroboration_type` and `canary_eligible` predicate

**Files:**

- `packages/agents/grounder.py`
- `packages/agents/nodes/tier_scorer.py`
- `packages/agents/nodes/corroborator.py`

**Done when:** FinCEN fixture path → `confidence_level=confirmed`, `source_tier=1`, `corroboration_type=documentary-case` for human_social vectors.

---



## Step 9 — Librarian + HITL

**Build:**

- Merge into Postgres Atlas; bump depth on duplicate embedding (cosine > 0.92), do not insert clone
- `status=proposed` → LangGraph **interrupt** before commit to map
- HITL payload: diff vs nearest `technique_id`, tier badges, `source_urls`, `vector_class`, `generate_mode`, `simulatable_signals` preview
- Actions: approve → `open`, reject, `reject_unsafe`, edit fields
- APIs: `POST /identify/run`, `POST /identify/approve/{vector_id}` (and reject/edit variants)

**Files:**

- `packages/agents/nodes/librarian.py`
- `apps/api/routes/identify.py`
- HITL queue UI tab (can ship minimal in Step 3 web app)

**Done when:** Identify run proposes 1–3 rows; approve flips to `open` on threat map.

---



## Step 10 — Generate handoff

**Build:**

- Generate reads Atlas rows with `status` in `{open, generating}` and `generate_mode=generate`
- **Population mode:** sample `simulatable_signals` + `simulator.injector_id`; injector is source of truth for ledger perturbation
- `canary_mode`**:** pin FinCEN FIN-2024-Alert004 campaign (T09 → T11 → T13 → T02); runs in Generate subgraph, not Identify
- `canary_eligible=true` only when Plan 01 §5 predicate holds
- Identify does not run injectors; only supplies catalog rows

**Files:**

- Generate consumer in `packages/sim/` or `packages/generate/` (Plan 02)
- Catalog query helper in `packages/catalog/`

**Done when:** one `open` catalog row drives one injector run with no manual JSON edits.

---



## Step 11 — Defend handoff

**Build:**

- On each `open` row, set `features_expected` (PulseFeatures / `features_auth` column names from Plan 02 §3 ledger envelope — e.g. `is_new_payee`, `call_active_flag`, `copy_paste_payee_flag`, `fan_in_1h`, `beneficiary_changed`, `liveness_score`)
- **Loop I:** new/open card → draft v0 rule from `control_bypassed` + economic shape (`[defense_architecture.md](../defense_architecture.md)` §3.1); if not observable at payment time → **named gap** (not a fake live rule)
- **Loop C:** coverage map = 24 techniques × (`live rule` | `named_gap` | `case_only`); empty cells → Scout topic for next Identify run
- Defend miss → set catalog `status: open` (not `solved`)
- Identify **never** calls AuthGate / Brake / scorer

**Files:**

- `features_expected` populated in seed + Extractor merge path
- `apps/web` coverage-map tab (Plan 03 §6 extra tab)
- `rules/` v0 draft stubs from Loop I (`[feedback-loop.md](../feedback-loop.md)` §2)

**Done when:** adding a T13 card produces a draft `call-and-paste-new-payee`-style rule or an explicit named gap row on the coverage map.

**Expected named gaps (by design):** deepfake video, live crypto cash-out, BIN testing (T07), T06 if no merchant nodes, Cat 4 until AuthGate exists — catalog card only.

---



## Step 12 — Live search default + demo gate

**Build:**

- `TAVILY_API_KEY` in `.env` / docker-compose (live is default)
- Optional `GREYNOISE_API_KEY` for network-footprint corroboration
- `IDENTIFY_LIVE_SEARCH=false` only for airplane / no-internet demo (`[plans/03](../../plans/03-platform-demo-build-lock.md)` §7 resilience table)
- Precomputed Identify results in Postgres as LLM-down fallback

**Demo script (6 clicks — full lab, not Identify-only):**

1. Threat map — 24 techniques, status / confidence / tier chips
2. Run Identify (live Tavily) → HITL approve → `open`
3. Simulate generation N — ledger + mule graph, fidelity badge
4. Decisioning — score stream, reason codes, Brake action
5. Arms race — HoldoutVault metrics across generations
6. Retrain from misses — Loop M once

**Done when:** live Identify proposes 1–3 rows from real allowlisted sources; `IDENTIFY_LIVE_SEARCH=false` airplane path still works.

---



## Identify success criteria (demo + write-up)

- Threat map shows all 24 IDs with status chips, `confidence_level`, `source_tier`
- Run Identify on fixture or live → 1–3 `proposed` → HITL → `open`
- Every `generate` row has valid `simulatable_signals`
- Confirmed rows have `source_urls`
- No dark-web collection, no exploit steps, no live criminal tooling in repo
- Generate population + `canary_mode` consume catalog without schema patches
- Coverage map shows live rule vs named gap per technique (Loop C)

---



## Boundaries (do not cross)

- `canary_mode` (Generate pin to one documented case) ≠ **HoldoutVault** (frozen model eval)
- Status `open` not `approved`
- Linear `identify_graph` — no parallel Identify swarm browsing the open web
- LLM: extraction + Loop I form-fill only; never on live payment path
- Unrestricted Google / scrapy / Firecrawl site crawl: forbidden
- Mastercard.com Akamai 403: use secondary citations from HACKATHON_RESEARCH; do not scrape around blocks

---



## Authority stack

1. `MC_PS.md` — problem statement
2. `Docs/HACKATHON_RESEARCH.md` §3 — content map
3. `plans/00-correct-planning-defects.md` — global locks
4. `plans/01-identify-catalog-lock.md` — schema + graph
5. This file — build order and gates
6. `Updated Identify Phase.md` — judge/write-up process (not implementation detail)

