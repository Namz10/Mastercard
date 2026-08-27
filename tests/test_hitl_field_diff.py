"""HITL field_diff payload."""

from packages.agents.librarian_db import hitl_payload_for_spec, spec_field_diff


def test_field_diff_populated_when_nearest_spec_differs():
    proposed = {
        "vector_id": "new-v",
        "technique_id": "T09",
        "name": "Deepfake Video-KYC",
        "one_liner": "bypass liveness",
        "rail": "onboarding",
    }
    nearest = {
        "vector_id": "cat-v",
        "technique_id": "T01",
        "name": "Mule fan-in",
        "one_liner": "many senders",
        "rail": "upi_like",
    }
    diff = spec_field_diff(proposed, nearest)
    assert diff.get("technique_id") == {"proposed": "T09", "existing": "T01"}
    payload = hitl_payload_for_spec(proposed, nearest_technique="T01", nearest_spec=nearest)
    assert payload["field_diff"]["technique_id"]["proposed"] == "T09"


def test_field_diff_empty_when_no_nearest():
    proposed = {"vector_id": "x", "technique_id": "T01", "name": "n", "one_liner": "o"}
    payload = hitl_payload_for_spec(proposed, nearest_technique="", nearest_spec=None)
    assert payload["field_diff"] == {}
