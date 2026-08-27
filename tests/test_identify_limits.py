"""Tests for identify limit helpers."""

from packages.agents.limits import (
    CURATOR_BATCH_HARD_MAX,
    TAVILY_API_MAX,
    curator_batch_size,
    resolve_limit,
    take,
    tavily_max_results,
)


def test_resolve_limit_zero_is_unlimited():
    assert resolve_limit(0) is None
    assert resolve_limit(-1) is None


def test_take_unlimited_returns_all():
    assert take([1, 2, 3, 4, 5], None) == [1, 2, 3, 4, 5]


def test_take_positive_slices():
    assert take([1, 2, 3], 2) == [1, 2]


def test_tavily_max_results_zero_maps_to_20():
    assert tavily_max_results(0) == TAVILY_API_MAX


def test_tavily_max_results_caps_at_20():
    assert tavily_max_results(4) == 4
    assert tavily_max_results(100) == TAVILY_API_MAX


def test_curator_batch_hard_max():
    assert curator_batch_size(0) == CURATOR_BATCH_HARD_MAX
    assert curator_batch_size(10) == 10
