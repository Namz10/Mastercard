# AegisLoop Booth Demo (Netlify)

Static SPA prototype of the full Identify → Generate → Defend loop with **champion metrics** and live narration. Deploy from branch `demo/netlify`, base directory `demo/`.

## Quick start

```bash
cd demo
npm ci
npm run bake    # refresh packs from ../data/validation
npm run dev     # http://localhost:5173
npm run build   # dist/ for Netlify
```

## Modes

| Query / env | Behavior |
|-------------|----------|
| default | Booth timing (~4–6 min full demo) |
| `?speed=fast` | ~30s jobs, no caption pauses |
| `?speed=presenter` | Slower + captions always on |
| `?speed=instant` | Instant replay |
| `VITE_API_BASE_URL` | Optional: point at real API (`make dev`) |

## Features

- **RECORDED** packs from `internal_01pct_fpr_freeze.json` (~98.5% recall @ OP)
- Live **NowHappening** rail + teleprompter during SSE replay
- **How it works** page + per-stage explainers
- **Play full demo** (landing + ⌘K) auto-walks the loop
- Feedback page uses **gtest before/after** (apples-to-apples), not eval-fold before vs gtest after

## Netlify

- Production branch: `demo/netlify`
- Base directory: `demo`
- Build: `npm ci && npm run build`
- Publish: `dist`

## Packs

`node demo/scripts/bake-packs.mjs` from repo root reads:

- `../data/validation/v1/` — champion freeze, loop M, pareto curves
- `../data/catalog/seed.yaml` — threat map + coverage
- `../data/osint/fixtures/` — identify URLs

Output: `demo/public/packs/`

## Do not merge

This branch is deploy-only. Product `frontend/` + API stay on `main`.
