"""Pocket scoring primitives.

A pocket score is an explainable synthesis of several bounded signals. This
module is intentionally pure: it does not run community detection and does not
query PostgreSQL. Upstream analyzers provide the metrics; this module turns them
into a canonical PocketRecord.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.shared.analytical_contract import CoverageLimit, PocketRecord, PocketType


class PocketMetrics(BaseModel):
    """Bounded evidence used to score one information pocket."""

    claim_exposure: float = Field(default=0.0, ge=0.0, le=1.0)
    coordination_density: float = Field(default=0.0, ge=0.0, le=1.0)
    bridge_presence: float = Field(default=0.0, ge=0.0, le=1.0)
    recidivism: float = Field(default=0.0, ge=0.0, le=1.0)
    stability: float = Field(default=0.0, ge=0.0, le=1.0)
    volume: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage: float = Field(default=1.0, ge=0.0, le=1.0)


WEIGHTS = {
    "claim_exposure": 0.25,
    "coordination_density": 0.25,
    "bridge_presence": 0.15,
    "recidivism": 0.15,
    "stability": 0.10,
    "volume": 0.10,
}


def score_pocket(metrics: PocketMetrics) -> float:
    """Compute a bounded pocket score from evidence metrics.

    Coverage is a multiplier, not a positive signal. Weak coverage can only
    reduce confidence in the pocket score.
    """

    base = sum(getattr(metrics, key) * weight for key, weight in WEIGHTS.items())
    return round(max(0.0, min(1.0, base * metrics.coverage)), 6)


def infer_pocket_type(metrics: PocketMetrics) -> PocketType:
    """Infer the dominant pocket type from the strongest signal."""

    candidates = {
        "diffusion": metrics.claim_exposure,
        "coordination": metrics.coordination_density,
        "bridging": metrics.bridge_presence,
        "recidivism": metrics.recidivism,
    }
    top_type, top_value = max(candidates.items(), key=lambda item: item[1])
    if top_value <= 0.0:
        return "mixed"

    near_top = sum(1 for value in candidates.values() if value >= max(0.01, top_value * 0.85))
    if near_top >= 2:
        return "mixed"
    return top_type  # type: ignore[return-value]


class PocketInput(BaseModel):
    """Input envelope for building a PocketRecord."""

    pocket_id: str
    mission: str = "russosphere"
    window_start: str
    window_end: str
    member_channel_ids: list[int]
    metrics: PocketMetrics
    claim_ids: list[str] = Field(default_factory=list)
    coordination_edge_refs: list[str] = Field(default_factory=list)
    coverage_limits: list[CoverageLimit] = Field(default_factory=list)

    @field_validator("pocket_id", "window_start", "window_end")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("pocket id and window bounds are required")
        return value


def build_pocket_record(inp: PocketInput) -> PocketRecord:
    """Build a canonical PocketRecord from bounded metrics."""

    metrics = inp.metrics
    return PocketRecord(
        pocket_id=inp.pocket_id,
        mission=inp.mission,
        pocket_type=infer_pocket_type(metrics),
        window_start=inp.window_start,
        window_end=inp.window_end,
        member_channel_ids=inp.member_channel_ids,
        pocket_score=score_pocket(metrics),
        claim_ids=inp.claim_ids,
        coordination_edge_refs=inp.coordination_edge_refs,
        stability_score=metrics.stability,
        coverage_limits=inp.coverage_limits,
    )
