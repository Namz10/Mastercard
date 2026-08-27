"""Survey abstain on arXiv meta papers."""

from packages.agents.llm.extraction import extract_from_document


def test_arxiv_global_survey_abstains():
    text = "A Global Survey of Opportunities, Threats, and Regulation\nAbstract\nWe survey generative AI in financial institutions."
    out = extract_from_document(text, "https://arxiv.org/pdf/2504.21574", "arxiv.org")
    assert out.get("extraction_source") == "abstain"
    assert "survey" in (out.get("abstain_reason") or "")
