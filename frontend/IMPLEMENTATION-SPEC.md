# AegisLoop frontend — implementation spec

**Status:** Phase-2 contract. Art direction: [DESIGN.md](DESIGN.md) (tokens §§1–3; **craft / micro-behaviour §13**). Product jobs: [MC_PS.md](../MC_PS.md). If this file and DESIGN.md §4/§9 conflict, **this file wins** (DESIGN §4 Identify-as-mule-scan and §9 skip-Generate are scoring failures). Look of chips, log, palette, drawer, charts: DESIGN §13. Behaviour of the 90s path: this file.

**Target:** 1920×1080, judge at 1.5–3 m, API via Vite `/api` → `:8000`.

---

## Operator intent (source of truth)

This is what the human operator asked for. Subagent pixel maps, P0 encyclopedias, and “complete product” plans do **not** override it. Session/SSE/API laws below still hold.

**Product:** AegisLoop at Mastercard Innovation Challenge @ GFF 2026 — Identify → Generate → Defend as **one closed loop**. Judges score diversity, fidelity, detection (recall **and** low genuine FPR), novelty (misses feed new attacks), live-payments feasibility, and a presentable prototype that **shows the loop**. Professional finance language. No Cursor/lab jargon. Live **search + LLM** on glass when configured; fallback **visible** (chip + ⌘K), never silent. Glass copy SSOT: **§6**.

**90s demo (what a standing judge remembers):** capability stills + metrics — not a training console.

| t | On glass | Pillar |
|---|---|---|
| 0–20s | T01–T24 landscape + Discover (sources + streamed ops log) + one Add | Diversity + “the system works” |
| 20–45s | Demo-scale payment tape + seed + fidelity sentence | Fidelity |
| 45–70s | Curve + 56px recall @ genuine FPR **already populated** | Detection |
| 70–90s | Second series / “defense updated” overlay → miss cell on Identify | Novelty |

**Train is off the critical path.** Fitting is how the curve exists. It is **eh**. Metrics are the Defend hero. Frozen/recorded score is an **honest booth**. Live fit is **proof that scoring is real**. The judge never waits on a spinner labeled Train.

**Booth path vs proof-of-backend** (detail in §11):

| Booth (timed, 90s, three nav items) | Proof (optional — “yes we have backend”) |
|---|---|
| Identify: catalog + Discover (sources + log) + Add | Topic search box; internal HITL dump (never labelled HITL on glass) |
| Generate: demo-scale ledger + fidelity | Full 2400×120×30/90 population |
| Defend: curve + Pareto + hero KPI on glass | Explicit Fit / hyperparams / Recompute |
| Loop: Retrain overlay + Identify highlight | Arms Race as a named page; live Tavily as a scoring requirement |
| LIVE/RECORDED chip, Continue as a guard | Copilot; GuidedDemoBar tour; 4th Metrics nav |

Pages/features may exist so a seated judge can see the backend. They are **not** the demo. Do not force every capability onto the timed path. Do not invent a fourth nav page.

**Composition, not a second product.** Identify / Generate / Defend aesthetic research is how the still is arranged (full viewport, paper/sage/ink, classy work, not lab cards). Do **not** import 112px ATT&CK cells, 1024\|627 px splits, or a required SCANNING reader column as competing law. Landscape must be **readable at 2 m**. Identify SCANNING stays **sources + log (62/38)**. Generate stays **ledger 62% \| seed + layered mule graph 38%**. Defend stays **metrics-first 72/28 curve**. Any Defend write-up that puts **Train and score** as the header primary is **overridden**.

---

## 0. How we lose MC_PS.md (do not ship this)

The brief scores five things plus a prototype that **shows the closed loop**.

| Axis | Current UI | DESIGN.md §4/§9 if followed literally | Required on glass |
|---|---|---|---|
| Diversity | Threat Map exists but is disconnected; Identify is a search box | One mule ring, “issuer feed” | T01–T24 landscape first; Discover proposes **new** typologies with sources |
| Fidelity | Generate exists; demo bar visits it | **Skipped** | Ledger + seed + fidelity sentence in the 90s |
| Detection | Fit/score + recall@FPR curve (good) | Drag OP + ₹ theatre as the story | Curve + 56px hero KPI **already on glass** (frozen pack or auto-score); annotated recall @ genuine FPR; holdout caveat. Train is proof, not the beat |
| Novelty | Loop M is a separate jargon page | “Apply operating point” ends the demo | **Retrain from missed fraud** on Defend; miss cell highlighted back on Identify |
| Feasibility | HITL exists, misnamed; no LIVE chip | Fake “connected to issuer feed” | Analyst review; interventions; LIVE vs RECORDED honesty |

**Kill shots we already have in code**

- Search-first Identify ([TopicResearchPanel.tsx](src/features/identify/TopicResearchPanel.tsx))
- Lab copy: HITL, Loop M, vector_id, inner_val, Scout/Curator
- Copilot “Planned”
- Demo bar navigates only
- No SSE — button spinner hides the product
- `model_run_id` stuck to generate `run_id` after retrain
- Stale score/Loop M in localStorage when generate run changes
- Curve baseline fabricated 0.84× in [recall-fpr-data.ts](src/features/decisioning/recall-fpr-data.ts)
- Full generate 2400×30 on the primary click (booth timeout)
- Train spinner as the 90s climax (fitting XGBoost is proof, not the story)
- Two booth buttons Fit | Score
- Entering Defend blocked on `training.status === completed`

---

## 1. Taste from 21st MCP (30 Aug 2026)

MCP `user-21st` is connected. **search** (free) used; **get_component** not used (2/2 quota reserved — do not burn on landing kits). **get_inspiration** without a `.21st/design.json` ranked candle charts for “light” — ignore it.

