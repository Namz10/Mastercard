"""Phase F — WorldCalibrator fixture HTML → HITL patch (no live net)."""

from __future__ import annotations

import inspect
from pathlib import Path

from packages.sim.calibrator import (
    FIXTURE_DIR,
    apply_proposal,
    fixture_path,
    hitl_decide,
    propose_from_path,
)
from packages.sim.priors import DEFAULT_PRIORS_PATH, load_priors

import packages.sim.calibrator as calibrator_mod
from apps.api.routes.generate import (
    CalibrateWorldRequest,
    calibrate_world,
    calibrate_world_fixtures,
)
from apps.api.routes.identify import router as identify_router


def test_no_live_fetch_in_calibrator():
    assert not hasattr(calibrator_mod, "httpx")
    assert "httpx" not in calibrator_mod.__dict__
    assert "tavily" not in calibrator_mod.__dict__
    src = inspect.getsource(calibrator_mod)
    assert "import httpx" not in src
    assert "import tavily" not in src
    assert "urllib.request" not in src


def test_good_html_proposes_patch_not_hours():
    priors = load_priors()
    proposal = propose_from_path(fixture_path("good_p2m_table"), current=priors)
    assert proposal.status == "propose"
    assert proposal.reason == "numeric_gate_passed"
    assert "source_url" in proposal.model_dump()
    assert proposal.as_of_month == "2024-06"
    assert proposal.raw_quotes
    assert "categories.grocery.mean_rupees" in proposal.fields_updated
    assert "p2m_share" in proposal.fields_updated
    assert "hour_of_day" in proposal.fields_unchanged
    assert "categories.salary" in proposal.fields_unchanged
    assert "categories.rent" in proposal.fields_unchanged
    assert "hour_of_day" not in proposal.patch
    assert "salary" not in (proposal.patch.get("categories") or {})
    assert proposal.patch["categories"]["grocery"]["mean_rupees"] == 220
    assert proposal.patch["p2m_share"] == 0.65
    updated = apply_proposal(priors, proposal)
    assert updated.categories["grocery"].mean_rupees == 220
    assert updated.hour_of_day.peak_hours == priors.hour_of_day.peak_hours
    assert updated.categories["salary"].mean_rupees == priors.categories["salary"].mean_rupees
    assert updated.categories["rent"].mean_rupees == priors.categories["rent"].mean_rupees
    assert updated.ticket_stat == "mean_from_value_over_volume"


def test_avg_mismatch_abstains():
    proposal = propose_from_path(fixture_path("avg_mismatch"))
    assert proposal.status == "abstain"
    assert proposal.reason == "value_volume_avg_mismatch"
    assert proposal.fields_updated == []
    assert proposal.patch == {}


def test_pdf_abstains_no_pipeline():
    proposal = propose_from_path(fixture_path("npci_stats.pdf"))
    assert proposal.status == "abstain"
    assert proposal.reason == "pdf_not_supported"
    assert proposal.patch == {}


def test_fraud_news_does_not_fill_hours():
    priors = load_priors()
    proposal = propose_from_path(fixture_path("fraud_news_hours"), current=priors)
    assert proposal.status == "abstain"
    assert "hour_of_day" not in proposal.patch
    assert proposal.patch == {}
    assert priors.hour_of_day.kind == "assumption"


def test_reject_keeps_seed(tmp_path: Path):
    seed = load_priors()
    dest = tmp_path / "priors.json"
    dest.write_text(DEFAULT_PRIORS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    proposal = propose_from_path(fixture_path("good_p2m_table"), current=seed)
    assert proposal.status == "propose"
    result = hitl_decide("reject", proposal, seed_path=DEFAULT_PRIORS_PATH, dest_path=dest)
    assert result["applied"] is False
    assert result["seed_unchanged"] is True
    kept = load_priors(dest)
    assert kept.categories["grocery"].mean_rupees == seed.categories["grocery"].mean_rupees
    assert kept.as_of_month == seed.as_of_month
    assert load_priors().categories["grocery"].mean_rupees == 214


def test_approve_writes_dest_not_repo_seed(tmp_path: Path):
    seed = load_priors()
    dest = tmp_path / "priors.json"
    dest.write_text(DEFAULT_PRIORS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    proposal = propose_from_path(fixture_path("good_p2m_table"), current=seed)
    result = hitl_decide("approve", proposal, seed_path=DEFAULT_PRIORS_PATH, dest_path=dest)
    assert result["applied"] is True
    assert result["seed_unchanged"] is True
    patched = load_priors(dest)
    assert patched.categories["grocery"].mean_rupees == 220
    assert patched.p2m_share == 0.65
    assert patched.as_of_month == "2024-06"
    repo = load_priors()
    assert repo.categories["grocery"].mean_rupees == 214
    assert repo.as_of_month == "2024-03"


def test_generate_route_not_identify():
    identify_paths = {getattr(r, "path", "") for r in identify_router.routes}
    assert not any("calibrate-world" in p for p in identify_paths)
    listed = calibrate_world_fixtures()
    assert "good_p2m_table.html" in listed["items"]
    body = calibrate_world(CalibrateWorldRequest(fixture_id="good_p2m_table"))
    assert body["status"] == "propose"
    assert FIXTURE_DIR.is_dir()
