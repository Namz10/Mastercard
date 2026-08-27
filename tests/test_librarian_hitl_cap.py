"""Librarian HITL cap."""

from packages.agents.nodes.librarian import librarian
from packages.agents.state import empty_identify_state


def _spec(i: int):
    return {
        "vector_id": f"v{i}",
        "technique_id": "T01",
        "name": f"spec{i}",
        "one_liner": "x",
        "category": 1,
        "rail": "upi_like",
        "lifecycle_stage": "disbursement_mule",
        "genai_modality": "bot",
        "social_surface": "none",
        "actor_type": "consumer",
        "economic_class": "mule",
        "is_authorized_push": False,
        "generate_mode": "name_only",
        "source_tier": 1,
        "confidence_level": "confirmed",
        "vector_class": "network_footprint",
        "source_urls": ["https://www.fincen.gov/a"],
        "status": "proposed",
    }


def test_librarian_hitl_cap_when_set(monkeypatch, postgres_required):
    monkeypatch.setenv("IDENTIFY_MAX_HITL", "1")
    state = empty_identify_state()
    state["proposed_specs"] = [_spec(1), _spec(2), _spec(3)]
    out = librarian(state)
    assert len(out["hitl_queue"]) == 1


def test_librarian_unlimited_hitl(monkeypatch, postgres_required):
    monkeypatch.setenv("IDENTIFY_MAX_HITL", "0")
    state = empty_identify_state()
    state["proposed_specs"] = [_spec(1), _spec(2), _spec(3)]
    out = librarian(state)
    assert len(out["hitl_queue"]) == 3
