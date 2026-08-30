# UI overhaul — done & next steps

**Date:** 2026-08-31  
**Scope:** Landing page, route split, dashboard-sidebar shell, card theming.

---

## What was done

### Routes

| Path | Surface |
|------|---------|
| `/` | `LandingPage` — GlobeStudy hero (light), no workspace shell |
| `/identify` | Shell + `IdentifyPage` |
| `/generate` | Shell + `GeneratePage` |
| `/defend` | Shell + `DefendPage` |
| Legacy | `/simulation`, `/decisioning`, `/arms-race`, `/copilot` → redirects |

### Landing (`src/features/landing/LandingPage.tsx`)

- Split layout: closed-loop copy + CTAs left, GlobeStudy right (light mode).
- `prefers-reduced-motion`: static sage poster (no iframe animation).
- Top bar only: wordmark, LIVE/DEMO chip, skip link.
- Phase preview: Identify → Generate → Defend.

### Shell

- `AegisSidebar` wraps `SidebarNav` from `dashboard-sidebar.tsx`.
- 260px expanded / 48px collapsed; ⌘K wired to `CommandPalette`.
- Main workspace in `rounded-xl` card (`border-border/60`, `shadow-sm`, `ring-1`).
- `.panel` in `globals.css` aligned to same card treatment.

### Dependencies

- `lucide-react` installed for sidebar chrome icons (collapse, Commands).

### Tests

- `e2e/booth.spec.ts` updated: landing test on `/`, workspace tests on `/identify`.

---

## DESIGN.md conflicts (flagged)

| Lock | Overhaul choice | Follow-up |
|------|-----------------|-----------|
| §14 Form A: `/` = Identify REST | User-directed marketing landing at `/` | Intentional product pivot; update DESIGN §14 when lock is revised |
| Sidebar 220px, no shadow | 260px + card ring on main panel | Tighten to 220px or remove ring if judges want strict lock |
| Sidebar: no icons | Lucide on Commands + collapse | Remove icons or keep Commands-only |
| No decorative motion loops | GlobeStudy animates on landing | OK on landing only; reduced-motion fallback added |
| Radii 6px standard | `rounded-xl` on shell card | Consider `rounded-lg` (8px drawer tier) for stricter match |
| No hero + CTA landing slop | Full landing with hero + dual CTA | User-requested; copy is ops narrative not marketing fluff |

---

## Next steps (paste-ready components)

When you paste more UI primitives, use this order:

1. **Registry** — add row to `COMPONENTS.md` before wiring.
2. **Token pass** — replace `primary` / `foreground` / `card` shadcn vars with `paper` / `ink` / `sage` from `tokens.css`.
3. **Route guard** — booth-path components only under `Shell`; attractors only on `/` or lab routes.
4. **Motion** — wrap loops in `usePrefersReducedMotion`; one-shot inserts only in workspace.
5. **Nav** — max 3 phase items in `AegisSidebar`; no Acme mock groups.

### Planned from prior brainstorm (not this task)

| Component | Target | Notes |
|-----------|--------|-------|
| PixelBlast | Generate ambience (optional) | Sage-tinted, paused on reduced-motion; shader policy |
| Audit Log steal (21st) | WorkLog density | Paper tokens |
| AnimatedContent (React Bits) | Row inserts | 160ms one-shot only |
| Sticky Continue bar | All phases | P0 in BOOTH-PLAN |

### Preview

```bash
cd frontend
npm run dev          # http://localhost:5173/
npm run build        # typecheck + production build
npm run test:e2e     # Playwright booth path
```
