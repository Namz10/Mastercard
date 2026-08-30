"""Unit tests for H7 recursive Loop M diagnostic (round 1)."""

from __future__ import annotations

import inspect

import pytest

from packages.eval import recursive_loop_m as rlm
from packages.eval.recursive_loop_m import _pick_weakest_family


def test_diagnose_weakness_source_gdev_only():
    src = inspect.getsource(rlm.diagnose_weakness)
    assert "fit_champion" not in src
    assert "mine_hard_negatives" not in src
    assert "no_blind_top_k_mining" in src
    assert "gdev_only" in src or "promote_gate" in src
    assert rlm.MAX_ROUNDS == 3


def test_diagnose_weakness_h6_d_filter():
    src = inspect.getsource(rlm.diagnose_weakness)
    assert "is_new_payee" in src
    assert rlm.HN_EXCLUDE_NEW_PAYEE is True
    assert "fp_normals_excl_new_payee" in src
    assert "no_blind_top_k_mining" in src


def test_pick_weakest_respects_n_pos_floor():
    ap_by = {
        "app_fraud": 0.99,
        "ato": 0.40,
        "identity_burst": 0.35,
        "invoice_fraud": 0.99,
        "mule": 0.98,
    }
    n_pos = {
        "app_fraud": 100,
        "ato": 10,
        "identity_burst": 500,
        "invoice_fraud": 80,
        "mule": 200,
    }
    weakest, reason = _pick_weakest_family(ap_by, n_pos, n_pos_floor=30)
    assert weakest == "identity_burst"
    assert "n_pos>=30" in reason
    assert "ato" not in reason


def test_pick_weakest_fallback_when_all_below_floor():
    ap_by = {"ato": 0.2, "identity_burst": 0.9}
    n_pos = {"ato": 5, "identity_burst": 8}
    weakest, reason = _pick_weakest_family(ap_by, n_pos, n_pos_floor=30)
    assert weakest == "ato"
    assert "fallback" in reason


def test_intervention_for_identity_burst():
    steps = rlm._intervention_for("identity_burst")
    assert any("identity_burst" in s or "Loop M" in s for s in steps)
    assert any("is_new_payee" in s for s in steps)
