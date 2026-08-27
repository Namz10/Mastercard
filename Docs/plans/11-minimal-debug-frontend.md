# Plan 11 — Minimal frontend for API testing and demo

**Status:** PROPOSED  
**Goal:** one clear web page to run and inspect Identify, approve cards, exercise
Generate/Defend, and immediately see API errors. This is a debugging console
first and a simple demo second—not the final competition UI.

## Current state

- FastAPI exists at `apps/api` with Identify, Catalog, Generate, and Defend
  routes.
- There is no `apps/web`, no `package.json`, and no browser UI.
- `POST /identify/run` is synchronous. The browser receives stage details only
  after the graph finishes; v1 must show a running timer, not fake live progress.
- FastAPI has no CORS setup. The frontend should proxy through Next.js rather
  than opening permissive CORS.

## Stack

- Next.js App Router + TypeScript in `apps/web`
- Tailwind for layout; no component library required in this pass
- Native `fetch`; no React Query/Zustand/chart dependency yet
- Next server proxy `/backend/*` → FastAPI using server-side
  `AEGIS_API_URL=http://127.0.0.1:8000`

No API keys go to the browser. The UI only displays the safe booleans/profile
already returned by `/ready` and `/identify/config`.

## One-page layout

### 1. System bar

Poll every 10 seconds:

- API, Postgres, pgvector: green/red
- Tavily: configured/not configured
- LLM: configured, profile, model
- Identify mode: live/offline

Source: `GET /ready` and `GET /identify/config`.

### 2. Identify runner

- Topic input
- `Run Identify` button
- elapsed timer while request is pending
- result summary:
  - Tavily/RSS candidate URLs
  - documents extracted
  - proposal count
  - HITL count
  - errors/abstains in a visible diagnostics panel
- source list with domain, URL, source type, and extraction/chunk id

Source: `POST /identify/run`.

Do not show “success” just because HTTP returned 200. Distinguish:
`new proposals`, `processed but no new attack`, `abstained`, and `failed`.

### 3. HITL queue

Cards show:

- technique/name/category/rail
- source tier and confidence
- source URLs
- proposed simulator and signal preview
- field difference from nearest catalog card

Actions: Approve, Reject, Reject unsafe. Require a confirmation click. Refresh
queue after each action.

Sources: `GET /identify/hitl`,
`POST /identify/approve/{vector_id}`,
`POST /identify/reject/{vector_id}`,
`POST /identify/reject-unsafe/{vector_id}`.

Editing a full AttackSpec is deferred; raw JSON editing is an easy way to create
invalid cards.

### 4. Atlas / threat map

Five compact category columns with T01–T24 chips. Chip shows status, source
tier, confidence, and whether Generate supports it. Clicking opens the complete
card in a drawer.

Source: `GET /catalog/threat-map`, then `GET /catalog?technique_id=Txx` for
details.

### 5. Generate and Defend debug panels

Generate:
- list eligible cards
- run Population or Canary
- show run id, injector, stage/event count, and returned errors
- clearly badge **stub today** until Plan 08 replaces one-event JSON

Defend:
- coverage counts
- T01–T24 coverage status
- rules list
- named gaps

Sources: existing `/generate/*` and `/defend/*` routes.

## Files

```text
apps/web/
  app/
    page.tsx
    layout.tsx
    globals.css
    backend/[...path]/route.ts
  components/
    SystemBar.tsx
    IdentifyRunner.tsx
    HitlQueue.tsx
    ThreatMap.tsx
    GeneratePanel.tsx
    DefendPanel.tsx
    JsonDetails.tsx
  lib/
    api.ts
    types.ts
  package.json
  next.config.ts
  tsconfig.json
```

Keep components below roughly 200 lines. `page.tsx` composes panels; it does not
contain request logic.

## API client rules

- One `api.ts` wrapper handles JSON parsing, timeouts, and FastAPI error bodies.
- Abort Identify after a configurable 120 seconds and display “request timed
  out; backend may still be running.” Do not silently retry a POST.
- GET health polling may retry with capped backoff.
- Render errors as plain text; never render article/LLM HTML.
- Type only fields used by the UI; preserve an expandable raw JSON view for
  debugging.

## Single-runner integration

After the frontend works:

1. `run.sh` performs the live e2e gates.
2. It starts FastAPI on `:8000` and Next.js on `:3000`.
3. One `trap` stops both child processes on Ctrl+C.
4. `./run.sh --check` performs gates and a production frontend build/type-check,
   then exits.
5. No second frontend shell script is added.

Until that slice is implemented, run `npm run dev` from `apps/web` separately;
do not complicate `run.sh` before the UI can build.

## Debugging and logging connection

Plan 10 adds durable run logs. When `GET /runs/{run_id}` exists, add:

- stage timeline with duration and counts
- Tavily query `ok | empty | error`
- LLM `llm | abstain | rules_fallback`
- Librarian candidate vs persisted HITL count
- final failure stage and redacted message

Before that endpoint exists, show only data returned by `/identify/run`; do not
fake a stage timeline.

## Build order

1. Scaffold Next.js + server proxy + API types.
2. System bar and reusable error/JSON details.
3. Identify runner and returned diagnostics.
4. HITL queue and actions.
5. Threat map.
6. Generate/Defend panels.
7. Responsive polish and empty/loading/error states.
8. Integrate both servers into `run.sh`.

## Tests

- TypeScript type-check and production build.
- API wrapper tests for success, timeout, and FastAPI `detail` errors.
- Component smoke tests for empty/loading/error/result states.
- One Playwright flow using a mocked backend:
  health → run Identify → view proposal → approve.
- One manual live check against FastAPI; not in CI.

## Done when

- A teammate can diagnose Postgres/Tavily/LLM configuration from the top bar.
- They can run Identify, see sources/errors, and approve a persisted card
  without curl.
- They can inspect Atlas, Generate stub output, and Defend coverage on one page.
- No keys, full prompts, or full article bodies reach browser output.
- Refreshing the page does not repeat POST requests.
- `./run.sh` is still the only complete product runner.

## Explicit cuts

No authentication, user accounts, charts, streaming, WebSockets, design system,
dark-mode work, rich JSON editor, or model-training dashboard in this pass.
