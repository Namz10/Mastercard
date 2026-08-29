"""Tests for genuine-FPR Pareto envelope."""

from __future__ import annotations

import numpy as np

from packages.eval.fpr_pareto import max_recall_at_genuine_fpr


def test_max_recall_at_genuine_fpr_respects_cap():
    scores = np.array([0.9, 0.8, 0.4, 0.3, 0.1, 0.05])
    y_bin = np.array([1, 1, 0, 0, 0, 0])
    normal_mask = y_bin == 0
    pt = max_recall_at_genuine_fpr(scores, y_bin, normal_mask, fpr_target=0.5)
    assert pt["genuine_fp"] <= 0.5 + 1e-9
    assert pt["recall"] >= 0.0


def test_max_recall_at_genuine_fpr_finds_best_recall_under_cap():
    scores = np.array([0.95, 0.85, 0.55, 0.45, 0.2, 0.1])
    y_bin = np.array([1, 1, 1, 0, 0, 0])
    normal_mask = y_bin == 0
    pt = max_recall_at_genuine_fpr(scores, y_bin, normal_mask, fpr_target=0.34)
    assert pt["genuine_fp"] <= 0.34 + 1e-9
    assert pt["recall"] == 1.0
