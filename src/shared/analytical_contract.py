"""Canonical analytical data contract for Idéfix.

These models define the shared objects used by the scorer, evidence dossiers,
static export and operator UI. They are intentionally lightweight: they do not
perform database I/O and they do not decide analytical thresholds.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MissionName = str
AttributionTier = Literal["T1", "T2"]
ClaimStatus = Literal["active", "archived", "replaced", "merged"]
PocketType = Literal["diffusion", "coordination", "recidivism", "bridging", "mixed"]
CoordinationEdgeType = Literal[
    "CO_FORWARD",
    "CO_URL",
    "CO_URL_EXACT",
    "CO_HASHTAG",
    "COPYPASTA",
    "TEXT_SIM",
    "TRANSLATION",
    "MEDIA_REUSE",
]


class MethodVersion(BaseModel):
    """Versions that make an analytical output reproducible."""

    methodology_version_hash: str
    scorer_version: str | None = None
    edge_builder_version: str | None = None
    claim_matcher_version: str | None = None
    export_version: str | None = None


class CoverageLimit(BaseModel):
    """Declared observation limit attached to an output."""

    limit_id: str
    label: str
    description: str
    severity: Literal["info", "degraded", "blocking"] = "info"

    @field_validator("limit_id", "label", "description")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("coverage limit fields must be non-empty")
        return value


class ClaimVariant(BaseModel):
    """One semantic or linguistic variant of a canonical claim."""

    text: str
    language: str = "fr"
    source: str | None = None

    @field_validator("text")
    @classmethod
    def _text_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("claim variant text must be non-empty")
        return value


class ClaimRecord(BaseModel):
    """Canonical claim tracked by the registry."""

    claim_id: str
    canonical_text: str
    target_entity: str = "FR_integrity"
    theme: str | None = None
    language: str = "fr"
    variants: list[ClaimVariant] = Field(default_factory=list)
    source_name: str | None = None
    source_url: str | None = None
    source_date: str | None = None
    status: ClaimStatus = "active"
    embedding_model: str | None = None
    embedding_ref: str | None = None

    @field_validator("claim_id", "canonical_text")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("claim_id and canonical_text must be non-empty")
        return value


class EpisodeRecord(BaseModel):
    """A tracked information episode: one or more claims over an observation window."""

    episode_id: str
    title: str
    mission: MissionName = "russosphere"
    claim_ids: list[str] = Field(default_factory=list)
    canonical_claim_id: str | None = None
    thematic_category: str | None = None
    target_entity: str = "FR_integrity"
    status: ClaimStatus = "active"
    window_start: str | None = None
    window_end: str | None = None
    source_refs: list[str] = Field(default_factory=list)

    @field_validator("episode_id", "title", "mission")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("episode_id, title and mission must be non-empty")
        return value


class MessageEvidence(BaseModel):
    """Message-level proof retained for a claim, edge, pocket or dossier."""

    mission: MissionName
    channel_id: int
    message_id: int
    timestamp: str | None = None
    text_excerpt: str | None = None
    urls: list[str] = Field(default_factory=list)
    matched_claim_id: str | None = None
    claim_proximity: float | None = Field(default=None, ge=0.0, le=1.0)
    method: str | None = None


class CoordinationEdgeEvidence(BaseModel):
    """Auditable coordination relation between two channels."""

    edge_type: CoordinationEdgeType
    source_channel_id: int
    target_channel_id: int
    mission: MissionName = "russosphere"
    window_start: str | None = None
    window_end: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    method: str
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("method")
    @classmethod
    def _method_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("coordination edge method must be non-empty")
        return value


class ChannelRoleEvidence(BaseModel):
    """Channel-level role and explanation used by queues, pockets and dossiers."""

    channel_id: int
    mission: MissionName = "russosphere"
    attribution_tier: AttributionTier = "T1"
    cascade_role: Literal[
        "seeding-source",
        "forward-hub",
        "cross-channel-bridge",
        "reactivator",
        "unclassified",
    ] = "unclassified"
    score: float = Field(ge=0.0, le=1.0)
    confidence_low: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_high: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class PocketRecord(BaseModel):
    """A measurable harmful-information pocket over a time window."""

    pocket_id: str
    mission: MissionName = "russosphere"
    pocket_type: PocketType
    window_start: str
    window_end: str
    member_channel_ids: list[int]
    pocket_score: float = Field(ge=0.0, le=1.0)
    claim_ids: list[str] = Field(default_factory=list)
    coordination_edge_refs: list[str] = Field(default_factory=list)
    stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    coverage_limits: list[CoverageLimit] = Field(default_factory=list)

    @field_validator("pocket_id", "window_start", "window_end")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("pocket_id and window bounds must be non-empty")
        return value

    @field_validator("member_channel_ids")
    @classmethod
    def _members_non_empty(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("a pocket must contain at least one channel")
        return value


class ScoreRunRecord(BaseModel):
    """Metadata envelope for one mission-scoped scoring run."""

    run_id: str
    mission: MissionName
    created_at: str
    method_versions: MethodVersion
    channel_count: int = Field(ge=0)
    top_k: int = Field(ge=0)
    coverage_limits: list[CoverageLimit] = Field(default_factory=list)
    symmetric_ratio: dict[str, float | int | str] = Field(default_factory=dict)

    @field_validator("run_id", "mission", "created_at")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("run_id, mission and created_at must be non-empty")
        return value
