"""Injector param schemas for simulatable_signals validation."""

from typing import Literal

from pydantic import BaseModel, Field

RailEnum = Literal[
    "upi_like",
    "imps",
    "neft",
    "rtgs",
    "card_cnp",
    "card_cp",
    "wire",
    "crypto_offramp",
    "onboarding",
]

InjectorId = Literal[
    "graph_mule",
    "identity_trajectory",
    "app_session",
    "doc_beneficiary",
]


class GraphMuleSignals(BaseModel):
    fan_in_1h: int = Field(ge=0)
    fan_out_ttl_hours: float = Field(gt=0)
    smurf_cap_ratio: float = Field(gt=0, le=1)
    hop_rails: list[RailEnum]
    mule_account_age_days: int = Field(ge=0)
    cashout_mcc_or_sink: str


class IdentityTrajectorySignals(BaseModel):
    seasoning_days: int
    seasoning_txn_count: int
    liveness_score: float = Field(ge=0, le=1)
    doc_consistency: float = Field(ge=0, le=1)
    device_hash_shift: bool
    kyc_tier: str


class AppSessionSignals(BaseModel):
    persuasion_labels: list[str]
    call_active_flag: bool
    copy_paste_payee_flag: bool
    pause_ms: int = Field(ge=0)
    new_payee: bool
    urgency_pressure: float = Field(ge=0, le=1)
    transcript_ref: str | None = None


class DocBeneficiarySignals(BaseModel):
    beneficiary_changed: bool
    gstin_checksum_ok: bool
    amount_vs_invoice_delta: float
    lookalike_domain_flag: bool


INJECTOR_SIGNAL_MODELS: dict[str, type[BaseModel]] = {
    "graph_mule": GraphMuleSignals,
    "identity_trajectory": IdentityTrajectorySignals,
    "app_session": AppSessionSignals,
    "doc_beneficiary": DocBeneficiarySignals,
}


def validate_simulatable_signals(injector_id: str, signals: dict) -> dict:
    """Validate and normalize simulatable_signals for a given injector."""
    model_cls = INJECTOR_SIGNAL_MODELS.get(injector_id)
    if model_cls is None:
        raise ValueError(f"Unknown injector_id: {injector_id}")
    return model_cls.model_validate(signals).model_dump()
