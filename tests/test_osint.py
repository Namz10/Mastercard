"""OSINT package tests (Batch 2 Step 4)."""

import pytest

from packages.osint.allowlist import (
    FORBIDDEN_QUERY_TERMS,
    is_allowlisted_url,
    tier_for_url,
    validate_search_query,
)
from packages.osint.collect import collect_candidate_urls
from packages.osint.extract import extract_fixture_text
from packages.osint.fixtures import load_fixture_documents
from packages.osint.search import tavily_search
from packages.osint.settings import get_osint_settings


def test_fixtures_load_without_api_key():
    docs = load_fixture_documents()
    assert len(docs) >= 2
    for doc in docs:
        assert doc.text
        assert is_allowlisted_url(doc.url)
        assert tier_for_url(doc.url) <= 2 or doc.source_domain == "rbi.org.in"


def test_extract_fixture_fincen():
    doc = extract_fixture_text("fincen_alert004")
    assert "deepfake" in doc.text.lower()
    assert doc.extractor == "fixture"


def test_airplane_collect_uses_fixtures(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    urls = collect_candidate_urls()
    assert len(urls) >= 2
    assert all(is_allowlisted_url(u["url"]) for u in urls)


def test_forbidden_query_rejected():
    for term in FORBIDDEN_QUERY_TERMS:
        with pytest.raises(ValueError):
            validate_search_query(f"payment fraud {term}")


@pytest.mark.skipif(not get_osint_settings().tavily_api_key, reason="TAVILY_API_KEY not set in .env")
def test_live_tavily_search_returns_allowlisted_url():
    results = tavily_search(max_results=3)
    assert len(results) >= 1
    assert all(is_allowlisted_url(r.url) for r in results)
