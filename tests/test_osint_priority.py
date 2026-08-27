"""OSINT candidate priority ordering."""

from packages.osint.priority import sort_osint_candidates


def test_sort_prefers_regulator_tavily_over_arxiv():
    candidates = [
        {
            "url": "https://arxiv.org/abs/1",
            "source": "arxiv_api",
            "source_domain": "arxiv.org",
            "source_tier": 2,
            "score": 0.99,
        },
        {
            "url": "https://www.fincen.gov/alert",
            "source": "tavily",
            "source_domain": "fincen.gov",
            "source_tier": 1,
            "score": 0.5,
        },
    ]
    ranked = sort_osint_candidates(candidates)
    assert ranked[0]["source_domain"] == "fincen.gov"


def test_sort_keeps_arxiv_when_only_source():
    arxiv = [
        {
            "url": "https://arxiv.org/abs/1",
            "source": "arxiv_api",
            "source_domain": "arxiv.org",
            "source_tier": 2,
        }
    ]
    assert sort_osint_candidates(arxiv)[0]["source"] == "arxiv_api"
