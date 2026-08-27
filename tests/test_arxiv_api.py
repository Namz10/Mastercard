"""arXiv API collector."""

from packages.osint.allowlist import is_allowlisted_url


def test_allowlist_includes_npci_and_ic3():
    from packages.osint.allowlist import DOMAIN_TIER

    assert "npci.org.in" in DOMAIN_TIER
    assert "ic3.gov" in DOMAIN_TIER


def test_arxiv_maps_allowlisted_abs_urls():
    sample = "https://arxiv.org/abs/2401.12345"
    assert is_allowlisted_url(sample)


def test_arxiv_drops_non_allowlisted():
    assert not is_allowlisted_url("https://evil.com/paper")


def test_arxiv_api_parses_atom(monkeypatch):
    atom = """<?xml version="1.0"?>
    <feed><entry>
    <id>https://arxiv.org/abs/2401.12345</id>
    <title>Payment fraud detection</title>
    <summary>Deep learning for fraud.</summary>
    </entry></feed>"""

    class FakeResp:
        text = atom

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return FakeResp()

    monkeypatch.setattr("httpx.Client", FakeClient)
    from packages.osint.arxiv_api import arxiv_api_candidate_urls

    rows = arxiv_api_candidate_urls(max_results=5)
    assert len(rows) == 1
    assert rows[0]["url"].startswith("https://arxiv.org/abs/")


def test_gnews_keeps_only_allowlisted_article_urls(monkeypatch):
    entries = [
        {"link": "https://www.fincen.gov/news/test", "title": "t", "summary": "s"},
        {"link": "https://news.google.com/articles/foo", "title": "bad", "summary": "s"},
    ]
    feed = type("FakeFeed", (), {"entries": entries})()

    monkeypatch.setattr("packages.osint.gnews_rss.feedparser.parse", lambda *a, **k: feed)
    from packages.osint.gnews_rss import gnews_candidate_urls

    rows = gnews_candidate_urls(max_entries=10)
    assert len(rows) == 1
    assert "fincen.gov" in rows[0]["url"]
