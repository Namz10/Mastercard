"""Scout node — multi-collector (Tavily, RSS, GNews, arXiv), fixtures (airplane)."""

from packages.agents.limits import resolve_limit, take
from packages.agents.settings import get_identify_settings
from packages.agents.state import IdentifyState
from packages.osint.collect import gather_live_candidates
from packages.osint.fixtures import fixture_candidate_urls


def scout(state: IdentifyState) -> IdentifyState:
    identify = get_identify_settings()
    errors = list(state.get("errors") or [])
    topic = (state.get("topic") or "").strip()

    if identify.identify_live_search:
        from packages.osint.settings import get_osint_settings

        candidates = gather_live_candidates(
            topic,
            identify=identify,
            osint=get_osint_settings(),
            errors=errors,
        )
        tavily_quota = any(
            "scout_tavily:" in e and ("432" in e or "429" in e or "401" in e or "403" in e)
            for e in errors
        )
        # Demo resilience: when Tavily is blocked, fixtures beat weak arXiv-only noise
        if not candidates or tavily_quota:
            fixtures = fixture_candidate_urls()
            if fixtures:
                reason = "empty live OSINT" if not candidates else "Tavily quota/auth failure"
                errors.append(f"scout_fallback:fixtures ({reason}; using local corpus)")
                candidates = fixtures if tavily_quota or not candidates else fixtures + candidates
    else:
        candidates = fixture_candidate_urls()

    max_cand = resolve_limit(identify.identify_max_candidates)
    candidates = take(candidates, max_cand)

    state["candidate_urls"] = candidates
    state["scout_candidate_count"] = len(candidates)
    state["errors"] = errors
    return state
