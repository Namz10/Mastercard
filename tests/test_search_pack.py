"""Search pack queries."""

from packages.osint.search_pack import (
    base_search_pack_queries,
    build_search_queries,
    catalog_gap_queries,
)


def test_pack_plus_hints_exceeds_three_when_unlimited():
    qs = build_search_queries("deepfake payment fraud KYC UPI", max_queries=0)
    assert len(qs) >= 4


def test_catalog_queries_off_by_default_not_in_pack():
    qs = build_search_queries("fraud", max_queries=0, include_catalog=False)
    catalog_only = set(catalog_gap_queries(max_count=24))
    overlap = [q for q in qs if q in catalog_only]
    assert len(overlap) == 0


def test_base_pack_non_empty():
    assert len(base_search_pack_queries()) >= 4
