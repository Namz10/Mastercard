---
name: Defend Peak Implementation
overview: "AGENT ENTRY. Read this file first. Code only from Docs/plans/defend-execution-ssot.md (§13 overrides). Tests from Docs/plans/defend-test-tracker.md (RED first). Sequence T1A+T1B→T2→T3→T4→T6→T7 then T5/T8/T9/T10. Loop G out."
todos:
  - id: t1a
    content: "Ticket 1A: Invoice booleans payload → features_auth + TRAIN_ALLOWLIST. RED tests 1A.1–1A.4 first."
    status: pending
  - id: t1b
    content: "Ticket 1B: fan_in_unique_payers_1h + burst_velocity = unique outbound payees. RED 1B.1–1B.2."
    status: pending
  - id: t2
    content: "Ticket 2: n_pos + not_comparable + _metrics_pass. RED 2.1, 2.5."
    status: pending
  - id: t3
    content: "Ticket 3: inner_folds_from_train; op_threshold on inner-val; early_stopping=False; refit outer train."
    status: pending
  - id: t4
    content: "Ticket 4: Makefile generate-scale full mix (no T13); defend-fit, defend-gtest all_rows, defend-gdev."
    status: pending
  - id: t6
    content: "Ticket 6: Loop M n_pos + family_chosen_from_slice required; reject gtest. Keep existing run_id scheme."
    status: pending
  - id: t7
    content: "Ticket 7 MUST Loop T: G-dev 44 mine/gate, 4 HTTP routes, list-root YAML, no _meta. RED 7.6, 7.8, 7.9."
    status: pending
  - id: t5
    content: "Ticket 5 SHOULD Optuna after T7 if time. Soft AP penalty. Never open seed 43."
    status: pending
  - id: t8
    content: "Ticket 8 SHOULD Isolation Forest stamp-free notify-only. Abort if genuine notify > 0.05."
    status: pending
  - id: t9
    content: "Ticket 9 SHOULD isotonic + ECE on inner-val."
    status: pending
  - id: t10
    content: "Ticket 10 SHOULD cluster bootstrap + permutation importance."
    status: pending
  - id: docs
    content: "Docs index lives in this plan + Docs/plans/README-defend.md. Do not reopen architecture."
    status: completed
isProject: false
---

# AGENT START HERE — Defend Peak

**Repo:** `/home/aarush_linux/projects/Mastercard`  
**You are implementing Defend only.** Do not reopen Identify LangGraph, do not add Loop G, five models, AutoGluon, GNN, or auto-promote rules.

**This Cursor plan is the index.** It does **not** contain ticket code. Ticket code is in the repo SSOT. The long historical ticket prose that used to sit in this file is **void** (it said Loop T on inner-val, seven HTTP routes, YAML `_meta`). Following that prose is a defect.

---

## 1. How to use every document

Open files from the **repo**, not from memory.

| Document | Path | When to open | When NOT to use it |
|----------|------|----------------|-------------------|
| **This plan** | `.cursor/plans/defend_peak_implementation_d6545d76.plan.md` | First. Todos, sequence, doc map. | Do not copy ticket snippets from old chat. |
| **Execution SSOT** | `Docs/plans/defend-execution-ssot.md` | **Before every line of product code.** Constants, file lists, Loop T spec, **§13 overrides**. | Do not skip §13. |
| **Test tracker** | `Docs/plans/defend-test-tracker.md` | **Before every line of test code.** Exact function names, RED oracles, E2E bodies. | Do not invent weaker asserts. |
| **Keep-in-minds** | `Docs/plans/defend-dev-keepinminds.md` | Before merge / if tempted to “just peek” G-test. | Not a license to change architecture. |
| **Architecture SSOT** | `Docs/plans/defense-architecture.md` | What the system is; Brake order; named gaps; feature names. | Ticket numbers in §15 may lag. Use SSOT §13 for tickets. |
| **Why** | `Docs/plans/defense-why.md` | Judge argument; do not implement from it. | |
| **Walkthrough note** | `Docs/plans/architecture-defense-doc.md` | Slides / English / mermaid. | Not for code. |
| **VALIDATION.md** | repo root | Metric definitions, G1–G7. Loop M ε is **0.02**; rule ε is **0.002**. | Old “threshold from G-eval” lines yield to inner-val (T3). |
| **Peak handoff** | `Docs/plans/defend-peak-handoff.md` | File inventory, what exists on disk. | **Do not implement tickets 7–8 from that file** (Loop G / optional T). Banner at top says so. |
| **Plan 08 Generate** | `Docs/plans/08-generate-world-build.md` | Scale 2400×120×90 only. | Do not change injectors unless T1 broke fidelity. |
| **Problem statement** | `MC_PS.md` | Judging axes. | |
| **Recipe** | `models/features.json` | MERGE new keys; never replace the whole file. | |
| **Live rules** | `data/rules/v0_rules.yaml` | List root. CI must not rewrite this file except via tmp path in tests. | |

**Conflict rule (memorize):**  
`defend-execution-ssot.md` **§13** > rest of that file > this plan’s todos > architecture.md > handoff.md > this plan’s deleted historical text.

---

## 2. Read order for a cold agent (do this once)

1. This file (§1–§6).  
2. `Docs/plans/defend-execution-ssot.md` §0 locked product, §1 constants, §13 addendum.  
3. `Docs/plans/defend-test-tracker.md` §0 QA rules + the ticket you will execute.  
4. Open the **source files named in that ticket** (`features.py`, `fit.py`, …).  
5. Write RED tests → run → confirm fail → implement → run until GREEN → run always-green regression in the test tracker.

