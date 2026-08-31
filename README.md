# Mastercard — AegisLoop (GFF 2026)

Identify, Generate, and Defend as **one closed-loop** lab. Problem statement: [`MC_PS.md`](MC_PS.md). Landscape: [`HACKATHON_RESEARCH.md`](Docs/HACKATHON_RESEARCH.md).

**Start here for implementation:** [`walkthrough.md`](walkthrough.md)

**Planning is locked.** [`Docs/LOCKED.md`](Docs/LOCKED.md) · Phase 1a: [`Docs/plans/04-phase-1-provider-baseline-identify.md`](Docs/plans/04-phase-1-provider-baseline-identify.md)

| Plan | File |
|---|---|
| Defects and fork winners | [`Docs/plans/00-correct-planning-defects.md`](Docs/plans/00-correct-planning-defects.md) |
| Identify + catalog | [`Docs/plans/01-identify-catalog-lock.md`](Docs/plans/01-identify-catalog-lock.md) |
| Generate, Defend, loop | [`Docs/plans/02-generate-defend-loop-lock.md`](Docs/plans/02-generate-defend-loop-lock.md) |
| Platform, demo, build order | [`Docs/plans/03-platform-demo-build-lock.md`](Docs/plans/03-platform-demo-build-lock.md) |
| Phase 1a (OmniRoute, pgvector, Identify) | [`Docs/plans/04-phase-1-provider-baseline-identify.md`](Docs/plans/04-phase-1-provider-baseline-identify.md) |

---

## Architecture

This is a **monorepo** — not four separate services. Everything except the browser UI runs inside one Python process.

| Layer | Location | How it runs |
|-------|----------|-------------|
| **Backend API** | `apps/api/` | FastAPI on **`:8000`** |
| **AI / Identify** | `packages/agents/`, `packages/osint/` | LangGraph + LLM inside the API process |
| **ML / Generate / Defend** | `packages/sim/`, `packages/eval/`, `packages/policy/` | sklearn GBDT via `/generate/*` and `/defend/*` |
| **Frontend** | `frontend/` | Vite React on **`:5173`**, proxies `/api` → `:8000` |
| **Database** | Docker Postgres + pgvector | Host port **`:5433`** |

Catalog and embeddings live in **Postgres + pgvector** (no Qdrant). 29 seed AttackSpec rows cover T01–T24.

---

## Prerequisites

- **Docker** — Postgres/pgvector container
- **Python 3.11+** and **uv** (or pip + venv)
- **Node.js 18+** and **npm** — frontend only
- Network access for Tavily, your LLM provider, and first-run fastembed model download

---

## First-time setup

### 1. Clone and install Python deps

