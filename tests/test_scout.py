"""Scout prioritizes Tavily when topic is set."""

from packages.agents.nodes.scout import scout
from packages.agents.state import empty_identify_state


def test_scout_airplane_fixtures(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    state = scout(empty_identify_state(run_id="scout-test"))
    assert len(state["candidate_urls"]) >= 2
    assert all("fincen" in u["url"] or "rbi" in u["url"] for u in state["candidate_urls"])