Do **not** start by reading `Docs/feedback-loop.md`, `Docs/defense_architecture.md`, or `Docs/ARCHITECTURE.md`. Those claim loops and models that are not in the repo.

---

## 3. Locked product (do not reopen)

- One `HistGradientBoostingClassifier`, `y = label_family` (6 classes). Family AP is a metric.  
- Specialists: **zero**. Loop G: **do not build**.  
- Loop T: **MUST**. HITL approve required. LLM `{id, reason}` only.  
- Headline metrics: G-test `world_seed=43`, `score_run(..., all_rows=True)`.  
- Decisions: G-dev `world_seed=44`. Inner-val = last 20% of **train** calendar (Optuna + `op_threshold` only).  
- Two FPR epsilons: Loop M **0.02**; rule promote **0.002**. Operating point **0.01**.  
- CI: `n_customers=20`. Plan 08 is Makefile, not default pytest. Loop M `not_comparable` on n=20 is **correct**.

---

## 4. Ticket sequence (one ticket per change-set)

```
T1A and T1B (parallel OK)
    → T2 → T3 → T4
        → T6 Loop M polish
        → T7 Loop T MUST
            → T5 Optuna SHOULD (skip if clock dying)
            → T8 IF SHOULD
            → T9 isotonic SHOULD
            → T10 bootstrap SHOULD
```

**Do not** start T5 before T3. **Do not** start T7 before T3 and T1A (invoice on X). **Do not** start T8 before T7 if you still need the HITL demo.

**Stop-gates** are in `defend-test-tracker.md`. If the stop-gate test is GREEN on HEAD before you code, the test is too weak — fix the oracle, do not mark the ticket done.

---

## 5. Per-ticket: where to look (spoonfeed)

| Ticket | Implement from | Test from | Touch these files only |
|--------|----------------|-----------|------------------------|
| 1A | SSOT §3.3 | tracker Ticket 1A | `packages/sim/features.py` `replay_features`, `packages/sim/export.py` |
| 1B | SSOT §3.4 | tracker 1B | `packages/sim/features.py` AccountRuntime; `COVERAGE_EQUIV` in `rules.py` |
| 2 | SSOT §5 | tracker 2 | `packages/eval/fit.py` |
| 3 | SSOT §4 | tracker 3 | `packages/eval/split.py`, `fit.py`, MERGE `models/features.json` |
| 4 | SSOT Ticket 4 | tracker 4 (`test_makefile_defend.py`) | `Makefile` only |
| 6 | SSOT Ticket 6 + §13.2 run_ids | tracker 6 | `loop_m.py`, `apps/api/routes/defend.py` |
| 7 | SSOT Ticket 7 + **§13.6–13.15** | tracker Ticket 7 **all IDs** | new `loop_t.py`, `rule_hitl.py`; 4 routes; tmp YAML in tests |
| 5 | SSOT Ticket 5 + §13.11 | tracker 5 | `pyproject.toml` dev extra, `fit.py`, `POST /defend/tune` |
| 8 | SSOT Ticket 8 | tracker 8 | `iso_check.py`, `brake.py` kwarg |
| 9 | SSOT Ticket 9 | tracker 9 | `fit.py` isotonic |
| 10 | SSOT Ticket 10 | tracker 10 | `fit.py` bootstrap/permutation |

Loop M ids **already in code:** `{run_id}__extra-{family}`, `{run_id}__gtest`, `{run_id}__loopm-train`. Do not rename.

Loop T HTTP **only:** `POST /defend/loop-t/mine`, `GET /defend/rules/drafts`, `POST /defend/rules/approve/{id}`, `POST /defend/rules/reject/{id}`.

Loop T data: mine on G-dev 44 first 70% `event_ts`; gate on last 30%. Never seed 43. YAML stays a **list**.

`features.json`: **merge** keys; keep `hang_guard_seconds_1k`, `app_flag_cols`, existing `loop_m`.

---

## 6. Commands

Always-green (after every ticket):

```bash
cd /home/aarush_linux/projects/Mastercard
pytest tests/test_sim_export.py tests/test_sim_inject.py tests/test_sim_world.py \
  tests/test_sim_fidelity.py tests/test_eval_fit.py tests/test_eval_split.py \
  tests/test_eval_loop_m.py tests/test_eval_rules_brake.py \
  tests/test_defend_handoff.py tests/test_defend_api.py -q --tb=short
```

After T7: add `pytest tests/test_loop_t.py -q --tb=short`.

Do **not** run `make generate-scale` in default CI.

---

## 7. Forbidden (instant reject)

- `train_test_split(shuffle=True)` as published protocol  
- Harvest / HPO / rule mine / miss-family pick on world_seed **43**  
- Auto-promote rules; `catalog_solved: True`  
- LLM emitting `when`  
- Putting `_meta` as YAML document root (breaks `load_v0_rules`)  
- Training from `packages/sim/injectors.py`  
- Claiming 24 detectors, five models, nine loops, live UPI  
- Copying APP flags onto genuine rows  
- Dropping `burst_velocity` instead of redefining it  

---

## 8. Definition of a finished sprint

Honesty tests 1A+1B GREEN (were RED). T2–T4, T6, T7 stop-gates GREEN. One Plan 08 G-test JSON is a **Makefile** artifact for the walkthrough, not a pytest default. n=20 Loop M may be `not_comparable` — ship it honestly.
