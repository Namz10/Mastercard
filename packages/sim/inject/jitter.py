"""±50% jitter on catalog knobs; canary pins exact values."""

from __future__ import annotations

from typing import Any

import numpy as np


def jitter_value(rng: np.random.Generator, value: float, pin: bool) -> float:
    if pin:
        return value
    factor = float(rng.uniform(0.5, 1.5))
    return value * factor


def jitter_signals(rng: np.random.Generator, signals: dict[str, Any], pin: bool) -> dict[str, Any]:
    out = dict(signals)
    if pin:
        return out
    if "fan_in_1h" in out:
        out["fan_in_1h"] = max(0, int(round(jitter_value(rng, float(out["fan_in_1h"]), False))))
    if "fan_out_ttl_hours" in out:
        out["fan_out_ttl_hours"] = max(0.1, jitter_value(rng, float(out["fan_out_ttl_hours"]), False))
    if "smurf_cap_ratio" in out:
        ratio = jitter_value(rng, float(out["smurf_cap_ratio"]), False)
        out["smurf_cap_ratio"] = min(1.0, max(0.01, ratio))
    if "seasoning_days" in out:
        out["seasoning_days"] = max(0, int(round(jitter_value(rng, float(out["seasoning_days"]), False))))
    if "liveness_score" in out:
        live = jitter_value(rng, float(out["liveness_score"]), False)
        out["liveness_score"] = min(1.0, max(0.0, live))
    if "doc_consistency" in out:
        doc = jitter_value(rng, float(out["doc_consistency"]), False)
        out["doc_consistency"] = min(1.0, max(0.0, doc))
    if "pause_ms" in out:
        out["pause_ms"] = max(0, int(round(jitter_value(rng, float(out["pause_ms"]), False))))
    if "urgency_pressure" in out:
        urg = jitter_value(rng, float(out["urgency_pressure"]), False)
        out["urgency_pressure"] = min(1.0, max(0.0, urg))
    return out


def clamp_seasoning(catalog_days: int, sim_days: int) -> tuple[int, bool]:
    cap = max(1, sim_days - 14)
    if catalog_days > cap:
        return cap, True
    return catalog_days, False
