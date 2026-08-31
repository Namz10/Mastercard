# Metrics legend (booth demo)

Three labeled rows for judges and engineering. The **prototype hero** uses champion freeze — not cold first-fit on seed 42.

| Label | Slice | Model | Recall @ OP | Genuine FPR | Source |
|-------|--------|--------|-------------|-------------|--------|
| **Champion (prototype default)** | `v1-gtest-48` | `v1-train-46__loopm-train` | **98.52%** | **0.032%** | `internal_01pct_fpr_freeze.json` |
| **Loop M pre (gtest)** | `v1-train-46__gtest` | base `v1-train-46` | from `gtest_before` | from `comparison` | `loop_m_result.json` |
| **Loop M post (gtest)** | same gtest | `v1-train-46__loopm-train` | from `gtest_after` | improved miss-family AP | `loop_m_result.json` |
| **Honest live reference** (not default UI) | eval fold `pop-*` | cold fit seed 42 | ~75% | ~1% OP target | live lab run |

## Footnotes

- Hero metric = `recall_at_op` at operating point chosen on **inner-val** only.
- Curve anchors = `tpr_at_fpr` from pareto merge on gtest-48.
- Champion freeze ≠ cold first fit on a new simulated world.
- Loop M grades on **new gtest seed 48** — cannot mark its own homework.
- identity_burst AP ~0.34 → ~0.97 post Loop M on champion pack.

## UI labels

- **RECORDED** — static packs; gates documented in lab artifacts, not re-run on Netlify.
- Never claim live UPI feed or issuer SLA — simulated corpus, lab rig.
