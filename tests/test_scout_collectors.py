"""Scout multi-collector tests."""

import pytest

from packages.agents.nodes.scout import scout
from packages.agents.state import empty_identify_state
from packages.osint.allowlist import validate_search_query


def test_scout_without_tavily_key_still_merges_rss_and_arxiv(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "true")
    monkeypatch.setenv("IDENTIFY_TAVILY_ENABLED", "true")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    monkeypatch.setattr(
        "packages.osint.rss.rss_candidate_urls",
        lambda **k: [{"url": "https://www.fincen.gov/a", "source_domain": "fincen.gov", "snippet": "x", "source": "rss:fincen", "source_tier": 1}],
    )
    monkeypatch.setattr(
        "packages.osint.arxiv_api.arxiv_api_candidate_urls",
        lambda **k: [{"url": "https://arxiv.org/abs/1", "source_domain": "arxiv.org", "snippet": "y", "source": "arxiv_api", "source_tier": 2}],
    )
    monkeypatch.setattr("packages.osint.gnews_rss.gnews_candidate_urls", lambda **k: [])

    state = scout(empty_identify_state(topic="fraud"))
    assert len(state["candidate_urls"]) >= 2
    assert any("scout_tavily:skipped" in e for e in state["errors"])


def test_scout_tavily_exception_is_non_fatal(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    def boom(*a, **k):
        raise RuntimeError("tavily down")

    monkeypatch.setattr("packages.osint.search.search_candidate_urls", boom)
    monkeypatch.setattr(
        "packages.osint.rss.rss_candidate_urls",
        lambda **k: [{"url": "https://www.ftc.gov/a", "source_domain": "ftc.gov", "snippet": "x", "source": "rss:ftc", "source_tier": 1}],
    )
    monkeypatch.setattr("packages.osint.arxiv_api.arxiv_api_candidate_urls", lambda **k: [])
    monkeypatch.setattr("packages.osint.gnews_rss.gnews_candidate_urls", lambda **k: [])

    state = scout(empty_identify_state(topic="fraud"))
    assert state["candidate_urls"]
    assert any("scout_tavily:" in e for e in state["errors"])


def test_forbidden_query_still_rejected():
    with pytest.raises(ValueError):
        validate_search_query("payment fraud dark web")


def test_airplane_ignores_live_collectors(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    state = scout(empty_identify_state())
    assert len(state["candidate_urls"]) >= 2