**React Bits / shadcn MCP:** `@react-bits` is in [components.json](components.json). Project `.cursor/mcp.json` runs `npx -y shadcn@latest mcp --cwd frontend` (Cursor, **not** `--client claude`). This session’s `GetDynamicTools` still has **no shadcn namespace** until the operator enables **shadcn** in Cursor Settings → MCP and reloads. Browse that way or `npx shadcn@latest list @react-bits --cwd frontend`. Install **allow-list only**. Default: implement DESIGN.md motion in our components.

| Steal (restyle + `prefers-reduced-motion`) | Maybe (usually skip) | Never on the booth |
|---|---|---|
| FadeContent / AnimatedContent — one-shot 80–160ms, not page scroll-reveal (upstream is 1000ms + ScrollTrigger). CountUp — counters; reduced-motion = final number instantly | Counter (CountUp sibling). Stepper (we already have a phase stepper) | Dither and **all** shader Backgrounds (Aurora, Plasma, Hyperspeed, …). ClickSpark, ElectricBorder, Glitch/Gradient/Particle/ASCII/Decrypted/Shiny text, BlobCursor, Cubes, glass, bounce/physics, marquees, cursor toys |

### Steal (structure only — restyle to paper/sage/ink, 6px, Plex)

| Job | 21st result | How it functions here |
|---|---|---|
| ⌘K | shadcn Command `id: 714` (unstyled). Fallback originui Command `382` | Overlay **480px** (DESIGN §13; was 320 — too Spotlight). Groups: Recorded / Live / Navigate / Copy seed. No 8-bit, no hover-pill (`23173`), no Omni recents theatre |
| Work log | Audit Log `id: 25163` (timestamp, type, status, row → detail) | Right rail. **Not** Interactive Logs `10635` (animated filters). **Not** Data Stream `18429` (terminal SOC). Pipeline stages may use collapsible **pattern** like CI log `24897` without the CI skin |
| Ledger / review table | originui dense Table `id: 89` or shadcn Data Table `1050` | 36px rows, hairlines, tabular nums. **Not** retroui neobrutalist `25153`, **not** Financial Markets Table `9045` (flags, sparklines, Framer) |
| Drawer | Keep [Drawer.tsx](src/components/ui/Drawer.tsx); Sheet pattern `25002` | 400px right; 8px radius; one shadow. Click log line / technique / proposal |
| Status | Keep StatusChip; restyle glyph + word | Policy colors only. **Not** HeroUI chips / pill badges |
| Sidebar | Existing 220px; no Limelight / dock / glass nav from inspiration | Three items only |

**Never `generate` UI from 21st AI** for booth screens. Never paste catalog CSS variables. Never Inter/indigo/`rounded-2xl`/glass from snippets.

---

## 2. Layout geometry (alignment law)

Viewport 1920×1080. No `max-w-[1280px]` ([Shell.tsx](src/components/layout/Shell.tsx) today — **remove**).

```
┌──────────┬─────────────────────────────────────────────────────────────┐
│ Sidebar  │ Status strip 32px  LIVE|RECORDED|RULES|FROZEN · run · seed │
│ 220px    ├─────────────────────────────────────────────────────────────┤
│ AegisLoop│ Phase stepper 36px  Identify → Generate → Defend            │
│ Identify │─────────────────────────────────────────────────────────────┤
│ Generate │ Page header 48px  title (Plex Serif 24) + one primary btn   │
│ Defend   │─────────────────────────────────────────────────────────────┤
│          │ Working surface  (chrome ≤ 15% ≈ 162px)                     │
│          │ 24px gutters; columns hairline-separated                     │
└──────────┴─────────────────────────────────────────────────────────────┘
```

**Identify stages (one hero)** — catalog + Discover (sources + log), not a search box, not a mule scan.

- REST: landscape **100%** of working surface (T01–T24, five categories, readable at 2 m). Discover in header. Do not lock 112px ATT&CK cells. **This REST still is the booth landing** (DESIGN.md §14, form A). Do not add a 4th route or a title card in front of it.
- SCANNING: landscape strip 72px top; **sources 62% | ops log 38%** of remaining; metrics strip 40px bottom. A center “reader” pane is optional if it fits; it is **not** a required third column.
- REVIEW: proposed cards 62% | log 38%; Continue banner 40px.

**Generate:** payment tape, not a sim playground. **Ledger 62% | right 38%** (seed stamp over layered mule graph); fidelity strip 40px. Demo-scale is the booth click. 1024\|627 px research is composition, not a second spec.

**Defend:** metrics-first **curve 72% | policy / interventions 28%**; **one** hero KPI at 56px (recall @ genuine FPR). Closed-loop is a **second series on the same chart**, not a named Arms-race page. Retrain is a short beat: that series + Identify highlight. Header primary after score exists is **Retrain from missed fraud**; **Recompute on this run** is secondary — never a Train hero. Empty/scoring Defend shows axes + counters, not a Train-labeled primary.

**Numbers:** Plex Mono, `font-variant-numeric: tabular-nums slashed-zero`, right-aligned in tables. Amounts ₹ Indian grouping. Timestamps IST `HH:mm:ss.SSS`.

**Z-index:** overlay 40, drawer 50, palette 60, modal 70. Focus trap in palette/drawer/modal.

---

## 3. Session law (kills run_id races)

One store: `aegisloop:session` (localStorage), shape:

```
{
  identify: { topic, runId, source: live|recorded, proposedIds[], approved: [{id, techniqueId, name}] },
  generate: { runId, seed, scale: demo|full, fidelityPass, eventCount },
  defend: { modelRunId, score, missTechniqueId, loopResult },
  ui: { highlightTechniqueId, sourceChip }
}
```

Rules:

- New generate run **clears** defend score + loop result.
- After retrain, `modelRunId` becomes server champion id (`{run}__loopm-train`); never rescore with generate `run_id` as model.
- New Identify topic does **not** wipe generate unless operator confirms.
- Demo step is derived from session (which phases are done), not a separate `aegisloop-demo-step`.
- Kill `useLoopMRun` (`loopm_${id}`) — dead key.
- Kill dual score stores (`aegisloop:decisioning-score` vs `lastScore`).

