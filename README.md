# AegisLoop — Mastercard Innovation Challenge @ GFF 2026

**AI Defense Lab for Payment Security** · Build the attack, then build the defense.

End-to-end **red-team / blue-team** system: **Identify** emerging GenAI payment fraud → **Generate** high-fidelity simulations at scale → **Defend** with an ML detector and closed-loop feedback.

Aligned to the official problem statement: [`MC_PS.md`](MC_PS.md).

| Doc | Purpose |
|-----|---------|
| [`walkthrough.md`](walkthrough.md) | Technical handoff — Generate, Defend, APIs |
| [`Docs/HACKATHON_RESEARCH.md`](Docs/HACKATHON_RESEARCH.md) | Threat landscape research |
| [`frontend/README.md`](frontend/README.md) | Web prototype UI (this PR) |
| [`VALIDATION.md`](VALIDATION.md) | Lab metrics, gates G1–G7, champion protocol |

---

## Challenge mapping ([`MC_PS.md`](MC_PS.md))

| Pillar | Challenge ask | AegisLoop implementation |
|--------|----------------|---------------------------|
| **Identify** | Breadth + depth of GenAI payment fraud vectors; grounded in real rails | KillChain Atlas **T01–T24** (`data/catalog/seed.yaml`); allowlisted OSINT → LLM extract → HITL → catalog; landscape + coverage map |
| **Generate** | Simulate attacks at scale with **fidelity** (realistic distributions, behaviours) | Event-driven UPI-like sim: quiet world → typed injectors (mule, identity burst, APP, invoice) → causal feature replay → PSI / fraud-rate fidelity gates → parquet export |
| **Defend** | Accurate detection; low false positives on legitimate payments | HistGradientBoosting champion + v0 rule bits; recall @ **genuine FPR** operating point; Brake policy histogram; **Loop M** retrain on miss families; optional Optuna on inner-val |

**Closed loop:** gaps from Defend (miss family, coverage chips) feed back to Identify landscape and Loop M — attacks you generate become the training and stress-test ground for defense.

---

## Submission artifacts ([`MC_PS.md`](MC_PS.md))

| Required artifact | Where |
|-------------------|--------|
| **1. Code repository** (Identify + Generate + Defend, runnable) | This repo — `make dev` + [`walkthrough.md`](walkthrough.md) |
| **2. Solution walkthrough** (.docx) | Team write-up + [`walkthrough.md`](walkthrough.md) + validation JSON in `data/validation/v1/` |
| **3. Working web prototype** | [`frontend/`](frontend/) — Vite React booth UI at `http://localhost:5173` |

### Web prototype — two ways to run it

