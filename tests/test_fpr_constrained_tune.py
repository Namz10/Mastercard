"""RED / regression tests for FPR-constrained tuning (H5c)."""

from __future__ import annotations

import inspect

import pytest

from packages.eval import fit as fit_mod
from packages.eval.fit import _build_hgb_kwargs, load_recipe


def test_build_hgb_kwargs_passes_expanded_hgb_params():
    recipe = load_recipe()
    kw = _build_hgb_kwargs(
        {
            "max_leaf_nodes": 31,
            "max_iter": 100,
            "learning_rate": 0.05,
            "min_samples_leaf": 15,
            "l2_regularization": 0.1,
            "max_bins": 128,
        },
        recipe,
    )
    assert kw["max_leaf_nodes"] == 31
    assert "max_depth" not in kw
    assert kw["min_samples_leaf"] == 15
    assert kw["l2_regularization"] == 0.1
    assert kw["max_bins"] == 128
    assert kw["early_stopping"] is False


def test_build_hgb_kwargs_falls_back_to_max_depth():
    recipe = load_recipe()
    kw = _build_hgb_kwargs({"max_depth": 4, "max_iter": 80, "learning_rate": 0.08}, recipe)
    assert kw["max_depth"] == 4
    assert "max_leaf_nodes" not in kw


def test_fit_champion_uses_genuine_fpr_threshold_helper():
    src = inspect.getsource(fit_mod.fit_champion)
    assert "_detect_thr_genuine_fpr" in src


def test_tune_champion_uses_genuine_fpr_threshold_helper():
    src = inspect.getsource(fit_mod.tune_champion)
    assert "_detect_thr_genuine_fpr" in src
    assert "inner_fit" in src
    assert "inner_val" in src
    assert "gdev" not in src.lower() or "never" in src.lower() or "refuses" in src


def test_tune_champion_expanded_search_space_in_source():
    src = inspect.getsource(fit_mod.tune_champion)
    for token in ("min_samples_leaf", "l2_regularization", "max_bins"):
        assert token in src