---

## 4. Backend + transport (no silent hangs)

**Existing (keep, wrap in human errors)**

| UI | Method | Notes |
|---|---|---|
| Landscape | `GET /catalog/threat-map` + `GET /defend/coverage-map` | Render if either succeeds; don’t blank the page if one fails |
| Discover | `POST /identify/run` | Empty topic; server may fill gaps |
| Queue | `GET /identify/hitl` | Show unused evidence fields in cards |
| Approve / dismiss / unsafe | existing POST routes | Parse `ApiError` JSON; per-row errors |
| Eligible attacks | `GET /generate/eligible` | **Call this** — Generate context strip |
| Config / health | `GET /identify/config`, `GET /health` | Drive LIVE chip; never invent live |
| Simulate | `POST /generate/population` | **Demo scale default** e.g. 200 cust × 40 merch × 14 days; caption honesty. Full 2400×120×30/90 is proof-of-backend, not the booth click |
| Train / score | `POST /defend/fit`, `/defend/score` | Combined job. Booth: auto-chain on Defend enter when `generate.runId` set and `defend.score` empty — **no second booth click**. Never Fit \| Score as two booth buttons. Pareto / curve from **score payload**, not `/metrics` |
| Retrain | `POST /defend/loop-m` | Label: Retrain from missed fraud. Use **this generate run’s scale** — must not inherit a 2400 sidecar |

**Add**

| UI | Contract |
|---|---|
| Identify stream | `POST /identify/run/stream` SSE. Events: `{t, verb, body, status, artifacts?}`. Verbs: COLLECT EXTRACT RANK GROUND PROPOSE REPLAY. First event ≤800ms (emit `COLLECT started` before scout returns). On collector/LLM fail: `{fallback:recorded, reason}` then fixture events. |
| Generate progress | SSE or poll. Events: COMMIT counts, family mix, graph edge batch. Ledger DOM cap 40 rows. |
| Recorded packs | `GET /demo/recorded/identify\|score\|loop` serving fixtures / `photography_day.json` / `loop_m_result.json`. Palette commands hit these. Chip FROZEN/RECORDED. |
| Vite | Proxy `/api` must not buffer SSE (`timeout: 0` or http-proxy `sse`). Client: `fetch` + `ReadableStream` (EventSource cannot POST). |

**Do not** claim issuer feed. Identify is allowlisted OSINT + catalog.

---

## 5. Click / keyboard matrix (behaviour)

### Continue / stepper

Entering Defend **does not wait** on `training.status === completed`. A judge on the 90s script never waits for train.

| Gate | Ready when | Not when |
|---|---|---|
| Continue to Generate | `approved ≥ 1` **or** operator accepts catalog seed | — |
| Continue to Defend / stepper Defend **ready** | Generate fidelity known (`session.generate.fidelityPass` set — pass or fail) | **Not** fit finished. Entering Defend with a generate run shows metrics or “scoring this run…” counters |
| Defend working surface | `generate.runId` present | If `defend.score` exists, paint it. Else preferred booth: frozen/recorded pack. Live path: auto-score (counters, not a Train spinner) |
| Stepper Defend **done** | Score on glass (live or frozen/recorded) | Retrain is the loop closer, not a gate to see the curve |

### Chrome

| Input | Result |
|---|---|
| Nav Identify/Generate/Defend | Route only; no job |
| Stepper click | Same |
| Source chip | Popover: mode, last reason, tavily/llm configured yes/no — never keys |
| ⌘K / Ctrl+K | Palette. Esc closes. |
| Palette: recorded Identify/score/loop | Sets chip; plays paced SSE or loads JSON |
| Palette: Return to live | Only if `/identify/config` says live search + LLM |
| End | Re-follow log |

**t=0 first paint (form A — landscape is the landing).** `/` **is** Identify REST. No `/landing`, no 3–8s dissolve cover, no marketing route. At 0.0s the judge sees: AegisLoop wordmark · LIVE\|RECORDED chip (reserved slot, glyph+word, **no pulse**) · stepper Identify · census **24** at 48px mono (constant — not CountUp) · **5** category columns · T01–T24 landscape **100%** of the working surface · primary **Discover emerging threats** · one `ink-3` caption: allowlisted OSINT + catalog, **never** “connected to issuer feed.” Catalog still fetching: cells appear as objects; empty = `—`; no pulse skeleton. **Skip does not exist on REST** — Skip is recorded Discover playback only. First 12s is talk, not motion. Discover click → SCANNING (this screen’s geometry, not a new look). See DESIGN.md §14.

### Identify

| Input | Guard | Result |
|---|---|---|
| Discover emerging threats | Not already SCANNING | POST stream; REST→SCANNING; first log ≤800ms |
| Double-click Discover | disabled while pending | No second run |
| Narrow the scan | collapsed | Optional topic; still not the default |
| Click landscape cell | — | Drawer. Gap: “Discover this coverage gap” pre-fills optional topic |
| Click log line | — | Drawer artifacts (URLs), not thoughts |
| Add to catalog | one click | Approve API; session.approved++; Continue banner |
| Dismiss / Mark unsafe | — | Human labels; unsafe tooltip: not safe to simulate |
| Continue to Generate | ≥1 approved else seed offer | `/generate` |
| Proposed list empty | after approve / dedup | Show **In catalog** cards from DB (`identify-*` rows, `status=open`) — demo context only; no second Approve |

Log auto-follow until scroll-up >40px; pill “↓ Live · n new”.

### Generate

| Input | Guard | Result |
|---|---|---|
| Simulate payment traffic | — | Demo scale; if no approvals, caption “catalog seed” + RECORDED |
| Full population | proof-of-backend (secondary / ⌘K) | 2400×120×30/90 — **not** the booth click |
| Canary | secondary | One-line: pinned FinCEN typology |
| Continue to Defend | fidelity known | `/defend` — does **not** wait on fit |

