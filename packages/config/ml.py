"""Single settings loader for ML feature flags & resource bounds (Phase 6 hardening).

All flags are read from models/features.json through this one loader. Every access
defaults defensively to OFF / safe values — a missing or malformed flag never raises
and never turns a feature on by accident.
"""

from __future__ import annotations

from typing import Any


def _bool_flag(block: dict[str, Any], key: str, default: bool = False) -> bool:
    value = block.get(key, default)
    return value if isinstance(value, bool) else default


def _try_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _try_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_ml_flags(recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read the feature-flag slice of the recipe (defaults OFF on any problem)."""
    if recipe is None:
        from packages.eval.fit import load_recipe

        recipe = load_recipe()
    iso = recipe.get("isolation_forest") or {}
    cal = recipe.get("calibration") or {}
    opt = recipe.get("optuna") or {}
    return {
        "isolation_forest_enabled_default": _bool_flag(iso, "enabled_default", default=False),
        "iso_p_normal_floor": _try_float(iso.get("p_normal_floor"), 0.95),
        "iso_genuine_notify_rate_abort": _try_float(iso.get("genuine_notify_rate_abort"), 0.05),
        "calibration_stage1_binary": _bool_flag(cal, "stage1_binary", default=False),
        "calibration_stage2_min_n_pos": _try_int(cal.get("stage2_min_n_pos"), 50),
        "ece_n_bins": _try_int(cal.get("ece_n_bins"), 10),
        "optuna_n_trials": _try_int(opt.get("n_trials"), 40),
        "optuna_n_trials_ci": _try_int(opt.get("n_trials_ci"), 10),
        "optuna_timeout_seconds": _try_float(opt.get("timeout_seconds"), 600),
    }


def load_remediation_flags(recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Phase 8 remediation-orchestrator flags (defaults OFF on any problem).

    ``remediation.orchestrator_enabled`` is the kill switch: when off,
    ``make defend-remediate`` is a no-op and the manual per-family
    ``POST /defend/loop-t/mine`` flow keeps working untouched.

    ``DEFEND_REMEDIATE_ORCHESTRATOR`` is a CI-only escape valve that forces the
    flag off (``=0``) or on (``=1``) without editing the frozen recipe.
    """
    import os

    if recipe is None:
        from packages.eval.fit import load_recipe

        recipe = load_recipe()
    rem = recipe.get("remediation") or {}
    env_val = os.environ.get("DEFEND_REMEDIATE_ORCHESTRATOR", "").strip().lower()
    if env_val == "1":
        enabled = True
    elif env_val == "0":
        enabled = False
    else:
        enabled = _bool_flag(rem, "orchestrator_enabled", default=False)
    return {
        "orchestrator_enabled": enabled,
        "llm_timeout_seconds": _try_float(rem.get("llm_timeout_seconds"), 5.0),
        "reviewer_capacity_hint": _try_int(rem.get("reviewer_capacity_hint"), 3),
        "ledger_path": str(_try_str(rem.get("ledger_path"), os.environ.get("DEFEND_REMEDIATE_LEDGER", ""))),
    }


def _try_str(value: Any, default: str) -> str:
    return str(value) if isinstance(value, str) and str(value).strip() else default


def select_n_trials(
    flags: dict[str, Any] | None = None,
    *,
    ci: bool = False,
    default: int = 40,
) -> int:
    """One constant for n_trials, environment-selected (real vs CI) — never two hardcodes."""
    flags = flags or load_ml_flags()
    return int(flags["optuna_n_trials_ci"] if ci else flags["optuna_n_trials"]) or default
