# GFF Booth UI — Design Lock v1.0

**Status:** Stored lock for the AegisLoop prototype. Visual, motion, type, honesty, and work-log rules in this file are canonical. **§13 Craft / micro-behaviour** is the visual SSOT for every booth-path micro (chip, log, palette, drawer, chart strokes, motion). Product jobs (Identify / Generate / Defend) still follow [`MC_PS.md`](../MC_PS.md) and [IMPLEMENTATION-SPEC.md](IMPLEMENTATION-SPEC.md) — see **Mapping to AegisLoop** at the end. Do not reopen product (train as climax, 4th nav, Copilot, search-first Identify, 2400 as primary).

**Basis:** paper/sage/ink token family + IBM Plex (locked, APCA-checked below). All UI copy in English, IST timestamps, ₹ amounts with Indian digit grouping (₹4,20,00,000). Target surface: 1920×1080, bright exhibition floor, judge at 1.5–3 m. Anything I could not verify from public sources is tagged **[NV]** (not independently verified) in Sources.

---

## 1. Executive lock

If a future agent violates any of these eight, the UI becomes slop.

1. **Light paper wins the floor.** Canvas `#F7F5F0`, cards `#FFFFFF`, ink text `#191C19`, one accent: sage `#3E6B4F`. Every other booth at GFF is a dark dashboard on an LED wall; we look like a bank document that is alive. Dark mode does not exist in this product.
2. **IBM Plex trio, strictly separated.** Plex Serif 500 for phase display titles only (24–32px, the "ledger header"). Plex Sans 400/500/600 for all UI (13–14px base). Plex Mono for every number, ID, timestamp, and log line (12–13px, tabular). Inter, Geist, and Space Grotesk are banned everywhere, including error states and charts.
3. **Ramp density, not Mercury minimal.** Table rows 36px, 13px text, 1px hairlines `#E2DFD6`, full-bleed layout with 24px gutters, no max-width container, no card-on-card. Chrome (header + status bar) ≤ 15% of viewport height. One primary metric per screen at 40–64px mono; everything else is 13px supporting text.
4. **Color is status, never decoration.** Exactly five policy colors: allow = sage `#3E6B4F`, notify = ochre `#8A5A00`, step-up = ochre outline variant, hold = slate `#55606B`, decline = rust `#9C3B23`, plus mule-credit-restrict = solid ink chip. Every chip is **glyph + word + color**; color alone is never the signal (WCAG 1.4.1).
5. **The system's proof of work is an append-only ops log** (right rail, 26–38% width). Verb chips (`INGEST`, `PARSE`, `SCORE`, `LINK`, `FLAG`, `QUEUE`, `APPLY`, `REPLAY`) — never personas, never "Agent thinking…". First log line ≤ 800ms after any primary action; this is a hard SLA.
6. **Charts are Stripe-plain.** 1px axes `#E2DFD6`, horizontal gridlines only, 2px ink line, no gradients, no area fills, no donuts, no rounded tooltips. The operating point is annotated with literal numbers ("recall 92.4% @ genuine FPR 0.38%"), not left for the judge to infer.
7. **Motion budget: 80–120ms color transitions, one-shot 160ms row insert. Zero loops.** No pulse, no shimmer, no fade-up on scroll, no line-draw that repeats, no bounce. `prefers-reduced-motion` gets identical *state* — counters and status text carry the state, animation only confirms it.
8. **Honesty is the aesthetic.** Live vs recorded is always visible in the status bar (`LIVE · search + LLM` / `RECORDED · captured 12 Mar, 14:32 IST` / `FROZEN · locked holdout`). LIVE means live **search + LLM + health**, never a live issuer feed or live UPI. Degraded mode is a slate banner, not an apology modal. Lab identifiers (`Loop M`, `HITL`, `Scout`, `vector_id`, `inner_val`) never appear in any user-visible string. Glass copy SSOT: [IMPLEMENTATION-SPEC.md §6](IMPLEMENTATION-SPEC.md).

**Locked tokens** (verified dark-on-light; all body-text pairs exceed WCAG AA 4.5:1 and are computed to exceed APCA Lc 75 — run exports through apcacontrast.com once before print assets):

| Token | Hex | Use |
|---|---|---|
| `paper-0` | `#F7F5F0` | canvas |
| `paper-1` | `#FFFFFF` | cards, rows, drawers |
| `hairline` | `#E2DFD6` | 1px borders, chart axes |
| `ink` | `#191C19` | primary text, primary button bg |
| `ink-2` | `#4A5248` | secondary text |
| `ink-3` | `#6B7367` | metadata (≥12px only) |
| `sage-100` | `#E9F0E9` | allow-tint fills, mule node fill |
| `sage-600` | `#3E6B4F` | accent, allow status, operating point |
| `sage-700` | `#2E5340` | hover, strong sage |
| `ochre-700` | `#8A5A00` | notify/step-up |
| `slate-600` | `#55606B` | hold, degraded banners |
| `rust-700` | `#9C3B23` | decline |

Radii: 6px standard, 4px chips, 8px drawers/modals. Shadows: none except drawers/modals (`0 8px 24px rgba(25,28,25,0.12)`). Primary button: ink solid, paper text, 36px height, 6px radius.

---

## 2. Competitive teardown

