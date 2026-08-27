"""Pydantic v2 AttackSpec — unified catalog model."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from packages.catalog.schemas import validate_simulatable_signals


class TechniqueId(str, Enum):
    T01 = "T01"
    T02 = "T02"
    T03 = "T03"
    T04 = "T04"
    T05 = "T05"
    T06 = "T06"
    T07 = "T07"
    T08 = "T08"
    T09 = "T09"
    T10 = "T10"
    T11 = "T11"
    T12 = "T12"
    T13 = "T13"
    T14 = "T14"
    T15 = "T15"
    T16 = "T16"
    T17 = "T17"
    T18 = "T18"
    T19 = "T19"
    T20 = "T20"
    T21 = "T21"
    T22 = "T22"
    T23 = "T23"
    T24 = "T24"


class Status(str, Enum):
    proposed = "proposed"
    rejected = "rejected"
    rejected_unsafe = "rejected_unsafe"
    open = "open"
    generating = "generating"
    defending = "defending"
    solved = "solved"


class GenerateMode(str, Enum):
    generate = "generate"
    name_only = "name_only"


class ConfidenceLevel(str, Enum):
    confirmed = "confirmed"
    reported_unverified = "reported-unverified"


class CorroborationType(str, Enum):
    network_telemetry = "network-telemetry"
    documentary_case = "documentary-case"
    not_yet_corroborated = "not-yet-corroborated"


class VectorClass(str, Enum):
    network_footprint = "network_footprint"
    human_social = "human_social"


class Rail(str, Enum):
    upi_like = "upi_like"
    imps = "imps"
    neft = "neft"
    rtgs = "rtgs"
    card_cnp = "card_cnp"
    card_cp = "card_cp"
    wire = "wire"
    crypto_offramp = "crypto_offramp"
    onboarding = "onboarding"


class LifecycleStage(str, Enum):
    onboarding_kyc = "onboarding_kyc"
    account_access_ato = "account_access_ato"
    payment_initiation = "payment_initiation"
    authorization = "authorization"
    clearing_settlement = "clearing_settlement"
    disbursement_mule = "disbursement_mule"
    dispute_sar = "dispute_sar"


class GenaiModality(str, Enum):
    text = "text"
    voice = "voice"
    video = "video"
    document = "document"
    bot = "bot"
    poisoning = "poisoning"
    mixed = "mixed"


class SocialSurface(str, Enum):
    email = "email"
    sms = "sms"
    voice = "voice"
    video_call = "video_call"
    in_app = "in_app"
    merchant = "merchant"
    none = "none"


class EconomicClass(str, Enum):
    APP = "APP"
    ATO = "ATO"
    CNP = "CNP"
    mule = "mule"
    BEC = "BEC"
    detector = "detector"


class ActorType(str, Enum):
    consumer = "consumer"
    merchant = "merchant"


class DualUseRating(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SimulatorSpec(BaseModel):
    injector_id: str
    param_schema: dict = Field(default_factory=dict)


class AttackSpec(BaseModel):
    vector_id: str
    technique_id: TechniqueId
    name: str
    one_liner: str | None = None
    category: Annotated[int, Field(ge=1, le=5)]
    rail: Rail
    lifecycle_stage: LifecycleStage
    genai_modality: GenaiModality
    social_surface: SocialSurface
    control_bypassed: list[str] = Field(default_factory=list)
    actor_type: ActorType
    economic_class: EconomicClass
    is_authorized_push: bool
    generate_mode: GenerateMode
    dual_use_rating: DualUseRating = DualUseRating.low
    source_tier: Annotated[int, Field(ge=1, le=5)]
    confidence_level: ConfidenceLevel
    corroboration_type: CorroborationType = CorroborationType.not_yet_corroborated
    vector_class: VectorClass
    source_urls: list[HttpUrl] = Field(default_factory=list)
    simulatable_signals: dict = Field(default_factory=dict)
    canary_eligible: bool = False
    simulator: SimulatorSpec | None = None
    features_expected: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    novelty_notes: str | None = None
    status: Status = Status.proposed

    @field_validator("source_urls", mode="before")
    @classmethod
    def coerce_urls(cls, v: list | None) -> list:
        if v is None:
            return []
        return v

    @model_validator(mode="after")
    def validate_confirmed_urls(self) -> "AttackSpec":
        if self.confidence_level == ConfidenceLevel.confirmed and not self.source_urls:
            raise ValueError("confidence_level=confirmed requires non-empty source_urls")
        return self

    @model_validator(mode="after")
    def validate_dual_use(self) -> "AttackSpec":
        if self.dual_use_rating == DualUseRating.high and self.generate_mode != GenerateMode.name_only:
            raise ValueError("dual_use_rating=high only allowed when generate_mode=name_only")
        return self

    @model_validator(mode="after")
    def validate_generate_signals(self) -> "AttackSpec":
        if self.generate_mode != GenerateMode.generate:
            return self
        if not self.simulator or not self.simulator.injector_id:
            raise ValueError("generate_mode=generate requires simulator.injector_id")
        validate_simulatable_signals(self.simulator.injector_id, self.simulatable_signals)
        return self
