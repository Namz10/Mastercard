"""Fixed Tavily query pack + optional catalog-gap queries."""

from packages.catalog.loader import load_catalog_yaml
from packages.osint.allowlist import validate_search_query
from packages.osint.search import DEFAULT_QUERY

_BASE_PACK: tuple[str, ...] = (
    "FinCEN deepfake KYC liveness payment fraud alert",
    "RBI UPI authorized push payment impersonation India",
    "FTC press payment fraud scam",
    "arxiv cs.CR payment fraud detection deepfake",
    "FinCEN money mule funnel cash-out",
    "deepfake video KYC bank onboarding fraud",
)


def base_search_pack_queries() -> list[str]:
    out: list[str] = []
    for q in _BASE_PACK:
        try:
            out.append(validate_search_query(q))
        except ValueError:
            continue
    return out


def catalog_gap_queries(max_count: int | None = 8) -> list[str]:
    """One query per technique from seed — opt-in only."""
    specs = load_catalog_yaml()
    seen_tid: set[str] = set()
    queries: list[str] = []
    for spec in specs:
        tid = spec.technique_id.value
        if tid in seen_tid:
            continue
        seen_tid.add(tid)
        q = f"{tid} {spec.name} payment fraud"
        try:
            queries.append(validate_search_query(q))
        except ValueError:
            continue
    if max_count is not None:
        return queries[:max_count]
    return queries


def build_search_queries(
    topic: str,
    max_queries: int | None = 3,
    *,
    include_pack: bool = True,
    include_catalog: bool = False,
    catalog_max: int = 8,
) -> list[str]:
    """Merge topic, pack, hints from query_expand."""
    from packages.osint.query_expand import expand_search_queries

    limit = max_queries
    if limit is not None and limit <= 0:
        limit = None
    queries: list[str] = []

    if include_pack:
        queries.extend(base_search_pack_queries())

    topic_queries = expand_search_queries(topic, max_queries=0)
    queries.extend(topic_queries)

    if include_catalog:
        queries.extend(catalog_gap_queries(max_count=catalog_max if limit is None else min(catalog_max, limit or 8)))

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = " ".join(q.split())
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)

    if not out:
        out = [DEFAULT_QUERY]

    if limit is not None:
        return out[:limit]
    return out
