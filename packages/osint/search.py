"""Tavily Search on allowlisted domains (live Identify collection)."""

from dataclasses import dataclass

import httpx

from packages.osint.allowlist import ALLOWLIST_DOMAINS, validate_search_query
from packages.osint.settings import get_osint_settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

DEFAULT_QUERY = "GenAI payment fraud regulator alert deepfake"


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    source_domain: str
    score: float


def tavily_search(
    query: str = DEFAULT_QUERY,
    max_results: int = 5,
    timeout: float = 30.0,
    search_depth: str = "basic",
) -> list[SearchResult]:
    """Run Tavily Search restricted to allowlisted domains."""
    settings = get_osint_settings()
    if not settings.tavily_api_key:
        raise ValueError("TAVILY_API_KEY is required for live Tavily search")

    clean_query = validate_search_query(query)
    payload = {
        "api_key": settings.tavily_api_key,
        "query": clean_query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_domains": sorted(ALLOWLIST_DOMAINS),
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(TAVILY_SEARCH_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    from packages.osint.allowlist import domain_from_url, is_allowlisted_url

    results: list[SearchResult] = []
    for item in data.get("results", []):
        url = item.get("url") or ""
        if not url or not is_allowlisted_url(url):
            continue
        results.append(
            SearchResult(
                url=url,
                title=(item.get("title") or "").strip(),
                snippet=(item.get("content") or "").strip(),
                source_domain=domain_from_url(url),
                score=float(item.get("score") or 0.0),
            )
        )
    return results


def search_candidate_urls(
    query: str = DEFAULT_QUERY,
    max_results: int = 5,
    search_depth: str = "basic",
) -> list[dict]:
    """Scout-style dicts from live Tavily search."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "url": r.url,
            "source_domain": r.source_domain,
            "snippet": (r.title + " — " + r.snippet)[:400],
            "fetched_at": now,
            "source": "tavily",
            "score": r.score,
        }
        for r in tavily_search(query=query, max_results=max_results, search_depth=search_depth)
    ]
