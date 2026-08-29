# H7 — Recursive Loop M (max 3 rounds)

## Protocol (G-dev / G-test split)

```
round = 1 .. MAX_ROUNDS (3):
  train on v1-train-46 (+ targeted extras from gdev mistakes only)
  score on v1-gdev-47  → promote/reject this round
  NEVER score v1-gtest-48 for promote decisions

after loop ends OR max rounds:
  one-shot score final candidate on v1-gtest-49 (confirmatory)
  optional: frozen v1-gtest-48 photograph compare (instrumentation only, not for promote)
```

**MAX_ROUNDS = 3** (hard cap).

## Mistake buckets (not blind HN dump)

Per round on **gdev-47** only:

- false-positive normals (family-filtered; exclude `is_new_payee=1` per H6-D)
- false-negative fraud (weakest family)
- borderline cases (score near `detect_thr`)

## ACCEPT gate (all required)

- FPR improves meaningfully vs prior champion on **gdev**
- Recall not ↓ >5% @ 1% FPR cap
- `identity_burst` AP not collapse (>5% relative drop)
- `mule` AP stable
- `cost_sketch` not worse materially
- No family large regression
- **gtest-49** confirmatory passes (one touch)
- No leakage / shortcut features

## Anti-rig

- Never tune Optuna or promote on gtest-48/49
- Never use seed-43 museum
- H6 generic top-k mining forbidden