### Defend

**Primary visual is the curve + 56px hero KPI, not a train button.** Preferred booth: frozen `photography_day` / recorded score pack paints immediately (chip FROZEN or RECORDED, caption “locked holdout”). Operator talks the numbers. Live path: auto-score on enter when `session.generate.runId` exists and `session.defend.score` is empty — chain fit+score **without a second booth click**. Counters: “scoring this run…”. Button **Recompute on this run** (was Train and score) is **secondary**, not the hero.

| Input | Guard | Result |
|---|---|---|
| Enter Defend | generate.runId | If `defend.score` set → paint curve. Else frozen/recorded pack **or** auto-score. Never a Train-labeled spinner as the hero |
| Recompute on this run | generate.runId; **secondary** | Fit then score; log two stages. Proof that scoring is real, not the 90s path |
| Fit \| Score as two buttons | — | **Forbidden on booth glass.** Hyperparameter Fit lives on a proof surface / ⌘K only |
| Retrain from missed fraud | has score | Confirm one line; loop-m; **second series on the same chart**; short beat. Payoff is the overlay + Identify highlight, not watching epochs. Frozen pack may instead show a one-line “defense updated” overlay if faster |
| Continue to Identify | after loop (or recorded overlay) | `/?highlight=Txx` miss cell — miss family **must** map to a technique id |

No drag-operating-point as the **primary** story. Annotation is read-only from model OP unless we explicitly add a “what-if” that does not claim applied policy. Pareto stays on this page — **do not** add a 4th Metrics nav item.

---

## 6. Copy (user-visible strings) — dictionary

**SSOT for every booth string.** DESIGN.md §3 is the forbidden/map summary; this section is the dictionary implementers ship. Landing / first-still uses the same glossary. Do not write a `copy.ts` that contradicts these literals. API field names in TypeScript types are allowed; **JSX, titles, labels, placeholders, aria-labels, chart legends, chip text, and banners are not**.

Voice: issuer-risk English. Short sentences. Numerals in Plex Mono. ₹ with Indian grouping (`en-IN`). Scoring words from [`MC_PS.md`](../MC_PS.md): diversity, fidelity, recall, genuine FPR, novelty, feasibility. LIVE chip = live **search + LLM + health**. Never claim live UPI, live issuer feed, or that this lab **is** Mastercard Decision Intelligence. Typology / step-up / genuine vs fraud are vocabulary only.

### 6.1 Grep law (tests)

CI must fail if any of these appear in **user-visible** strings under `frontend/src/**/*.{tsx,ts}` (JSX text, quoted UI copy, `title`/`label`/`placeholder`/`aria-label`). Allow: comments; API/type field names (`vector_id` in `api-types.ts` is not glass).

```
HITL|Loop M|vector_id|inner_val|Scout|Curator|Seed Atlas|Researching|Coming soon|Planned|Decisioning|Arms Race|Simulation Console|AI-powered
```

Also fail (same surfaces): `Librarian|LangGraph|kill shot|catalog_solved|Analyst Copilot|Coming soon|G-TEST|Champion recall|issuer feed|live UPI`.

**Visual grep CI** (1920×1080 stills + source): `rounded-2xl|#2563EB|#6366F1|HITL|Loop M|vector_id|inner_val|Scout|Curator|Seed Atlas|Researching|Coming soon|Planned|Decisioning|Arms Race|Simulation Console|AI-powered`

`vector_id` on glass includes column headers and drawer `Row label="vector_id"`. Technique id on glass is `T01`…`T24` or “Attack ID”.

### 6.2 Canonical glossary (internal → glass → never)

| Internal | Glass | Never on glass |
|---|---|---|
| HITL / HITL queue | Proposed attacks / analyst review | HITL, HITL queue |
| Loop M | Retrain from missed fraud | Loop M, Run Loop M |
| Loop I | Draft rule (not live) | Loop I |
| Scout | Collect (COLLECT); allowlisted OSINT | Scout, scout candidates, Researching |
| Curator | Rank (RANK) | Curator kept |
| Librarian | Write to catalog | Librarian |
| LangGraph / identify_graph | (omit) | LangGraph, agent, pipeline as a product name |
| KillChain Atlas / Seed Atlas | Catalog | Seed Atlas, KillChain Atlas |
| Threat Map (page) | Identify landscape / catalog | Threat Map as a fourth nav item |
| `vector_id` | Attack ID / technique id | `vector_id` |
| `inner_val` | Training validation fold | inner_val |
| G-test | Locked holdout | G-TEST as a title; gtest_seed= |
| G-dev | Development world | G-dev |
| Decisioning | Defend | Decisioning |
| Simulation Console | Generate | Simulation Console |
| Arms Race | Folded into Defend (second series) | Arms Race, Red evasion, Blue PR-AUC |
| Analyst Copilot | Absent from chrome | Copilot, Coming soon, Planned |
| `mule_credit_restrict` | Restrict (payee credit) | mule_credit_restrict |
| Brake | Interventions / policy actions | Brake (product name) |
| FeatureComputer / Optuna / AuthGate | (omit) | Engine names |
| Injectors (`graph_mule`, identity trajectory, `app_session`, `doc_beneficiary`) | Fraud family / technique on the ledger | Engine file names |
| champion (artifact / trophy) | Current detector / after retrain | Champion recall, trophy cup |
| `catalog_solved` | (omit; or “Coverage gap remains”) | catalog_solved trophy |
| Train and score / Fit \| Score | Recompute on this run (secondary) | Train as booth hero |
| issuer feed / live UPI | Allowlisted OSINT + catalog | Connected to issuer feed; live UPI |
| `named_gap` | Coverage gap | named_gap |
| `label_family` | Fraud family | label_family |
| generate → defend pipeline | Continue to Defend / closed loop | pipeline as a product name |
| agent / copilot / vibe / kill shot | (ops verbs) | agent, copilot, vibe, kill shot |
| AI-powered | (omit) | AI-powered |
| Researching… | Discover emerging threats (pending = disabled, same label) | Researching… |

