"""Allowlisted domains and source-tier mapping (Plan 01 §4, FinalIdentify freeze)."""

from urllib.parse import urlparse

# v1 domain → tier freeze
DOMAIN_TIER: dict[str, int] = {
    "fincen.gov": 1,
    "ftc.gov": 1,
    "rbi.org.in": 1,
    "treasury.gov": 1,
    "npci.org.in": 1,
    "ic3.gov": 1,
    "arxiv.org": 2,
    "dhs.gov": 2,
    "feedzai.com": 3,
    "wipro.com": 3,
    "deloitte.com": 3,
    "bny.com": 3,
    "paymentservices.amazon.com": 3,
    "reuters.com": 4,
    "bbc.com": 4,
}

DEFAULT_TIER = 4

ALLOWLIST_DOMAINS: frozenset[str] = frozenset(DOMAIN_TIER.keys())

# Scout / search safety — reject queries containing these terms
FORBIDDEN_QUERY_TERMS: frozenset[str] = frozenset(
    {
        "dark-web",
        "dark web",
        "criminal-market",
        "criminal market",
        "jailbreak-as-a-service",
        "jailbreak as a service",
        "exploit-payload",
        "exploit payload",
    }
)


def normalize_domain(host: str) -> str:
    host = host.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"URL has no host: {url}")
    return normalize_domain(parsed.hostname)


def is_allowlisted_url(url: str) -> bool:
    try:
        domain = domain_from_url(url)
    except ValueError:
        return False
    return domain in ALLOWLIST_DOMAINS or any(
        domain.endswith(f".{allowed}") for allowed in ALLOWLIST_DOMAINS
    )


def tier_for_domain(domain: str) -> int:
    domain = normalize_domain(domain)
    if domain in DOMAIN_TIER:
        return DOMAIN_TIER[domain]
    for allowed, tier in DOMAIN_TIER.items():
        if domain.endswith(f".{allowed}") or domain == allowed:
            return tier
    return DEFAULT_TIER


def tier_for_url(url: str) -> int:
    return tier_for_domain(domain_from_url(url))


def validate_search_query(query: str) -> str:
    lowered = query.lower()
    for term in FORBIDDEN_QUERY_TERMS:
        if term in lowered:
            raise ValueError(f"Search query contains forbidden term: {term}")
    return query
