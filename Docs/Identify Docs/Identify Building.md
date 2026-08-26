---

name: Identify Step-by-Step Runbook

overview: Replace `Identify Docs/FinalIdentify.md` with a no-fluff, numbered implementation runbook — file paths, what to build, and done-when gates for each step.

todos:

  - id: write-runbook

    content: Replace Identify Docs/[FinalIdentify.md](http://FinalIdentify.md) with numbered Step 0–12 runbook (build / files / done-when per step)

    status: pending

  - id: inline-tables

    content: Add only domain-tier, simulatable_signals, status enum, and env var tables inline

    status: pending

  - id: cross-refs-after-approval

    content: "After user approves execution: add one-line pointer from Updated Identify [Phase.md](http://Phase.md) and [LOCKED.md](http://LOCKED.md) to Identify Docs/[FinalIdentify.md](http://FinalIdentify.md)"

    status: pending

isProject: false

---

# Identify step-by-step runbook

## Deliverable

Write **`Identify Docs/FinalIdentify.md`](Identify%20Docs/[FinalIdentify.md](http://FinalIdentify.md))** — a straight implementation runbook. No design essays, no judge prose, no mermaid unless one tiny flow helps. Each step = **what to build → where → done when**.

Replace the current file (it is a pasted plan outline, not a runbook).

**Keep elsewhere unchanged for now:** `Updated Identify Phase.md`](Updated%20Identify%[20Phase.md](http://20Phase.md)) stays the process contract. Cross-ref updates to LOCKED/README happen only after you approve execution.

---

## Document format (locked)

```markdown

# Identify — build steps

> SSOT: plans/[01-identify-catalog-lock.md](http://01-identify-catalog-lock.md). Process: Updated Identify [Phase.md](http://Phase.md).

## Step N — Title

**Build:** ...

**Files:** ...

**Done when:** ...

```

Rules for the runbook:

- Numbered steps only (0–12)

- Bullet lists, not paragraphs

- Every step names exact paths under `packages/`, `data/`, `apps/`

- Every step has a **Done when** gate you can actually test

- Schema/tier tables only where code needs them inline (domain→tier, `simulatable_signals` keys) — no T01–T24 essay; link to `plans/01` for the full table

---

## Step outline (content to write)

### Step 0 — Scaffold

- Create `packages/catalog/`, `packages/osint/`, `packages/agents/`, `data/catalog/`, `data/osint/fixtures/`

- Add deps: `pydantic`, `langgraph`, `httpx`, `trafilatura`, `feedparser`, `sentence-transformers`, `qdrant-client`, `pyyaml`

- **Done when:** `python -c "from packages.catalog.models import AttackSpec"` works

### Step 1 — `AttackSpec` model

- **File:** `packages/catalog/models.py`

- Pydantic v2 model with all fields from Plan 01 §3 `technique_id`, `source_tier`, `confidence_level`, `corroboration_type`, `vector_class`, `simulatable_signals`, `simulator`, `features_expected`, `status` enum, etc.)

- Validators: `confirmed` requires `source_urls`; `generate_mode=generate` requires valid `simulatable_signals` vs `simulator.param_schema`

- **File:** `packages/catalog/loader.py` — load/validate `data/catalog/seed.yaml`

- **Done when:** invalid row raises; valid row parses

### Step 2 — Seed catalog

- **File:** `data/catalog/seed.yaml`

- 28–36 rows, every `T01T24` present at least once

- Transcribe from `HACKATHON_RESEARCH.md` §3: `source_urls`, pre-filled tiers, `simulatable_signals` per Plan 01 §6

- FinCEN/arXiv rows: `status: open`, `confidence_level: confirmed` where cited

- `name_only` rows still included (T07, T19, T22, T23, etc.)

- **Done when:** loader passes; count ≥ 28; all 24 technique IDs present

### Step 3 — Threat map API + UI stub

- **Files:** `apps/api/routes/catalog.py` → `GET /catalog`; `apps/web` threat-map page

- Render: `technique_id`, `name`, `status`, `confidence_level`, `source_tier`, `generate_mode`

- Seed Postgres from YAML on `make seed` (or equivalent)

- **Done when:** UI shows 24 technique chips from seed

### Step 4 — OSINT fixtures + fetchers

- **Files:**

  - `data/osint/fixtures/fincen_alert004.txt` (and one RBI-style note)

  - `packages/osint/rss.py` — FinCEN, FTC, arXiv RSS

  - `packages/osint/extract.py` — Tavily Extract → trafilatura fallback; `OSINT_EXTRACTOR` flag

  - `packages/osint/allowlist.py` — domain allowlist + `DOMAIN_TIER` dict (Plan 01 §4)

- Default: `IDENTIFY_LIVE_SEARCH=true` — Tavily Search + Extract on allowlisted domains (`TAVILY_API_KEY` required)
- Fallback: `IDENTIFY_LIVE_SEARCH=false` reads `data/osint/fixtures/` only (airplane / no-API-key demo)

- **Done when:** live search returns ≥1 allowlisted URL; fixture fallback still loads when flag is `false`

### Step 5 — `identify_graph` skeleton

- **File:** `packages/agents/identify_graph.py`

- Linear LangGraph: `Scout → Extractor → Grounder → TierScorer → Corroborator → Librarian`

- Shared state typed dict carrying `candidate_urls`, partial `AttackSpec`, HITL flag

- **Done when:** graph compiles and runs empty pass-through on fixtures

### Step 6 — Scout node

- Default: RSS poll + Tavily Search with `include_domains` (allowlist)
- Fallback: fixture URLs only when `IDENTIFY_LIVE_SEARCH=false`

- Output: `candidate_urls[]` with `source_domain`, `snippet`, `fetched_at`

- Never query dark-web / exploit terms

- **Done when:** Scout returns ≥1 URL (live Tavily by default; fixture URLs when `IDENTIFY_LIVE_SEARCH=false`)

### Step 7 — Extractor node

- Fetch body via extract module

- LLM structured output → partial `AttackSpec` (temp ≤ 0.2, retry on validation fail)

- Embed chunk → Qdrant collection `osint_chunks` `BAAI/bge-small-en-v1.5`)

- **Done when:** one article (live or fixture) → valid partial `AttackSpec` JSON

### Step 8 — Grounder + TierScorer + Corroborator (deterministic)

- **Grounder** `packages/agents/grounder.py`): reject no rail, buzzword-only, cosine dedup > 0.92, exploit detail

