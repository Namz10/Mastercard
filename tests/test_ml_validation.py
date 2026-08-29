"""Phase 7 §8 — ML validation at realistic scale.

Extends the ticket-level metrics tests with scale-honest assertions. n_customers=20
unless marked `slow`. It is NEVER required that all five fraud families have n_pos>0
at n=20 — that is the ML.6 slow gate instead.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from packages.eval.fit import fit_champion
from packages.sim.ledger import LABEL_FAMILIES
from packages.sim.runner import run_population

FRAUD_FAMILIES = LABEL_FAMILIES - {"normal"}


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-ml")
    return run_population(
        None,
        run_id="ml-val",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


@pytest.fixture(scope="module")
def fitted(pop: dict, tmp_path_factory) -> dict:
    dest = tmp_path_factory.mktemp("models-ml")
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("ml-val", world_seed=42, runs_dir=runs, models_dir=dest)
    return {"dest": dest, "runs": runs, "body": body}


def test_n_pos_key_complete(fitted: dict):
    """ML.1 — n_pos keys must exactly equal LABEL_FAMILIES. This is a completeness
    guard, NOT an assertion that all fraud families are positive at n=20."""
    n_pos = fitted["body"]["metrics"]["n_pos"]
    assert set(n_pos) == set(LABEL_FAMILIES)


def test_app_ablation_with_ge_without(fitted: dict):
    """ML.2 — with APP flags must never be materially worse than without. Uses
    >= - 1e-9, never strict > when n_app == 0."""
    ab = fitted["body"]["metrics"]["app_ablation"]
    with_ap = ab["with_app_flags"]["average_precision"]
    without_ap = ab["without_app_flags"]["average_precision"]

    if without_ap is None or without_ap == "NaN" or not np.isfinite(float(without_ap)):
        # If there is no app fraud to measure, neither AP is comparable.
        assert with_ap is None or with_ap == "NaN" or not np.isfinite(float(with_ap)), (
            "with_app_flags and without_app_flags must agree on non-comparability"
        )
        return

    # When comparable, with-flags must not be worse than without by more than 1e-9.
    assert float(with_ap) >= float(without_ap) - 1e-9, (
        "APP ablation must not report that removing synthetic flags IMPROVED the app-fraud AP"
    )


def test_invoice_ap_finite_when_n_pos_positive(fitted: dict):
    """ML.3 — if invoice_fraud has positive support, its AP must be a finite number."""
    metrics = fitted["body"]["metrics"]
    n_inv = metrics["n_pos"].get("invoice_fraud", 0)
    ap = metrics["ap_by_family"].get("invoice_fraud")
    if n_inv and n_inv > 0:
        assert ap is not None, "invoice_fraud AP must be reported when n_pos>0"
        assert ap != "NaN", "invoice_fraud AP must be finite when n_pos>0"
        assert np.isfinite(float(ap)), "invoice_fraud AP must be finite when n_pos>0"
    # else: AP may legitimately be NaN / absent — not a failure.


def test_y_not_technique_id_exists():
    """ML.5 — the family-y guard tests must keep existing (guard against technique-id y)."""
    import inspect

    from tests.test_eval_fit import test_fit_y_is_family_enum_not_technique

    src = inspect.getsource(test_fit_y_is_family_enum_not_technique)
    assert "TECHNIQUE_IDS" in src or "technique_id" in src


@pytest.mark.slow
def test_n80_all_fraud_families_positive_n_pos():
    """ML.6 — at n_customers=80 every fraud family must have n_pos >= 1."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        runs = Path(td) / "runs"
        models = Path(td) / "models"
        run_population(
            None,
            run_id="n80",
            n_customers=80,
            n_merchants=16,
            sim_days=60,
            world_seed=42,
            pin=True,
            runs_dir=runs,
        )
        body = fit_champion("n80", world_seed=42, runs_dir=runs, models_dir=models)
        n_pos = body["metrics"]["n_pos"]
        for fam in FRAUD_FAMILIES:
            assert n_pos.get(fam, 0) >= 1, f"{fam} must have n_pos>=1 at n=80"


def test_fraud_families_are_subset_of_labels():
    """Sanity — the fraud set used here is exactly the non-normal families."""
    assert FRAUD_FAMILIES == LABEL_FAMILIES - {"normal"}
    assert len(FRAUD_FAMILIES) == 5
