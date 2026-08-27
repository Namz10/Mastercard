"""Google News site-scoped RSS — article URLs must pass allowlist."""

from datetime import datetime, timezone
from urllib.parse import quote

import feedparser

from packages.osint.allowlist import domain_from_url, is_allowlisted_url, tier_for_domain

_DEFAULT_SITES = (
    "fincen.gov",
    "rbi.org.in",
    "npci.org.in",
    "ic3.gov",
    "ftc.gov",
    "arxiv.org",
    "bbc.com",
)


def _gnews_feed_url(sites: tuple[str, ...] = _DEFAULT_SITES, when: str = "30d") -> str:
    site_q = " OR ".join(f"site:{s}" for s in sites)
    q = f"{site_q} payment fraud OR deepfake OR UPI when:{when}"
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=en-US&gl=US&ceid=US:en"


def gnews_candidate_urls(
    when: str = "30d",
    max_entries: int | None = 30,
    timeout: float = 20.0,
) -> list[dict]:
    """Parse Google News RSS; keep only allowlisted article URLs."""
    feed_url = _gnews_feed_url(when=when)
    now = datetime.now(timezone.utc).isoformat()
    parsed = feedparser.parse(
        feed_url,
        request_headers={"User-Agent": "AegisLoop-OSINT/0.1"},
    )
    candidates: list[dict] = []
    entries = parsed.entries if parsed.entries else []
    if max_entries is not None and max_entries > 0:
        entries = entries[:max_entries]

    for item in entries:
        link = (item.get("link") or "").strip()
        if not link or not is_allowlisted_url(link):
            continue
        domain = domain_from_url(link)
        title = (item.get("title") or "").strip()
        summary = (item.get("summary") or item.get("description") or "").strip()
        candidates.append(
            {
                "url": link,
                "source_domain": domain,
                "snippet": (title + " — " + summary)[:300],
                "fetched_at": item.get("published") or now,
                "source": "gnews_rss",
                "source_tier": tier_for_domain(domain),
                "score": 0.0,
            }
        )
    return candidates
