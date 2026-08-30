# Component registry (UI overhaul brainstorm)

Living inventory of integrated, planned, and reference components for AegisLoop. **Not all entries belong on the booth path** — see `DESIGN.md` §13 and `BOOTH-PLAN.md` before shipping anything to glass.

---

## Project setup (verified)

| Requirement | Status | Location / notes |
|-------------|--------|------------------|
| **shadcn** | ✅ Configured | `components.json` — style `new-york`, aliases `@/components/ui` |
| **Tailwind CSS** | ✅ | `tailwind.config.ts`, `src/styles/globals.css`, `src/styles/tokens.css` |
| **TypeScript** | ✅ | Vite + `tsconfig.app.json`, path alias `@/*` → `src/*` |
| **Default UI path** | `@/components/ui` | Maps to `frontend/src/components/ui/` (shadcn convention) |
| **React Bits Pro registries** | ✅ Configured | `@reactbits-starter`, `@reactbits-pro` in `components.json` — needs `REACTBITS_LICENSE_KEY` in `frontend/.env.local` |

### If you were starting from scratch

```bash
cd frontend
npx shadcn@latest init   # sets components.json, Tailwind, aliases
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Why `/components/ui` matters:** shadcn CLI, docs, and community examples assume `@/components/ui`. Keeping primitives there lets you `npx shadcn add button` without retargeting paths and keeps imports consistent (`@/components/ui/button`).

---

### Dashboard sidebar (`dashboard-sidebar.tsx`)

| Field | Value |
|-------|-------|
| **Path** | `src/components/ui/dashboard-sidebar.tsx` |
| **Demo** | `src/components/ui/dashboard-sidebar.demo.tsx` (Acme mock — lab only) |
| **Layout adapter** | `src/components/layout/AegisSidebar.tsx` |
| **npm deps** | `lucide-react` |
| **Icons** | Lucide — Commands (⌘K) only on booth path; phase nav is text-only |

**Exports**

| Export | Role |
|--------|------|
| `SidebarNav` | 260px collapsible nav shell with session header |
| `SessionContextHeader` | Optional session strip (demo / lab only) |
| `NavItemData`, `NavGroupData` | Nav item schema |

**Props (`SidebarNav`)**

| Prop | Type | Notes |
|------|------|-------|
| `activeId` | `string` | Current phase id |
| `onSelect` | `(id) => void` | Selection handler |
| `navGroups` | `NavGroupData[]` | Grouped nav (no mock Acme data in production) |
| `bottomItems` | `NavItemData[]` | Optional footer items |
| `sessionContext` | `{ title, subtitle?, badge? }` | Session strip |
| `header` / `footer` | `ReactNode` | Collapse control, ⌘K hint |

**Production (`AegisSidebar`):** Static AegisLoop wordmark + `ModeChip`; nav = Search (⌘K), Identify, Generate, Defend; badges from session (`approved.length`, generate seed/run, defend recall).

**Design notes:** Adapted from pasted dashboard-sidebar preview — paper/sage tokens, `rounded-xl` card shell, 260px width. Conflicts with DESIGN §13 (220px, no icons, no shadow): width + Commands icon + subtle ring on shell — documented in `UI-OVERHAUL-PLAN.md`.

---

### AdvancedStats (`advanced-stats.tsx`)

| Field | Value |
|-------|-------|
| **Path** | `src/components/ui/advanced-stats.tsx` |
| **Utils** | `advanced-stats-utils/charts.tsx` (`ClippedAreaChart`), `advanced-stats-utils/timeline-animation.tsx` |
| **shadcn deps** | `chart.tsx`, `badge.tsx` |
| **npm deps** | `recharts`, `class-variance-authority`, `tailwind-merge`, `clsx` |
| **Demo** | `src/components/ui/advanced-stats.demo.tsx` (lab only) |

**Exports**

| Export | Role |
|--------|------|
| `AdvancedStats` | Hero clipped area chart + goal/insight column + KPI row |
| `AegisDefendStats` | Defend session metrics adapter (`compact` or full layout) |
| `AegisIdentifyStats` | Identify REST census row (`compact` default) |

**Booth wiring**

| Route | Placement |
|-------|-----------|
| `/defend` | Full `AegisDefendStats` above `RecallFprCurve` — recall trend chart, OP goal, weakest-slice insight, 4 KPIs |
| `/identify` | Compact `AegisIdentifyStats` in REST state above landscape grid |

**Design notes:** Paper/sage/ink tokens only — no zinc-900 hero cards. `ClippedAreaChart` uses sage fill + ink stroke; `TimelineAnimation` honors `prefers-reduced-motion`. Goal progress bar uses `sage-600` on `sage-100`, not dark SOC panels.

---

## Integrated components

### GlobeStudy (`globe-study.tsx`)

| Field | Value |
|-------|-------|
| **Path** | `src/components/ui/globe-study.tsx` |
| **Source HTML** | `src/components/ui/globe-study-document.html` (trimmed from [MengTo/threeui](https://github.com/MengTo/threeui), MIT) |
| **Demo** | `src/components/ui/globe-study.demo.tsx` |
| **npm deps** | None (React only) |
| **Icons / assets** | None — land mask is inline base64 in embedded script |
| **Lucide** | Not required |

**Props**

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `mode` | `"dark" \| "light"` | `"dark"` | Swaps ink + focus surface |
| `scale` | `number` | `1` | Clamped 0.65–1.5, CSS transform on iframe |
| `opacity` | `number` | `1` | Clamped 0.1–1 |
| `hue` | `number` | `0` | deg, −180…180 |
| `saturation` | `number` | `1` | 0…2 |
| `brightness` | `number` | `1` | 0.4…1.8 |
| `className` | `string` | — | Wrapper |
| `style` | `CSSProperties` | — | Wrapper |

**State / context:** Self-contained iframe `srcDoc`; no providers. Continuous `requestAnimationFrame` inside sandboxed iframe (`sandbox="allow-scripts"`).

**Responsive:** Parent must give explicit height (`h-full` / `h-screen`). Canvas resizes via `ResizeObserver` on `#grid`.