| Product | Steal | Never steal |
|---|---|---|
| **Stripe Dashboard** (dashboard.stripe.com; marketing shots — internals **[NV]**) | Event-object naming (`payment_intent.succeeded` → our `mule.ring.flagged`); "system is working" = money moving, not a spinner; Test-mode badge honesty | Left nav icon soup; the blue; marketing gloss |
| **Stripe Radar** (stripe.com/radar) | Plain-language block reason per transaction; risk eval as a row-level attribute, not a separate screen | Fraud-score as a vanity gauge |
| **Stripe Sigma / Events log** | Query → table → row detail as one motion; every event is inspectable JSON behind a drawer | Exposing raw query DSL to judges |
| **Feedzai RiskOps / Case Manager / Cosmos** (feedzai.com — public shots only **[NV]**) | Case queue as the destination of detection; ingestion shown as *counts of messages collected*, not nodes completing | Cosmos explorer's dark cosmic-graph aesthetic — the metaphor, not the mechanics |
| **Mastercard Decision Intelligence + Scam Protect** (mastercard.com newsroom, public pages) | The vocabulary: *typology, step-up, genuine FPR, scoring as a service decision*; operating-point framing | Their blue branding; "AI-powered" hero copy |
| **Ramp** (ramp.com) | Density: 36px rows, one lead number, next-action column; data fills viewport | Ramp's particular green; "smart savings" cheerfulness |
| **Brex** (brex.com) | Policy-as-first-class-object (limits, controls visible as config, not hidden) | Fintech-illustration headers |
| **Mercury** (mercury.com) | Restraint in state communication | Minimalism — we are denser by design (track A verdict: Ramp-dense) |
| **Wise** (wise.com) | Status honesty ("arriving by 14:32" beats badges); fee transparency as trust | Illustration-heavy marketing shell |
| **Sift / Forter / Unit21 / ComplyAdvantage** (public sites) | Review-queue framing; source-tier and corroboration columns in case lists (Unit21 explicitly) | "99.x% accuracy" claims; dark SOC screenshots |
| **Recorded Future / Mandiant Advantage** (public shots **[NV]**) | Analyst-card layout: evidence list → disposition, one disposition per entity | Threat-map theatrics |
| **Bloomberg Terminal** (principles only) | Density discipline: every pixel is data; timestamps to the second; nothing decorative | Amber-on-black; function-key lore |
| **Linear** (linear.app) | 13px type, hairline borders, ⌘K palette as operator tool, zero wasted chrome | Cargo-culting their font instead of their discipline |
| **Airline ops boards / clearing-house tapes** (reference genre) | Append-only tape metaphor, time on the left, auto-scroll | Airport-evacuated-slate styling |
| **Bloomberg Terminal CVD / color semantics** (bloomberg.com/ux; bloomberg.com/company/stories) | Color = semantic status only; glyph+word+color (WCAG 1.4.1). Conceal complexity: one object on glass, depth in the drawer | Amber-on-black; red/green as the only signal; function-key chrome |
| **LSEG / Reuters RT_ITEM_DELAYED · SUSPECT** (developer community, public) | Honest feed-state chips: delayed ≠ down; suspect ≠ blank the numbers. Chip word changes, geometry does not | Red “ERROR” for delayed; pulse-dot “live” theatre |
| **Stripe TEST / sandbox badge** (docs.stripe.com/testing; stripe-ios TEST label) | Mode chip is a reserved slot; livemode honesty is always visible, never a crash | Red alert for test/recorded; layout jump when the word changes |
| **Stripe Events list** (docs.stripe.com/api/events, dashboard/events) | Named event objects (`payment_intent.succeeded` → our `COLLECT started`); row → inspect payload in a drawer, collapsed | Dumping JSON in the banner; tool-call theatre |
| **Feedzai IQ Score / RiskOps** (feedzai.com — public; internals **[NV]**) | Threshold as a **sentence** (recall @ genuine FPR; precision / loss avoided). Case queue as destination | 0–1000 vanity dial; agentic copilot column; “AI-powered” |
| **Recorded Future Intelligence Cards** (recordedfuture.com/blog/intel-cards-overview) | Heading (id + aliases) → evidence list → **one disposition**; related entities as clickable rows | 0–99 risk gauge as the hero; threat-map globe |
| **MITRE ATT&CK Navigator** (github.com/mitre-attack/attack-navigator layer spec) | `layout: side`, `showID: true`, `showName: true`; IDs always visible | Heat / gradient scores; mini layout that hides names at 2 m |
| **Datadog Live Tail + APM Live Search** (docs.datadoghq.com) | Follow until the operator inspects; select/scroll detaches; Pause/Play analogue = `↓ Live · n new`; selecting a row must not steal focus from Approve | Smooth-scroll fight; sampling theatre; terminal green |
| **Datadog quick nav / Grafana ⌘K** (datadoghq.com/blog/datadog-quick-nav-menu; grafana.com dashboards/shortcuts) | Ops palette: grouped commands, shortcuts on the right, Esc. Not product search | Spotlight recents; Raycast hover-pill; 8-bit skin |
| **Linear audit log** (linear.app/docs/audit-log) | `createdAt` · `type` · body; filter by type; JSON behind the API/drawer | Avatar spine timelines; “2m ago” as the only time |
| **NPCI UPI Product Statistics** (npci.org.in/product/upi/product-statistics) | Monthly **aggregates** (volume Mn, value Cr) in a table — settlement tape, not a live ticker | Fake live UPI firehose; “connected to issuer feed” |
| **ISO 20022 camt.053 / nostro–vostro** (SWIFT camt.053; correspondent recon) | Layered statement: originator → intermediary → beneficiary; amounts on edges; one-shot entries | Force-directed SOC graph; pulsing nodes |
| **Fraud Detection Handbook** (fraud-detection-handbook.github.io — ROC/PR) | Recall vs FPR; **log FPR** so the operating region is readable; PR as the zoom of low-FPR | Rainbow area fill; linear FPR that hides 0.1–1%; fabricated 0.84 baseline |
| **Ramp / Brex density; Mercury restraint** (public product shots **[NV]**) | 36px rows, tabular amounts, status = word+color, one lead number | Mercury-minimal empty canvas; six equal KPI cards |
| **IBM Plex loading** (ibm.com/plex; font-display swap) | Preload Serif 500 + Sans 400/500/600 + Mono 400; `tnum` + `slashed-zero` | Inter; FOIT blank titles; proportional figures in metrics |

---

## 3. Forbidden list

| Tell (2024–26 slop) | Why models emit it | Our replacement |
|---|---|---|
| Inter / Geist / Space Grotesk everywhere | Tailwind/shadcn defaults dominate training corpora | IBM Plex Sans/Mono/Serif trio (§1.2) |
| Indigo-500 `#6366F1`, purple→cyan gradients | "AI = gradient" shorthand; RLHF rewards gloss | Sage as the only accent; flat fills |
| Glassmorphism, `rounded-2xl`, `shadow-lg` | Screenshot-pretty; models copy Stripe *marketing*, not Stripe app | 6px radius, 1px hairlines, no shadows except drawer/modal |
| 3 feature cards / hero + CTA | Landing-page prior overwhelms app prior | Every screen is a workspace: canvas + rail + status strip |
| Bounce/lift hover, pulse loops, shimmer skeletons | Perceived "aliveness" via looped motion | 80–120ms color only; skeleton replaced by counters ("8,214 of 15,000") that are the loading state |
| Dark neon SOC / matrix green / pulsing-globe with dots / Orbitron | "Cyber" genre data; hackathon winners looked like this in 2019 | Paper ledger; the globe becomes the mule graph (§7) |
| Agent theater: rainbow borders, tool-call JSON, "the agent is thinking…" | Cursor/Devin/LangGraph UX copy | Ops verb chips + results ("`LINK` 4 accounts → ring R-118-3") |
| Particle backgrounds, "AI-powered" pill, "99.9% accuracy", "Coming soon" | Hackathon cargo cult | A real number with its caveat ("92.4% recall on held-out month · genuine FPR 0.38%") |
| Headline jargon: HITL, Loop M, Scout, Curator, Librarian, LangGraph, Seed Atlas, vector_id, inner_val, Decisioning, Arms Race, Simulation Console | Internal codenames leak into copy | Glass names in the map below. Never print the internal token. |
| Agent / copilot / pipeline-as-product / "vibe" / "kill shot" | Cursor and hackathon theatre | Ops verbs and finance nouns. The product is Identify / Generate / Defend, not an agent. |
| "Champion" as a trophy, G-test as a page title, `catalog_solved` | Lab scoreboard leaking onto glass | Series = detector / after retrain. Holdout, not G-test. Coverage gap remains — no trophy chip. |
| "Connected to issuer feed" / "live UPI" / "this lab is Decision Intelligence" | Honesty collapse; Mastercard brand theft | Allowlisted OSINT + catalog. LIVE chip = search + LLM + health. Typology / step-up / genuine FPR are **vocabulary only**. |
| Card-only / US framing ("chargeback", "card fraud") | US training data | UPI/APP vocabulary: *authorised push payment, mule account, typology, step-up, beneficiary* |
| Donut charts, blue gradient area charts | Tailwind chart-demo prior | §7 chart spec |

**Canonical map (internal → glass).** Full strings, Continue reasons, ⌘K, and errors: [IMPLEMENTATION-SPEC.md §6](IMPLEMENTATION-SPEC.md). Landing / first-still uses the same dictionary.

| Internal (code, docs, API) | On glass | Never on glass |
|---|---|---|
| HITL | Proposed attacks / analyst review | HITL, HITL queue |
| Loop M | Retrain from missed fraud | Loop M, Run Loop M, Arms Race |
| Loop I | Draft rule (not live) | Loop I |
| Scout / Curator / Extractor / Grounder / Librarian | COLLECT / RANK / EXTRACT / GROUND; catalog write | Scout, Curator, Librarian, LangGraph, Researching |
| KillChain Atlas / Seed Atlas | Catalog (T01–T24) | Seed Atlas, KillChain Atlas, Threat Map as a 4th nav |
| `vector_id` | Attack ID or technique id (Txx) | `vector_id` as a column or label |
| `inner_val` | Training validation fold | inner_val |
| G-test / G-dev | Locked holdout / development world | G-TEST as a title; gtest_seed= on a tooltip |
| Decisioning | Defend | Decisioning |
| Simulation Console | Generate | Simulation Console |
| Arms Race / co-evolution / RED·BLUE | Second series on the Defend chart | Arms Race, Red evasion, Blue PR-AUC |
| Analyst Copilot | (absent from chrome) | Copilot, Coming soon, Planned |
| `mule_credit_restrict` | Restrict (payee credit) | mule_credit_restrict, mule credit restrict |
| Brake | Interventions / policy actions | Brake as a product name |
| FeatureComputer / Optuna / AuthGate | (omit) | Engine names |
| Injector engines (`graph_mule`, …) | Technique / fraud family on the ledger | Engine file names |
| champion (artifact) | Current detector / after retrain | Champion recall, trophy, catalog_solved |
| Train and score / Fit \| Score | Recompute on this run (secondary) | Train as the booth hero |
| issuer feed / live UPI | Allowlisted OSINT + catalog | Connected to issuer feed; live UPI |
| `named_gap` | Coverage gap | named_gap |
| `label_family` | Fraud family | label_family |
| pipeline (product name) | Discover / closed loop | generate → defend pipeline |
| agent / copilot | (ops verbs only) | agent, copilot, AI-powered |

