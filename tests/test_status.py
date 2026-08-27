"""HITL + Atlas status persistence on real Postgres."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status


@pytest.fixture()
def db(postgres_required):
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_cannot_jump_solved_from_proposed(db):
    from packages.agents.librarian_db import merge_proposed_spec

    merge_proposed_spec(
        db,
        {
            "vector_id": "hitl-test-t13",
            "technique_id": "T13",
            "name": "HITL test APP",
            "one_liner": "test",
            "category": 3,
            "rail": "upi_like",
            "lifecycle_stage": "payment_initiation",
            "genai_modality": "voice",
            "social_surface": "voice",
            "control_bypassed": ["human_callback"],
            "actor_type": "consumer",
            "economic_class": "APP",
            "is_authorized_push": True,
            "generate_mode": "generate",
            "source_tier": 1,
            "confidence_level": "confirmed",
            "vector_class": "human_social",
            "source_urls": ["https://www.fincen.gov/x"],
            "simulatable_signals": {
                "persuasion_labels": ["x"],
                "call_active_flag": True,
                "copy_paste_payee_flag": True,
                "pause_ms": 0,
                "new_payee": True,
                "urgency_pressure": 0.5,
            },
            "simulator": {"injector_id": "app_session", "param_schema": {}},
            "status": "proposed",
        },
    )
    with pytest.raises(IllegalStatusTransition):
        transition_atlas_status(db, "hitl-test-t13", "solved")
    row = transition_atlas_status(db, "hitl-test-t13", "open")
    assert row.status == "open"


def test_edit_validates_pydantic(db):
    with pytest.raises(ValidationError):
        transition_atlas_status(
            db,
            "t13-upi-impersonation-app",
            "open",
            {"confidence_level": "confirmed", "source_urls": []},
        )