**Status chips (word + colour; never snake_case):** Allow · Notify · Step-up · Hold · Decline · Restrict (payee credit). Coverage: Live rule · Draft rule · Coverage gap. Mode: LIVE · RECORDED · FROZEN · RULES. LIVE only if `/identify/config` says live search + LLM **and** health is up.

**Log verbs (ops, never personas):** Identify `COLLECT` `EXTRACT` `RANK` `GROUND` `PROPOSE` `REPLAY`. Generate `COMMIT` `INJECT` `FIDELITY`. Defend `FIT` `SCORE` `APPLY` `RETRAIN`.

### 6.3 Copy sheet — chrome, ⌘K, Continue, Skip

| Surface | String |
|---|---|
| Wordmark | AegisLoop |
| Nav (three items only) | Identify · Generate · Defend |
| First-still / landing (DESIGN.md §14) | Caption: Allowlisted OSINT + seed catalog — not an issuer feed. Census **24** (constant). Primary: Discover emerging threats. Not “AI-powered”. Not “this is Decision Intelligence.” |
| Status LIVE | MODE `LIVE` · suffix `search + LLM` |
| Status RECORDED | `RECORDED` · suffix `captured {dd Mon, HH:mm IST}` |
| Status FROZEN | `FROZEN` · suffix `locked holdout` |
| Status RULES | `RULES` · suffix `policy table` |
| Phase stepper | Identify → Generate · Defend |
| Discover (header primary) | Discover emerging threats |
| Narrow the scan (collapsed, optional) | Narrow the scan |
| Skip | Skip to result |
| Continue (ready, Identify) | Continue to Generate |
| Continue (ready, Generate) | Continue to Defend |
| Log pill | ↓ Live · {n} new |

**⌘K groups** (ops palette, not product search): Recorded · Live · Navigate · Copy seed.

| Command | Glass label |
|---|---|
| Recorded Identify | Play recorded Identify |
| Recorded score | Load locked holdout |
| Recorded loop | Play recorded retrain |
| Skip (recorded Identify only) | Skip to result |
| Return to live | Return to live search |
| Copy seed | Copy seed |
| Copy OP | Copy operating point |
| Full population | Full population (proof) |
| Fit hyperparams | Fit hyperparameters (proof) |

**Continue / primary disabled reasons** (tooltip or one-line under the control):

| Control | Disabled reason |
|---|---|
| Continue to Generate | Add at least one attack to the catalog, or continue on catalog seed. |
| Continue to Defend | Fidelity not yet known for this corpus. |
| Discover emerging threats | Discovery already running. |
| Retrain from missed fraud | Score this run before retraining. |
| Return to live search | Live search and LLM are not configured. |
| Add to catalog | (enabled on the card; do not steal log focus) |

### 6.4 Copy sheet — Identify (REST / SCANNING / REVIEW)

| State | String |
|---|---|
| REST title | Identify |
| REST body | Catalog of 24 techniques across five categories. Discover proposes new attacks from allowlisted OSINT. |
| SCANNING | Collecting from allowlisted OSINT — {n} sources. |
| SCANNING metrics | {sources} sources · {proposed} proposed |
| REVIEW heading | Proposed attacks |
| Add | Add to catalog |
| Dismiss | Dismiss |
| Unsafe | Mark unsafe |
| Unsafe tooltip | Not safe to simulate. |
| Success line | {n} proposed · {k} added to catalog. |
| Gap drawer CTA | Discover this coverage gap |
| Drawer field (was vector_id) | Attack ID |
| Drawer field (was named_gap) | Coverage gap |
| Empty proposed | No proposed attacks yet. Discover emerging threats, or continue on catalog seed. |
| Live fail banner | Using recorded FinCEN / RBI corpus. |
| Catalog load fail | Could not load catalog. Retry. |
| SSE drop | Discovery interrupted. Use a recorded pack (⌘K). |

Never: Topic research as the hero, Research / Researching…, HITL queue, Approve (say Add to catalog), Topic → HITL, “enter a topic above”.

### 6.5 Copy sheet — Generate (empty / running / success / fail)

| State | String |
|---|---|
| Title | Generate |
| Primary | Simulate payment traffic |
| Secondary canary | Canary — pinned FinCEN typology |
| Empty | No corpus on this session. Simulate payment traffic (demo scale) · seed required for audit. |
| Empty, no approvals | Catalog seed · RECORDED |
| Running | Simulating payment traffic — {done} of {n} events · seed {seed}. |
| Success | Corpus ready — {n} events · seed {seed} recorded. |
| Fidelity pass | Fidelity pass — PSI versus this run’s priors within band · fraud-rate in lab envelope · not a live UPI distribution. |
| Fidelity fail | Fidelity fail — do not score this run. {reason}. |
| Fidelity checking | Checking fidelity — PSI, fraud-rate band, mule fan-in. |
| Fail | Generation stopped at {n} events — seed preserved. Retry continues from checkpoint. |
| Seed stamp | seed {n} · reproducible |
| Eligible strip | {n} catalog techniques eligible to simulate |

### 6.6 Copy sheet — Defend (empty / scoring / frozen / retrained)