Mastercard Decision Intelligence / Scam Protect: **vocabulary only** (step-up, genuine vs fraud, typology). Never claim this lab is Decision Intelligence.

---

## 4. Phase art direction

### IDENTIFY — Discover emerging threats (composition in this section is Generate’s mule graph; product job is catalog + Discover — see Mapping below)
- **Composition:** header 7% · graph canvas 58% (left) · work-log rail 26% (right) · metrics strip 9% (bottom: ingested / flagged / ring count).
- **Hero object:** the mule-network graph, layered left→right (originators → mule layer → aggregation → cash-out). **Secondary:** auto-following work log.
- **Primary button:** rest → **"Discover emerging threats"** · scanning → same label, disabled · review → **"Add to catalog"** on the card (header stays Discover).
- **Copy (product SSOT: IMPLEMENTATION-SPEC §6).** REST — *"Catalog of 24 techniques across five categories. Discover proposes new attacks from allowlisted OSINT."* SCANNING — *"Collecting from allowlisted OSINT — {n} sources."* REVIEW — *"Proposed attacks — add to catalog or dismiss."* Error — *"Using recorded FinCEN / RBI corpus."* Never *"Connected to issuer feed"* / *"Begin scan"* / HITL.
- **Killer still:** the moment ring R-118-3 resolves — four sage-tinted nodes snap into one-shot alignment with ₹-labelled edges while the log simultaneously prints `LINK 4 accts → R-118-3`.

### GENERATE — build the synthetic corpus
- **Composition:** header 7% · corpus ledger table 64% (full-bleed) · typology/seed panel 20% (right) · summary strip 9%.
- **Hero object:** the filling ledger — rows insert one-shot as generation proceeds, each tagged `APP scam` / `ATO` / `mule layering` / `first-party`. **Secondary:** seed panel — `seed 1337 · reproducible` in mono.
- **Primary button:** **"Simulate payment traffic"** (running: label unchanged, disabled; secondary "Stop" if present). Full population is proof, not this click.
- **Copy (product SSOT: IMPLEMENTATION-SPEC §6).** Empty — *"No corpus on this session. Simulate payment traffic (demo scale) · seed required for audit."* Running — *"Simulating payment traffic — {done} of {n} events · seed {seed}."* Success — corpus ready + fidelity sentence. Error — seed preserved; retry from checkpoint. Never engine names (`graph_mule`) on the ledger.
- **Killer still:** ledger mid-fill with the seed stamp visible — reproducibility as a design element no competitor shows.

### DEFEND — operating point and closed-loop policy
- **Composition:** header 7% · recall–FPR curve 46% (left) · policy lever column 27% (right: allow/notify/step-up/hold/decline/restrict thresholds, each a row) · closed-loop outcome strip 20% (bottom: *fraud prevented / genuine blocked*, ₹, mono).
- **Hero object:** the operating point on the curve. **Secondary:** policy levers with live ₹ consequences.
- **Primary button (after score exists):** **"Retrain from missed fraud"**. **Recompute on this run** is secondary. Never **Train** / **Fit \| Score** on booth glass.
- **Copy (product SSOT: IMPLEMENTATION-SPEC §6).** Empty — *"No score on glass. Continue from Generate, or load a recorded pack (⌘K)."* Scoring — *"Scoring this run — {done} of {n}."* Frozen — *"Locked holdout — recall {r}% @ genuine FPR {f}%."* Retrained — *"Defense updated — second series is after retrain from missed fraud."* OP annotation — *"Operating point — recall 92.4% @ genuine FPR 0.38%"* (placeholders until ML supplies holdout numbers). Never Decisioning, Loop M, inner_val, Champion recall.
- **Killer still:** operating point annotated mid-curve with crosshair hairlines and the ₹ outcome strip below — the "Mastercard-shaped chart" made executable.

---

## 5. Stage machine — Identify

States: `REST → SCANNING → REVIEW`, overlay `DEGRADED` on any state.

| Transition | Trigger | Motion | What grows / compresses |
|---|---|---|---|
| REST→SCANNING | "Discover emerging threats" click | Instant; no tween | Metrics strip appears (one-shot 160ms slide-up); log rail begins auto-follow; graph nodes fill as ingested — each node/edge is a **one-shot** insert, never re-animated |
| SCANNING→REVIEW | Scan completes, or operator clicks "View flagged (n)" with n≥1 | Canvas compresses 58%→40% width as **one 160ms** transition; case queue takes the freed space; no bounce | Case queue rows insert one-shot by `FLAG` time order |
| REVIEW→(Defend handoff) | "Escalate to review" | Instant state change, 120ms sage confirm flash on the button | — |
| Any→DEGRADED | SSE drop | Instant; slate banner replaces status strip content | Log rail switches to `REPLAY` verb chips |

**Timing SLAs:** first log line ≤ 800ms after click · first flagged account ≤ 4s · metrics counter updates ≥ 4×/s · full recorded run 12–18s (§8). Counters and status text carry all state; with `prefers-reduced-motion`, inserts are instant and nothing else changes.

---

## 6. Work-log spec