- **TierScorer**: domain table → `source_tier`; independence check → `confidence_level`

- **Corroborator**: set `vector_class`; telemetry (GreyNoise) only for `network_footprint`; set `canary_eligible` per Plan 01 §5

- **Done when:** FinCEN fixture → `confirmed`, tier 1, `documentary-case` for human_social vectors

### Step 9 — Librarian + HITL

- Merge into Postgres Atlas; bump depth on dupes

- `status=proposed` → LangGraph **interrupt**

- HITL actions: approve → `open`, reject, reject_unsafe, edit fields

- **API:** `POST /identify/run`, `POST /identify/approve/{vector_id}`

- **Done when:** Identify run proposes 1–3 rows; approve flips to `open` on map

### Step 10 — Generate handoff

- Generate reads `open` rows with `generate_mode=generate`

- **Population:** sample `simulatable_signals` + `simulator.injector_id`

- *`canary_mode`:** pin FinCEN FIN-2024-Alert004 chain (T09 → T11 → T13 → T02) — runs in Generate, not Identify

- **Done when:** one catalog row drives one injector run without manual JSON edits

### Step 11 — Defend handoff

- On each `open` row, set `features_expected` (PulseFeatures column names that should fire)

- **Loop I:** new card → draft v0 rule from `control_bypassed` + shape (see `defense_architecture.md` §3.1); skip if not observable at payment time → mark named gap

- **Loop C:** coverage map = 24 techniques × (has live rule | named gap | case_only); empty cells → Scout topic for next Identify run

- Miss path: Defend miss → set catalog `status: open` (not `solved`)

- Identify never calls AuthGate/Brake

- **Done when:** adding a T13 card produces a draft `call-and-paste-new-payee`-style rule or explicit named gap

### Step 12 — Live search default + demo gate

- **Required:** `TAVILY_API_KEY` in `.env` / docker-compose (live search is on by default)
- **Optional:** `GREYNOISE_API_KEY` for network-footprint corroboration
- Set `IDENTIFY_LIVE_SEARCH=false` only for airplane mode (no API key / no internet)

- **Demo script (6 clicks):** map → run Identify (live Tavily) → HITL approve → population sim → canary_mode → arms chart

- **Done when:** live Identify run proposes 1–3 rows from real allowlisted sources; airplane fallback still works with `IDENTIFY_LIVE_SEARCH=false`

---

## Inline reference blocks (minimal, in the doc)

Include only these tables inline (code needs them at keyboard):

1. **Domain → tier** (13 domains from Plan 01 §4)

2. *`simulatable_signals` required keys** per `injector_id` (5 blocks from Plan 01 §6)

3. **Status enum** one line

4. **Env vars** (live default):

| Flag | Default | Effect |
|------|---------|--------|
| `IDENTIFY_LIVE_SEARCH` | `true` | Tavily Search + Extract on allowlisted domains |
| `TAVILY_API_KEY` | required | Live collection (fail fast if missing when live) |
| `GREYNOISE_API_KEY` | optional | Network-footprint corroboration only |
| `OSINT_EXTRACTOR` | `tavily` | `trafilatura` / `firecrawl` extract fallback |

Everything else → link `plans/01-identify-catalog-lock.md`.

---

## What we are NOT writing

- No 16-section architecture essay

- No duplicate T01–T24 full table (link out)

- No judge write-up prose

- No changes to code in this task — doc only

