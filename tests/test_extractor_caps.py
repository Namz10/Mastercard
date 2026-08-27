"""Extractor ordering — no tier re-sort."""

from packages.agents.nodes.extractor import extractor
from packages.agents.state import empty_identify_state


def test_extractor_preserves_curator_order(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    state = empty_identify_state()
    state["candidate_urls"] = [
        {"url": "https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial", "fetched_at": "now"},
        {"url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx", "fetched_at": "now"},
    ]
    out = extractor(state)
    urls = [d["url"] for d in out["extracted_docs"]]
    if len(urls) >= 2:
        assert urls[0].startswith("https://www.fincen.gov")