| State | String |
|---|---|
| Title | Defend |
| Empty | No score on glass. Continue from Generate, or load a recorded pack (⌘K). |
| Scoring | Scoring this run — {done} of {n}. |
| Frozen caption | Locked holdout. Threshold chosen on the training validation fold; scored once. |
| Frozen hero | recall {r}% @ genuine FPR {f}% |
| OP annotation | Operating point — recall {r}% @ genuine FPR {f}% |
| Holdout caveat | Threshold chosen on the training validation fold. Holdout scored once. Thresholds are not searched on the test labels. |
| Secondary | Recompute on this run |
| Primary after score | Retrain from missed fraud |
| Confirm retrain | Retrain from missed fraud on this run’s scale. Promote only if family ranking and genuine FPR do not collapse. |
| Retrained overlay | Defense updated — second series is after retrain from missed fraud. |
| Series A | Detector |
| Series B | After retrain |
| Rules baseline | Rules baseline |
| Miss caption | Miss family: {family} → technique {Txx} |
| Score fail | Could not score this run. Load locked holdout (⌘K). |
| Artifact missing | Model artifact missing. See source status (⌘K). |

Policy chips: Allow · Notify · Step-up · Hold · Decline · Restrict (payee credit). Histogram title: **Interventions**, not “Brake action histogram”.

### 6.7 Copy sheet — errors

Parse the API body to **one sentence**. Never dump JSON in the banner. Never “check API logs”, “is the API running?”, “please run population on the Simulation Console”.

| Failure | Banner |
|---|---|
| Tavily/LLM down mid-Identify | Using recorded FinCEN / RBI corpus. |
| Fit/score timeout | Locked holdout, not this session. |
| Retrain fail | Could not retrain. Showing locked holdout overlay. |
| Postgres/API down | Service unavailable. Retry. |
| SSE drop | Discovery interrupted. Use a recorded pack (⌘K). |
| Generate fail | Generation stopped at {n} events — seed preserved. |

### 6.8 Appendix — `copy.ts` literals (paste in phase 2; do not invent variants)

```ts
export const COPY = {
  nav: { identify: "Identify", generate: "Generate", defend: "Defend" },
  chip: {
    live: "LIVE · search + LLM",
    recorded: "RECORDED",
    frozen: "FROZEN · locked holdout",
    rules: "RULES · policy table",
  },
  identify: {
    discover: "Discover emerging threats",
    rest: "Catalog of 24 techniques across five categories. Discover proposes new attacks from allowlisted OSINT.",
    firstStillCaption: "Allowlisted OSINT + seed catalog — not an issuer feed",
    scanning: "Collecting from allowlisted OSINT",
    review: "Proposed attacks",
    add: "Add to catalog",
    dismiss: "Dismiss",
    unsafe: "Mark unsafe",
    continue: "Continue to Generate",
    continueDisabled: "Add at least one attack to the catalog, or continue on catalog seed.",
    fallback: "Using recorded FinCEN / RBI corpus.",
  },
  generate: {
    primary: "Simulate payment traffic",
    empty: "No corpus on this session. Simulate payment traffic (demo scale) · seed required for audit.",
    catalogSeed: "Catalog seed · RECORDED",
    continue: "Continue to Defend",
    continueDisabled: "Fidelity not yet known for this corpus.",
    fidelityPass:
      "Fidelity pass — PSI versus this run’s priors within band · fraud-rate in lab envelope · not a live UPI distribution.",
  },
  defend: {
    empty: "No score on glass. Continue from Generate, or load a recorded pack (⌘K).",
    scoring: "Scoring this run",
    op: (r: string, f: string) => `Operating point — recall ${r}% @ genuine FPR ${f}%`,
    frozen: "Locked holdout. Threshold chosen on the training validation fold; scored once.",
    retrain: "Retrain from missed fraud",
    recompute: "Recompute on this run",
    updated: "Defense updated — second series is after retrain from missed fraud.",
  },
  skip: "Skip to result",
  palette: {
    recordedIdentify: "Play recorded Identify",
    lockedHoldout: "Load locked holdout",
    recordedRetrain: "Play recorded retrain",
    returnLive: "Return to live search",
    copySeed: "Copy seed",
    copyOp: "Copy operating point",
  },
  policy: {
    allow: "Allow",
    notify: "Notify",
    stepUp: "Step-up",
    hold: "Hold",
    decline: "Decline",
    restrictPayeeCredit: "Restrict (payee credit)",
  },
} as const;
```

---
## 7. Failure / recorded (must not look like a crash)

| Failure | Chip | UI |
|---|---|---|
| Tavily/LLM down mid-Identify | RECORDED | Same layout; banner “Using recorded FinCEN / RBI corpus.” |
| Operator ⌘K recorded Identify | RECORDED | 12–18s paced playback; Skip to result |
| Preferred booth / ⌘K recorded score | FROZEN or RECORDED | Curve paints immediately; caption “Locked holdout”; this **is** the 90s Defend beat. Live fit is the proof |
| No approvals | RECORDED · catalog seed | Generate still runs |
| Fit/score timeout | FROZEN | photography_day.json; “Locked holdout, not this session.” |
| Retrain (Loop M) fail | FROZEN | loop_m_result.json; banner “Could not retrain. Showing locked holdout overlay.” |
| Postgres/API down | — | Hard error “Service unavailable. Retry.”; `GET /health` |
| SSE drop | DEGRADED slate banner | “Discovery interrupted. Use a recorded pack (⌘K).” |
| Proposed attacks empty after approve | — | **Demo fallback:** `GET /identify/hitl` also returns prior **open** rows whose `vector_id` starts with `identify-` (discovered attacks approved in earlier runs). Glass label **In catalog**; read-only — not re-approvable. `count` stays pending-only; full list in `items` with `disposition: review \| in_catalog`. |

Recorded Identify must not complete in <12s wall clock unless Skip.

---

## 8. Design fuckups to prevent at runtime

