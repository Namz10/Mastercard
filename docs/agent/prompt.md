# Agent prompt (user overrides)

**Standing:** PLAN → CRITIC → RED → implement → pytest → JUDGE. Never skip gates.

**Session priority (2026-08-29):** Run **H5 FPR-constrained optimization** and **H6 failure diagnosis** in parallel this cycle. Success = **Pareto improvement**, not lower FPR alone.

**Loop:** Loop M → FPR op → gtest-49 → weakest family → diagnose → intervention → critic → 46/47/48/49 → ACCEPT on full gate table.