**Interaction:** Drag to spin, scroll to zoom, click to pin (max 7 pins).

**Design conflict (booth):** Dark `#08090a`, Inter, infinite motion loop — **forbidden on live booth path** per `DESIGN.md`. Treat as **lab / overhaul reference** until restyled to paper/sage/light and motion policy is resolved.

**Brainstorm placements**

- Identify landscape empty-state hero (restyled light variant)
- Defend “global threat surface” metaphor (static poster frame, not live loop)
- Booth attractor on secondary monitor only
- Command palette preview thumbnail

**Preview locally:** import `GlobeStudyDemo` in a throwaway route or Storybook later; not wired to `/identify` yet.

---

### SimpleGraph (`simple-graph.tsx`)

| Field | Value |
|-------|-------|
| **Path** | `src/components/ui/simple-graph.tsx` |
| **Registry** | `@reactbits-starter/simple-graph-tw` (React Bits Pro) |
| **Install** | `npx shadcn@latest add @reactbits-starter/simple-graph-tw --yes` (requires `REACTBITS_LICENSE_KEY`) |
| **Status** | Hand-adapted stub — registry install blocked until license key is set; API matches Pro docs |
| **npm deps** | None (React + SVG) |
| **Data helpers** | `src/lib/graph-series.ts` |

