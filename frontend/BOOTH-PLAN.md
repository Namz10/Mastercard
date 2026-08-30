# AegisLoop booth — execution plan

**Status:** living checklist for GFF 2026 prototype.  
**Law:** [DESIGN.md](DESIGN.md) (look) · [IMPLEMENTATION-SPEC.md](IMPLEMENTATION-SPEC.md) (behaviour, copy, clicks) wins over DESIGN §4/§9.

---

## Judge story (60s)

Map fraud landscape → discover from OSINT → simulate payment traffic → score detection on holdout → (proof) miss feeds next attack.

**Three routes only:** Identify → Generate → Defend. No Copilot, no 4th nav, Train is not the climax.

---

## Done

| Item | Notes |
|------|--------|
| Session store + routes + LIVE chip | `aegisloop:session` |
| Identify SSE Discover + landscape + REVIEW | cmdk palette structure (21st 382) |
| Generate demo scale + seed stamp + ledger tape | auto-simulate on catalog seed |
| Defend frozen curve + KPI + retrain proof | flat `tpr_at_fpr` fixed in demo pack |
| HITL **catalog demo fallback** | `GET /identify/hitl` returns `disposition: review \| in_catalog` for prior `identify-*` approvals |
| Playwright chrome (Brave) + vitest copy grep | not full 90s oracle |

---

## Next (priority order)

### P0 — workflow (judge never dead-ends)

| # | Task | Acceptance |
|---|------|------------|
| 1 | **⌘K → Run booth demo** | One command: catalog seed → demo simulate → `/defend` frozen score; chip RECORDED |
| 2 | **Sticky Continue bar** | Bottom 48px: next action always visible (Add done → Continue to Generate, etc.) |
| 3 | **Discover 0-proposal card** | When `proposed_count=0`: explain why + **Continue with catalog seed** primary (not footer only) |
| 4 | **FinCEN PDF extract** | Fix `llm_fallback` on `.pdf` URLs so more than one attack proposes per run |

### P1 — visual (DESIGN §13, paper/sage/ink)

| # | Task | Acceptance |
|---|------|------------|
| 5 | **Panel system everywhere** | Ledger, log, curve, KPI strip — white cards on paper well, 36px rows |
| 6 | **WorkLog steal** (21st Audit Log 25163) | IST · verb chip · row→drawer; AnimatedContent 160ms inserts (React Bits allow-list) |
| 7 | **Landscape at 2m** | Full height, dashed gaps, highlight `?highlight=Txx`, no wireframe emptiness |
| 8 | **Defend hero** | 56px recall cell, shaped ROC (not flat), interventions allow-heavy bars |

### P2 — proof / tests

| # | Task | Acceptance |
|---|------|------------|
| 9 | Playwright **booth-demo** | ⌘K run → tape rows → defend KPI ≠ `—` |
| 10 | API test: HITL `in_catalog` after approve | `tests/test_identify_api.py` |
| 11 | Retrain stays secondary | Visible, wired; not required on stage |

---

## Demo paths

### A — Live (Tavily + LLM up)

Discover → Add (≥1) → Generate tape → Defend curve on glass → optional Retrain proof.

### B — Certainty (Tavily thin / 0 proposals)

⌘K booth demo **or** catalog seed → auto-simulate → frozen Defend. REVIEW shows **In catalog** for earlier approvals.

---

## Honesty (never fake)

| Show | Never show |
|------|------------|
| LIVE = search + LLM + health | Live UPI / issuer feed |
| RECORDED / FROZEN chips | Silent fallback |
| Recall @ genuine FPR + holdout caveat | 99.9% accuracy, Champion trophy |
| In catalog = prior lab approval | Re-approve same row |

---

## Component steals (structure only — restyle to tokens)

| Job | Source |
|-----|--------|
| ⌘K | shadcn Command 714 / originui 382 |
| Ops log | 21st Audit Log 25163 |
| Ledger table | originui Table 89 / shadcn Data Table 1050 |
| Row motion | React Bits AnimatedContent-TS-TW (no Dither/shaders) |

21st `get_component` quota may be 0 — implement structure by hand when needed.

---

## API quick reference

| UI | Endpoint |
|----|----------|
| Landscape | `GET /catalog/threat-map` |
| Discover | `POST /identify/run/stream` |
| Proposed + catalog demo | `GET /identify/hitl` → `items[].disposition` |
| Approve | `POST /identify/approve/{vector_id}` |
| Simulate | `POST /generate/population` (demo 200×40×14) |
| Frozen score | `GET /demo/recorded/score` |
| Retrain proof | `POST /defend/loop-m` |

---

*Last updated: HITL catalog demo fallback shipped; plan items P0–P2 open.*
