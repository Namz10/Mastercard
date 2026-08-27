"""arXiv API collector for payment-fraud research papers."""

from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from packages.osint.allowlist import domain_from_url, is_allowlisted_url, tier_for_domain

ARXIV_API_URL = "https://export.arxiv.org/api/query"
_DEFAULT_QUERY = (
    "cat:cs.CR AND (all:payment OR all:fraud OR all:deepfake OR all:mule "
    "OR all:authorized OR all:account+takover)"
)


def arxiv_api_candidate_urls(
    query: str | None = None,
    max_results: int = 20,
    timeout: float = 30.0,
) -> list[dict]:
    """Query arXiv API; return allowlisted arxiv.org URLs only."""
    q = query or _DEFAULT_QUERY
    url = f"{ARXIV_API_URL}?search_query={quote(q)}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    now = datetime.now(timezone.utc).isoformat()
    candidates: list[dict] = []

    with httpx.Client(timeout=timeout, headers={"User-Agent": "AegisLoop-OSINT/0.1"}) as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.text

    # Parse Atom entries without heavy XML deps
    entries = text.split("<entry>")
    for block in entries[1:]:
        link = ""
        title = ""
        summary = ""
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("<id>") and "arxiv.org" in line:
                link = line.replace("<id>", "").replace("</id>", "").strip()
            elif line.startswith("<title>"):
                title = line.replace("<title>", "").replace("</title>", "").strip()
            elif line.startswith("<summary>"):
                summary = line.replace("<summary>", "").replace("</summary>", "").strip()
        if not link:
            continue
        if "/abs/" in link:
            abs_url = link
        elif link.endswith(".pdf"):
            abs_url = link.replace("/pdf/", "/abs/").replace(".pdf", "")
        else:
            abs_url = link
        if not is_allowlisted_url(abs_url):
            continue
        domain = domain_from_url(abs_url)
        candidates.append(
            {
                "url": abs_url,
                "source_domain": domain,
                "snippet": (title + " — " + summary)[:400],
                "fetched_at": now,
                "source": "arxiv_api",
                "source_tier": tier_for_domain(domain),
                "score": 0.0,
            }
        )

    return candidates
