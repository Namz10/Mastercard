"""HITL dedupe helpers."""

from packages.agents.librarian_db import dedupe_atlas_rows, proposal_dedupe_key


def test_proposal_dedupe_key_normalizes():
    key = proposal_dedupe_key(
        {"technique_id": "t09", "name": "  Deepfake VKYC  ", "rail": "Onboarding"}
    )
    assert key == ("T09", "deepfake vkyc", "onboarding")


def test_dedupe_atlas_rows_keeps_newest_first():
    class Row:
        def __init__(self, vector_id: str, spec: dict):
            self.vector_id = vector_id
            self.spec = spec

    rows = [
        Row("new", {"technique_id": "T09", "name": "Same attack", "rail": "onboarding"}),
        Row("old", {"technique_id": "T09", "name": "Same attack", "rail": "onboarding"}),
        Row("other", {"technique_id": "T01", "name": "Mule", "rail": "upi_like"}),
    ]
    out = dedupe_atlas_rows(rows)
    assert [r.vector_id for r in out] == ["new", "other"]
