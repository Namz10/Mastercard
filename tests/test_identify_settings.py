"""Identify settings defaults."""

from packages.agents.settings import IdentifySettings


def test_defaults_are_unlimited(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    monkeypatch.setenv("IDENTIFY_MAX_DOCS", "0")
    monkeypatch.setenv("IDENTIFY_MAX_HITL", "0")
    monkeypatch.setenv("IDENTIFY_MAX_CANDIDATES", "0")
    s = IdentifySettings()
    assert s.identify_live_search is False
    assert s.identify_max_docs == 0
    assert s.identify_max_hitl == 0
    assert s.identify_max_candidates == 0
    assert s.identify_catalog_queries_enabled is False


def test_env_override(monkeypatch):
    monkeypatch.setenv("IDENTIFY_MAX_DOCS", "2")
    monkeypatch.setenv("IDENTIFY_MAX_HITL", "1")
    s = IdentifySettings()
    assert s.identify_max_docs == 2
    assert s.identify_max_hitl == 1
