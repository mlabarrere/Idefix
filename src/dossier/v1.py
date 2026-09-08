"""Evidence Dossier v1 contract.

This is the production-oriented dossier object for the remediation roadmap. It
is separate from the historical frontend episode dossier builder, and can be
used by future export/UI work without changing the existing static bundle.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.shared.analytical_contract import (
    AttributionTier,
    ChannelRoleEvidence,
    CoordinationEdgeEvidence,
    CoverageLimit,
    EpisodeRecord,
    MessageEvidence,
    MethodVersion,
    PocketRecord,
    ScoreRunRecord,
)
from src.shared.dossier import COVERAGE_CALLOUT_FR


class EvidenceDossierV1(BaseModel):
    schema_version: str = "evidence-dossier/v1"
    dossier_id: str
    mission: str
    episode: EpisodeRecord
    attribution_tier: AttributionTier
    method_versions: MethodVersion
    score_run: ScoreRunRecord | None = None
    channel_roles: list[ChannelRoleEvidence] = Field(default_factory=list)
    pockets: list[PocketRecord] = Field(default_factory=list)
    coordination_edges: list[CoordinationEdgeEvidence] = Field(default_factory=list)
    message_evidence: list[MessageEvidence] = Field(default_factory=list)
    coverage_callout: str = COVERAGE_CALLOUT_FR
    coverage_limits: list[CoverageLimit] = Field(default_factory=list)
    analyst_notes: list[str] = Field(default_factory=list)

    @field_validator("dossier_id", "mission", "coverage_callout")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("dossier id, mission and coverage_callout are required")
        return value


def build_evidence_dossier_v1(
    *,
    dossier_id: str,
    episode: EpisodeRecord,
    attribution_tier: AttributionTier,
    method_versions: MethodVersion,
    score_run: ScoreRunRecord | None = None,
    channel_roles: list[ChannelRoleEvidence] | None = None,
    pockets: list[PocketRecord] | None = None,
    coordination_edges: list[CoordinationEdgeEvidence] | None = None,
    message_evidence: list[MessageEvidence] | None = None,
    coverage_limits: list[CoverageLimit] | None = None,
    analyst_notes: list[str] | None = None,
) -> EvidenceDossierV1:
    """Build a validated EvidenceDossierV1."""

    return EvidenceDossierV1(
        dossier_id=dossier_id,
        mission=episode.mission,
        episode=episode,
        attribution_tier=attribution_tier,
        method_versions=method_versions,
        score_run=score_run,
        channel_roles=channel_roles or [],
        pockets=pockets or [],
        coordination_edges=coordination_edges or [],
        message_evidence=message_evidence or [],
        coverage_limits=coverage_limits or [],
        analyst_notes=analyst_notes or [],
    )
