"""Deterministic OSINT candidate ordering — tier and collector precedence."""

from __future__ import annotations

from typing import Any

from packages.osint.allowlist import DEFAULT_TIER, tier_for_url

_COLLECTOR_PRIORITY: dict[str, int] = {
    "tavily": 0,
    "rss": 1,
    "gnews_rss": 2,
    "arxiv_api": 3,
}


def collector_priority(source: str) -> int:
    if source.startswith("rss:"):
        return _COLLECTOR_PRIORITY["rss"]
    return _COLLECTOR_PRIORITY.get(source, 4)


def osint_candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, int, float]:
    url = str(candidate.get("url") or "")
    tier = int(candidate.get("source_tier") or (tier_for_url(url) if url else DEFAULT_TIER))
    source = str(candidate.get("source") or "")
    rank_score = int(candidate.get("rank_score") or 0)
    score = float(candidate.get("score") or 0.0)
    return (tier, collector_priority(source), -rank_score, -score)


def sort_osint_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer regulator-tier Tavily hits; arXiv remains available but ranks later."""
    return sorted(candidates, key=osint_candidate_sort_key)
