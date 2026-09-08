"""Readiness gates for advanced conditional capabilities.

B9 capabilities are useful, but they are not allowed into the production path
unless their data, thresholds and sponsor need are explicit. This module is pure
policy: it does not activate features by itself.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AdvancedCapability = Literal[
    "media_reuse",
    "genai_origin_probability",
    "gnn_misinfotelegraph_fr",
    "stix_serializer",
]
ReadinessStatus = Literal["ready", "blocked"]


REQUIREMENTS: dict[AdvancedCapability, tuple[str, ...]] = {
    "media_reuse": (
        "media_hash_populated",
        "non_empty_edges",
        "threshold_documented",
        "organic_control_checked",
        "sponsor_need_confirmed",
    ),
    "genai_origin_probability": (
        "detector_selected",
        "ood_limits_documented",
        "calibration_set_available",
        "false_positive_reviewed",
        "sponsor_need_confirmed",
    ),
    "gnn_misinfotelegraph_fr": (
        "gold_set_available",
        "channel_labels_balanced",
        "volume_sufficient",
        "baseline_outperformed",
        "explainability_plan_documented",
        "sponsor_need_confirmed",
    ),
    "stix_serializer": (
        "csirt_chain_confirmed",
        "mapping_documented",
        "tlp_marking_defined",
        "consumer_validated",
        "sponsor_need_confirmed",
    ),
}


class CapabilityReadinessInput(BaseModel):
    capability: str
    evidence: dict[str, bool] = Field(default_factory=dict)

    @field_validator("capability")
    @classmethod
    def _capability_known(cls, value: str) -> str:
        if value not in REQUIREMENTS:
            raise ValueError(f"unknown advanced capability: {value}")
        return value


class CapabilityReadinessDecision(BaseModel):
    capability: AdvancedCapability
    status: ReadinessStatus
    can_activate: bool
    satisfied_requirements: list[str]
    missing_requirements: list[str]
    decision_note: str


def assess_capability_readiness(
    readiness: CapabilityReadinessInput,
) -> CapabilityReadinessDecision:
    """Assess whether one B9 capability may enter the production path."""

    capability = readiness.capability
    requirements = REQUIREMENTS[capability]  # type: ignore[index]
    satisfied = [requirement for requirement in requirements if readiness.evidence.get(requirement)]
    missing = [requirement for requirement in requirements if requirement not in satisfied]
    can_activate = not missing
    return CapabilityReadinessDecision(
        capability=capability,  # type: ignore[arg-type]
        status="ready" if can_activate else "blocked",
        can_activate=can_activate,
        satisfied_requirements=satisfied,
        missing_requirements=missing,
        decision_note=(
            "All B9 activation requirements are satisfied."
            if can_activate
            else "Capability remains outside the production path until every requirement is met."
        ),
    )
