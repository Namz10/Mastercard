"""Phase 4 — scale pipeline & production infrastructure test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from packages.config.scale import (
    SCALE_CONFIRM_SEED,
    SCALE_FULLMIX_RUN_ID,
    SCALE_GCONFIRM_RUN_ID,
    SCALE_GDEV_RUN_ID,
    SCALE_GDEV_SEED,
    SCALE_GTEST_RUN_ID,
    SCALE_GTEST_SEED,
    SCALE_N_CUSTOMERS,
    SCALE_N_MERCHANTS,
    SCALE_SIM_DAYS,
    SCALE_TRAIN_SEED,
)
from packages.eval.fit import fit_champion, run_paths
from packages.sim.export import export_run
from packages.sim.ledger import make_event


# ---------------------------------------------------------------------------
# 4.1 — makefile generate-scale block has no t13 vector_id pin
# ---------------------------------------------------------------------------
def test_makefile_generate_scale_has_no_t13_vector_id():
    makefile = Path("Makefile").read_text()
    # Find the generate-scale recipe lines
    lines = makefile.splitlines()
    gen_scale_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("generate-scale:"):
            gen_scale_idx = i
            break
    assert gen_scale_idx != -1, "generate-scale target missing in Makefile"

    # Gather recipe text up to next target or empty line
    recipe_lines = []
    for line in lines[gen_scale_idx + 1 :]:
        if line.startswith(("\t", " ")) or not line.strip():
            recipe_lines.append(line)
        else:
            break
    block = "\n".join(recipe_lines)

    assert "t13-upi-impersonation-app" not in block, (
        "generate-scale must not be pinned to t13-upi-impersonation-app; full mix must run"
    )
    assert "make-scale-fullmix" in block, (
        "generate-scale target must use run_id='make-scale-fullmix'"
    )


# ---------------------------------------------------------------------------
# 4.2 — makefile generate-validate still has t13 vector_id pin
# ---------------------------------------------------------------------------
def test_makefile_generate_validate_still_t13():
    makefile = Path("Makefile").read_text()
    lines = makefile.splitlines()
    gen_val_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("generate-validate:"):
            gen_val_idx = i
            break
    assert gen_val_idx != -1, "generate-validate target missing in Makefile"

    recipe_lines = []
    for line in lines[gen_val_idx + 1 :]:
        if line.startswith(("\t", " ")) or not line.strip():
            recipe_lines.append(line)
        else:
            break
    block = "\n".join(recipe_lines)

    assert "t13-upi-impersonation-app" in block, (
        "generate-validate must maintain the t13 smoke test pin"
    )


# ---------------------------------------------------------------------------
# 4.3 — makefile has defend-fit, defend-gtest, defend-gdev targets
# ---------------------------------------------------------------------------
def test_makefile_has_defend_gtest_all_rows():
    makefile = Path("Makefile").read_text()
    phony_line = ""
    for line in makefile.splitlines():
        if line.startswith(".PHONY:"):
            phony_line = line
            break
    assert phony_line, "Makefile missing .PHONY header"

    for target in ("defend-fit", "defend-gtest", "defend-gdev", "defend-loop-m"):
        assert target in phony_line, f"{target} missing in .PHONY header"
        assert f"{target}:" in makefile, f"{target} target missing in Makefile"

    # Check defend-gtest calls score_run with all_rows=True
    idx = makefile.find("defend-gtest:")
    block = makefile[idx : idx + 1000]
    assert "all_rows=True" in block or "all_rows= True" in block, (
        "defend-gtest must pass all_rows=True to score_run"
    )


# ---------------------------------------------------------------------------
# 4.4 — validate-all does not invoke generate-scale
# ---------------------------------------------------------------------------
def test_validate_all_does_not_call_generate_scale():
    makefile = Path("Makefile").read_text()
    lines = makefile.splitlines()
    val_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("validate-all:"):
            val_idx = i
            break
    assert val_idx != -1, "validate-all target missing in Makefile"

    recipe_lines = []
    for line in lines[val_idx + 1 :]:
        if line.startswith(("\t", "@", " ")) or not line.strip():
            recipe_lines.append(line)
        else:
            break
    block = "\n".join(recipe_lines)

    assert "generate-scale" not in block, (
        "validate-all must not run generate-scale (CI scale run is manual/Makefile-triggered only)"
    )


# ---------------------------------------------------------------------------
# 4.5 — production scale constants pinned in packages/config/scale.py
# ---------------------------------------------------------------------------
def test_scale_config_constants():
    assert SCALE_FULLMIX_RUN_ID == "make-scale-fullmix"
    assert SCALE_GTEST_RUN_ID == "make-gtest"
    assert SCALE_GDEV_RUN_ID == "make-gdev"
    assert SCALE_GCONFIRM_RUN_ID == "make-gconfirm"

    assert SCALE_TRAIN_SEED == 42
    assert SCALE_GTEST_SEED == 43
    assert SCALE_GDEV_SEED == 44
    assert SCALE_CONFIRM_SEED == 45

    assert SCALE_N_CUSTOMERS == 2400
    assert SCALE_N_MERCHANTS == 120
    assert SCALE_SIM_DAYS == 90


# ---------------------------------------------------------------------------
# 4.6 — export_run atomic writes, manifest.json, and _DONE marker
# ---------------------------------------------------------------------------
def test_atomic_run_export_writes_done_and_manifest(tmp_path: Path):
    events = [
        make_event(
            seq=1,
            ts=pd.Timestamp("2024-01-01T10:00:00Z"),
            rail="upi_like",
            payer="VID-SIM-C-000001",
            payee="VID-SIM-M-000001",
            amount_minor=1000,
            label_family="normal",
            features_auth={"fan_in_1h": 0, "kyc_tier": "tier2"},
            kyc_tier="tier2",
        )
    ]
    sidecar = {"run_id": "test-run", "world_seed": 42, "n_customers": 16}
    paths = export_run(events, sidecar, "test-run", runs_dir=tmp_path)

    run_dir = tmp_path / "test-run"
    assert (run_dir / "_DONE").is_file(), "_DONE marker file must exist after export_run"
    assert (run_dir / "manifest.json").is_file(), "manifest.json file must exist after export_run"

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "test-run"
    assert manifest["world_seed"] == 42
    assert manifest["row_count"] == 1
    assert "wall_clock_seconds" in manifest


# ---------------------------------------------------------------------------
# 4.7 — run_paths raises FileNotFoundError if _DONE marker is missing
# ---------------------------------------------------------------------------
def test_incomplete_run_without_done_raises_error(tmp_path: Path):
    run_dir = tmp_path / "incomplete-run"
    run_dir.mkdir(parents=True)
    (run_dir / "train.parquet").touch()
    (run_dir / "split.parquet").touch()
    (run_dir / "sidecar.json").touch()

    # Without _DONE, run_paths should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="incomplete"):
        run_paths("incomplete-run", runs_dir=tmp_path)

    with pytest.raises(FileNotFoundError, match="incomplete"):
        fit_champion("incomplete-run", runs_dir=tmp_path)
