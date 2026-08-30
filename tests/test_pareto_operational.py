"""RED / minimal tests for operational Pareto scoring (H5d)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from packages.eval.pareto_operational import (
    DEFAULT_FPR_TARGETS,
    score_at_pareto_ops,
    write_operational_report,
)


def test_score_at_pareto_ops_structure(monkeypatch):
    scores = np.array([0.95, 0.85, 0.55, 0.45, 0.2, 0.1, 0.05, 0.02])
    y = ["app_fraud", "mule", "normal", "normal", "normal", "normal", "ato", "normal"]

    class FakeChamp:
        op_threshold = 0.5
        detect_thr = 0.5
        raw_columns = ["x"]
        encoder = None
        cat_cols: list[str] = []
        classes = ["normal", "app_fraud", "mule", "ato"]
        model = object()
        pmap_calibrators = None

    monkeypatch.setattr(
        "packages.eval.pareto_operational.load_champion",
        lambda *_a, **_k: FakeChamp(),
    )
    monkeypatch.setattr(
        "packages.eval.pareto_operational.run_paths",
        lambda *_a, **_k: {"train": Path("t"), "split": Path("s")},
    )
    monkeypatch.setattr(
        "packages.eval.pareto_operational.pd.read_parquet",
        lambda *_a, **_k: object(),
    )
    monkeypatch.setattr(
        "packages.eval.pareto_operational._score_rows",
        lambda *_a, **_k: (scores, __import__("pandas").Series(y)),
    )

    out = score_at_pareto_ops("v1-gtest-48", "v1-train-46__loopm-train")
    assert out["run_id"] == "v1-gtest-48"
    assert out["model_run_id"] == "v1-train-46__loopm-train"
    assert set(out["pareto_ops"]) == {f"{t:g}" for t in DEFAULT_FPR_TARGETS}
    for cap in out["pareto_ops"].values():
        assert "recall" in cap and "genuine_fp" in cap
        assert "family_recall" in cap and "cost_sketch_proxy" in cap
    assert "default_op" in out and "genuine_fp" in out["default_op"]


def test_pareto_ops_respect_fpr_cap(monkeypatch):
    rng = np.random.default_rng(0)
    n_norm, n_fraud = 400, 40
    scores = np.concatenate([rng.uniform(0.6, 1.0, n_fraud), rng.uniform(0.0, 0.4, n_norm)])
    y = ["app_fraud"] * n_fraud + ["normal"] * n_norm

    class FakeChamp:
        op_threshold = 0.01
        detect_thr = 0.01
        raw_columns = ["x"]
        encoder = None
        cat_cols: list[str] = []
        classes = ["normal", "app_fraud"]
        model = object()
        pmap_calibrators = None

    monkeypatch.setattr("packages.eval.pareto_operational.load_champion", lambda *_a, **_k: FakeChamp())
    monkeypatch.setattr("packages.eval.pareto_operational.run_paths", lambda *_a, **_k: {"train": Path("t"), "split": Path("s")})
    monkeypatch.setattr("packages.eval.pareto_operational.pd.read_parquet", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "packages.eval.pareto_operational._score_rows",
        lambda *_a, **_k: (scores, __import__("pandas").Series(y)),
    )

    out = score_at_pareto_ops("v1-gdev-47", "v1-train-46__loopm-train", fpr_targets=(0.01,))
    cap = out["pareto_ops"]["0.01"]
    assert cap["genuine_fp"] <= 0.01 + 1e-9
    assert cap["recall"] >= 0.0


def test_write_operational_report(tmp_path: Path):
    fake = {
        "run_id": "v1-gtest-48",
        "model_run_id": "v1-train-46__loopm-train",
        "pareto_ops": {"0.01": {"recall": 0.99, "genuine_fp": 0.01}},
        "default_op": {"recall": 0.95, "genuine_fp": 0.08},
    }
    dest = tmp_path / "pareto_operational_v1.json"
    with patch("packages.eval.pareto_operational.score_at_pareto_ops", return_value=fake):
        path = write_operational_report(
            model_run_id="v1-train-46__loopm-train",
            run_ids=("v1-gdev-47",),
            dest=dest,
        )
    assert path == dest
    body = json.loads(dest.read_text(encoding="utf-8"))
    assert body["model_run_id"] == "v1-train-46__loopm-train"
    assert "v1-gdev-47" in body["worlds"]