- Two blues (`#2563EB` vs tokens) — grep hex in `frontend/src`
- Card-on-card / `rounded-xl` / `shadow-sm` on curve
- Sidebar drop shadow
- Centered empty `·`
- Buttons wrapping on 1920 header — primary stays one line
- Table header vs cell misalignment — one `<table>` or CSS grid with shared column template
- Drawer covering primary button — header stays clickable or drawer 400px from right
- Log stealing focus while adding to catalog
- Landscape reordering under cursor
- React StrictMode double-mount starting two SSE runs — abort controller on unmount
- Chart tooltip off-screen at 1% FPR — clamp
- Indian grouping vs `toLocaleString('en-IN')` only for ₹; percents 1 decimal
- Spinner on the working surface (counters and status text carry state)
- Train-labeled primary on Defend booth glass
- Status chip **width jump** when LIVE → RECORDED (8ch MODE slot — DESIGN §13.4)
- IBM Plex Serif 500 missing (titles fall back to Sans — preload Serif)
- `en-US` grouping on ₹ (`₹4,200,000` instead of `₹42,00,000`)
- Empty state as a centered `·` dashed card (same geometry as success; objects unfilled)
- Palette as Spotlight (recents, 8-bit, hover-pill) instead of grouped ops commands

---

## 9. Tests (exhaust the 90s path)

**Unit / RTL (frontend)**

- Session: new generate clears defend; retrain updates modelRunId
- Copy glossary: grep test per **§6.1** — forbidden tokens absent from user-visible strings in `src/**/*.{tsx,ts}` (allow comments and API type fields)
- StatusChip: coverage enums → human labels (`named_gap` → Coverage gap; `mule_credit_restrict` → Restrict (payee credit))
- Log auto-follow attach/detach
- Identify stage machine REST/SCANNING/REVIEW
- Recorded playback duration ≥12s without Skip
- recall-fpr: no fabricated 0.84 baseline if API lacks stage-1 — show single series + caption
- Continue / stepper: Defend **ready** when generate fidelity is known; **not** gated on fit complete
- Enter Defend with `generate.runId` and empty `defend.score`: paints frozen/recorded pack **or** starts auto-score — no Train click required
- No Spinner as the working-surface loading state (counters / status text)

**API contract (pytest already exists — add)**

- `POST /identify/run` empty topic succeeds (airplane)
- SSE identify emits ≥1 event in 800ms (fake clock / first yield)
- Fallback event when live search off
- `GET /demo/recorded/*` 200

**Playwright (booth path — after glass exists, not a gate before tokens)**

1. Keys off: Discover → playback → Add → Generate demo → Defend **curve already on glass** (frozen pack ok — **no Train click**) → Retrain or loop overlay (frozen ok) → highlight on map
2. Keys on: same with LIVE chip; auto-score may run in background — 90s path does not wait on a Train button
3. Double-click Discover: one stream
4. ⌘K recorded while LIVE: chip switches, no layout jump
5. 1920×1080 screenshot of four killer stills; no indigo, no Inter
6. Continue to Defend enabled when fidelity known even if fit has not started
7. Defend booth glass has no Fit \| Score pair

**Do not** block first glass on an encyclopedic Playwright suite, perfect HITL mutex, or every a11y trap. Session / SSE abort / Continue / auto-score-or-frozen tests travel **with** §10 build order. HITL dump, Copilot, and Fit-hyperparam surfaces are proof — not 90s oracles.

**Visual grep CI:** `rounded-2xl|#2563EB|#6366F1|HITL|Loop M|vector_id|inner_val|Scout|Curator|Seed Atlas|Researching|Coming soon|Planned|Decisioning|Arms Race|Simulation Console|AI-powered`

---

## 10. Build order (phase 2 gates)

Do not start page chrome until tokens match DESIGN.md.

1. **Tokens + copy.ts + Shell geometry** (full bleed, stepper, chip, no Copilot). Gate: grep forbidden copy = 0.
2. **Session store** + clear-on-generate. Gate: unit tests.
3. **Identify** landscape + SSE + cards + Continue. **Demo:** `GET /identify/hitl` appends prior `identify-*` approvals as `in_catalog` (read-only) so REVIEW does not feel empty after Add. Gate: airplane 90s Identify still.
4. **Generate** demo scale + eligible strip + Continue.
5. **Defend** metrics-first (frozen pack or auto-score paints the curve) + second series on retrain + highlight query. Gate: 90s path never clicks Train.
6. **⌘K + recorded packs + Skip.** Proof surfaces (full population, Fit hyperparams, HITL dump) behind palette / secondary — not chrome.
7. **Playwright 90s live and recorded.**

---

## 11. Booth path vs proof-of-backend

Operator intent (top of this file) is the lock. This section is the implementer table. Two classes of surface. Do not force every capability onto the 90s click path. A standing judge remembers metrics, landscape, ledger, Pareto, closed-loop overlay. Training is how the curve exists, not the story.

**Booth path (judge-facing, timed, 1920×1080, ~90s, operator standing, LIVE/RECORDED chip, no jargon):**

| Beat | On glass | Scoring axis |
|---|---|---|
| Identify | REST landscape T01–T24 + Discover (SSE log, OSINT sources) + Add to catalog | Diversity + feasibility |
| Identify (demo) | If pending queue empty after approve: **In catalog** cards from DB (`identify-*`, `status=open`) — read-only context, not re-approvable | Feasibility / analyst review without empty panel |
| Generate | Demo-scale ledger + fidelity chip | Fidelity (India UPI sim) |
| Defend | **Metrics already populated** — recall @ genuine FPR, Pareto/curve, miss cell | Detection |
| Loop closer | Retrain from missed fraud **or** a one-line “defense updated” overlay if the frozen pack is faster; then highlight Txx on Identify | Novelty |

Train wait is **off this path**. If live score is not ready, the recorded pack **is** the demo; live fit is the proof.

**Proof-of-backend** (optional, not on the 90s path). May live behind a secondary control or ⌘K. A judge who asks “is this real?” can be shown one. A judge on the 90s script never waits for train.

| Surface | Status |
|---|---|
| Full population 2400×120×30/90 | Secondary / palette. Honest caption. Not the booth Simulate |
| Explicit Fit / retrain hyperparameters | Proof only. Never two buttons Fit \| Score on booth glass |
| HITL queue dump / topic search box | Proof or kill from chrome. Identify is not a search box |
| Arms-race as a named page | **Folded into Defend** (second series on the same chart). No extra nav |
| Copilot | Stay out of chrome |
| Live Tavily when keys on | Capability, not required for scoring. Chip LIVE only when `/identify/config` says so |

