"""Curator LLM — batch rank candidate snippets against taxonomy."""

from __future__ import annotations

import json
from typing import Any

from packages.agents.limits import curator_batch_size
from packages.agents.llm.config import is_llm_configured, load_provider_config
from packages.agents.llm.errors import LlmError
from packages.agents.llm.providers import build_provider
from packages.agents.settings import get_identify_settings
from packages.catalog.taxonomy_brief import build_taxonomy_brief


def _tier_sort_key(c: dict[str, Any]) -> tuple:
    tier = int(c.get("source_tier") or 5)
    score = float(c.get("score") or 0.0)
    return (tier, -score)


def tier_fallback_rank(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic rank: best tier (low number) then Tavily score."""
    ranked = sorted(candidates, key=_tier_sort_key)
    out: list[dict[str, Any]] = []
    for c in ranked:
        row = dict(c)
        row.setdefault("rank_score", 100 - int(row.get("source_tier") or 4) * 10)
        row.setdefault("rank_reason", "curator_fallback:tier_sort")
        out.append(row)
    return out


def rank_candidates(
    candidates: list[dict[str, Any]],
    topic: str = "",
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Rank candidates via LLM or tier fallback.
    Returns (ranked_candidates, fallback_reason or None).
    """
    if not candidates:
        return [], None

    settings = get_identify_settings()
    if not settings.identify_curator_enabled or not is_llm_configured():
        return tier_fallback_rank(candidates), "curator_fallback:tier_sort"

    batch = curator_batch_size(settings.identify_curator_batch_size)
    snippet_cap = settings.identify_curator_snippet_chars
    brief = build_taxonomy_brief()

    payload = []
    for c in candidates[:batch]:
        snippet = str(c.get("snippet") or "")[:snippet_cap]
        payload.append(
            {
                "url": c.get("url"),
                "domain": c.get("source_domain"),
                "tier": c.get("source_tier"),
                "snippet": snippet,
            }
        )

    user = (
        f"Topic: {topic or 'GenAI payment fraud'}\n\n"
        f"Taxonomy (T01-T24):\n{brief}\n\n"
        f"Rank these candidate URLs for typology relevance. "
        f"Return JSON object with key rankings: array of "
        f"{{url, relevance_score (0-100), predicted_technique_id, reason}}.\n\n"
        f"Candidates:\n{json.dumps(payload, indent=2)}"
    )

    try:
        cfg = load_provider_config()
        provider = build_provider(cfg)
        raw = provider.complete_json(
            system=(
                "You rank OSINT URLs for payment-fraud typology research. "
                "Respond with JSON only: {\"rankings\": [...]}."
            ),
            user=user,
            schema_name="CuratorRank",
        )
        rankings = raw.get("rankings") if isinstance(raw, dict) else None
        if not isinstance(rankings, list):
            return tier_fallback_rank(candidates), "curator_fallback:malformed_json"

        by_url = {str(c.get("url")): dict(c) for c in candidates}
        scored: list[dict[str, Any]] = []
        for item in rankings:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            if url not in by_url:
                continue
            row = dict(by_url[url])
            row["rank_score"] = int(item.get("relevance_score") or 0)
            row["rank_reason"] = str(item.get("reason") or "")
            pred = item.get("predicted_technique_id")
            if pred:
                row["predicted_technique_id"] = str(pred)
            scored.append(row)

        if not scored:
            return tier_fallback_rank(candidates), "curator_fallback:empty_rankings"

        min_score = settings.identify_curator_min_score
        if min_score > 0:
            scored = [r for r in scored if int(r.get("rank_score") or 0) >= min_score]
            if not scored:
                return tier_fallback_rank(candidates), "curator_fallback:min_score_empty"

        scored.sort(
            key=lambda r: (
                -int(r.get("rank_score") or 0),
                int(r.get("source_tier") or 5),
                -float(r.get("score") or 0.0),
            ),
        )
        # Append any URLs the LLM omitted (preserve scout discovery)
        seen = {r["url"] for r in scored}
        for c in candidates:
            if c.get("url") not in seen:
                scored.append(tier_fallback_rank([c])[0])
        return scored, None
    except (LlmError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return tier_fallback_rank(candidates), "curator_fallback:tier_sort"
