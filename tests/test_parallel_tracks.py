"""Tests for H5d/H7/H9 parallel tracks."""

from __future__ import annotations

import inspect

from packages.eval import ablation_audit, pareto_operational, recursive_loop_m


def test_pareto_operational_has_write_report():
    assert hasattr(pareto_operational, "write_operational_report")
    assert "max_recall_at_genuine_fpr" in inspect.getsource(pareto_operational.score_at_pareto_ops)


def test_recursive_loop_m_gdev_only():
    src = inspect.getsource(recursive_loop_m.diagnose_weakness)
    assert "gdev" in src.lower() or "run_id" in src
    assert recursive_loop_m.MAX_ROUNDS == 3


def test_ablation_audit_groups():
    assert "app_flags" in ablation_audit.ABLATION_GROUPS
    assert "stamps" in ablation_audit.ABLATION_GROUPS