```bash
cd /path/to/Mastercard
uv sync --extra dev
# or: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your keys. Minimum required for live Identify:

```bash
DATABASE_URL=postgresql://aegisloop:aegisloop@127.0.0.1:5433/aegisloop
IDENTIFY_LIVE_SEARCH=true
TAVILY_API_KEY=tvly-...
```

**LLM — pick one provider:**

OmniRoute (default — requires a local router on port 20128):

```bash
AEGIS_LLM_PROFILE=omniroute
AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1
AEGIS_LLM_MODEL=auto
AEGIS_LLM_API_KEY=your-omniroute-key
AEGIS_LLM_ALLOW_LOOPBACK_HTTP=true
```

OpenRouter (or any OpenAI-compatible API):

```bash
AEGIS_LLM_PROFILE=generic_openai
AEGIS_LLM_BASE_URL=https://openrouter.ai/api/v1
AEGIS_LLM_MODEL=openai/gpt-4o-mini
AEGIS_LLM_API_KEY=sk-or-...
```

Groq (opt-in only — do not mix `GROQ_API_KEY` with OmniRoute profile):

```bash
AEGIS_LLM_PROFILE=groq
AEGIS_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=gsk_...
```

Never commit `.env`. Keys stay server-side only.

### 3. Install frontend deps

```bash
cd frontend && npm install && cd ..
```

---

## Quick start (3 terminals)

**One-time setup**

```bash
make install   # .venv + Python deps
```

**Terminal 1 — Database + API**

```bash
make dev     # Postgres → seed → API on :8000 (uses .venv)
```

Or split across terminals:

**Terminal 1 — Database**

```bash
make up
```

**Terminal 2 — Backend (API + AI + ML)**

```bash
make seed    # load catalog into Postgres (first run)
make api     # http://127.0.0.1:8000 with hot reload
```

**Terminal 3 — Frontend**

```bash
cd frontend && npm run dev
```

Open **http://localhost:5173**

The Vite dev server proxies `/api/*` → `http://localhost:8000/*`. No API keys reach the browser.

---

## Full product entrypoint

[`./run.sh`](run.sh) is the single product entrypoint for live end-to-end validation. It reads `.env` (without shell-sourcing it), requires live Tavily + LLM configuration, starts Postgres/pgvector, runs product gates, then serves FastAPI.

```bash
./run.sh                 # live e2e gates, then API on :8000
./run.sh --check         # live e2e gates, then exit
./run.sh --down          # stop Postgres container
```

Use `./run.sh` when you want the full live validation path. Use `make dev` or `make api` for day-to-day development (faster, skips e2e gates).

---

## Verify

```bash
# API health
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready

# Offline validation (no Tavily / LLM needed)
make validate-all

# Live validation (Tavily + LLM required)
./run.sh --check
```

`/ready` should return `postgres: true`, `pgvector: true`, `tavily_configured: true`, and `llm.configured: true`.

---

## Frontend pages

| URL | Purpose |
|-----|---------|
| `/` | Threat map — catalog + coverage |
| `/identify` | Run Identify pipeline, HITL approve/reject |
| `/simulation` | Generate population and canary runs |
| `/decisioning` | Fit and score the GBDT champion model |
| `/arms-race` | Loop M co-evolution |
| `/copilot` | Copilot UI |

---

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `DATABASE_URL` | `postgresql://aegisloop:aegisloop@127.0.0.1:5433/aegisloop` | Atlas + pgvector |
| `TAVILY_API_KEY` | — | Live OSINT search/extract |
| `AEGIS_LLM_PROFILE` | `omniroute` | `omniroute`, `generic_openai`, or `groq` |
| `AEGIS_LLM_BASE_URL` | `http://127.0.0.1:20128/v1` | OpenAI-compatible base URL |
| `AEGIS_LLM_MODEL` | `auto` | Model id (required for non-OmniRoute profiles) |
| `AEGIS_LLM_API_KEY` | — | Bearer token for the active profile |
| `IDENTIFY_LIVE_SEARCH` | `true` | `true` = live collectors + Tavily; `false` = fixtures (CI) |
| `IDENTIFY_TAVILY_MAX_CALLS_PER_RUN` | `12` | Tavily query budget per Identify run |
| `IDENTIFY_MAX_DOCS` | `0` | Max URLs after curator (`0` = unlimited) |
| `IDENTIFY_MAX_HITL` | `0` | Max HITL rows per run (`0` = unlimited) |
| `IDENTIFY_CURATOR_ENABLED` | `true` | LLM rank before deep extract |
| `OSINT_EXTRACTOR` | `tavily` | `trafilatura` or `firecrawl` fallback |
| `AEGIS_EMBEDDINGS` | `fastembed` | `hash` for CI (no model download) |
| `VITE_API_BASE_URL` | `/api` | Frontend API base (Vite proxy in dev) |

### Optional

| Variable | Purpose |
|----------|---------|
| `GREYNOISE_API_KEY` | Network IOC corroboration (telemetry gate) |
| `HF_TOKEN` | Optional Hugging Face model downloads |
| `GROQ_API_KEY` | Only when `AEGIS_LLM_PROFILE=groq` |
| `REDIS_URL` | Reserved for later phases — not used now |

See [`.env.example`](.env.example) for the full list with dev cost-control examples.

---

## Makefile shortcuts

```bash
make install          # .venv + deps (uv sync, or pip fallback)
make setup            # install + Postgres + seed (no API)
make dev              # Postgres + seed + API on :8000
make up               # docker compose up -d postgres --wait
make down             # docker compose down
make seed             # reset + load catalog YAML → Postgres
make api              # .venv uvicorn with reload on :8000
make test             # pytest (offline markers only)
make validate-all     # offline CI gates
make validate-all-live  # same as ./run.sh --check
make generate-validate  # smoke-test population sim
make defend-fit         # train GBDT champion on a run
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No module named 'sqlalchemy'` (or `pydantic`, etc.) | `make install` then `make api` / `make dev` — do not run bare `uvicorn` |
| `No .venv found` | `make install` |
| `postgres` connection refused | Run `make up` or `make dev`; confirm `DATABASE_URL` uses port **5433** |
| `llm.configured: false` | Set `AEGIS_LLM_API_KEY` and check profile/base URL match your provider |
| OmniRoute / LLM errors | Start OmniRoute on `:20128`, or switch to `generic_openai` + OpenRouter URL |
| Identify uses fixtures | Set `IDENTIFY_LIVE_SEARCH=true` and `TAVILY_API_KEY` |
| Frontend can't reach API | Ensure `make api` is running on `:8000`; Vite proxy handles `/api` |
| `./run.sh` fails at telemetry gate | Network/IC3 fetch issue — use `make api` for local dev instead |
| First Identify run is slow | Normal — Tavily + LLM + fastembed ONNX model download on first run |
| Port 5432 in use | Default compose maps Postgres to host **5433** to avoid conflicts |

---

## Repo map

```
apps/api/                 FastAPI app + routes (catalog, identify, generate, defend)
packages/agents/          Identify LangGraph + LLM extraction
packages/osint/           Tavily, RSS, allowlist, pgvector chunks
packages/sim/             Generate — population + canary simulation
packages/eval/            Defend — GBDT fit, score, Loop M/T
packages/policy/          v0 rules, coverage map, Loop I drafts
frontend/                 Vite React UI
data/catalog/seed.yaml    29 AttackSpec rows — source of truth
```
