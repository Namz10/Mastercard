"""Identify P0: provenance, abstain, confidence, status, pgvector dedup."""

from __future__ import annotations

import pytest

from packages.agents.llm.extraction import extract_from_document, rule_based_extract
from packages.agents.nodes.extractor import _body_for_url
from packages.agents.tier_scorer import score_spec_sources
from packages.catalog.status import IllegalStatusTransition, assert_legal_transition
from packages.osint.fixtures import FIXTURE_FILES
from packages.osint.vector_store import max_catalog_similarity, register_catalog_embedding


def test_rbi_fixture_is_not_fincen(postgres_required):
    rbi_url = FIXTURE_FILES["rbi_note"][1]
    fincen_url = FIXTURE_FILES["fincen_alert004"][1]
    rbi_text, _ = _body_for_url(rbi_url)
    fincen_text, _ = _body_for_url(fincen_url)
    assert "FIN-2024-Alert004" not in rbi_text
    assert "FIN-2024-Alert004" in fincen_text
    assert "Reserve Bank of India" in rbi_text


def test_unknown_offline_url_does_not_use_fincen():
    with pytest.raises(ValueError, match="no_fixture_for_url"):
        _body_for_url("https://www.fincen.gov/not-a-fixture")


def test_rule_based_abstains_on_weak_text():
    assert (
        rule_based_extract("hello world weather report", "https://www.fincen.gov/x", "fincen.gov")
        is None
    )


def test_extract_weak_article_abstains():
    spec = extract_from_document("irrelevant prose about sports", "https://www.fincen.gov/x", "fincen.gov")
    assert spec["extraction_source"] == "abstain"
    assert spec.get("technique_id") is None


def test_fincen_rules_extract_t09():
    from packages.osint.extract import extract_fixture_text

    doc = extract_fixture_text("fincen_alert004")
    spec = rule_based_extract(doc.text, doc.url, "fincen.gov")
    assert spec is not None
    assert spec["technique_id"] == "T09"
    assert spec["status"] == "proposed"


def test_confidence_two_urls_same_org_not_confirmed():
    spec = {
        "source_urls": [
            "https://www.feedzai.com/a",
            "https://www.feedzai.com/b",
        ],
        "source_tier": 5,
        "confidence_level": "reported-unverified",
    }
    scored = score_spec_sources(spec)
    assert scored["confidence_level"] == "reported-unverified"


def test_confidence_two_orgs_tier3_confirmed():
    spec = {
        "source_urls": [
            "https://www.feedzai.com/a",
            "https://www.deloitte.com/b",
        ]
    }
    scored = score_spec_sources(spec)
    assert scored["confidence_level"] == "confirmed"


def test_confidence_tier1_confirmed():
    spec = {"source_urls": ["https://www.fincen.gov/news/x"]}
    scored = score_spec_sources(spec)
    assert scored["source_tier"] == 1
    assert scored["confidence_level"] == "confirmed"


def test_status_matrix_legal():
    assert_legal_transition("proposed", "open")
    assert_legal_transition("defending", "open")
    with pytest.raises(IllegalStatusTransition):
        assert_legal_transition("defending", "proposed")
    with pytest.raises(IllegalStatusTransition):
        assert_legal_transition("solved", "open")


def test_pgvector_catalog_similarity(postgres_required):
    register_catalog_embedding("Deepfake VKYC liveness bypass", "onboarding", "T09", vector_id="sim-t09")
    same = max_catalog_similarity("Deepfake VKYC liveness bypass", "onboarding", "T09")
    assert same >= 0.99
    other = max_catalog_similarity("Completely different invoice GST fraud", "wire", "T24")
    assert other < 0.92