| Mode | When to use | How |
|------|-------------|-----|
| **Full lab** (live API + ML) | Reproducibility, real SSE, your own runs | `make dev` + `cd frontend && npm run dev` — see [Quick start](#quick-start) |
| **Booth demo** (recorded packs) | Judges / quick walkthrough without 10–20 min generate + multi-minute fit | Separate deploy on fork `aarush323/markoblitz`, branch **`demo`** — _[Netlify URL — add here]_ |

The full pipeline is **slow by design** (population sim + nested HGB fit + permutation + bootstrap). Use the **booth demo site** to understand the flow in minutes; use **`make dev`** for the real stack.

---

## Evaluation criteria ([`MC_PS.md`](MC_PS.md))

| Criterion | How we address it |
|-----------|-------------------|
| **Diversity of attacks** | 24 techniques T01–T24 across mule, identity, APP, adversarial, merchant; coverage map (`live_rule`, `named_gap`, `case_only`) |
| **Fidelity of simulation** | PSI on amount/hour; fraud-rate band; mule fan-in checks; ~400K-row ledger with family injectors |
| **Detection efficacy** | Champion freeze: **~98.5% recall @ ~0.032% genuine FPR** on locked gtest (`data/validation/v1/internal_01pct_fpr_freeze.json`); Loop M identity_burst AP lift on gtest |
| **Novelty** | Closed-loop lab: OSINT → atlas → sim → nested CV champion → Loop M on new gtest seed (cannot mark own homework) |
| **Real-world feasibility** | UPI-like rails, Brake actions (allow/notify/step-up/hold/decline/mule restrict); lab protocol documented — not issuer SLA claims |

Reported metrics use **recall at genuine FPR operating point** on locked holdout — not accuracy trophies or live UPI feeds.

---

## Architecture

Monorepo: browser UI + one Python process (API, agents, sim, eval).

```
┌─────────────────────────────────────────────────────────────────┐
│  frontend/  (Vite React :5173)  ──proxy /api──►  apps/api :8000 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  packages/agents/     packages/sim/         packages/eval/
  packages/osint/      Generate world        Defend fit/score
  Identify LLM         injectors+fidelity    Loop M, Optuna
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    Postgres + pgvector (:5433)
                    KillChain Atlas (seed.yaml)
```

| Layer | Path | Role |
|-------|------|------|
| API | `apps/api/` | FastAPI routes: catalog, identify, generate, defend, streaming SSE |
| Identify | `packages/agents/`, `packages/osint/` | LangGraph, Tavily, pgvector, HITL |
| Generate | `packages/sim/` | Quiet world, injectors, feature replay, export |
| Defend | `packages/eval/`, `packages/policy/` | HistGBM champion, rules, coverage, Loop M |
| UI | `frontend/` | Booth chrome: Identify → Generate → Defend |
| Data | `data/catalog/`, `data/validation/` | Atlas seed + frozen metrics |

---

## Repository structure

```
markoblitz/                          # Team repo (GitHub)
├── MC_PS.md                         # Official challenge problem statement
├── README.md                        # This file
├── walkthrough.md                   # Engineer handoff
├── VALIDATION.md                    # Metrics protocol + G1–G7 gates
├── Makefile                         # make dev, seed, validate-all, …
├── run.sh                           # Live e2e gates + API
├── pyproject.toml                   # Python package (aegisloop)
├── docker-compose.yml               # Postgres/pgvector
│
├── apps/api/                        # FastAPI application
│   ├── main.py
│   ├── streaming.py               # SSE job progress
│   └── routes/                    # catalog, identify, generate, defend, demo
│
├── packages/
│   ├── agents/                    # Identify LangGraph
│   ├── osint/                     # Allowlist, Tavily, fixtures
│   ├── sim/                       # World, injectors, fidelity, export
│   ├── eval/                      # fit_champion, loop_m, score, job_progress
│   └── policy/                    # v0 rules, coverage map, Brake
│
├── frontend/                      # ★ Web prototype (this PR)
│   ├── src/
│   │   ├── features/
│   │   │   ├── landing/           # Hero, enter workspace
│   │   │   ├── identify/          # Landscape, Discover, Review (HITL)
│   │   │   ├── generate/          # Population sim + ledger + mule graph
│   │   │   ├── defend/            # Detection, Interventions, Feedback, Tune
│   │   │   └── decisioning/       # Recall–FPR curve, metrics
│   │   ├── components/            # Shell, JobThread, MetricHero, …
│   │   └── lib/                   # session-store, api-client, job streams
│   ├── package.json
│   └── README.md                  # UI route map
│
├── data/
│   ├── catalog/seed.yaml          # T01–T24 attack specs (SSOT)
│   ├── validation/v1/             # Champion freeze, loop_m, pareto curves
│   └── osint/fixtures/            # Recorded identify URLs (CI / demo)
│
├── tests/                         # pytest (offline + integration)
└── Docs/                          # Planning locks, identify runbooks
```

`demo/` (static Netlify booth SPA) lives on fork branch **`demo`** only — not in this product branch (`demo/` is gitignored here).

---

## Web prototype flow (`frontend/`)

Landing → workspace with three phases and SSE job threads (⌘K command palette, LIVE/RECORDED chip).

| Route | Stage | What the judge sees |
|-------|--------|---------------------|
| `/` | Landing | Closed-loop story; enter workspace |
| `/identify` | Landscape | T01–T24 grid + coverage chips (live_rule / named_gap) |
| `/identify/discover` | Discover | OSINT stream: COLLECT → EXTRACT → RANK → GROUND → PROPOSE |
| `/identify/review` | Review | HITL approve attacks → catalog seed |
| `/generate` | Generate | Quiet traffic → inject families → fidelity → ledger tape + mule graph |
| `/defend/detection` | Detection | Fit + score stream; **MetricHero** recall @ OP; Recall–FPR curve |
| `/defend/interventions` | Interventions | Brake policy histogram at operating point |
| `/defend/feedback` | Feedback | Loop M — gtest before/after curves, miss-family verdict |
| `/defend/hyperparameters` | Tune | Base vs feedback vs Optuna compare |

Legacy paths redirect: `/simulation` → `/generate`, `/decisioning` → `/defend/detection`, `/arms-race` → `/defend/feedback`.

Design system: [`frontend/DESIGN.md`](frontend/DESIGN.md) (paper/sage/ink, booth glass chrome).

---

## Quick start

**Prerequisites:** Docker, Python 3.11+, Node 18+, Tavily + LLM keys for live Identify.

```bash
git clone git@github.com:aarush323/markoblitz.git
cd markoblitz
make install
cp .env.example .env    # edit DATABASE_URL, TAVILY_API_KEY, AEGIS_LLM_*
make dev                # Postgres → seed → API :8000
```

**Frontend (terminal 2):**

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` → `:8000` (keys never in browser).

**Suggested booth path:** Landscape → Discover → Review (approve) → Generate → Defend Detection → Interventions → Feedback (Loop M).

**Full live validation:** `./run.sh --check` then `./run.sh`

---

## Verify

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
make validate-all          # offline CI gates
./run.sh --check           # live Tavily + LLM gates
```

---

## Key metrics (lab protocol)

| Label | Slice | Recall @ OP | Genuine FPR | Source |
|-------|--------|-------------|-------------|--------|
| Champion freeze | `v1-gtest-48` | ~98.5% | ~0.032% | `internal_01pct_fpr_freeze.json` |
| Loop M (identity_burst AP) | gtest before/after | family AP lift | FPR guard ε | `loop_m_result.json` |

Cold first-fit on a new seed-42 population (~75% OP) is an honest live reference — not the hero metric. See [`VALIDATION.md`](VALIDATION.md).

---

## Environment variables

| Variable | Effect |
|----------|--------|
| `DATABASE_URL` | Postgres + pgvector (default host port **5433**) |
| `TAVILY_API_KEY` | Live OSINT |
| `AEGIS_LLM_*` | LLM for Identify (OmniRoute / OpenRouter / Groq) |
| `IDENTIFY_LIVE_SEARCH` | `true` = live; `false` = fixtures (CI) |
| `VITE_API_BASE_URL` | Frontend API base (`/api` in dev) |

Full list: [`.env.example`](.env.example)

---

## Makefile

```bash
make install          # Python deps
make dev              # Postgres + seed + API
make seed             # Reload catalog YAML → Postgres
make api              # API only (reload)
make test             # pytest
make validate-all     # offline gates
make defend-fit       # train champion on a run
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API import errors | `make install` then `make api` |
| Postgres refused | `make up`; `DATABASE_URL` port **5433** |
| UI shows RECORDED | Expected without Tavily/LLM; set keys + `IDENTIFY_LIVE_SEARCH=true` |
| Generate / fit very slow | Full-scale sim + ML — use booth demo URL for quick UI walkthrough |
| Frontend 404 on API | Ensure `make api` on :8000 |

---

## Planning & docs

[`Docs/LOCKED.md`](Docs/LOCKED.md) · [`Docs/plans/`](Docs/plans/) · Phase 1a: [`Docs/plans/04-phase-1-provider-baseline-identify.md`](Docs/plans/04-phase-1-provider-baseline-identify.md)

---

## Team

Mastercard Innovation Challenge 2026 — GFF Mumbai.  
Repository: **markoblitz** (public GitHub). PR branch: **`feature/frotnend-final`** → `main`.
