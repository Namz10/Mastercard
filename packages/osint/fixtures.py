"""Airplane-mode fixture corpus (IDENTIFY_LIVE_SEARCH=false)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "osint" / "fixtures"

FIXTURE_FILES: dict[str, tuple[str, str]] = {
    "fincen_alert004": (
        "fincen_alert004.txt",
        "https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial",
    ),
    "rbi_note": (
        "rbi_note.txt",
        "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
    ),
}


@dataclass(frozen=True)
class FixtureDocument:
    key: str
    url: str
    source_domain: str
    text: str
    fetched_at: str


def load_fixture_documents() -> list[FixtureDocument]:
    """Load all fixture text files; no API keys required."""
    docs: list[FixtureDocument] = []
    now = datetime.now(timezone.utc).isoformat()
    for key, (filename, url) in FIXTURE_FILES.items():
        path = FIXTURES_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing OSINT fixture: {path}")
        text = path.read_text(encoding="utf-8").strip()
        from packages.osint.allowlist import domain_from_url

        docs.append(
            FixtureDocument(
                key=key,
                url=url,
                source_domain=domain_from_url(url),
                text=text,
                fetched_at=now,
            )
        )
    return docs


def fixture_candidate_urls() -> list[dict]:
    """Candidate URL records for Scout-style consumers."""
    return [
        {
            "url": doc.url,
            "source_domain": doc.source_domain,
            "snippet": doc.text[:280].replace("\n", " "),
            "fetched_at": doc.fetched_at,
        }
        for doc in load_fixture_documents()
    ]
