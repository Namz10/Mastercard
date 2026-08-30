# AegisLoop Workspace Design System

**Scope:** Identify · Generate · Defend booth paths (`/identify`, `/generate`, `/defend`). Landing uses `.landing-*` only — do not mix.

**Status:** Implementation SSOT for **Bento × Spatial**. Supersedes the glass-everywhere / beige-mesh pass. Product honesty rules remain in [DESIGN.md](DESIGN.md) and [IMPLEMENTATION-SPEC.md](IMPLEMENTATION-SPEC.md).

**Explicit lock override:** DESIGN.md forbids indigo. This brief **requires** one sophisticated electric indigo as `--accent`. Sage recedes to success / safe signal only.

---

## Hierarchy

**Hierarchy > whitespace > composition > typography > depth > decoration**

| Layer | Treatment |
|---|---|
| **Canvas** | Cool near-white `#fbfbfc` + barely-visible indigo radial at top-left. Not beige mesh, not muddy `paper-0` slab. |
| **Primary surfaces** | Solid warm-white / cool-white panels. 1px low-contrast border, radius 20–24px, soft diffuse shadow. |
| **Glass** | **Selective only** — floating secondary sheets: sidebar, status/stepper chrome, command overlay, sticky Continue, KPI chips. Not every card. |
| **Accent** | One color: `--accent` indigo. Active nav, primary CTA, selected metric, LIVE. Sparingly. |
| **Sage** | Success / safe / LIVE RULE / fidelity pass only. |
| **Ink** | Charcoal `#191c19` on white. Numbers punch. |
| **Motion** | 80–160ms opacity/elevation. Hover lift 1–2px. No looping shaders on workspace. Globe stays landing. PixelBlast only on named hero cards, paused on `prefers-reduced-motion`. |

**Forbidden:** rainbow, neon SaaS KPI walls, heavy glass on every tile, beige zebra, equal-card grids, looping shaders on `/identify` `/generate` `/defend`.

---

## Tokens

Defined in `tokens.css` / `globals.css`:

```css
--canvas            /* #fbfbfc */
--surface-solid     /* #ffffff */
--surface-float     /* rgba(255,255,255,0.72) */
--accent            /* #3b4fd9 — not Tailwind #2563EB / #6366F1 */
--accent-hover
--accent-muted
--workspace-mesh    /* cool white + indigo radial */
--glass-bg / --glass-border / --glass-highlight
--shadow-float / --shadow-bento
--radius-sheet: 20px
--radius-bento: 24px
```

| Class | Use |
|---|---|
| `.workspace-bg` | Shell canvas |
| `.bento-panel` | Dominant solid surfaces (landscape, tape, curve) |
| `.glass-sheet` | Floating sidebar, chrome bars, Continue, command palette |
| `.glass-control` | Search row, compact chips |
| `.panel` | Alias of `.bento-panel` (legacy call sites) |
| `.workspace-card-lift` | 1–2px hover lift, 140ms |

---

## Chrome (peak spatial)

- **Canvas padding** 10–12px so sidebar and main are separate objects.
- **Sidebar** 260px floating `rounded-[20px]` sheet, 8–12px gap, not a flush beige strip. Active Identify = accent fill, not mint pill. Search = `.glass-control`.
- **Status strip + PhaseStepper** = floating translucent sheets, 1px tonal border, inner highlight. Breadcrumb active state is architectural (accent bar + weight), not a faint sage dot.
- **Main** inset, `rounded-[24px]` solid white window with 1px border.

---

## Bento composition

1–2 dominant large surfaces + smaller orbiting modules. Avoid equal-card grids.

### Identify `/identify`

- **Dominant:** landscape as **one** large `.bento-panel` (five columns live inside it; not five beige slabs).
- **Orbiting:** `AegisIdentifyStats` unequal mass — Techniques Mapped (hero 24 + PixelBlast), Approved (sage-tinted READY), Queue (quiet).
- **Cells:** LIVE RULE filled + left sage bar; COVERAGE GAP outline/dashed + quieter weight.
- **Discover CTA** and Continue: accent indigo. Continue = floating `.glass-sheet`.

### Generate `/generate`

- **Dominant:** payment tape left **55–60%**.
- **Right:** stacked unequal — Seed stamp (compact + PixelBlast), Corpus growth **min 240px**, Mule chain **min 300px**.
- Tape: no zebra; hover-only row highlight.

### Defend `/defend`

- **Dominant:** `RecallFprCurve` **min-h 380px**, ~70%.
- **Orbiting:** `AegisDefendStats` — hero recall (large + `ClippedAreaChart` sparkline); supporting metrics smaller.
- `BrakeRail` slim floating sheet.

### Landing `/`

White canvas + spatial globe as the dominant object. Left copy as a floating sheet. Accent on primary CTA. GlobeStudy only here.

---

## Component wiring (must be on a live route)

| Component | Route |
|---|---|
| `GlobeStudy` | `/` landing hero only |
| `PixelBlast` | Identify Techniques Mapped hero; Generate Seed stamp |
| `SidebarNav` / `AegisSidebar` | Shell left rail |
| `AegisIdentifyStats` / `AegisDefendStats` | `/identify` REST, `/defend` |
| `ClippedAreaChart` | Defend recall hero sparkline |
| `SimpleGraph` | Generate corpus (large); Identify discover timeline (scanning) |
| `ChartFooterStrip` | Defend curve + Generate corpus footers |
| lucide-react | Sidebar collapse + Search |

---

## Motion

- Allowed: 80–120ms color; 140ms card lift; 160ms row insert; one-shot chart draw ≤160ms.
- PixelBlast: `liquid={false}` `enableRipples={false}` `transparent` `pointer-events-none`. Reduced-motion → static CSS pixel grid.
- `prefers-reduced-motion`: disable lift; keep state in text/counters.

---

## What stays from DESIGN.md

| Rule | Workspace expression |
|---|---|
| IBM Plex trio | Serif titles (larger), Sans UI, Mono numbers |
| Honesty | `ModeChip` LIVE/RECORDED/FROZEN; degraded banners |
| Color = status | StatusChip glyph+word+color; sage = safe only |
| `data-demo` attrs | **Never remove** |
| Copy SSOT | Do not change `COPY.ts` strings; layout may hide excess |

---

## Verification

```bash
cd frontend && npm run build && npm run test
```

Preview: `/` · `/identify` · `/generate` · `/defend`