Do **not:** add a 4th Metrics nav item; restore GuidedDemoBar; put Copilot back; make Identify a search box; invent a 0.84× baseline.

### 90-second script (replaces DESIGN.md §9)

Train wait is **off the critical path**. If live score is not ready, recorded pack is the demo; live is the proof.

| t | Click | Judge must see |
|---|---|---|
| 0–20s | Identify REST → Discover → Add | **t=0 first paint = REST landscape** (no intro). T01–T24 (diversity). SSE log + sources (OSINT). One Add (analyst review) |
| 20–45s | Generate → Simulate (demo scale) | Ledger filling, seed, **fidelity sentence** (India UPI sim — fidelity). **Not** full population |
| 45–70s | Continue to Defend | **Curve already there** (frozen pack or auto-scored). Talk recall vs genuine FPR. One miss family. Hero KPI 56px. No Train spinner |
| 70–90s | Retrain from missed fraud **or** recorded loop overlay | Second series on the **same** chart; then Identify `?highlight=Txx` (novelty) |

Operator line at 45s: the numbers, not “watch it train.” At 70s: a miss feeds the next attack. Fit may have run silently on first live enter, or not at all (frozen). Either is honest if the chip matches.

---

## 12. Craft lock (look → DESIGN.md §13)

Operator intent and the 90s beat sheet above **do not change**. This section is only the behaviours the rest of this spec under-specified. Visual anatomy (chip template, log row, palette groups, drawer, chart strokes, motion table): **[DESIGN.md §13](DESIGN.md#13-craft--micro-behaviour)**.

| Gap in this spec | Lock |
|---|---|
| Chip geometry when LIVE → RECORDED | MODE token `min-width: 8ch`. Chip must not shove run/seed. 80–120ms color only; no pulse. RECORDED/FROZEN are slate, never rust. |
| Source popover contents | Mode, tavily/llm **configured yes/no**, last reason. Never keys, never model names. |
| Stepper disabled | Tooltip is a **reason** (`Defend after fidelity is known (pass or fail).`), not a tour / % bar. |
| Sidebar | Three items + `AegisLoop` wordmark (Sans 600, not `AEGISLOOP` shout). No shadow, no icons. |
| ⌘K | **480px** ops overlay (supersedes Taste §1 “320px” — 320 reads as Spotlight). Groups: Recorded / Live / Navigate / Copy. Shortcuts on the right. No recents theatre. Empty query shows all groups. |
| Skip to result | Secondary on the **working surface** during recorded Identify, not only inside the palette. |
| Error banner | One sentence. Never JSON. |
| Landscape | ATT&CK-side: IDs visible, no heat. Hover/focus without lift. `?highlight=Txx` tints in place — **no reorder**. Gap = dashed + `Coverage gap`. |
| Discover mutex | Disabled + `aria-busy` while SCANNING; double-click ignored. |
| SCANNING log | Auto-follow until scroll-up >40px; pill `↓ Live · n new`; drawer-open = detach. **Add/Approve does not steal focus** and does not re-attach. |
| First log ≤800ms | A **row object** (`COLLECT started`), not a spinner. Reduced-motion: still appears by 800ms, no fade. Recorded **wall clock** stays 12–18s even when motion is instant. |
| Verb chips | Identify `COLLECT EXTRACT RANK GROUND PROPOSE REPLAY`. Generate `COMMIT INJECT FIDELITY`. Defend `FIT SCORE APPLY RETRAIN`. |
| REVIEW | Evidence → one disposition (Add / Dismiss / Mark unsafe). Continue copy if `approved = 0`: catalog-seed offer. **Demo fallback:** prior `identify-*` approvals render as **In catalog** (sage badge, no buttons); `count` = pending only. |
| Drawer | 400px, Esc, focus trap, return focus, z-50. Raw JSON collapsed. OP drawer = protocol words. |
| Seed | 48px object, copy-on-click, 120ms sage flash. |
| Eligible strip | Family names, not `vector_id`. |
| Ledger | 36px, `en-IN` ₹, last-40 DOM, same follow/detach as Identify. |
| Mule graph | L→R correspondent layers; one-shot edges; no force layout. |
| Fidelity | **Sentence** (pass/fail + PSI + scale honesty). Continue when fidelity **known** (including fail). |
| Simulate label | **Simulate payment traffic** unchanged while running. |
| Defend empty | Axes + counters already laid out. No Train hero. Frozen pack paints immediately (no line-draw). |
| Hero KPI | 56px recall @ genuine FPR in a **4-cell unequal strip**, not 6 cards. Log FPR. No 0.84 baseline. |
| Brake rail | Allow-heavy histogram (honest). APP/mule one-liners. |
| Retrain | Second series same axes; 160ms sage flash on OP; 56px `Defense updated` inset; then `?highlight=Txx`. |
| Tooltip | Clamp inside plot; `allowEscapeViewBox` false; `isAnimationActive={false}`. |
| Type | Preload IBM Plex **Serif 500** (missing in Tailwind today) + Sans + Mono. All metrics `tnum slashed-zero`. |
| Empty/running/fail | **Same geometry** as success; objects fill. Kill centered `·`. |
| Viewport | 1920×1080 full bleed; remove `max-w-[1280px]`; chrome ≤15%. |
| Forbidden copy | DESIGN §13.9 grep list (extends §6). |

Tests already in §9 that now have craft oracles: chip no layout jump; recorded ≥12s without Skip **and** with `prefers-reduced-motion`; no Spinner on the working surface; 1920×1080 stills with Plex Serif titles. Add: chip width constant across LIVE/RECORDED; palette has four named groups; first Identify log is a `COLLECT` row not a spinner.
