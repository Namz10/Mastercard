"""Golden Identify fixtures — schema, provenance, abstain, unsafe reject."""

from __future__ import annotations

from packages.agents.grounder import grounder_reject_reason
from packages.agents.identify_graph import run_identify_graph
from packages.agents.llm.extraction import extract_from_document, rule_based_extract
from packages.catalog.models import AttackSpec
from packages.osint.extract import extract_fixture_text
from packages.osint.fixtures import FIXTURE_FILES


def test_golden_fincen_and_rbi_schema(postgres_required):
    result = run_identify_graph(run_id="golden-fixtures")
    assert len(result["proposed_specs"]) >= 1
    urls = {d["url"] for d in result["extracted_docs"]}
    assert FIXTURE_FILES["fincen_alert004"][1] in urls
    assert FIXTURE_FILES["rbi_note"][1] in urls
    for spec in result["proposed_specs"]:
        AttackSpec.model_validate(spec)
        assert spec["status"] == "proposed"
        assert spec["source_urls"]


def test_golden_unsafe_how_to_rejected():
    reason = grounder_reject_reason(
        {
            "name": "malware payload dropper",
            "rail": "upi_like",
            "technique_id": "T13",
            "control_bypassed": ["otp"],
            "economic_class": "APP",
        },
        "step 1: download the exploit payload from the dark web",
    )
    assert reason == "exploit_or_unsafe_content"


def test_golden_abstain_irrelevant():
    spec = extract_from_document(
        "Today's cricket scores and weather in Mumbai.",
        "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "rbi.org.in",
    )
    assert spec["extraction_source"] == "abstain"


def test_golden_fixture_extractors_match_keys():
    fincen = extract_fixture_text("fincen_alert004")
    rbi = extract_fixture_text("rbi_note")
    f_spec = rule_based_extract(fincen.text, fincen.url, "fincen.gov")
    r_spec = rule_based_extract(rbi.text, rbi.url, "rbi.org.in")
    assert f_spec and r_spec
    assert f_spec["technique_id"] == "T09"
    assert r_spec["technique_id"] == "T13"
    assert f_spec["source_urls"] == [fincen.url]
    assert r_spec["source_urls"] == [rbi.url]
