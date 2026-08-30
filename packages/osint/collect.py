"""Collection router: fixtures (airplane) vs live multi-collector gather."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from packages.agents.limits import resolve_limit, tavily_max_results
from packages.agents.settings import IdentifySettings
from packages.osint.allowlist import is_allowlisted_url
from packages.osint.fixtures import fixture_candidate_urls
from packages.osint.priority import sort_osint_candidates
from packages.osint.search import DEFAULT_QUERY, search_candidate_urls
from packages.osint.search_pack import build_search_queries
from packages.osint.settings import OsintSettings, get_osint_settings


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    q = parse_qs(parsed.query, keep_blank_values=True)
    for key in list(q.keys()):
        if key.lower().startswith("utm_"):
            del q[key]
    clean_q = urlencode({k: v[0] if len(v) == 1 else v for k, v in q.items()}, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, parsed.params, clean_q, ""))


def dedupe_osint_candidates(candidates: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for candidate in candidates:
        url = candidate.get("url", "")
        if not url or not is_allowlisted_url(url):
            continue
        key = _normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def gather_live_candidates(
    topic: str,
    *,
    identify: IdentifySettings,
    osint: OsintSettings,
    errors: list[str] | None = None,
) -> list[dict]:
    """Merge enabled live collectors; Tavily first, arXiv last, then tier-sort."""
    err = errors if errors is not None else []
    candidates: list[dict] = []

    tavily_ok = identify.identify_tavily_enabled and bool(osint.tavily_api_key)
    if tavily_ok:
        max_calls = identify.identify_tavily_max_calls_per_run
        max_q = resolve_limit(identify.identify_max_queries)
        queries = build_search_queries(
            topic,
            max_queries=max_q,
            include_pack=identify.identify_search_pack_enabled,
            include_catalog=identify.identify_catalog_queries_enabled,
        )
        per_query = tavily_max_results(identify.identify_tavily_max_results)
        calls = 0
        for query in queries:
            if calls >= max_calls:
                break
            depth = "basic"
            if topic and identify.identify_tavily_advanced_on_topic and query == queries[0]:
                depth = "advanced"
            try:
                candidates.extend(
                    search_candidate_urls(
                        query=query,
                        max_results=per_query,
                        search_depth=depth,
                    )
                )
                calls += 1
            except Exception as exc:
                err.append(f"scout_tavily:{query}:{exc}")
    elif identify.identify_tavily_enabled:
        err.append("scout_tavily:skipped:no_key")

    if identify.identify_rss_enabled:
        try:
            from packages.osint.rss import rss_candidate_urls

            rss_max_with = resolve_limit(identify.identify_rss_max_with_topic)
            rss_max_no = resolve_limit(identify.identify_rss_max_no_topic)
            rss_max = rss_max_with if topic else rss_max_no
            candidates.extend(rss_candidate_urls(topic=topic, max_entries=rss_max))
        except Exception as exc:
            err.append(f"scout_rss:{exc}")

    if identify.identify_gnews_enabled:
        try:
            from packages.osint.gnews_rss import gnews_candidate_urls

            gnews_max = resolve_limit(identify.identify_max_candidates)
            candidates.extend(gnews_candidate_urls(max_entries=gnews_max))
        except Exception as exc:
            err.append(f"scout_gnews:{exc}")

    if identify.identify_arxiv_api_enabled:
        try:
            from packages.osint.arxiv_api import arxiv_api_candidate_urls

            candidates.extend(arxiv_api_candidate_urls())
        except Exception as exc:
            err.append(f"scout_arxiv:{exc}")

    now = datetime.now(timezone.utc).isoformat()
    ranked = sort_osint_candidates(dedupe_osint_candidates(candidates))
    for candidate in ranked:
        candidate.setdefault("fetched_at", now)
    return ranked


def collect_candidate_urls(query: str = DEFAULT_QUERY, max_results: int = 5) -> list[dict]:
    """Return candidate URLs per IDENTIFY_LIVE_SEARCH flag."""
    settings = get_osint_settings()
    if not settings.identify_live_search:
        return fixture_candidate_urls()
    return search_candidate_urls(query=query, max_results=max_results)
