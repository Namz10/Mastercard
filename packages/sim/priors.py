"""WorldPriors load + amount/hour sampling (Plan 08 Phase A)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRIORS_PATH = _ROOT / "data" / "priors.json"

TICKET_STAT_MEAN = "mean_from_value_over_volume"


class Provenance(BaseModel):
    source_url: str
    note: str | None = None


class Caps(BaseModel):
    txn_min_minor: int = Field(ge=1)
    txn_max_minor: int = Field(gt=1)
    day_max_minor: int = Field(gt=1)

    @model_validator(mode="after")
    def _ordered(self) -> Caps:
        if self.txn_min_minor > self.txn_max_minor:
            raise ValueError("txn_min_minor must be <= txn_max_minor")
        return self


class HourOfDay(BaseModel):
    kind: Literal["assumption"] = "assumption"
    note: str | None = None
    peaks: list[int] = Field(default_factory=lambda: [11, 20])
    peak_hours: list[int] = Field(default_factory=lambda: [10, 11, 12, 19, 20, 21, 22])

    @field_validator("peak_hours")
    @classmethod
    def _hours(cls, value: list[int]) -> list[int]:
        for h in value:
            if h < 0 or h > 23:
                raise ValueError("hour must be 0..23")
        return value


class CategoryPrior(BaseModel):
    mean_rupees: float = Field(gt=0)
    rail: str = "upi_like"
    kind: Literal["mean_from_value_over_volume", "assumption"] | None = None


class WorldPriors(BaseModel):
    version: int = 1
    as_of_month: str
    ticket_stat: Literal["mean_from_value_over_volume"]
    provenance: list[Provenance]
    p2m_share: float = Field(gt=0, lt=1)
    caps: Caps
    hour_of_day: HourOfDay
    lognormal_sigma: float = Field(gt=0, le=2)
    categories: dict[str, CategoryPrior]
    persona_weights: dict[str, float]
    persona_txn_per_day: dict[str, float]

    @field_validator("ticket_stat")
    @classmethod
    def _not_median(cls, value: str) -> str:
        if "median" in value.lower():
            raise ValueError("ticket_stat must not be median")
        return value

    @model_validator(mode="after")
    def _personas(self) -> WorldPriors:
        w = sum(self.persona_weights.values())
        if abs(w - 1.0) > 0.02:
            raise ValueError("persona_weights must sum to ~1")
        for name in self.persona_weights:
            if name not in self.persona_txn_per_day:
                raise ValueError(f"missing txn rate for persona {name}")
        return self


def load_priors(path: Path | None = None) -> WorldPriors:
    target = path or DEFAULT_PRIORS_PATH
    return WorldPriors.model_validate_json(target.read_text(encoding="utf-8"))


def rupees_to_minor(rupees: float) -> int:
    return int(round(rupees * 100))


def clamp_amount_minor(amount_minor: int, caps: Caps) -> int:
    return max(caps.txn_min_minor, min(caps.txn_max_minor, amount_minor))


def lognormal_mu_for_mean(mean_rupees: float, sigma: float) -> float:
    """mu such that E[LogNormal(mu, sigma^2)] = mean_rupees."""
    return float(np.log(mean_rupees) - 0.5 * sigma * sigma)


def sample_amount_minor(
    rng: np.random.Generator,
    priors: WorldPriors,
    category: str,
) -> int:
    spec = priors.categories[category]
    sigma = priors.lognormal_sigma
    mu = lognormal_mu_for_mean(spec.mean_rupees, sigma)
    rupees = float(rng.lognormal(mu, sigma))
    minor = rupees_to_minor(rupees)
    return clamp_amount_minor(minor, priors.caps)


def sample_hour(rng: np.random.Generator, priors: WorldPriors) -> int:
    """Discrete hour draw. Peak hours get higher mass (assumption, not a public table)."""
    hours = np.arange(24)
    weights = np.ones(24, dtype=np.float64)
    for h in priors.hour_of_day.peak_hours:
        weights[h] += 4.0
    weights /= weights.sum()
    return int(rng.choice(hours, p=weights))


def expected_mean_rupees(priors: WorldPriors, category: str) -> float:
    return priors.categories[category].mean_rupees
