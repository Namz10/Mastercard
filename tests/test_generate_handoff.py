"""Step 10 — Generate handoff tests."""

import pytest

from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.catalog.query import list_generate_eligible
from packages.sim.runner import run_canary, run_population


@pytest.fixture()
def db():
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_population_one_open_row_drives_injector(db):
    eligible = list_generate_eligible(db)
    assert len(eligible) >= 1
    result = run_population(db, vector_id="t13-upi-impersonation-app", run_id="test-pop")
    assert result["mode"] == "population"
    assert result["vector_id"] == "t13-upi-impersonation-app"
    assert result["injector_id"] == "app_session"
    assert result["simulatable_signals"]["call_active_flag"] is True
    inj = result["injections"][0]
    assert inj["ledger_event"]["schema"] == "gff.txn.v1"
    assert inj["ledger_event"]["features_auth"]["call_active_flag"] is True


def test_canary_fincen_campaign_chain(db):
    result = run_canary(db, campaign_id="fincen-fin-2024-alert004", run_id="test-canary")
    assert result["mode"] == "canary"
    assert result["campaign_id"] == "fincen-fin-2024-alert004"
    assert result["event_count"] == 4
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