**Craft SSOT for Identify/Generate/Defend verbs, auto-follow pill, first-line-as-object, and drawer-from-row:** [§13](#13-craft--micro-behaviour). This section keeps the row geometry.

**Line template** (36px row, mono 12px, columns: 88px / 72px / flex / 64px):

```
14:32:07.412   INGEST   batch-118 · 12,480 txns · 3,912 accounts            ok
14:32:08.109   SCORE    acct_4f2a · typology: APP scam · p=0.91             ok
14:32:08.940   LINK     4 accounts → ring R-118-3 · ₹18,40,000              flagged
14:32:09.201   QUEUE    R-118-3 → case #4412 · 2 corroborating sources      ok
```

**Verbs (ops, never personas):** `INGEST` (messages received) · `PARSE` (normalised) · `SCORE` (model probability + typology) · `LINK` (graph relation formed) · `FLAG` (threshold crossed) · `QUEUE` (case created) · `APPLY` (policy change) · `REPLAY` (recorded fixture event — always suffixed "· recorded").

**Click → drawer (400px, `paper-1`, 8px radius, single shadow):** ① event header (verb chip + timestamp + `source: live|replay`) ② domain summary (accounts, amounts, ring id) ③ related entities as clickable rows ④ "Raw event" disclosure — JSON in mono, collapsed by default. No tool-call theatre.

**Auto-follow rules:** pinned to bottom while user is within 40px of it; scroll up detaches instantly (no smooth-scroll fight); a detached pill appears at rail bottom — *"↓ Live · 14 new — Jump"* (sage). Re-follow on pill click or `End` key. New lines insert one-shot 160ms; no flash highlight loops (single 120ms sage background fade allowed on `FLAG` lines only).

---

## 7. Chart spec

### Recall–genuine FPR curve (Defend hero)
- **Size:** 480×280 desktop; stroke 2px. **X:** genuine FPR, log scale, 0.05%–5%, ticks at 0.1 / 0.5 / 1 / 5%. **Y:** recall 50–100%, ticks every 10%. Axes/gridlines 1px `#E2DFD6`; horizontal gridlines only.
- **Series:** model = 2px solid `ink`; rules baseline = 2px dashed `slate-600`. Legend top-right, 12px, no box.
- **Operating point:** 8px dot `sage-600` with 1.5px `paper-1` stroke; dashed hairline crosshairs to both axes; annotation 13px Plex Sans: *"Operating point — recall 92.4% @ genuine FPR 0.38%"*. Movable by dragging; y/x readout follows in a `paper-1` tooltip with 1px hairline border, `tnum` figures.
- Forbidden: gradient area fill, donut, blue, rounded tooltip, animated line-draw.
- Tooltip clamp, OP flash, KPI strip: [§13.8](#138-defend).

### Mule graph (Identify canvas)
- **Layout:** deterministic layered left→right by role — originators → mule layer(s) → aggregation → cash-out. No force simulation, no physics.
- **Nodes:** 48×28 rects, 6px radius. Originator: `paper-1` fill, 1px `ink` border. Mule: `sage-100` fill, 1px `sage-600` border, word label "mule". Aggregation/cash-out: `ink` fill, `paper-1` text.
- **Edges:** 1.5px `ink` at 70% opacity; label 11px Plex Mono, ₹ Indian grouping (`₹12,40,000`); width fixed (no weight-scaling spaghetti).
- **Time bands:** vertical 1px hairlines labelled `T+0 · T+3d · T+7d · T+14d` in `ink-3`.
- Nodes/edges appear only as one-shot inserts during scan; the graph is a static, inspectable artifact — a correspondent-banking statement, not a threat map.

---

## 8. Playback spec — RECORDED (12–18s beat sheet)

Status bar throughout: `RECORDED · captured 12 Mar, 14:32 IST` (slate, not red). Skippable via "Skip to result" (secondary, bottom-right, always visible). Deterministic timings; SSE fixture replays with compressed timestamps.

| t | Beat | UI |
|---|---|---|
| 0.0s | Operator: "Discover emerging threats" | Instant → SCANNING; status `REPLAY` |
| 0.4s | First log lines burst (3 lines) | Rail fills; counters active |
| 1.0s | Ingest counter reads 8,214/15,000 | Metrics strip climbing |
| 4.0s | First `FLAG` | Sage chip in log; button "View flagged (1)" enables |
| 7.0s | Ring R-118-3 resolves in graph | 4 nodes + edges one-shot insert; `LINK` line prints |
| 10.0s | Scan complete | Success copy; 6 cases in queue |
| 12.5s | Operator: "View flagged (6)" | Canvas compresses; case queue |
| 15.0s | Operator opens case #4412 | Drawer with corroboration rows |
| 17.0s | Hold for judge read | Static — the still does the talking |

---

## 9. 90-second script

**Superseded.** DESIGN.md §4 Identify-as-mule-scan and any Identify→Defend skip **fail MC_PS scoring**. Canonical booth path, click matrix, and tests: [IMPLEMENTATION-SPEC.md](IMPLEMENTATION-SPEC.md) §§5, 9–11.

Keep §§1–3, 6–8 (look, log, charts, playback *timing*). Do not skip Generate. Primary Identify copy is **Discover emerging threats**, not Begin scan. ⌘K remains an operator tool (recorded packs, source status), never the demo.

---

## 10. Open questions (only these; everything else is locked)

1. **Real eval numbers.** All metrics above (92.4% / 0.38% / ₹ outcomes) are fixture placeholders — ML must supply held-out + transfer numbers before print assets. Design is not blocked; copy slots are sized for "92.4%"-length strings.
2. **Product wordmark.** Header ships with a wordmark slot + batch breadcrumb; naming was not in scope and no name is invented here. **AegisLoop** is the product name already locked in this repo.

No other decisions are blocked. Palette passes contrast as specced; no fourth nav item; Identify is never search-first; no Copilot page exists. **First still is form A** (§14): Identify REST is the landing.

---

## 11. Sources

**Product surfaces (public):** stripe.com/radar · docs.stripe.com/api/events · docs.stripe.com/development/dashboard/events · docs.stripe.com/radar/reviews · docs.stripe.com/testing · feedzai.com/blog/riskops-studio-risk-operations-platform · feedzai.com/blog/feedzai-iq-score-ai-fraud-detection (IQ Score 0–1000 + threshold-as-sentence; copilot **never steal**) · mastercard.com/news/media — *Building digital trust…* May 2025 PDF (Decision Intelligence, Scam Protect, ScamClassifier typologies, RC56 — **vocabulary only**) · ramp.com · brex.com · mercury.com · wise.com · sift.com · forter.com · unit21.ai · complyadvantage.com · recordedfuture.com/blog/intel-cards-overview · mandiant.com (**[NV]** — behind-login) · linear.app · linear.app/docs/audit-log · bloomberg.com/professional · bloomberg.com/ux/2021/10/14/designing-the-terminal-for-color-accessibility · bloomberg.com/company/stories/how-bloomberg-terminal-ux-designers-conceal-complexity (**[NV]** internals) · datadoghq.com/blog/datadog-quick-nav-menu · grafana.com/docs/grafana/latest/dashboards/shortcuts.

**Standards / docs:** attack.mitre.org · github.com/mitre-attack/attack-navigator `layers/spec` (`layout: side`, `showID`) · developer.mozilla.org SSE · docs.datadoghq.com/logs/explorer/live_tail · docs.datadoghq.com/tracing/trace_explorer (Pause/Play; selecting a span pauses the stream) · w3.org/TR/WCAG22 (1.4.1; 2.3.3) · w3.org/WAI/WCAG21/Techniques/css/C39 (`prefers-reduced-motion`) · apcacontrast.com · ibm.com/plex · developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric (`tnum`, `slashed-zero`) · developer.mozilla.org Intl.NumberFormat `en-IN` · recharts.org Tooltip (`allowEscapeViewBox` default false; `isAnimationActive={false}`; clamp at log-FPR) · LSEG `RT_ITEM_DELAYED` / `SUSPECT` (community.developers.lseg.com).

**Domain / India / fraud charts:** npci.org.in/product/upi/product-statistics (monthly volume Mn / value Cr — **aggregates**) · SWIFT camt.053 statement / entry / entry-detail layering · rbihub.in — RBIH MuleHunter.AI · psr.org.uk — APP reimbursement · fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_4_PerformanceMetrics/ThresholdFree.html (ROC vs PR; low-FPR region) · sklearn DET curve (operating-point readability — we keep recall vs **log genuine FPR**, not a DET relabel) · arxiv.org/abs/2404.13234 — SAML-D.

All Stripe Dashboard, Bloomberg, Feedzai, and Mandiant in-app behaviors cited are from public marketing/documentation imagery — marked **[NV]** where the exact screen layout could not be independently confirmed.

---

## Mapping to AegisLoop (do not let art direction replace the problem statement)

This lock is **visual and interaction doctrine**. The Mastercard brief is still Identify (emerging GenAI fraud landscape + discovery) → Generate (simulate those attacks) → Defend (detect at a genuine-FPR cap, then retrain from misses).

When this file and the product conflict, keep the **look** from §§1–3, 6–8 and map the **jobs** as follows:

| Lock section | Use as | Do not use as |
|---|---|---|
| §1 tokens, type, density, motion, honesty | Law for all three phases | — |
| §4 Identify mule-graph composition | Generate’s mule graph + Identify work-log rail pattern | The whole Identify product (that would drop T01–T24 diversity) |
| §4 Generate ledger + seed | Generate phase (demo-scale corpus / payment tape) | A second product story |
| §4 Defend curve + operating point + ₹ strip | Defend hero chart and policy chips | Replacing closed-loop retrain; keep “Retrain from missed fraud” as the novelty beat |
| §5 stage machine | Identify rest / scanning / review | “Begin scan” copy if the primary remains **Discover emerging threats** |
| §6 verbs | Identify: `COLLECT` `EXTRACT` `RANK` `GROUND` `PROPOSE` `REPLAY`. Generate: `COMMIT` `INJECT` `FIDELITY`. Defend: `FIT` `SCORE` `APPLY` `RETRAIN` | `INGEST`/`SCORE` on Identify as if we were scoring a live issuer feed |
| **§13 Craft / micro-behaviour** | Visual SSOT for chips, palette, log, drawer, landscape, ledger, fidelity sentence, Defend OP/KPI/tooltip, motion, type loading | A second product; reopening 90s composition |
| §7 mule graph | Generate canvas (layered, no force layout) | Identify’s primary hero — Identify’s rest hero stays the 24-technique landscape |
| §8–9 timings / ⌘K / Skip to result | Booth playback and script structure | Script that skips Generate; the 90s path must still hit all three pillars |
| Wordmark | **AegisLoop** | Inventing a new name |
| **§14 First still / landing** | Identify REST *is* the cover (form A). `/` = catalog landscape | A 4th marketing route; a dissolve title card; hero/testimonials/Get started |

Eval numbers in this lock are placeholders. Wire real holdout metrics from the Defend run (or `FROZEN` photography artifacts) before any judge-facing claim.

---

## 12. MCP catalogs (phase 1 research — do not become the look)

**Phase 1 of the frontend plan is this file.** Phase 2 implements the UI against it. 21st.dev and React Bits are **research and structure sources**, not a second design system. **`get_component` is reserved — do not call.** Never `generate`. `get_inspiration` with paper/sage/ink context still ranked 8-bit Command / Omni / Bash Tool (≤53%) — **ignore it**.

Invoke in Cursor: `/21stdev` · `/reactbits`. Skills: `~/.cursor/skills/21stdev`, `~/.cursor/skills/reactbits`. MCP: `21st` at `https://21st.dev/api/mcp`; **shadcn** in project `.cursor/mcp.json` as `npx -y shadcn@latest mcp --cwd frontend` so it reads [components.json](components.json) (`@react-bits`). React Bits’ site defaults to `--client claude`; this repo is Cursor — do not run that. Enable **shadcn** in Cursor Settings → MCP. Browse/search via that MCP (or `npx shadcn@latest list @react-bits --cwd frontend`); install **allow-list only**; never Dither or any shader Background on the booth. Wiring is on disk; this session still cannot see shadcn tools until you enable it. Default remains: do not install Bits except the allow list.

### 21st.dev — steal structure only (ids from 30 Aug 2026 search)

Restyle every steal to paper/sage/ink, radii 6/4/8, IBM Plex, hairlines, zero loops. Never paste catalog CSS variables.

| Job | Steal (id) | Restyle / never |
|---|---|---|
| Work log | Audit Log **25163** (timestamp · type · status · row → detail) | Not Interactive Logs **10635** (animated filters). Not Data Stream **18429** (terminal SOC). CI log **24897** = collapsible *pattern* only, no CI skin. Not AI Agent Pipeline **20802**. |
| ⌘K | shadcn Command **714** (unstyled). Fallback originui Command **382** | Overlay 480px, groups (Recorded / Live / Navigate / Copy). Not hover-pill **23173**, not 8-bit **13175**, not Omni recents **5530**, not Efferd Search Modal **8115**, not full-screen **3931**. |
| Ledger / review | originui dense Table **89** or shadcn Data Table **1050**. Dense grid **4783** OK as density | Not retroui **25153**, not Financial Markets Table **9045** (flags, sparklines, Framer), not Market Watchlist **20110**, not Sortable Table **23561** (row dance), not striped zebra as brand. |
| Drawer | Keep existing Drawer; Sheet **25002** / scrollable Sheet **25010** for header+body+footer slots | 400px right, 8px, one shadow, focus trap, Esc. Not 8-bit Drawer **13174**, not Vaul shopping **4485**, not bottom-sheet grids **24848**. |
| Status | Keep StatusChip: glyph + word + color | Not HeroUI Chip **13844**, not pulsing Status **25395**, not Globe Live **11609**, not Animated Status **2498**. |
| Stepper | originui Stepper **769** (progress, not a wizard) | Hairline labels Identify → Generate → Defend. Not Wizard Steps **23576**, not onboarding **19143** / **25064**, not Framer accordion **8864**. |
| Error | Banner **356** or Project Banner **3905** (one sentence + action) | Slate degraded / rust fail. Never JSON. Not toast-as-error. Not Error Alert icon soup **23621** as the look. |
| Tooltip | originui Tooltip **213** (chart tooltip *structure*) | `paper-1` + 1px hairline, `tnum`, clamp. `allowEscapeViewBox={false}`. `isAnimationActive={false}`. Not rounded indigo. |
| KPI | **Do not steal KPI Card 6537 / Ruixen 5120 / 8-bit Stats 13218 / six-up skeletons 18999** | Four **unequal** strip cells; one 56px hero. Hairline separators, not cards. |
| Empty | **Do not steal** dashed-card Empty **19369**, marquee **19377**, 8bit Empty **13892** | Same geometry as success; objects unfilled. Copy is the empty state. |
| Theme | Green Soft `b86967bd-…` read-only: steal **CSS variable names** (background/card/border) | Never steal `#2ee92b`, Outfit, Geist Mono, `radius: 1rem`, `.dark`, chart-2 `#9c87f5`. Never Matrix Green. Tokens stay §1. |
| Logo | search_logo “IBM” → svgl IBM mark | **Never** the IBM logo. Wordmark is **AegisLoop**. |

### React Bits — almost all forbidden

MCP **not connected**. Allowed later only as one-shot, tokenized, `prefers-reduced-motion` safe: FadeContent / AnimatedContent (80–160ms, not scroll-reveal); CountUp (reduced-motion = final number). Banned: Dither and all shader Backgrounds, ClickSpark, ElectricBorder, Glitch/Gradient/Particle/ASCII/Decrypted text, BlobCursor, Cubes, shiny/marquee.

### Implementation rule

If MCP output introduces Inter, `#6366F1`, `rounded-2xl`, `shadow-lg`, glass, or a motion loop, it is rejected. Rebuild with [tokens](src/styles/tokens.css) remapped to this lock’s hex.

---

## 13. Craft / micro-behaviour (visual SSOT)

Composition is locked in [IMPLEMENTATION-SPEC.md](IMPLEMENTATION-SPEC.md) (90s path, 62/38, 72/28, 56px hero KPI, Train off the critical path). This section is **how it feels**: issuer / clearing / risk desk, 2026, on paper/sage/ink. Bloomberg conceals complexity; Stripe Radar puts outcomes on the row; Feedzai IQ states the threshold as a sentence; NPCI publishes **monthly aggregates**, not a ticker.

**Thesis:** The booth is a **working ledger**. Canvas `#F7F5F0`, objects `#FFFFFF`, type IBM Plex (Serif 500 titles only), color only for policy/feed status, motion only to confirm an object arriving. Cutting-edge finance is density, honesty, and materials — not a new palette, not Mastercard blue, not “AI-powered.”

### 13.1 Motion table (law)

| Event | Default | `prefers-reduced-motion: reduce` |
|---|---|---|
| Color / chip fill / hover | 80–120ms | Instant |
| Row / node / edge / source-row insert | 160ms one-shot (`opacity` 0→1 + `translateY(4px)`→0) | Instant insert — **object still appears** |
| Drawer / palette / popover | 160ms translate or opacity | Instant open/close |
| Sage flash (`FLAG`, retrain OP, Continue) | 120ms background fade, once | Skip flash; text/chip already carry state |
| Log auto-follow | Instant snap to bottom (no smooth-scroll fight) | Same |
| Recorded Identify **wall clock** | 12–18s paced SSE | **Same 12–18s** — time is the demo, not the tween |
| Loops (pulse, shimmer, line-draw, bounce, marquee) | None | None |

WCAG 2.3.3 / C39: wrap tweens in `@media (prefers-reduced-motion: no-preference)`. Trading-floor laptops often have Reduce Motion on; the booth still **works** — counters and status text carry state.

### 13.2 Type loading (Serif is missing today)

Tailwind today: Sans + Mono only. **Add Serif.**

| Face | Weights | Use | Load |
|---|---|---|---|
| IBM Plex Serif | **500 only** | Phase titles 24–32px | `preload` woff2 latin; `font-display: swap`; metric-matched fallback (`size-adjust` on Georgia/Times) so 24px titles do not CLS |
| IBM Plex Sans | 400 / 500 / 600 | All UI 13–14px | preload 400+500 |
| IBM Plex Mono | 400 (500 optional) | Numbers, IDs, logs, chips, seed | preload 400 |

Every metric, amount, timestamp, ID, KPI: `font-variant-numeric: tabular-nums slashed-zero` (OpenType `tnum` + `zero`). Amounts: `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })` → `₹4,20,00,000`. Never `en-US` + `INR` (that yields `₹4,200,000`). Percents: 1 decimal, `en-IN` grouping if ≥1000. Timestamps IST `HH:mm:ss.SSS` Mono 12px.

### 13.3 Materials

- Surfaces: canvas `paper-0`, objects `paper-1`, separators 1px `hairline` `#E2DFD6`. **No drop shadows** except overlay (`0 8px 24px rgba(25,28,25,0.12)` on drawer / palette / modal).
- Radii: 6px controls, 4px chips, 8px drawer/palette/modal.
- 1920×1080 full bleed, 24px gutters, **no `max-w-[1280px]`**. Chrome (sidebar 220 + status 32 + stepper 36 + page header 48) ≤ 15% ≈ 162px of 1080.
- Empty / running / success / fail / degraded: **same geometry**. Only objects fill. Never swap in a centered `·` dashed card ([EmptyState.tsx](src/components/ui/EmptyState.tsx) today — kill).

### 13.4 Chrome

#### LIVE / RECORDED / RULES / FROZEN chip

**Lab risk:** pulsing green dot; chip width jumps LIVE (4) → RECORDED (8) and shoves run/seed.

**Finance treatment:** Stripe TEST-badge honesty + LSEG `RT_ITEM_DELAYED` / `SUSPECT`: the word is the status; delayed is not a crash. Bloomberg: color is semantic, never the only signal.

Anatomy (height 20px, radius 4px, 1px hairline, Plex Mono 11px uppercase):

```
┌── 20px ──────────────────────────────────────────────┐
│ [6px glyph]  [8ch MODE]  ·  [suffix, ink-3, 11px]   │
└──────────────────────────────────────────────────────┘
```

| Mode | Glyph | Color | Suffix example |
|---|---|---|---|
| `LIVE` | filled 6px sage disc (static — **no pulse**) | sage-600 | `search + LLM` |
| `RECORDED` | 6px slate ring (hollow) | slate-600 | `captured 12 Mar, 14:32 IST` |
| `RULES` | 6px ochre disc | ochre-700 | `policy table` |
| `FROZEN` | 6px slate disc | slate-600 | `locked holdout` |
| `DEGRADED` | 6px slate disc | slate-600 | `SSE dropped · recorded available` |

**Fixed slot:** MODE sits in `min-width: 8ch` (covers `RECORDED` / `DEGRADED`). The chip’s outer width is reserved for the longest mode+suffix pair used in chrome; if suffix length differs, truncate suffix with ellipsis — **do not let the chip grow**. 80–120ms fill/border color only. Never red for RECORDED/FROZEN.

**Forbidden:** pulse; layout jump; `LIVE` in rust; “DEMO MODE” pill.

#### Source popover

Click the chip (or a `Source` control beside it). Popover 280px, `paper-1`, 8px, hairline, one shadow, z-50.

```
Mode          RECORDED
Tavily        configured     (yes/no word — never a key)
LLM           configured
Last reason   Using recorded FinCEN / RBI corpus
```

Yes/no as sage/slate words. **Never** API keys, `tvly-`, model names, or `Bearer`. Esc + click-outside close.

#### Phase stepper Identify → Generate → Defend

originui Stepper **769** structure: three labels, hairline connectors, current = ink 600, done = sage word, blocked = ink-3. Height 36px. **Not a tour.**

Disabled reasons (title tooltip, one sentence):

| Step | Blocked when | Copy |
|---|---|---|
| Defend | Generate fidelity **unknown** | `Fidelity not yet known for this corpus.` |
| Identify / Generate | — | Click = route; Continue gates are separate |

No checkmark burst, no percent bar, no “Step 2 of 3”. Click = route only (same as nav).

#### Sidebar

220px, `paper-1`, 1px hairline right, **no box-shadow** (today’s Sidebar has one — remove). Wordmark `AegisLoop` — Plex Sans 600 14px, not `AEGISLOOP` mono shout. Three items only: Identify / Generate / Defend. Active: 3px sage bar on the left edge + ink text; inactive ink-2. **No icons.** No Copilot, no Arms Race, no Threat Map as a fourth.

#### ⌘K palette (ops, not Spotlight)

Datadog quick nav + Grafana Ctrl+K + Linear shortcuts-on-the-right. Overlay **480px** wide, max-height 60vh, 8px, hairline, one shadow, z-60. Input 36px, Plex Sans 13px, placeholder `Command`. Groups as 11px uppercase ink-3 headers. Each row 36px: label left, `kbd` Mono 11px right. Hover: `paper-0` fill, 80ms. Focus trap. Esc / click-scrim closes. Empty query shows **all groups**; no “Recent” theatre.

| Group | Commands |
|---|---|
| Recorded | Play recorded Identify (12–18s) · Load locked holdout · Play recorded retrain · Skip to result *(enabled only during recorded Identify)* |
| Live | Return to live search *(disabled unless `/identify/config` says live search + LLM)* |
| Navigate | Identify · Generate · Defend |
| Copy | Copy seed · Copy operating point |

**Forbidden:** Omni recents, 8-bit, hover-pill grow, full-screen Spotlight, searching the threat catalog (Identify is not search-first).

#### Skip to result

Secondary, bottom-right of the **working surface** (not only in the palette), always visible during recorded Identify. Label `Skip to result`. Instant jump to REVIEW/success still; chip stays `RECORDED`. Hidden or disabled on live. Never “Skip demo”.

#### Error banner

One sentence, 40px, full width of the working surface, slate (degraded) or rust (hard fail). Optional `Retry` / `Use recorded (⌘K)` as text buttons. Parse API body to English. **Never JSON**, never `check API logs`, never stack traces. Geometry: replaces the status-strip *content* or sits under the header — does not add a new chrome row that breaks the 15% budget.

### 13.5 Identify

#### REST landscape cells (T01–T24)

ATT&CK Navigator `layout: "side"`, `showID: true`, `showName: true`, **no heat**. Five category columns; IDs `T01`–`T24` Mono 11px `ink-3` always visible; name Sans 13px ink. Readable at 2 m — do not lock 112px cells; grow to fill the working surface.

| State | Fill | Border | Copy |
|---|---|---|---|
| Named | `paper-1` | 1px hairline | ID + name |
| Gap | `paper-0` | 1px dashed hairline | ID + `Coverage gap` |
| Hover | — | 1px ink | No lift, no scale |
| Focus | — | 2px sage-600 offset | Keyboard |
| Name-only (catalog, not generated) | `paper-1` | hairline | name; no “Generate” CTA on the cell |
| `?highlight=Txx` | `sage-100` | 1px sage-600 | **Do not reorder** under the cursor; scroll cell into view if needed |

Click → drawer. Gap cell primary in drawer: `Discover this coverage gap` (pre-fills optional topic). Double-click does nothing (Discover owns the mutex).

#### Discover

Header primary, rest: **Discover emerging threats**. Disabled + `aria-busy` while `SCANNING`; double-click ignored (abort controller). Empty topic is the booth click. Optional `Narrow the scan` collapsed — not the default.

#### SCANNING

Landscape compresses to a **72px strip** (IDs remain). Below: sources **62%** | ops log **38%**. Metrics 40px bottom (ingested / proposed / sources). A reader column is **optional** — if present, excerpt **replaces** in place (one-shot 160ms), never a third competing hero.

- **Source row insert:** 36px, URL + title, 160ms. Oldest stay; list caps, does not shuffle.
- **Log auto-follow:** pinned while scroll position is within 40px of bottom. Scroll up **detaches instantly**. Detached pill, rail bottom, sage: `↓ Live · 14 new` (count in Mono `tnum`). Click pill or `End` re-follows. **Approve / Add must not steal log focus** and must not re-attach.
- Datadog: selecting a line pauses follow (drawer open = detached).

#### Verb chips

Plex Mono 11px, 4px radius, 1px hairline, 72px column. Identify: `COLLECT` `EXTRACT` `RANK` `GROUND` `PROPOSE` `REPLAY`. Generate: `COMMIT` `INJECT` `FIDELITY`. Defend: `FIT` `SCORE` `APPLY` `RETRAIN`. `REPLAY` always suffixes `· recorded`. Never personas, never `INGEST` on Identify, never “Agent thinking…”.

#### First log ≤800ms as **craft**

The first object is a **real row** (`14:32:07.412  COLLECT  started · FinCEN / RBI / OSINT  ok`), not a spinner. If the network is slow, emit `COLLECT started` from the client/SSE first yield before scout returns. Reduced-motion: the row still appears by 800ms; it does not fade.

#### REVIEW cards

Recorded Future card anatomy: heading (id + name) → evidence list → **one disposition**. Not a 0–99 gauge.

- Add to catalog (primary, ink button)
- Dismiss (secondary)
- Mark unsafe (slate; tooltip: `Not safe to simulate`)

Continue banner 40px: `Continue to Generate` enabled at `approved ≥ 1`; else `Continue with catalog seed` as the honest offer — never a blocked dead-end without copy.

### 13.6 Drawer (cell / log / OP)

Keep [Drawer.tsx](src/components/ui/Drawer.tsx); restyle.

| Token | Value |
|---|---|
| Width | 400px from the right; header stays clickable |
| Radius | 8px (left corners only if full-height) |
| Shadow | `0 8px 24px rgba(25,28,25,0.12)` only |
| z | overlay 40 · drawer 50 · palette 60 · modal 70 |
| Motion | 160ms translateX; reduced-motion = instant |
| Focus | trap while open; Esc closes; return focus to the opener |
| Title | Plex Sans 500 14px, not mono shout |

Body: ① header (verb chip or technique ID + timestamp + `source: live\|replay`) ② domain summary ③ related entities as 36px clickable rows ④ “Raw event” disclosure, JSON Mono, **collapsed**. Log drawer: artifacts (URLs), not thoughts. OP drawer: protocol words only (`allow` / `notify` / `step-up` / `hold` / `decline` / `mule-credit-restrict`) + recall @ genuine FPR — Mastercard DI **vocabulary**, not their blue.

### 13.7 Generate

#### Seed stamp

48×48px object, Mono 13px, `paper-1`, 1px hairline, 6px radius. Content: seed digits, `tnum slashed-zero`. Click copies; 120ms sage flash; tooltip `Copied · reproducible`. This is the audit object — not a badge in the header chrome.

#### Eligible strip

40px, chips = **families** (`APP scam`, `ATO`, `mule layering`, `first-party`), not `vector_id`. 4px chips, glyph+word. Caption if no approvals: `Catalog seed · RECORDED`.

#### Ledger

originui **89** density: 36px rows, one `<table>` or shared grid template, hairlines, amounts right-aligned `en-IN`. Last-**40** DOM rows (cap). Auto-follow same 40px / detach / `↓ Live · n new` as Identify. Columns: time · family · payer/beneficiary (truncated) · ₹ · status word.

#### Mule graph

camt.053 layering, not SOC: L→R originators → mule → aggregation → cash-out. Nodes 48×28, 6px, one-shot edges 1.5px ink 70%. ₹ labels Mono 11px `en-IN`. No force layout, no pulse, no weight-scaled spaghetti. §7 remains the node/edge spec.

#### Fidelity strip = a sentence

40px, not a chip wall. Pass: sage. Fail: rust. Always include PSI (or the named fidelity stat) and honesty.

- Pass: `Fidelity pass — PSI 0.12 · demo scale 200×40×14d · not full population.`
- Fail: `Fidelity fail — PSI 0.41 · continue anyway (known).`

**Continue to Defend** enables when fidelity is **known** (pass **or** fail). Primary button label **Simulate payment traffic** is unchanged while running (disabled + secondary Stop). Never “Generating…” as the primary label.

### 13.8 Defend

#### Empty / scoring (live path)

**Same axes** as success: log genuine FPR 0.05–5%, recall 50–100%, 1px hairlines, horizontal grid only. Counters in the hero slot: `Scoring this run… 31,200 of 50,000` Mono `tnum`. **No Train-labeled primary.** No 6 KPI cards.

#### Frozen / recorded pack

Paints the curve **immediately** (no line-draw). Chip `FROZEN` or `RECORDED`. Caption under chart: `Locked holdout — not this session` or `Recorded score`. This **is** the 90s Defend beat.

#### Curve + OP

§7 strokes. Series: 2px ink (model); optional 2px dashed slate (rules) **only if the payload includes it** — never fabricate 0.84×. OP: 8px sage dot, 1.5px paper stroke, dashed hairlines to axes. Chart annotation 13px Sans: `Operating point — recall 92.4% @ genuine FPR 0.38%`. The **hero KPI** (strip) is **56px** Mono recall; the OP callout on the plot may use 48px for the recall figure if the strip is already 56px — do not ship two competing heroes. Log FPR axis; ticks 0.1 / 0.5 / 1 / 5%.

**Tooltip:** `paper-1`, 1px hairline, 6px, 12px Mono `tnum`, `isAnimationActive={false}`, `allowEscapeViewBox={{ x:false, y:false }}`. At 0.05–0.1% FPR **clamp** inside the plot (IMPLEMENTATION-SPEC §8). Reduced-motion: no tooltip tween.

**Forbidden:** indigo, gradient fill, donut, rounded tooltip, animated draw, 0.84 baseline.

#### KPI strip (4 unequal cells)

Hairline-separated strip, not cards. One hero + three supporting:

| Cell | Width | Type |
|---|---|---|
| 1 | ~40% | 56px recall @ genuine FPR (the number + one line `recall @ genuine FPR 0.38%`) |
| 2 | ~20% | Precision or held-out caveat (13px) |
| 3 | ~20% | Miss family (word, not `vector_id`) |
| 4 | ~20% | ₹ modelled prevented / genuine held `en-IN` or `—` if unknown |

#### Interventions rail

Allow-heavy histogram (honest: most mass on Allow). APP / mule = **one-liners**, not extra charts. Policy colors only, glyph+word. Glass title: **Interventions** — never “Brake”.

#### Retrain

Second series, **same axes**, 2px sage-600. 160ms sage flash on the OP dot once. 56px verdict inset: `Defense updated — miss family → next attack`. Then Identify `?highlight=Txx`. Frozen pack may use a one-line overlay instead of waiting on loop-m. Header primary after score exists: **Retrain from missed fraud**. **Recompute on this run** is secondary.

OP drawer: protocol words (13.6). No drag-OP as the booth story.

### 13.9 Forbidden copy (grep list)

Ship a test that greps user-visible strings in `frontend/src/**/*.{ts,tsx}` (allow comments and API type fields). Pattern SSOT: IMPLEMENTATION-SPEC **§6.1**.

`HITL` · `Loop M` · `vector_id` · `inner_val` · `Scout` · `Curator` · `Librarian` · `LangGraph` · `Seed Atlas` · `Researching` · `Coming soon` · `Planned` · `Decisioning` · `Arms Race` · `Simulation Console` · `AI-powered` · `AI powered` · `check API logs` · `is the API running?` · `generate → defend pipeline` · `Agent thinking` · `the agent is` · `catalog_solved` · `Champion recall` · `G-TEST` · `Analyst Copilot` · `99.9%` · `accuracy` as a vanity claim · `Train and score` as visible primary · `Begin scan` as Identify primary · `issuer feed` · `live UPI` · `Copilot` · `chargeback` as a headline · `innerVal` · `model_run_id` in UI strings · `kill shot` · `vibe`

Plus visual grep: `rounded-2xl` · `#2563EB` · `#6366F1` · `Inter` · `Geist` · `Space Grotesk`.

### 13.10 Micro-behaviour cheat sheet

| Behaviour | Finance treatment | Never |
|---|---|---|
| Mode chip | Fixed 8ch MODE; glyph+word; 80–120ms color | Pulse; width jump; red for recorded |
| Source popover | tavily/llm yes-no | Keys |
| Stepper | Disabled *reason* | Tour / % bar |
| Sidebar | 3 words + wordmark | Icon soup; 4th nav |
| ⌘K | Grouped ops commands, 480px | Spotlight / 8-bit / recents |
| Skip | Recorded only, secondary | Skip the pillar |
| Error | One sentence | JSON |
| Landscape | Side layout, IDs on, highlight in place | Heat; reorder under cursor |
| First still | Identify REST is `/`; **24** 48px mono; Discover primary | Marketing `/`; dissolve cover; CountUp on 24 |
| Discover | Disabled while SCANNING | Double-run |
| SCANNING | Source insert + log follow/detach | Focus steal on Add to catalog |
| Verbs | COLLECT… / COMMIT… / FIT… | Personas |
| First log | Row object ≤800ms | Spinner |
| REVIEW | Evidence → disposition | Score gauge |
| Drawer | 400px, Esc, trap, z-50 | Vaul shopping sheet |
| Seed | 48px object, copy on click | Header badge |
| Eligible | Family chips | `vector_id` |
| Ledger | 36px, `en-IN`, last-40, follow | Sparklines / flags |
| Mule graph | L→R correspondent, one-shot | SOC physics |
| Fidelity | Sentence + Continue on known | Vanity chip-only |
| Simulate label | Unchanged while running | “Generating…” |
| Defend empty | Axes + counters | Train hero |
| Frozen | Immediate paint | Line-draw |
| OP / KPI | 56px strip hero; log FPR; 2px ink | 0.84; indigo; 6 cards |
| Interventions | Allow-heavy honest histogram | Extra donuts |
| Retrain | 2nd series + 160ms sage flash + 56px inset | Epoch spinner |
| Tooltip | Clamp; no tween | Escape viewport |
| Type | Preload Serif 500; `tnum slashed-zero` | Inter; FOIT titles |
| Motion | 80–120 / 160; recorded time still 12–18s | Loops |
| Empty states | Same geometry | Centered `·` |
| Viewport | 1920×1080 full bleed | `max-w-1280` |

---

## 14. First still / landing

**Form A — the landscape is the landing.** Locked for GFF 2026 (Mumbai booth, 1920×1080, standing judges, ~90s). `/` is Identify REST. No fourth route. No dissolve cover.

### What it is

The first paint a judge sees is the **T01–T24 census already on glass**: five category columns, IDs + names readable at 2 m, AegisLoop wordmark, LIVE|RECORDED chip in a reserved slot, one census numeral (**24** at 48px Plex Mono), one primary (**Discover emerging threats**). The cover *is* the scored diversity still. Operator talks for ~12s, then clicks Discover. Same visual system as Identify SCANNING / REVIEW — paper `#F7F5F0`, sage `#3E6B4F`, ink `#191C19`, IBM Plex, chrome ≤15%.

### What it is not

Not a product site. Not a 3–8s title card that “dissolves into” Identify. Not hero + testimonials + Get started. Not Copilot, pricing, three feature cards, chatbot, mesh gradient, or “AI-powered fraud OS.” Not a second look that Identify then has to catch up to.

**Why not B.** A one-shot cover still burns 3–8s of a standing judge before T01–T24 — the thing they score for diversity. Bloomberg and Radar do not fade from a wordmark into the desk. Skip is for **recorded Discover playback**, not for skipping a marketing intro.

**Why not C.** A real `/` marketing landing would steal the 90s path, add a fourth destination, and import the exact slop this lock forbids. Judges do not need a brochure; they need the closed loop. C is not chosen.

### Show / hide (first still)

| Object | Placement |
|---|---|
| AegisLoop wordmark | **On cover** — sidebar lockup, Plex Sans 600 15px ink (Serif stays phase titles only) |
| LIVE vs RECORDED honesty | **On cover** — status strip reserved slot; glyph + word; geometry does not jump when the word changes; **no pulse-dot** |
| 24 techniques / 5 categories | **On cover** — **24** at 48px mono (`tnum` + slashed-zero); **5** as supporting 13px; five column headers on the landscape |
| Mastercard challenge context without issuer-feed claim | **On cover** — one `ink-3` caption: *Allowlisted OSINT + seed catalog — not an issuer feed* |
| That the next beat is Discover | **On cover** — header primary already labelled **Discover emerging threats** |
| Landscape cell click → drawer | **After click** (REST stays still until then) |
| Discover stream (sources + ops log) | **After click** — REST→SCANNING; landscape strip 72px; sources 62% \| log 38% |
| Add to catalog / analyst review cards | **After click** (REVIEW) |
| Continue to Generate | **After click** (banner when approved ≥1 or catalog seed) |
| HITL queue dump, topic search box | **Never** on cover · **proof-only** if at all |
| Fit hyperparameters, Train button, Pareto empty axes | **Never** on cover · Defend / **proof-only** |
| 2400 population | **Never** on cover · Generate **proof-only** |
| Copilot, API keys, `vector_id`, Scout/Curator, Loop M, inner_val | **Never** |
| “Connected to live UPI”, accuracy donut, ₹ fraud-prevented theatre | **Never** |
| Team bios, GitHub, 6 KPI cards | **Never** |

### Composition (t=0, 1920×1080)

```
Sidebar 220px          Status 32px   LIVE|RECORDED|RULES|FROZEN  · run · seed
AegisLoop              Stepper 36px  Identify → Generate → Defend
Identify               Header 48px   Plex Serif 24 “Identify”  |  24  (48px mono) · 5 categories
Generate                             primary: Discover emerging threats
Defend                 Working 100%  five columns · T01–T24 · ID + name (ATT&CK side)
                       Caption       allowlisted OSINT + catalog — not an issuer feed
```

Landscape: MITRE ATT&CK Navigator principles — `layout: side`, `showID: true`, `showName: true`. Cells are hairline objects on paper, not 112px heat tiles, not bento, not a 2×3 / 4-col card wrap. Five structural categories (Network / Identity / APP / Model / Document) as **columns**, techniques as rows. Coverage is a word+color chip inside the cell, never a heat score.

Census **24** is a **known constant**, not a climbing counter. Paint it immediately. If the catalog GET is still in flight, cells fill as objects appear; empty cells are `—` in mono — **not** a pulse skeleton.

### Motion (0–12s) and Skip

| t | Beat | Motion |
|---|---|---|
| 0.0s | First paint = Identify REST | Instant. No fade-up, no page reveal, no CountUp on 24, no dissolve from a cover |
| 0–12s | Operator talks census, chip, OSINT caption, Discover as next beat | Zero loops. Hover on Discover: 80–120ms sage. Cell hover: hairline only |
| 12s+ | Operator clicks **Discover emerging threats** | Instant REST→SCANNING (IMPLEMENTATION-SPEC geometry). First log ≤800ms |
| Skip | **Does not exist on REST** | Skip is recorded Discover playback only (12–18s fixture). Never “Skip intro” |

`prefers-reduced-motion`: identical state; nothing else was animating.

### Components — steal structure / never install

**Native (this still):** StatusChip (glyph + word, reserved slot) · census numeral 48px mono · five-column landscape · existing 220px sidebar wordmark. Rebuild; do not paste catalog CSS.

**21st.dev** (`search` only, 30 Aug 2026 — **`get_component` not called**):

| Job | Steal (structure) | Never |
|---|---|---|
| ⌘K (chrome, not the still) | shadcn Command `714` / originui `382` — grouped ops, shortcuts right, Esc | Raycast Omni recents `5530`; hover-pill Command Menu `23173`; 8-bit skins |
| Status strip | Keep StatusChip; Tremor-style *word* badge `521` as a *pattern* (restyle) | Pulse Status `25396`; Status Dot `24882`; Hud Status `2549`; Globe Live Badge `11609`; HeroUI chips `13844`; Animated Status `2498` |
| Wordmark / chrome | Existing sidebar lockup; light sidebar *density* `19361` as a *pattern* | Logo clouds / marquees `21467` `21465` `23537` `18224` (“trusted by”); floating glass Header `8137`; notch nav `25735`; marketing Header Navbar `18258`; dark dual-theme Dashboard Sidebar `14941` |
| Landscape | ATT&CK side matrix (public Navigator spec — not a 21st kit) | Cybernetic bento `6014`; Constellation Grid `23960`; Grid Background `7599`; Integrations / Achievement grids; originui Table `95` as the census (table is Generate) |

**React Bits:** shadcn MCP **not connected**. Default: **no Bits on the first still.** CountUp on “24” is rejected (constant, not a live climb — that would be theatre). FadeContent is for later one-shot inserts (log lines, SCANNING sources), not for revealing the landing. Never Dither / glitch / shader Backgrounds.

Handoff into Identify SCANNING is a **geometry change of this screen**, not a route and not a new visual system. Generate ledger and Defend curve inherit the same tokens; they do not inherit this census composition.
