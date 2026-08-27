"""Catalog model and loader tests."""

import pytest
from pydantic import ValidationError

from packages.catalog.loader import catalog_summary, load_catalog_yaml
from packages.catalog.models import AttackSpec, ConfidenceLevel, GenerateMode


def test_import_attack_spec():
    from packages.catalog.models import AttackSpec as AS

    assert AS is AttackSpec


def test_seed_loads_all_techniques():
    specs = load_catalog_yaml()
    summary = catalog_summary(specs)
    assert summary["count"] >= 28
    assert summary["missing_techniques"] == []


def test_confirmed_requires_urls():
    with pytest.raises(ValidationError):
        AttackSpec(
            vector_id="bad",
            technique_id="T01",
            name="Test",
            category=1,
            rail="upi_like",
            lifecycle_stage="disbursement_mule",
            genai_modality="bot",
            social_surface="none",
            actor_type="consumer",
            economic_class="mule",
            is_authorized_push=False,
            generate_mode="name_only",
            source_tier=1,
            confidence_level="confirmed",
            vector_class="network_footprint",
            source_urls=[],
        )


def test_generate_requires_valid_signals():
    with pytest.raises(ValidationError):
        AttackSpec(
            vector_id="bad-gen",
            technique_id="T01",
            name="Test",
            category=1,
            rail="upi_like",
            lifecycle_stage="disbursement_mule",
            genai_modality="bot",
            social_surface="none",
            actor_type="consumer",
            economic_class="mule",
            is_authorized_push=False,
            generate_mode="generate",
            source_tier=1,
            confidence_level="reported-unverified",
            vector_class="network_footprint",
            simulatable_signals={},
            simulator={"injector_id": "graph_mule", "param_schema": {}},
        )


def test_high_dual_use_only_name_only():
    with pytest.raises(ValidationError):
        AttackSpec(
            vector_id="bad-dual",
            technique_id="T07",
            name="Test",
            category=1,
            rail="card_cnp",
            lifecycle_stage="authorization",
            genai_modality="bot",
            social_surface="none",
            actor_type="consumer",
            economic_class="CNP",
            is_authorized_push=False,
            generate_mode="generate",
            dual_use_rating="high",
            source_tier=3,
            confidence_level="reported-unverified",
            vector_class="network_footprint",
            simulatable_signals={
                "fan_in_1h": 1,
                "fan_out_ttl_hours": 1.0,
                "smurf_cap_ratio": 0.5,
                "hop_rails": ["card_cnp"],
                "mule_account_age_days": 1,
                "cashout_mcc_or_sink": "x",
            },
            simulator={"injector_id": "graph_mule", "param_schema": {}},
        )
