# AegisLoop web prototype (`frontend/`)

Presentable **working web UI** for the Mastercard Innovation Challenge submission ([`MC_PS.md`](../MC_PS.md) artifact #3). Same closed-loop story as the backend: **Identify → Generate → Defend**.

Parent repo README: [`../README.md`](../README.md) · Design: [`DESIGN.md`](DESIGN.md) · API handoff: [`../walkthrough.md`](../walkthrough.md)

---

## Run locally

Requires API on `:8000` (from repo root: `make dev`).

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Dev server proxies `/api` → `http://localhost:8000`.

```bash
npm run build    # production bundle → dist/
npm run test     # vitest
npm run test:e2e # Playwright booth chrome (optional)
```

---

## UI structure

```
frontend/src/
├── features/
│   ├── landing/           # LandingPage — hero, loop steps
│   ├── identify/
│   │   ├── LandscapePage  # T01–T24 threat grid + coverage
│   │   ├── DiscoverPage   # OSINT job thread (SSE)
│   │   └── ReviewPage     # HITL approve → session
│   ├── generate/
│   │   ├── GeneratePage   # Population sim SSE + fidelity
│   │   ├── LedgerTape     # Synthetic ledger view
│   │   └── LayeredMuleGraph
│   └── defend/
│       ├── DetectionPage  # Fit stream + MetricHero + curve
│       ├── InterventionsPage # Brake histogram
│       ├── FeedbackPage   # Loop M before/after (gtest)
│       └── HyperparametersPage
├── components/
│   ├── layout/            # Shell, sidebar, stage pills, ⌘K palette
│   └── ui/                # JobThread, MetricHero, RunGate, …
└── lib/
    ├── session-store.ts   # Booth session (identify → generate → defend)
    ├── api-client.ts      # REST + SSE to /api
    ├── defend-job.ts      # Fit, Loop M, tune job hooks
    └── generate-job.ts    # Population stream
```

---

## Routes

| Path | MC_PS pillar | UI |
|------|--------------|-----|
| `/` | — | Landing |
| `/identify` | Identify | Landscape — catalog + coverage |
| `/identify/discover` | Identify | Live/recorded discover pipeline |
| `/identify/review` | Identify | HITL approve attacks |
| `/generate` | Generate | Simulate payment traffic |
| `/defend/detection` | Defend | Train + score champion |
| `/defend/interventions` | Defend | Policy actions at OP |
| `/defend/feedback` | Defend | Loop M closed-loop |
| `/defend/hyperparameters` | Defend | Optuna compare |

Redirects: `/simulation` → `/generate`, `/decisioning` → `/defend/detection`, `/arms-race` → `/defend/feedback`.

---

## Session & chips

- **LIVE** — Tavily + LLM + health OK; SSE streams hit real API.
- **RECORDED** — Fixture packs / demo fallback; chip shows reason.
- **Session** — `session-store.ts` persists identify approvals, generate run id, defend scores across stages (sessionStorage).

⌘K **command palette**: booth demo shortcut, jump to stage, copy seed / OP line.

---

## Booth demo (fast walkthrough)

Full `make dev` generate + fit can take **many minutes**. For judges:

- Deployed static replay: fork **`aarush323/markoblitz`**, branch **`demo`** — _[Netlify URL]_
- Same visual language; recorded champion metrics; not in this `frontend/` tree (separate `demo/` SPA on demo branch).

---

## Stack

React 19 · Vite · TypeScript · Tailwind · TanStack Query · Recharts · cmdk · IBM Plex (paper/sage/ink tokens in `src/styles/`).
