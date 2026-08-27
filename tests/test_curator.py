"""Curator ranker tests (mock LLM)."""

import importlib

from packages.agents.llm.curator import rank_candidates, tier_fallback_rank
from packages.agents.nodes.curator import curator
from packages.agents.state import empty_identify_state

_CURATOR_MOD = importlib.import_module("packages.agents.nodes.curator")


def _candidates():
    return [
        {
            "url": "https://www.fincen.gov/a",
            "source_domain": "fincen.gov",
            "snippet": "deepfake KYC",
            "source_tier": 1,
            "score": 0.5,
        },
        {
            "url": "https://www.feedzai.com/b",
            "source_domain": "feedzai.com",
            "snippet": "vendor blog",
            "source_tier": 3,
            "score": 0.9,
        },
    ]


def test_curator_sorts_by_relevance_not_tier(monkeypatch):
    def fake_rank(candidates, topic=""):
        out = []
        for c in candidates:
            row = dict(c)
            if "feedzai" in c["url"]:
                row["rank_score"] = 95
            else:
                row["rank_score"] = 50
            out.append(row)
        out.sort(key=lambda r: -int(r.get("rank_score") or 0))
        return out, None

    monkeypatch.setattr(_CURATOR_MOD, "rank_candidates", fake_rank)
    state = empty_identify_state()
    state["candidate_urls"] = _candidates()
    out = curator(state)
    urls = [u["url"] for u in out["candidate_urls"]]
    assert "feedzai" in urls[0]


def test_curator_malformed_json_falls_back_to_tier(monkeypatch):
    def fake_rank(candidates, topic=""):
        return tier_fallback_rank(candidates), "curator_fallback:malformed_json"

    monkeypatch.setattr(_CURATOR_MOD, "rank_candidates", fake_rank)
    state = empty_identify_state()
    state["candidate_urls"] = _candidates()
    out = curator(state)
    assert out["candidate_urls"][0]["url"].startswith("https://www.fincen.gov")
    assert any("curator_fallback" in e for e in out["errors"])


def test_curator_empty_rank_list_falls_back(monkeypatch):
    def fake_rank(candidates, topic=""):
        return tier_fallback_rank(candidates), "curator_fallback:empty_rankings"

    monkeypatch.setattr(_CURATOR_MOD, "rank_candidates", fake_rank)
    state = empty_identify_state()
    state["candidate_urls"] = _candidates()
    out = curator(state)
    assert len(out["candidate_urls"]) == 2


def test_airplane_uses_tier_fallback(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    state = empty_identify_state()
    state["candidate_urls"] = _candidates()
    out = curator(state)
    assert len(out["candidate_urls"]) == 2
    assert any("curator_fallback" in e for e in out["errors"])


def test_max_docs_applied_after_rank(monkeypatch):
    monkeypatch.setenv("IDENTIFY_MAX_DOCS", "2")

    def fake_rank(candidates, topic=""):
        ranked = []
        for i, c in enumerate(candidates):
            row = dict(c)
            row["rank_score"] = 100 - i * 10
            ranked.append(row)
        return ranked, None

    monkeypatch.setattr(_CURATOR_MOD, "rank_candidates", fake_rank)
    five = [
        {
            "url": f"https://www.fincen.gov/{i}",
            "source_domain": "fincen.gov",
            "snippet": f"s{i}",
            "source_tier": 1,
        }
        for i in range(5)
    ]
    state = empty_identify_state()
    state["candidate_urls"] = five
    out = curator(state)
    assert len(out["candidate_urls"]) == 2
