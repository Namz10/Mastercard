"""Article body extraction: Tavily Extract → trafilatura (or firecrawl) fallback."""

from dataclasses import dataclass

import httpx
import trafilatura

from packages.osint.allowlist import is_allowlisted_url
from packages.osint.settings import get_osint_settings

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"


@dataclass(frozen=True)
class ExtractedDocument:
    url: str
    text: str
    extractor: str


def extract_url(url: str, timeout: float = 30.0) -> ExtractedDocument:
    """Extract main article text from a single allowlisted URL."""
    if not is_allowlisted_url(url):
        raise ValueError(f"URL not on allowlist: {url}")

    settings = get_osint_settings()
    backend = settings.osint_extractor.lower().strip()

    if backend == "firecrawl":
        return _extract_firecrawl(url, settings, timeout)
    if backend == "trafilatura":
        return _extract_trafilatura(url, timeout)

    # default: tavily then trafilatura fallback
    if settings.tavily_api_key:
        try:
            doc = _extract_tavily(url, settings.tavily_api_key, timeout)
            if doc.text.strip():
                return doc
        except (httpx.HTTPError, ValueError):
            pass
    return _extract_trafilatura(url, timeout)


def extract_fixture_text(key: str) -> ExtractedDocument:
    """Read fixture body by key (fincen_alert004 | rbi_note)."""
    from packages.osint.fixtures import FIXTURE_FILES, FIXTURES_DIR

    if key not in FIXTURE_FILES:
        raise KeyError(f"Unknown fixture key: {key}")
    filename, url = FIXTURE_FILES[key]
    text = (FIXTURES_DIR / filename).read_text(encoding="utf-8").strip()
    return ExtractedDocument(url=url, text=text, extractor="fixture")


def _extract_tavily(url: str, api_key: str, timeout: float) -> ExtractedDocument:
    payload = {"api_key": api_key, "urls": [url]}
    with httpx.Client(timeout=timeout) as client:
        response = client.post(TAVILY_EXTRACT_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    results = data.get("results") or []
    if not results:
        raise ValueError("Tavily extract returned no results")
    text = (results[0].get("raw_content") or results[0].get("content") or "").strip()
    return ExtractedDocument(url=url, text=text, extractor="tavily")


def _extract_trafilatura(url: str, timeout: float) -> ExtractedDocument:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "AegisLoop-OSINT/0.1"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    text = trafilatura.extract(html, url=url) or ""
    return ExtractedDocument(url=url, text=text.strip(), extractor="trafilatura")


def _extract_firecrawl(url: str, settings, timeout: float) -> ExtractedDocument:
    if not settings.firecrawl_api_key:
        return _extract_trafilatura(url, timeout)

    headers = {
        "Authorization": f"Bearer {settings.firecrawl_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"url": url, "formats": ["markdown"]}
    with httpx.Client(timeout=timeout) as client:
        response = client.post(FIRECRAWL_SCRAPE_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    markdown = (data.get("data") or {}).get("markdown") or ""
    if not markdown.strip():
        return _extract_trafilatura(url, timeout)
    return ExtractedDocument(url=url, text=markdown.strip(), extractor="firecrawl")
