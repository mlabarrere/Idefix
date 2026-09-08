"""
Shared dossier schema and invariants.
EVERY dossier produced by Idéfix must use these definitions.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

# --------------------------------------------------------------------------- #
# MANDATORY — coverage callout (single-platform-blindness)                    #
# This string MUST appear in every evidence dossier. Non-negotiable.          #
# --------------------------------------------------------------------------- #
COVERAGE_CALLOUT_FR = (
    "Ce dossier observe uniquement la couche d'ensemencement Telegram. "
    "Une opération atteignant la France principalement via d'autres plateformes "
    "sans étape Telegram ne sera PAS détectée."
)


def get_methodology_version_hash() -> str:
    """Return first 8 chars of SHA-256 of METHODOLOGY.md.
    Used in every dossier and FastAPI response for EIP-resistance.
    """
    methodology_path = Path(__file__).parent.parent.parent / "METHODOLOGY.md"
    try:
        content = methodology_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:8]
    except FileNotFoundError:
        return "00000000"


# --------------------------------------------------------------------------- #
# Score result — unified format for all 5 families                            #
# --------------------------------------------------------------------------- #

class ScoreResult(BaseModel):
    # `family` was a Literal of the 5 original families (a–e). Widened to `str`
    # (2026-06-09, scope-change-multi-mission) so mission-specific families can
    # plug into the same combiner — notably the GAN mission's telegram_* families
    # (telegram_visibility / telegram_velocity / telegram_source_diversity /
    # telegram_disclosure_precision / telegram_propagation /
    # telegram_adverse_attention). Backward compatible: the 5 original names
    # ("claim_proximity", "cascade_role", "coordination", "recidivism", "genai")
    # remain valid str values.
    family: str
    value: float                # [0.0, 1.0]
    confidence_low: float = 0.0
    confidence_high: float = 1.0
    triggered: bool = False     # True if above configured threshold
    evidence: dict = {}         # family-specific detail


# --------------------------------------------------------------------------- #
# Evidence dossier schema                                                      #
# --------------------------------------------------------------------------- #

class EvidenceChannel(BaseModel):
    channel_id: int
    username: str | None = None
    cascade_role: (
        Literal["seeding-source", "forward-hub", "cross-channel-bridge", "reactivator"] | None
    ) = None
    bridge_score: float | None = None
    first_seen_at: str | None = None  # ISO8601


class DossierSchema(BaseModel):
    dossier_id: str
    episode_id: str
    attribution_tier: Literal["T1", "T2"]   # T3 raises ValidationError — by design
    severity_tier: Literal["T1", "T2", "T3", "T4", "T5"]
    methodology_version_hash: str
    created_at: str                          # ISO8601 UTC
    multi_source_rule_met: bool
    scores: list[ScoreResult]
    evidence_channels: list[EvidenceChannel] = []
    coverage_callout: str                    # Must equal COVERAGE_CALLOUT_FR

    @field_validator("coverage_callout")
    @classmethod
    def callout_must_be_present(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("coverage_callout is mandatory and cannot be empty")
        return v

    @field_validator("attribution_tier")
    @classmethod
    def no_t3(cls, v: str) -> str:
        if v == "T3":
            raise ValueError("T3 attribution is out of scope for this system — never claim T3")
        return v


def new_dossier_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
