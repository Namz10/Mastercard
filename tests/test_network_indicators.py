"""Network indicator sanitization and GreyNoise corroboration."""

from unittest.mock import patch

import pytest

from packages.agents.corroborator import apply_corroboration
from packages.osint.telemetry.greynoise import GreynoiseResult, qualifies_for_corroboration
from packages.osint.telemetry.indicators import sanitize_network_indicators

_ARTICLE = (
    "A credential-stuffing botnet targeted payment APIs from scanner host 185.220.101.45 "
    "and card-testing infrastructure at evil-checkout.example before cash-out."
)
_SOURCE = "https://www.reuters.com/article/card-testing-botnet"


def test_sanitize_keeps_valid_ip_with_evidence():
    out = sanitize_network_indicators(
        _ARTICLE,
        [
            {
                "type": "ip",
                "value": "185.220.101.45",
                "role": "scanner",
                "evidence_span": "scanner host 185.220.101.45",
            }
        ],
        _SOURCE,
    )
    assert len(out) == 1
    assert out[0]["type"] == "ip"
    assert out[0]["value"] == "185.220.101.45"


def test_sanitize_rejects_hallucinated_ip():
    out = sanitize_network_indicators(
        _ARTICLE,
        [
            {
                "type": "ip",
                "value": "203.0.113.50",
                "role": "scanner",
                "evidence_span": "scanner host 203.0.113.50",
            }
        ],
        _SOURCE,
    )
    assert out == []


def test_sanitize_rejects_victim_context():
    text = "The victim logged in from 203.0.113.10 during the scam call."
    out = sanitize_network_indicators(
        text,
        [
            {
                "type": "ip",
                "value": "203.0.113.10",
                "role": "scanner",
                "evidence_span": "victim logged in from 203.0.113.10",
            }
        ],
        _SOURCE,
    )
    assert out == []


def test_sanitize_rejects_private_ip():
    text = "Attackers used internal relay 10.0.0.5 for card testing."
    out = sanitize_network_indicators(
        text,
        [
            {
                "type": "ip",
                "value": "10.0.0.5",
                "role": "card_testing",
                "evidence_span": "internal relay 10.0.0.5",
            }
        ],
        _SOURCE,
    )
    assert out == []


def test_sanitize_rejects_public_dns_without_attack_context():
    text = "Use Google DNS at 8.8.8.8 for resolution during testing."
    out = sanitize_network_indicators(
        text,
        [
            {
                "type": "ip",
                "value": "8.8.8.8",
                "role": "scanner",
                "evidence_span": "Google DNS at 8.8.8.8",
            }
        ],
        _SOURCE,
    )
    assert out == []


def test_qualifies_rejects_benign_riot_only():
    result = GreynoiseResult(
        seen=False,
        noise=False,
        riot=True,
        classification="benign",
        tags=[],
        raw={},
    )
    assert qualifies_for_corroboration(result) is False


def test_qualifies_accepts_noise_scanner():
    result = GreynoiseResult(
        seen=True,
        noise=True,
        riot=False,
        classification="malicious",
        tags=["scanner"],
        raw={},
    )
    assert qualifies_for_corroboration(result) is True


def test_corroborator_human_social_strips_indicators():
    spec = apply_corroboration(
        {
            "technique_id": "T13",
            "genai_modality": "voice",
            "confidence_level": "confirmed",
            "network_indicators": [{"type": "ip", "value": "1.2.3.4", "role": "scanner", "evidence_span": "x"}],
        }
    )
    assert spec["vector_class"] == "human_social"
    assert "network_indicators" not in spec


@patch.dict("os.environ", {"GREYNOISE_API_KEY": "test-key"})
@patch("packages.agents.corroborator.check_ip")
def test_corroborator_network_telemetry_on_hit(mock_check):
    mock_check.return_value = GreynoiseResult(
        seen=True,
        noise=True,
        riot=False,
        classification="malicious",
        tags=["scanner"],
        raw={},
    )
    spec = apply_corroboration(
        {
            "technique_id": "T01",
            "genai_modality": "bot",
            "confidence_level": "reported-unverified",
            "network_indicators": [
                {
                    "type": "ip",
                    "value": "185.220.101.45",
                    "role": "scanner",
                    "evidence_span": "scanner host 185.220.101.45",
                }
            ],
        }
    )
    assert spec["corroboration_type"] == "network-telemetry"
    assert spec["corroboration_evidence"]["provider"] == "greynoise"


