"""Generate API / runner contract (Plan 08 population + canary)."""

import pytest

from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.catalog.query import list_generate_eligible
from packages.sim.export import assert_train_schema
from packages.sim.runner import run_canary, run_population


@pytest.fixture()
def db(tmp_path):
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session, tmp_path
    finally:
        session.close()


def test_population_t13_no_signals_in_body(db):
    session, tmp = db
    eligible = list_generate_eligible(session)
    assert len(eligible) >= 1
    result = run_population(
        session,
        vector_id="t13-upi-impersonation-app",
        run_id="test-pop",
        n_customers=20,
        n_merchants=8,
        sim_days=40,
        world_seed=42,
        pin=True,
        runs_dir=tmp / "runs",
    )
    assert result["mode"] == "population"
    assert result["vector_id"] == "t13-upi-impersonation-app"
    assert result["injector_id"] == "app_session"
    assert result["event_count"] > 1
    assert "simulatable_signals" not in result
    assert "injections" not in result
    assert result["counts_by_label_family"].get("app_fraud", 0) >= 3
    extras = set(result["counts_by_label_family"]) - {"normal", "app_fraud"}
    assert not extras
    assert_train_schema(result["parquet_path"])


def test_canary_fincen_campaign_chain(db):
    session, tmp = db
    result = run_canary(
        session,
        campaign_id="fincen-fin-2024-alert004",
        run_id="test-canary",
        n_customers=12,
        n_merchants=6,
        sim_days=180,
        world_seed=42,
        runs_dir=tmp / "runs",
    )
    assert result["mode"] == "canary"
    assert result["campaign_id"] == "fincen-fin-2024-alert004"
    assert result["event_count"] > 4
    stages = [s["lifecycle_stage"] for s in result["lifecycle_stages_logged"]]
    assert stages == [
        "onboarding_kyc",
        "account_access_ato",
        "payment_initiation",
        "disbursement_mule",
    ]
    vector_ids = [s["vector_id"] for s in result["lifecycle_stages_logged"]]
    assert vector_ids == [
        "t09-deepfake-vkyc",
        "t11-identity-farming",
        "t13-upi-impersonation-app",
        "t02-mule-fan-out",
    ]
    parties = {s["party_id"] for s in result["lifecycle_stages_logged"]}
    assert len(parties) == 1
    assert "simulatable_signals" not in result
