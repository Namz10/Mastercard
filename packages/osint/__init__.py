"""Allowlisted OSINT fetchers."""

from packages.osint.allowlist import ALLOWLIST_DOMAINS, DOMAIN_TIER, tier_for_url
from packages.osint.collect import collect_candidate_urls
from packages.osint.extract import extract_fixture_text, extract_url
from packages.osint.fixtures import load_fixture_documents
from packages.osint.settings import get_osint_settings

__all__ = [
    "ALLOWLIST_DOMAINS",
    "DOMAIN_TIER",
    "collect_candidate_urls",
    "extract_fixture_text",
    "extract_url",
    "get_osint_settings",
    "load_fixture_documents",
    "tier_for_url",
]
