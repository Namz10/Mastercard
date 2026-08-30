"""Stage 4 SAML-D adapter: FeatureComputer replay, no APP/ATO map, no native reindex."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from packages.eval.saml_d import (
    CSV_HEADERS,
    FORBIDDEN_FAMILIES,
    assert_csv_headers,
    calendar_from_ends,
    map_label_family,
    parse_event_ts,
    replay_saml_d,
    score_saml_d,
)


def _mini_csv(path: Path) -> Path:
    t0 = datetime(2022, 10, 7, 10, 0, 0)
    rows = []
    # fan-in: three payers → one sink within an hour
    for i, sender in enumerate((1001, 1002, 1003)):
        ts = t0 + timedelta(minutes=10 * i)
        rows.append(
            {
                "Time": ts.strftime("%H:%M:%S"),
                "Date": ts.strftime("%Y-%m-%d"),
                "Sender_account": sender,
                "Receiver_account": 9000,
                "Amount": 500.0,
                "Payment_currency": "UK pounds",
                "Received_currency": "UK pounds",
                "Sender_bank_location": "UK",
                "Receiver_bank_location": "UK",
                "Payment_type": "ACH",
                "Is_laundering": 1 if i else 0,
                "Laundering_type": "Fan-In" if i else "Normal_Fan-In",
            }
        )
    rows.append(
        {
            "Time": "12:00:00",
            "Date": "2022-10-07",
            "Sender_account": 2001,
            "Receiver_account": 2002,
            "Amount": 80.0,
            "Payment_currency": "UK pounds",
            "Received_currency": "UK pounds",
            "Sender_bank_location": "UK",
            "Receiver_bank_location": "UK",
            "Payment_type": "Cash",
            "Is_laundering": 1,
            "Laundering_type": "Over-Invoicing",
        }
    )
    rows.append(
        {
            "Time": "13:00:00",
            "Date": "2022-10-07",
            "Sender_account": 3001,
            "Receiver_account": 2002,
            "Amount": 20.0,
            "Payment_currency": "UK pounds",
            "Received_currency": "UK pounds",
            "Sender_bank_location": "UK",
            "Receiver_bank_location": "UK",
            "Payment_type": "Cheque",
            "Is_laundering": 1,
            "Laundering_type": "Behavioural_Change_1",
        }
    )
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_headers_reject_paper_prose_names():
    with pytest.raises(ValueError, match="Is_laundering"):
        assert_csv_headers(["Time", "Date", "Is_Suspicious", "Type"])


def test_map_never_app_or_ato():
    assert map_label_family(0, "Fan-In") == "normal"
    assert map_label_family(1, "Smurfing") == "mule"
    assert map_label_family(1, "Fan-In") == "mule"
    assert map_label_family(1, "Over-Invoicing") == "invoice_fraud"
    assert map_label_family(1, "Behavioural_Change_1") == "unmapped"
    assert map_label_family(1, "Single Large Transaction") == "unmapped"
    for fam in (map_label_family(1, t) for t in ("ATO", "APP", "Smurfing")):
        assert fam not in FORBIDDEN_FAMILIES


def test_parse_ts_iso_and_slash():
    ts = parse_event_ts("2022-10-07", "10:15:00")
    assert ts.tzinfo == timezone.utc
    assert ts.hour == 10


def test_calendar_from_ends_matches_first_last(tmp_path: Path):
    csv = _mini_csv(tmp_path / "SAML-D.csv")
    t0, t1 = calendar_from_ends(csv)
    df = replay_saml_d(csv)
    assert t0 == df["event_ts"].min()
    assert t1 == df["event_ts"].max()


def test_replay_computes_fan_in_and_zeros_stamps(tmp_path: Path):
    csv = _mini_csv(tmp_path / "SAML-D.csv")
    df = replay_saml_d(csv)
    assert list(CSV_HEADERS)
    assert df["call_active_flag"].eq(False).all()
    assert df["beneficiary_changed"].eq(False).all()
    assert df["is_new_device"].eq(0).all()
    assert not df["mapped_family"].isin(FORBIDDEN_FAMILIES).any()
    sink = df[df["payee"] == "SAML-9000"]
    assert len(sink) == 3
    assert int(sink.iloc[0]["fan_in_1h"]) == 0
    assert int(sink.iloc[2]["fan_in_1h"]) >= 1
    assert "Fan-In" not in df.columns  # native typology is not a feature
    assert "Sender_account" not in df.columns
    mapped = set(df["mapped_family"])
    assert "mule" in mapped
    assert "invoice_fraud" in mapped
    assert "unmapped" in mapped


def test_score_missing_csv_is_blocked(tmp_path: Path):
    body = score_saml_d(tmp_path / "missing.csv")
    assert body["status"] == "blocked_no_csv"


def test_score_forbids_negative_subsample(tmp_path: Path):
    csv = _mini_csv(tmp_path / "SAML-D.csv")
    with pytest.raises(ValueError, match="subsample"):
        score_saml_d(csv, negative_subsample_ratio=0.1)
