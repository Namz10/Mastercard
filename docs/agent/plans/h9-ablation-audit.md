# H9 — Ablation audit (frozen v1)

**Critic PASS.** Zero feature groups on frozen champion; no retrain.

Artifact: `data/validation/v1/h9_ablation_audit.json`

**Largest binary AP drops (gdev-47):** temporal (−0.31), graph (−0.31), app_flags (−0.12). Stamps/velocity smaller — model leans on temporal/graph portable signal.
