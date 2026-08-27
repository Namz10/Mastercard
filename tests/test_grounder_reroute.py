"""Grounder technique reroute."""

from packages.agents.grounder import apply_technique_reroute


def test_onboarding_kyc_deepfake_t01_becomes_t09():
    spec = {
        "vector_id": "x",
        "technique_id": "T01",
        "lifecycle_stage": "onboarding_kyc",
        "name": "Deepfake Video-KYC",
        "one_liner": "bypass liveness",
        "rail": "upi_like",
    }
    out = apply_technique_reroute(spec, "deepfake kyc onboarding")
    assert out["technique_id"] == "T09"
    assert out["rail"] == "onboarding"


def test_call_center_voice_ato_t02_becomes_t12():
    spec = {
        "vector_id": "x",
        "technique_id": "T02",
        "lifecycle_stage": "account_access_ato",
        "name": "Voice call center",
        "one_liner": "voice clone at call center",
    }
    out = apply_technique_reroute(spec, "call center voice")
    assert out["technique_id"] == "T12"


def test_mule_fan_in_without_kyc_stays_t01():
    spec = {
        "vector_id": "x",
        "technique_id": "T01",
        "lifecycle_stage": "disbursement_mule",
        "name": "Mule fan-in",
        "one_liner": "many senders funnel",
    }
    out = apply_technique_reroute(spec, "mule cash-out")
    assert out["technique_id"] == "T01"
