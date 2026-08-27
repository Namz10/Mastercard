"""Deterministic tier and confidence scoring (Plan 01 §4)."""

from packages.osint.allowlist import domain_from_url, tier_for_url

# Registrable org roots for independence (simplified v1)
_ORG_BY_DOMAIN: dict[str, str] = {
    "fincen.gov": "fincen",
    "ftc.gov": "ftc",
    "rbi.org.in": "rbi",
    "treasury.gov": "treasury",
    "arxiv.org": "arxiv",
    "dhs.gov": "dhs",
    "feedzai.com": "feedzai",
    "wipro.com": "wipro",
    "deloitte.com": "deloitte",
    "bny.com": "bny",
    "paymentservices.amazon.com": "amazon",
    "reuters.com": "reuters",
    "bbc.com": "bbc",
}


def org_for_url(url: str) -> str:
    domain = domain_from_url(url)
    for key, org in _ORG_BY_DOMAIN.items():
        if domain == key or domain.endswith(f".{key}"):
            return org
    return domain


def score_spec_sources(spec: dict) -> dict:
    """Set source_tier (best) and confidence_level from source_urls."""
    urls = spec.get("source_urls") or []
    if not urls:
        spec["confidence_level"] = "reported-unverified"
        return spec

    tiers = [tier_for_url(str(u)) for u in urls]
    best_tier = min(tiers)
    spec["source_tier"] = best_tier

    orgs = {org_for_url(str(u)) for u in urls}
    tier3_or_better = [t for t in tiers if t <= 3]

    confirmed = best_tier <= 2 or (len(tier3_or_better) >= 2 and len(orgs) >= 2)
    spec["confidence_level"] = "confirmed" if confirmed else "reported-unverified"
    return spec
