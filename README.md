<div align="center">

# AegisLoop

### Mastercard Innovation Challenge @ GFF 2026 · AI Defense Lab for Payment Security

**Identify → Generate → Defend** as one closed-loop red-team / blue-team system.

Build the attack. Train the defense. Close the loop.

[![Problem statement](https://img.shields.io/badge/Challenge-MC_PS.md-sage?style=for-the-badge)](MC_PS.md)
[![Walkthrough](https://img.shields.io/badge/Handoff-walkthrough.md-ink?style=for-the-badge)](walkthrough.md)
[![Validation](https://img.shields.io/badge/Metrics-VALIDATION.md-ink?style=for-the-badge)](VALIDATION.md)

</div>

---

## Table of contents

1. [What this repo is](#what-this-repo-is)
2. [Visual proof — working prototype](#visual-proof--working-prototype)
3. [Model metrics (champion freeze)](#model-metrics-champion-freeze)
4. [Evaluator quickstart — run everything](#evaluator-quickstart--run-everything)
5. [API keys & services you need](#api-keys--services-you-need)
6. [OmniRoute setup (default LLM)](#omniroute-setup-default-llm)
7. [Alternative: OpenRouter / Groq (no OmniRoute)](#alternative-openrouter--groq-no-omniroute)
8. [Booth walkthrough (UI)](#booth-walkthrough-ui)
9. [Architecture & repo map](#architecture--repo-map)
10. [Verify & troubleshoot](#verify--troubleshoot)
11. [Booth demo site (fast preview)](#booth-demo-site-fast-preview)
12. [Docs index](#docs-index)

---

## What this repo is

Aligned to [`MC_PS.md`](MC_PS.md) — three pillars, one feedback loop:

| Pillar | Challenge ask | AegisLoop |
|--------|----------------|-----------|
| **Identify** | Map emerging GenAI payment fraud — breadth + depth | KillChain Atlas **T01–T24** · allowlisted OSINT → LLM → HITL → catalog |
| **Generate** | Simulate attacks at scale with **fidelity** | UPI-like event sim · quiet world → injectors → PSI / fraud-rate gates → parquet |
| **Defend** | Detect with high accuracy, low false positives | **HistGradientBoosting** champion · recall @ **genuine FPR** OP · Brake policy · **Loop M** |

**Submission artifacts:** runnable code (this repo) · solution walkthrough ([`walkthrough.md`](walkthrough.md) + team docx) · **web prototype** ([`frontend/`](frontend/)).

> **Note for evaluators:** Full generate + ML fit can take **10–20+ minutes** on a laptop. For a **5-minute UI walkthrough** without waiting, use the booth demo site (branch `demo` on fork) — link in [Booth demo site](#booth-demo-site-fast-preview). This README gets you the **real** stack running locally.

---

## Visual proof — working prototype

Screenshots from the live booth UI (`frontend/` + `make dev`).

### Landing — closed loop on glass

![AegisLoop landing — Identify, Generate, Defend](DEMO_PICS/landing.png)

### Identify — threat landscape (T01–T24)

![Identify landscape — catalog and coverage](DEMO_PICS/idenitfy.png)

### Generate — simulate payment traffic

![Generate phase 1 — job thread and scan banner](DEMO_PICS/generate_p1.png)

![Generate phase 2 — ledger tape and mule graph](DEMO_PICS/generate_p2.png)

### Defend — detection & champion metrics

![Defend detection — MetricHero and recall–FPR curve](DEMO_PICS/defend_p1.png)

### Feedback loop (Loop M)

![Loop M — gtest before/after and verdict](DEMO_PICS/feedbackloop.png)

### Hyperparameters (Optuna)

![Optuna tune — base vs feedback vs tuned](DEMO_PICS/optuna.png)

---

## Model metrics (champion freeze)

Locked holdout: **`v1-gtest-48`** · Model: **`v1-train-46__loopm-train`** (post Loop M) · Threshold selected on **inner-val only** (never on gtest).

Source: [`data/validation/v1/internal_01pct_fpr_freeze.json`](data/validation/v1/internal_01pct_fpr_freeze.json) · Protocol: [`VALIDATION.md`](VALIDATION.md)

### Best score (operating point)

| Metric | Value |
|--------|-------|
| **Recall @ OP** | **98.52%** |
| **Precision @ OP** | **98.57%** |
| **Recall at 0.1% FPR** (reference post-hoc on gtest-48) | **98.7%** |
| **PR-AUC** (binary average precision) | **0.9985** |
| **Genuine false-positive rate @ OP** | **0.032%** |

> We report **recall at genuine FPR operating point** on a locked time-cut holdout — not headline “accuracy” on a random split. Simulated corpus; lab protocol, not issuer SLA.

### Fraud family — average precision @ champion OP

| Fraud family | Average precision |
|--------------|-------------------|
| Identity burst | **0.984** |
| Mule behavior | **0.994** |
| Authorized-push scam (APP) | **0.990** |
| Account takeover | **0.056** |
| Invoice fraud | **1.000** |

Loop M example: identity_burst AP **0.34 → 0.97** on new gtest seed 48 ([`loop_m_result.json`](data/validation/v1/loop_m_result.json)) — loop cannot grade its own homework.

---

## Evaluator quickstart — run everything

**Goal:** Postgres + API on `:8000` + UI on `:5173` with **live** Identify (Tavily + LLM).

### 0. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** | recent | Postgres + pgvector (`:5433` on host) |
| **Python** | 3.11+ | API, sim, ML (`uv` or venv) |
| **Node.js** | 18+ | Frontend only |
| **Git** | — | Clone repo |

Network: Tavily API, your LLM endpoint (OmniRoute or OpenRouter), Docker Hub for Postgres image.

### 1. Clone

```bash
git clone git@github.com:aarush323/markoblitz.git
cd markoblitz
```

### 2. Python environment

```bash
make install
# Creates .venv and installs aegisloop + dev deps (FastAPI, sim, sklearn, LangGraph, …)
```

### 3. Configure `.env`

```bash
cp .env.example .env
```

**Minimum for live product** (copy from [API keys table](#api-keys--services-you-need)):

```bash
DATABASE_URL=postgresql://aegisloop:aegisloop@127.0.0.1:5433/aegisloop

# Identify — live OSINT
IDENTIFY_LIVE_SEARCH=true
TAVILY_API_KEY=tvly-xxxxxxxx

# LLM — OmniRoute (default) — see OmniRoute section below
AEGIS_LLM_PROFILE=omniroute
AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1
AEGIS_LLM_MODEL=auto
AEGIS_LLM_API_KEY=your-omniroute-dashboard-key
AEGIS_LLM_ALLOW_LOOPBACK_HTTP=true
```

Never commit `.env`. Keys stay server-side; the browser only talks to `/api` via Vite proxy.

### 4. Start OmniRoute (if using default profile)

See [OmniRoute setup](#omniroute-setup-default-llm). Router must be listening on **`http://127.0.0.1:20128/v1`** before Identify runs.

### 5. Start backend (one command)

```bash
make dev
# Docker Postgres → seed catalog → FastAPI on http://127.0.0.1:8000
```

**Or** full live validation gates first:

```bash
./run.sh --check   # Tavily + LLM + pgvector gates — exits 0 if OK
./run.sh           # same gates, then API stays up
```

### 6. Start frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### 7. Smoke-check API

```bash
curl -s http://127.0.0.1:8000/health | head
curl -s http://127.0.0.1:8000/ready
```

`/ready` should show `postgres: true`, `pgvector: true`, `tavily_configured: true`, `llm.configured: true`.

### 8. Walk the booth (recommended path)

1. **Landing** → Enter workspace  
2. **Identify → Landscape** — T01–T24 grid  
3. **Discover** — OSINT stream (COLLECT → … → PROPOSE)  
4. **Review** — approve HITL items  
5. **Generate** — Simulate payment traffic (SSE; **slow** at full scale)  
6. **Defend → Detection** — Fit & score (**slow** — nested HGB + bootstrap)  
7. **Interventions** — Brake histogram  
8. **Feedback** — Loop M  
9. **Hyperparameters** — Optuna compare  

⌘K command palette: jump stages, copy seed, booth shortcuts.

### 9. Offline CI (no API keys)

```bash
make validate-all
```

Uses fixtures + hash embeddings — proves repo integrity without Tavily/LLM.

---

## API keys & services you need

| Service | Env variable(s) | Required for | Get it |
|---------|-----------------|--------------|--------|
| **Postgres** | `DATABASE_URL` | Everything | `make up` (Docker, no key) |
| **Tavily** | `TAVILY_API_KEY` | Live Identify search/extract | [tavily.com](https://tavily.com) |
| **OmniRoute** (default LLM) | `AEGIS_LLM_API_KEY`, `AEGIS_LLM_BASE_URL` | Live Identify LLM steps | OmniRoute dashboard (local `:20128`) |
| **OpenRouter** (alt LLM) | `AEGIS_LLM_PROFILE=generic_openai`, `AEGIS_LLM_API_KEY` | Same | [openrouter.ai](https://openrouter.ai) |
| **Groq** (alt LLM) | `AEGIS_LLM_PROFILE=groq`, `GROQ_API_KEY` | Same | [console.groq.com](https://console.groq.com) |
| **GreyNoise** (optional) | `GREYNOISE_API_KEY` | `./run.sh` telemetry gate | [greynoise.io](https://www.greynoise.io) |

### Identify tuning (optional — in `.env.example`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `IDENTIFY_TAVILY_MAX_CALLS_PER_RUN` | `12` | Tavily budget per run |
| `IDENTIFY_MAX_DOCS` | `0` | Max URLs to deep-extract (`0` = unlimited) |
| `IDENTIFY_MAX_HITL` | `0` | Max HITL rows (`0` = unlimited) |
| `IDENTIFY_CURATOR_ENABLED` | `true` | LLM rank before extract |
| `AEGIS_EMBEDDINGS` | `fastembed` | `hash` for CI only |

Full list: [`.env.example`](.env.example)

---

## OmniRoute setup (default LLM)

AegisLoop’s **default** profile routes LLM calls through **OmniRoute** — an OpenAI-compatible proxy (model routing, dashboard keys).

1. **Install & run OmniRoute** on the same machine (dashboard docs — typically listens on port **20128**).
2. Copy your **Bearer API key** from the OmniRoute dashboard.
3. In `.env`:

```bash
AEGIS_LLM_PROFILE=omniroute
AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1
AEGIS_LLM_MODEL=auto          # or pin e.g. openai/gpt-4o-mini for reproducibility
AEGIS_LLM_API_KEY=sk-or-...   # OmniRoute dashboard key
AEGIS_LLM_ALLOW_LOOPBACK_HTTP=true
```

4. Verify router responds:

```bash
curl -s http://127.0.0.1:20128/v1/models -H "Authorization: Bearer $AEGIS_LLM_API_KEY" | head
```

5. Start API (`make dev` or `./run.sh`) — Identify graph uses this endpoint for extract / curator / HITL staging.

> Do **not** set `GROQ_API_KEY` while `AEGIS_LLM_PROFILE=omniroute` unless you intend to switch profile.

---

## Alternative: OpenRouter / Groq (no OmniRoute)

If you do not run OmniRoute locally:

**OpenRouter:**

```bash
AEGIS_LLM_PROFILE=generic_openai
AEGIS_LLM_BASE_URL=https://openrouter.ai/api/v1
AEGIS_LLM_MODEL=openai/gpt-4o-mini
AEGIS_LLM_API_KEY=sk-or-v1-...
AEGIS_LLM_ALLOW_LOOPBACK_HTTP=false
```

**Groq:**

```bash
AEGIS_LLM_PROFILE=groq
AEGIS_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=gsk_...
```

Restart API after changing `.env`.

---

## Booth walkthrough (UI)

| Route | Pillar | What you see |
|-------|--------|--------------|
| `/` | — | Landing + loop story |
| `/identify` | Identify | Landscape — coverage chips |
| `/identify/discover` | Identify | Live OSINT job thread (SSE) |
| `/identify/review` | Identify | HITL approve → catalog |
| `/generate` | Generate | Quiet traffic → inject → fidelity → ledger |
| `/defend/detection` | Defend | Fit stream · **98.5% recall** hero · PR curve |
| `/defend/interventions` | Defend | Brake actions at OP |
| `/defend/feedback` | Defend | Loop M before/after on gtest |
| `/defend/hyperparameters` | Defend | Optuna three-column compare |

Design: [`frontend/DESIGN.md`](frontend/DESIGN.md) · UI details: [`frontend/README.md`](frontend/README.md)

---

## Architecture & repo map

```
┌──────────────────────────────────────────────────────────────┐
│  frontend/  :5173  ──proxy /api──►  apps/api  :8000          │
└──────────────────────────────────────────────────────────────┘
         │              │                    │
         ▼              ▼                    ▼
   session-store   packages/agents/   packages/sim/     packages/eval/
   JobThread SSE   packages/osint/    Generate world    Defend + Loop M
                         │                    │                    │
                         └────────────────────┴────────────────────┘
                                              ▼
                              Postgres + pgvector  (:5433)
                              data/catalog/seed.yaml (T01–T24)
```

```
markoblitz/
├── MC_PS.md                 # Official challenge statement
├── README.md                # ← you are here
├── walkthrough.md           # Engineer API handoff
├── VALIDATION.md            # G1–G7 gates + metric protocol
├── Makefile / run.sh        # make dev · live e2e gates
├── apps/api/                # FastAPI + SSE streaming
├── packages/
│   ├── agents/              # Identify LangGraph
│   ├── osint/               # Tavily, allowlist, fixtures
│   ├── sim/                 # Generate + fidelity
│   └── eval/                # HistGBM fit, score, Loop M
├── frontend/                # ★ Web prototype (Vite React)
├── data/
│   ├── catalog/seed.yaml    # Attack atlas SSOT
│   └── validation/v1/       # Champion freeze JSON
├── DEMO_PICS/               # Screenshots for this README
└── tests/                   # pytest
```

---

## Verify & troubleshoot

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
make validate-all          # offline — no keys
./run.sh --check           # live — Tavily + LLM required
```

| Symptom | Fix |
|---------|-----|
| `No module named 'sqlalchemy'` | `make install` then `make dev` |
| Postgres connection refused | `make up`; `DATABASE_URL` port **5433** |
| `llm.configured: false` | Set `AEGIS_LLM_API_KEY`; start OmniRoute or use OpenRouter |
| `tavily_configured: false` | Set `TAVILY_API_KEY`; `IDENTIFY_LIVE_SEARCH=true` |
| UI chip says RECORDED | Missing live keys — expected in CI mode |
| Generate / fit hangs long | **Normal** at full scale — use booth demo URL for quick UI |
| Frontend can't reach API | `make api` or `make dev` must run on **:8000** |
| `./run.sh` telemetry fail | Optional — use `make dev` for local booth |

---

## Booth demo site (fast preview)

Full `make dev` pipeline is slow. For judges / quick understanding:

| | |
|--|--|
| **Fork** | `aarush323/markoblitz` |
| **Branch** | `demo` |
| **URL** | https://markoblitz.netlify.app/|
| **What it is** | Same UI · recorded champion metrics · SSE replay · no Python install |

Product code + this README live on **`main`** / **`feature/frotnend-final`**. Static booth SPA is on branch **`demo`** only.

---

## Docs index

| Doc | Content |
|-----|---------|
| [`MC_PS.md`](MC_PS.md) | Official problem statement |
| [`walkthrough.md`](walkthrough.md) | Generate / Defend APIs |
| [`VALIDATION.md`](VALIDATION.md) | Metrics protocol, G1–G7 |
| [`frontend/README.md`](frontend/README.md) | UI routes & session |
| [`Docs/HACKATHON_RESEARCH.md`](Docs/HACKATHON_RESEARCH.md) | Threat research |
| [`Docs/LOCKED.md`](Docs/LOCKED.md) | Planning SSOT |

---

<div align="center">

**Mastercard Innovation Challenge 2026** · Global Fintech Fest · Team markoblitz

PR branch: `feature/frotnend-final` → `main`

</div>
