"""Scout node — Tavily-first (live), topic-aware RSS, fixtures (airplane)."""

from datetime import datetime, timezone

from packages.agents.state import IdentifyState
from packages.osint.fixtures import fixture_candidate_urls
from packages.osint.query_expand import expand_search_queries
from packages.osint.rss import rss_candidate_urls
from packages.osint.search import search_candidate_urls
from packages.osint.settings import get_osint_settings

MAX_CANDIDATES = 8
MAX_RSS_WITH_TOPIC = 3
MAX_RSS_NO_TOPIC = 5
TAVILY_RESULTS_PER_QUERY = 4


def _dedupe_urls(candidates: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in candidates:
        url = c.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(c)
    return out


def scout(state: IdentifyState) -> IdentifyState:
    settings = get_osint_settings()
    topic = (state.get("topic") or "").strip()
    candidates: list[dict] = []
    errors = list(state.get("errors") or [])

    if settings.identify_live_search:
        # 1) Tavily first — user topic drives search (not drowned by RSS)
        depth = "advanced" if topic else "basic"
        queries = expand_search_queries(topic)
        for q in queries:
            try:
                candidates.extend(
                    search_candidate_urls(
                        query=q,
                        max_results=TAVILY_RESULTS_PER_QUERY,
                        search_depth=depth,
                    )
                )
            except Exception as exc:
                errors.append(f"scout_tavily:{q}:{exc}")

        # 2) RSS supplement — keyword-filtered when topic set
        try:
            rss_max = MAX_RSS_WITH_TOPIC if topic else MAX_RSS_NO_TOPIC
            candidates.extend(rss_candidate_urls(topic=topic, max_entries=rss_max))
        except Exception as exc:
            errors.append(f"scout_rss:{exc}")
    else:
        candidates.extend(fixture_candidate_urls())

    candidates = _dedupe_urls(candidates)[:MAX_CANDIDATES]
    now = datetime.now(timezone.utc).isoformat()
    for c in candidates:
        c.setdefault("fetched_at", now)

    state["candidate_urls"] = candidates
    state["errors"] = errors
    return state