@patch.dict("os.environ", {"GREYNOISE_API_KEY": "test-key"})
@patch("packages.agents.corroborator.check_ip")
def test_corroborator_network_miss_stays_not_corroborated(mock_check):
    mock_check.return_value = GreynoiseResult(
        seen=False,
        noise=False,
        riot=False,
        classification=None,
        tags=[],
        raw={},
    )
    spec = apply_corroboration(
        {
            "technique_id": "T01",
            "genai_modality": "bot",
            "confidence_level": "reported-unverified",
            "network_indicators": [
                {
                    "type": "ip",
                    "value": "185.220.101.45",
                    "role": "scanner",
                    "evidence_span": "scanner host 185.220.101.45",
                }
            ],
        }
    )
    assert spec["corroboration_type"] == "not-yet-corroborated"
    assert "corroboration_evidence" not in spec


@patch.dict("os.environ", {}, clear=True)
def test_corroborator_skips_greynoise_without_key():
    spec = apply_corroboration(
        {
            "technique_id": "T01",
            "genai_modality": "bot",
            "confidence_level": "confirmed",
            "network_indicators": [
                {
                    "type": "ip",
                    "value": "185.220.101.45",
                    "role": "scanner",
                    "evidence_span": "scanner host 185.220.101.45",
                }
            ],
        }
    )
    assert spec["corroboration_type"] == "documentary-case"


def test_propose_indicators_ic3_advisory_table():
    from packages.osint.telemetry.indicators import propose_indicators_from_text

    text = """
    FBI cybersecurity advisory on a botnet used to compromise SOHO routers.
    Integrity Tech actors used IP addresses to control and manage the botnet.

    Domain IP Address Last Seen
    acqv.w8510.com 208.85.16.100 8/29/2024
    aewreiuicajo.w8510.com 45.77.231.209 9/1/2024
    """
    proposed = propose_indicators_from_text(text)
    values = {row["value"] for row in proposed}
    assert "208.85.16.100" in values
    assert "45.77.231.209" in values
    assert proposed[0]["role"] == "botnet"


def test_collect_network_indicators_merges_llm_and_text():
    from packages.osint.telemetry.indicators import collect_network_indicators

    text = (
        "A credential-stuffing botnet used scanner host 185.220.101.45 "
        "against payment authorization APIs."
    )
    llm_inds = [
        {
            "type": "ip",
            "value": "203.0.113.50",
            "role": "scanner",
            "evidence_span": "scanner host 203.0.113.50",
        }
    ]
    out = collect_network_indicators(text, llm_inds, "https://www.reuters.com/x")
    values = {row["value"] for row in out}
    assert "185.220.101.45" in values
    assert "203.0.113.50" not in values

    from packages.osint.telemetry.indicators import propose_indicators_from_text

    text = (
        "A credential-stuffing botnet used scanner host 185.220.101.45 "
        "against payment authorization APIs."
    )
    proposed = propose_indicators_from_text(text)
    assert len(proposed) == 1
    assert proposed[0]["value"] == "185.220.101.45"
    assert proposed[0]["role"] == "credential_stuffing"


def test_vendor_ioc_fixture_rule_extract_and_sanitize():
    from pathlib import Path

    from packages.agents.llm.extraction import rule_based_extract
    from packages.osint.fixtures import FIXTURE_FILES

    filename, url = FIXTURE_FILES["vendor_ioc_report"]
    text = (Path(__file__).resolve().parents[1] / "data" / "osint" / "fixtures" / filename).read_text()
    raw = rule_based_extract(text, url, "reuters.com")
    assert raw is not None
    assert raw["technique_id"] == "T07"
    sanitized = sanitize_network_indicators(text, raw["network_indicators"], url)
    assert len(sanitized) == 1
    assert sanitized[0]["value"] == "185.220.101.45"

    spec = apply_corroboration({**raw, "network_indicators": sanitized})
    assert spec["vector_class"] == "network_footprint"
    assert spec["corroboration_type"] in {
        "network-telemetry",
        "documentary-case",
        "not-yet-corroborated",
    }
