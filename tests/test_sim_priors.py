"""Phase A — WorldPriors + lognormal sampling."""

from __future__ import annotations

import numpy as np
import pytest

from packages.sim.priors import (
    TICKET_STAT_MEAN,
    WorldPriors,
    clamp_amount_minor,
    expected_mean_rupees,
    load_priors,
    rupees_to_minor,
    sample_amount_minor,
    sample_hour,
)


def test_seed_priors_validate():
    priors = load_priors()
    assert priors.ticket_stat == TICKET_STAT_MEAN
    assert priors.ticket_stat != "median"
    assert "median" not in priors.ticket_stat
    assert priors.hour_of_day.kind == "assumption"
    assert priors.categories["grocery"].mean_rupees == 214
    assert priors.categories["fast_food"].mean_rupees == 113
    assert priors.categories["utilities"].mean_rupees == 1345
    assert priors.caps.txn_max_minor == 10_000_000
    assert priors.provenance[0].source_url.startswith("https://")


def test_ticket_stat_rejects_median():
    priors = load_priors()
    payload = priors.model_dump()
    payload["ticket_stat"] = "median"
    with pytest.raises(Exception):
        WorldPriors.model_validate(payload)


def test_lognormal_mean_matches_category_not_uniform():
    priors = load_priors()
    rng = np.random.default_rng(42)
    samples = [sample_amount_minor(rng, priors, "grocery") / 100.0 for _ in range(8000)]
    mean = float(np.mean(samples))
    target = expected_mean_rupees(priors, "grocery")
    assert abs(mean - target) / target < 0.12

    uniform = np.random.default_rng(42).uniform(1, 1e5, size=8000)
    assert abs(float(np.mean(uniform)) - target) / target > 5


def test_amount_clamped_to_caps():
    priors = load_priors()
    huge = rupees_to_minor(1e12)
    clamped = clamp_amount_minor(huge, priors.caps)
    assert clamped == priors.caps.txn_max_minor
    tiny = clamp_amount_minor(1, priors.caps)
    assert tiny == priors.caps.txn_min_minor


def test_hour_assumption_bimodal_mass():
    priors = load_priors()
    rng = np.random.default_rng(0)
    hours = [sample_hour(rng, priors) for _ in range(4000)]
    peak = set(priors.hour_of_day.peak_hours)
    peak_share = sum(h in peak for h in hours) / len(hours)
    assert peak_share > 0.45
    assert all(0 <= h <= 23 for h in hours)


def test_sample_reproducible_with_seed():
    priors = load_priors()
    a = [sample_amount_minor(np.random.default_rng(7), priors, "p2p") for _ in range(20)]
    b = [sample_amount_minor(np.random.default_rng(7), priors, "p2p") for _ in range(20)]
    assert a == b
