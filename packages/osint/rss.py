"""RSS polling for FinCEN, FTC, and arXiv (allowlisted sources)."""

from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

from packages.osint.allowlist import domain_from_url, is_allowlisted_url, tier_for_domain

# Public RSS endpoints on allowlisted domains
RSS_FEEDS: dict[str, str] = {
    "fincen": "https://www.fincen.gov/news/rss.xml",
    "ftc": "https://www.ftc.gov/feeds/press-release.xml",
    "arxiv_cs_cr": "https://rss.arxiv.org/rss/cs.CR",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "bbc_technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
}


@dataclass(frozen=True)
class RssEntry:
    feed_id: str
    url: str
    title: str
    summary: str
    published: str | None
    source_domain: str
    source_tier: int


def poll_rss_feeds(timeout: float = 20.0, max_entries_per_feed: int | None = None) -> list[RssEntry]:
    """Fetch RSS feeds and return allowlisted entries only."""
    entries: list[RssEntry] = []
    for feed_id, feed_url in RSS_FEEDS.items():
        parsed = feedparser.parse(feed_url, request_headers={"User-Agent": "AegisLoop-OSINT/0.1"})
        if parsed.bozo and not parsed.entries:
            continue
        feed_items = parsed.entries
        if max_entries_per_feed is not None and max_entries_per_feed > 0:
            feed_items = feed_items[:max_entries_per_feed]
        for item in feed_items:
            link = item.get("link") or ""
            if not link or not is_allowlisted_url(link):
                continue
            domain = domain_from_url(link)
            entries.append(
                RssEntry(
                    feed_id=feed_id,
                    url=link,
                    title=(item.get("title") or "").strip(),
                    summary=(item.get("summary") or item.get("description") or "").strip(),
                    published=item.get("published") or item.get("updated"),
                    source_domain=domain,
                    source_tier=tier_for_domain(domain),
                )
            )
    return entries


def _rss_matches_topic(entry: RssEntry, topic: str) -> bool:
    """Keep RSS rows that overlap the scout topic (reduces FTC feed noise)."""
    if not topic.strip():
        return True
    topic_words = [w for w in topic.lower().split() if len(w) > 3]
    if not topic_words:
        return True
    text = (entry.title + " " + entry.summary).lower()
    hits = sum(1 for w in topic_words if w in text)
    # Also match typology hint keywords
    fraud_markers = (
        "fraud",
        "payment",
        "scam",
        "money",
        "mule",
        "identity",
        "deepfake",
        "upi",
        "launder",
        "merchant",
        "imperson",
    )
    if any(m in text for m in fraud_markers) and hits >= 1:
        return True
    return hits >= 2


def rss_candidate_urls(topic: str = "", max_entries: int | None = None, timeout: float = 20.0) -> list[dict]:
    """Map RSS entries to Scout-style candidate URL dicts."""
    now = datetime.now(timezone.utc).isoformat()
    per_feed = None
    if max_entries is not None and max_entries > 0:
        per_feed = max(max_entries // len(RSS_FEEDS), 5)
    entries = poll_rss_feeds(timeout=timeout, max_entries_per_feed=per_feed)
    if topic.strip():
        entries = [e for e in entries if _rss_matches_topic(e, topic)]
    if max_entries is not None and max_entries > 0:
        entries = entries[:max_entries]
    return [
        {
            "url": e.url,
            "source_domain": e.source_domain,
            "snippet": (e.title + " — " + e.summary)[:400],
            "fetched_at": e.published or now,
            "source": f"rss:{e.feed_id}",
            "source_tier": e.source_tier,
        }
        for e in entries
    ]
