"""Collection router: fixtures (airplane) vs live Tavily search."""

from packages.osint.fixtures import fixture_candidate_urls
from packages.osint.search import DEFAULT_QUERY, search_candidate_urls
from packages.osint.settings import get_osint_settings


def collect_candidate_urls(query: str = DEFAULT_QUERY, max_results: int = 5) -> list[dict]:
    """Return candidate URLs per IDENTIFY_LIVE_SEARCH flag."""
    settings = get_osint_settings()
    if not settings.identify_live_search:
        return fixture_candidate_urls()
    return search_candidate_urls(query=query, max_results=max_results)