**Props** — matches [React Bits Pro Simple Graph](https://pro.reactbits.dev/docs/components/simple-graph): `data`, `lineColor`, `dotColor`, `height`, grid/dot/curve options, `animationDuration`, `prefers-reduced-motion` skips draw.

**Design notes:** Paper/sage/ink only (`#3E6B4F` line, `#E2DFD6` grid). No gradient fill on booth path. Animation capped at 160ms; horizontal grid only.

**Production wiring**

- **Generate** — `CorpusGrowthGraph` in right column (`buildCorpusGrowthSeries` from run `event_count` + seed)
- **Identify** — `DiscoverTimelineGraph` during `scanning` stage (cumulative ops-log depth from SSE stream)

**Preview routes:** `/generate` after simulate; `/identify` → Discover → scanning stage.

---

## In-repo UI primitives (shadcn-adjacent)

| Component | File | Role |
|-----------|------|------|
| Button | `Button.tsx` | Primary actions |
| Card | `Card.tsx` | Panel shells |
| Drawer | `Drawer.tsx` | Technique detail |
| ModeChip | `ModeChip.tsx` | LIVE / DEMO |
| StatusChip | `StatusChip.tsx` | Phase status |
| Table | `Table.tsx` | Data grids |
| Spinner | `Spinner.tsx` | Loading |
| EmptyState | `EmptyState.tsx` | Zero data |
| ErrorState | `ErrorState.tsx` | API errors |
| ChartFooterStrip | `ChartFooterStrip.tsx` | Chart chrome |
| Chart | `chart.tsx` | shadcn recharts wrapper (paper tokens) |
| Badge | `badge.tsx` | shadcn badge (sage/signal variants) |
| Chart | `chart.tsx` | shadcn recharts shell + tooltip |
| Badge | `badge.tsx` | Status pills (sage tokens) |
| AdvancedStats | `advanced-stats.tsx` | KPI dashboard cards + clipped area chart |

---

### AdvancedStats (`advanced-stats.tsx`)

| Field | Value |
|-------|-------|
| **Path** | `src/components/ui/advanced-stats.tsx` |
| **Utils** | `src/components/ui/advanced-stats-utils/timeline-animation.tsx`, `charts.tsx` |
| **Demo** | `src/components/ui/advanced-stats.demo.tsx` (full layout — lab only) |
| **npm deps** | `recharts`, `class-variance-authority`, `tailwind-merge`, `lucide-react` |

**Exports**

| Export | Role |
|--------|------|
| `AdvancedStats` | Configurable dashboard: clipped area chart, goal card, insight, KPI row |
| `AegisDefendStats` | Defend metrics from session / score API |
| `AegisIdentifyStats` | Identify census + approval queue |

**Props (`AdvancedStats`)**

| Prop | Type | Notes |
|------|------|-------|
| `compact` | `boolean` | KPI row only (booth path) |
| `kpis` | `StatKpi[]` | Label, value, optional change badge |
| `chartData` | `ChartPoint[]` | Area series for full layout |
| `goal` / `insight` | optional | Side column cards (full layout) |

**Production wiring**

- **Defend** — `AegisDefendStats` replaces legacy KPI strip (`DefendPage.tsx`)
- **Identify** — compact `AegisIdentifyStats` above landscape grid in REST stage

**Design notes:** Paper/sage/ink tokens; no zinc-900 SaaS chrome. `TimelineAnimation` uses intersection observer; respects `prefers-reduced-motion`. Goal card uses `sage-700` (not dark SOC).

---

## Planned / stolen references (not integrated)

| Name | Origin | Intent | Booth? |
|------|--------|--------|--------|
| Audit Log table | 21st #25163 | WorkLog density | Yes — adapt to paper tokens |
| Command palette | 21st originui 382 | ⌘K structure | Yes — wired, needs polish |
| AnimatedContent | React Bits | Section reveals | Maybe — allow-list only, no Dither |
| Seed stamp | Custom | Generate provenance | Yes — in app |
| Ledger tape | Custom | Generate activity | Yes — in app |

---

## Overhaul principles (when we brainstorm)

1. **Paper / sage / ink** — no indigo, no dark SOC chrome on main path.
2. **Motion** — no decorative loops on booth; pauses on `prefers-reduced-motion`.
3. **Honesty** — LIVE chip only when backend is live; catalog fallback labeled.
4. **Steal structure, not palette** — 21st/React Bits layout patterns, AegisLoop tokens.
5. **Registry first** — add rows here before dropping components into Identify/Generate/Defend.

---

## Changelog

- **2026-08-31** — SimpleGraph (React Bits Pro API) wired to Generate corpus growth + Identify discover timeline; Pro registries in `components.json`.
- **2026-08-31** — AdvancedStats dashboard (chart, badge, timeline reveal) wired to Defend KPI row + Identify REST stats.
- **2026-08-31** — AdvancedStats + shadcn `chart`/`badge`, Defend hero stats, Identify compact census row.
- **2026-08-31** — Landing at `/`, Identify at `/identify`, dashboard-sidebar + AegisSidebar shell, lucide-react.
- **2026-08-30** — Added GlobeStudy + this registry file.
