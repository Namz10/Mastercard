"""Tier scorer vendor confidence cap."""

from packages.agents.tier_scorer import score_spec_sources


def test_tier3_feedzai_cannot_be_confirmed():
    spec = {"source_urls": ["https://www.feedzai.com/blog/genai-fraud-prevention"]}
    out = score_spec_sources(spec)
    assert out["confidence_level"] == "reported-unverified"
