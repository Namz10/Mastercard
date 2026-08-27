#!/usr/bin/env python3
"""GreyNoise-only test — no Postgres, no Tavily, no full run.sh.

Runs the telemetry slice end-to-end on the IOC fixture article:
  propose indicators from text → sanitize → corroborator → optional live GreyNoise API

Usage:
  .venv/bin/python scripts/test_greynoise.py           # unit checks + pipeline smoke
  .venv/bin/python scripts/test_greynoise.py --live    # also call GreyNoise API (needs GREYNOISE_API_KEY)
  .venv/bin/python scripts/test_greynoise.py --pytest  # run mocked unit tests only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.env import load_project_env


def _run_pytest() -> int:
    py = ROOT / ".venv" / "bin" / "python"
    if not py.is_file():
        py = Path(sys.executable)
    print("==> GreyNoise unit tests (mocked API)", flush=True)
    result = subprocess.run(
        [str(py), "-m", "pytest", "tests/test_network_indicators.py", "-q"],
        cwd=ROOT,
    )
    return result.returncode


def _pipeline_smoke(*, live_api: bool) -> int:
    from packages.agents.corroborator import apply_corroboration
    from packages.osint.fixtures import FIXTURE_FILES
    from packages.osint.telemetry.greynoise import check_ip, qualifies_for_corroboration
    from packages.osint.telemetry.indicators import (
        indicator_lookup_ip,
        propose_indicators_from_text,
        sanitize_network_indicators,
    )

    filename, url = FIXTURE_FILES["vendor_ioc_report"]
    text = (ROOT / "data" / "osint" / "fixtures" / filename).read_text(encoding="utf-8")

    print("\n==> Pipeline smoke (IOC fixture article)", flush=True)
    proposed = propose_indicators_from_text(text)
    print(f"proposed_from_text={len(proposed)}", flush=True)
    if not proposed:
        print("FAIL: no indicators proposed from fixture text", flush=True)
        return 1

    sanitized = sanitize_network_indicators(text, proposed, url)
    print(f"sanitized={len(sanitized)} value={sanitized[0].get('value')}", flush=True)
    if not sanitized:
        print("FAIL: sanitize dropped all indicators", flush=True)
        return 1

    spec = apply_corroboration(
        {
            "technique_id": "T07",
            "genai_modality": "bot",
            "confidence_level": "reported-unverified",
            "network_indicators": sanitized,
        }
    )
    print(
        f"vector_class={spec.get('vector_class')} "
        f"corroboration_type={spec.get('corroboration_type')}",
        flush=True,
    )

    api_key = os.getenv("GREYNOISE_API_KEY", "").strip()
    if live_api:
        if not api_key:
            print("FAIL: --live requires GREYNOISE_API_KEY in .env", flush=True)
            return 1
        ip = indicator_lookup_ip(sanitized[0])
        print(f"\n==> Live GreyNoise Community API lookup ip={ip}", flush=True)
        result = check_ip(ip, api_key=api_key)
        if result is None:
            print("FAIL: GreyNoise API unreachable or non-200", flush=True)
            return 1
        qualifies = qualifies_for_corroboration(result)
        print(
            f"greynoise_seen={result.seen} noise={result.noise} "
            f"riot={result.riot} classification={result.classification} "
            f"tags={result.tags} qualifies={qualifies}",
            flush=True,
        )
        if qualifies and spec.get("corroboration_type") != "network-telemetry":
            print("WARN: API qualifies but corroborator did not upgrade (check corroborator)", flush=True)
        elif not qualifies:
            print(
                "greynoise_miss=ok (IP not currently seen as noise — honest not-yet-corroborated)",
                flush=True,
            )
    elif api_key:
        print("greynoise_live_skipped (pass --live to hit API; key is set)", flush=True)
    else:
        print("greynoise_skipped=no_api_key", flush=True)

    if spec.get("vector_class") != "network_footprint":
        print("FAIL: expected network_footprint", flush=True)
        return 1
    if spec.get("corroboration_type") not in {
        "network-telemetry",
        "not-yet-corroborated",
        "documentary-case",
    }:
        print("FAIL: unexpected corroboration_type", flush=True)
        return 1

    print("\n=== GREYNOISE TEST PASSED ===", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GreyNoise-only telemetry test")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call live GreyNoise API (requires GREYNOISE_API_KEY)",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Run only tests/test_network_indicators.py and exit",
    )
    args = parser.parse_args()

    load_project_env()

    if args.pytest:
        return _run_pytest()

    code = _run_pytest()
    if code != 0:
        return code
    return _pipeline_smoke(live_api=args.live)


if __name__ == "__main__":
    raise SystemExit(main())
