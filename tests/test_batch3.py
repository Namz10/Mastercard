"""Batch 3 — Scout through HITL pipeline tests."""

import os

import pytest

from packages.agents.corroborator import apply_corroboration
from packages.agents.grounder import grounder_reject_reason
from packages.agents.identify_graph import run_identify_graph
from packages.agents.nodes.scout import scout
from packages.agents.state import empty_identify_state
from packages.agents.tier_scorer import score_spec_sources
from packages.osint.fixtures import load_fixture_documents
from packages.osint.vector_store import clear_memory_store


@pytest.fixture(autouse=True)
def _clear_vector_memory():
    clear_memory_store()
    yield
    clear_memory_store()


def test_scout_airplane_returns_urls(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    state = scout(empty_identify_state(run_id="scout-test"))
    assert len(state["candidate_urls"]) >= 2


def test_tier_scorer_fincen_confirmed():
    doc = load_fixture_documents()[0]
    spec = {
        "source_urls": [doc.url],
        "source_tier": 5,
        "confidence_level": "reported-unverified",
    }
    scored = score_spec_sources(spec)
    assert scored["source_tier"] == 1
    assert scored["confidence_level"] == "confirmed"


def test_corroborator_human_social_documentary():
    spec = apply_corroboration(
        {
            "technique_id": "T13",
            "genai_modality": "voice",
            "confidence_level": "confirmed",
            "control_bypassed": ["human_callback"],
            "generate_mode": "generate",
            "source_tier": 1,
            "simulator": {"injector_id": "app_session", "param_schema": {}},
            "simulatable_signals": {
                "persuasion_labels": ["x"],
                "call_active_flag": True,
                "copy_paste_payee_flag": True,
                "pause_ms": 0,
                "new_payee": True,
                "urgency_pressure": 0.5,
            },
        }
    )
    assert spec["vector_class"] == "human_social"
    assert spec["corroboration_type"] == "documentary-case"
    assert spec["canary_eligible"] is True


def test_grounder_rejects_buzzword():
    reason = grounder_reject_reason(
        {"name": "GenAI fraud", "rail": "upi_like", "technique_id": "T13"},
        "",
    )
    assert reason == "buzzword_only"


@pytest.mark.skipif(
    os.getenv("IDENTIFY_SKIP_GRAPH_TEST") == "1",
    reason="Skip heavy graph test",
)
def test_identify_graph_airplane_proposes(monkeypatch):
    from unittest.mock import patch

    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    monkeypatch.setenv("QDRANT_DISABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_DISABLED", "true")

    with patch("packages.agents.nodes.librarian.merge_proposed_spec"), patch(
        "packages.agents.nodes.librarian.find_merge_target", return_value=None
    ):
        result = run_identify_graph(run_id="batch3-airplane")

    assert len(result.get("candidate_urls") or []) >= 2
    assert len(result.get("proposed_specs") or []) >= 1
    assert result.get("hitl_required")
