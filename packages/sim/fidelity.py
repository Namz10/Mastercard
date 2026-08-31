"""PSI vs this run's priors + anti-stub recompute (Plan 08 Phase D)."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.features import parse_ts
from packages.sim.priors import WorldPriors, sample_amount_minor, sample_hour

# Frozen fixture thresholds (not KS p > 0.05).
PSI_AMOUNT_MAX = 0.25
PSI_HOUR_MAX = 0.35
FRAUD_RATE_MIN = 0.005
FRAUD_RATE_MAX = 0.035
MULE_FAN_IN_MEDIAN_MIN = 5

AMOUNT_LOG_EDGES = np.array([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 6.0])


def psi(expected: np.ndarray, actual: np.ndarray, eps: float = 1e-4) -> float:
    e = np.clip(expected.astype(float), eps, None)
    a = np.clip(actual.astype(float), eps, None)
    e = e / e.sum()
    a = a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def _hour_weights(priors: WorldPriors) -> np.ndarray:
    w = np.ones(24, dtype=np.float64)
    for h in priors.hour_of_day.peak_hours:
        w[h] += 4.0
    return w / w.sum()


def amount_hist_rupees(rupees: np.ndarray) -> np.ndarray:
    logs = np.log10(np.clip(rupees, 1.0, None))
    hist, _ = np.histogram(logs, bins=AMOUNT_LOG_EDGES)
    return hist.astype(float)


def expected_amount_hist(priors: WorldPriors, n: int, rng: np.random.Generator) -> np.ndarray:
    cats = [
        c
        for c in ("grocery", "fast_food", "utilities", "fuel", "telecom", "p2p")
        if c in priors.categories
    ]
    samples = []
    for _ in range(max(n, 100)):
        cat = cats[int(rng.integers(0, len(cats)))]
        samples.append(sample_amount_minor(rng, priors, cat) / 100.0)
    return amount_hist_rupees(np.array(samples, dtype=float))


def psi_amount_normal(events: list[dict[str, Any]], priors: WorldPriors, rng: np.random.Generator) -> float:
    rupees = np.array(
        [e["amount_minor"] / 100.0 for e in events if e["label_family"] == "normal"],
        dtype=float,
    )
    if len(rupees) < 30:
        return 0.0
    actual = amount_hist_rupees(rupees)
    expected = expected_amount_hist(priors, len(rupees), rng)
    return psi(expected, actual)


def psi_hour(events: list[dict[str, Any]], priors: WorldPriors) -> float:
    hours = [parse_ts(e["event_ts"]).hour for e in events if e["label_family"] == "normal"]
    if len(hours) < 30:
        return 0.0
    actual = np.bincount(hours, minlength=24).astype(float)
    expected = _hour_weights(priors) * len(hours)
    return psi(expected, actual)


def fraud_rate(events: list[dict[str, Any]]) -> float:
    n = len(events)
    if n == 0:
        return 0.0
    fraud = sum(1 for e in events if e["label_family"] != "normal")
    return fraud / n


def recompute_fan_in_1h(events: list[dict[str, Any]]) -> dict[str, int]:
    """Independent of features_auth: count prior inbound to payee in the last hour."""
    ordered = sorted(events, key=lambda e: (e["event_ts"], e["event_id"]))
    inbound: dict[str, list] = defaultdict(list)
    out: dict[str, int] = {}
    hour = timedelta(hours=1)
    for ev in ordered:
        ts = parse_ts(ev["event_ts"])
        payee = ev["party_ids"]["payee"]
        cutoff = ts - hour
        prior = [t for t in inbound[payee] if t >= cutoff]
        out[ev["event_id"]] = len(prior)
        inbound[payee] = prior + [ts]
    return out


def mule_inbound_fan_in_values(events: list[dict[str, Any]]) -> list[int]:
    return [
        int(e["features_auth"]["fan_in_1h"])
        for e in events
        if e["label_family"] == "mule" and str(e["party_ids"]["payee"]).startswith("VID-SIM-U-")
    ]


def evaluate_fidelity(
    events: list[dict[str, Any]],
    priors: WorldPriors,
    *,
    rng: np.random.Generator | None = None,
    require_mix_rate: bool = True,
) -> dict[str, Any]:
    rng = rng or np.random.default_rng(42)
    psi_a = psi_amount_normal(events, priors, rng)
    psi_h = psi_hour(events, priors)
    rate = fraud_rate(events)
    recomputed = recompute_fan_in_1h(events)
    mismatches = 0
    for ev in events:
        stored = int(ev["features_auth"]["fan_in_1h"])
        if stored != recomputed[ev["event_id"]]:
            mismatches += 1
    mule_vals = mule_inbound_fan_in_values(events)
    mule_median = float(np.median(mule_vals)) if mule_vals else 0.0
    reasons: list[str] = []
    if psi_a > PSI_AMOUNT_MAX:
        reasons.append(f"psi_amount={psi_a:.3f}>{PSI_AMOUNT_MAX}")
    if psi_h > PSI_HOUR_MAX:
        reasons.append(f"psi_hour={psi_h:.3f}>{PSI_HOUR_MAX}")
    if require_mix_rate and not (FRAUD_RATE_MIN <= rate <= FRAUD_RATE_MAX):
        reasons.append(f"fraud_rate={rate:.4f} outside [{FRAUD_RATE_MIN},{FRAUD_RATE_MAX}]")
    # mule_fan_in_median is informational on glass — never blocks booth scoring.
    if mismatches:
        reasons.append(f"fan_in_recompute_mismatches={mismatches}")
    return {
        "pass": not reasons,
        "psi_amount": psi_a,
        "psi_hour": psi_h,
        "fraud_rate": rate,
        "mule_fan_in_median": mule_median,
        "fan_in_mismatches": mismatches,
        "reasons": reasons,
    }
