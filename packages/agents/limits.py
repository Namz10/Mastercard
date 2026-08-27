"""Identify limit helpers — 0 or negative means unlimited in-process."""

from typing import TypeVar

T = TypeVar("T")

TAVILY_API_MAX = 20
CURATOR_BATCH_HARD_MAX = 40


def resolve_limit(raw: int) -> int | None:
    """<=0 → unlimited (None). Positive → cap."""
    if raw <= 0:
        return None
    return raw


def take(items: list[T], limit: int | None) -> list[T]:
    if limit is None:
        return list(items)
    return items[:limit]


def tavily_max_results(raw: int) -> int:
    if raw <= 0:
        return TAVILY_API_MAX
    return min(raw, TAVILY_API_MAX)


def curator_batch_size(raw: int) -> int:
    if raw <= 0:
        return CURATOR_BATCH_HARD_MAX
    return min(raw, CURATOR_BATCH_HARD_MAX)
