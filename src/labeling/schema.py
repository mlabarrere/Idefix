"""Pydantic schema for the gold-labeling pipeline (Story 1.1).

Design axiom (AR-10): never a bare float/bool — every label is a structured,
evidence-bearing object. Taxonomy is graded (garde-fou #3), never binary.
A verdict without a named source is invalid (garde-fou #6).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Verdict(str, Enum):
    """Graded veracity taxonomy (garde-fou #3). NEVER binary true/false.

    Anti-France disinformation is most often misleading or decontextualized
    rather than plainly false, so the scale must capture that.
    """

    VRAI = "Vrai"
    FAUX = "Faux"
    TROMPEUR = "Trompeur"
    DECONTEXTUALISE = "Décontextualisé"
    NON_ETAYE = "Non-étayé"


def make_item_id(channel_id: int, message_id: int, batch_id: str) -> str:
    """Deterministic, reproducible item id for a (channel, message) in a batch.

    Stable across runs so judge files and the batch always align on the same key.
    """
    digest = hashlib.sha1(f"{channel_id}:{message_id}".encode()).hexdigest()[:10]
    return f"{batch_id}-{digest}"


class BatchItem(BaseModel):
    """One message to be labeled, plus its France/claim sampling context.

    The candidate claim is a *sampling aid* (lexical nearest claim) giving judges
    context — it is NOT the label. Judges decide veracity against fact-checkers.
    """

    item_id: str
    batch_id: str
    channel_id: int
    message_id: int
    channel_name: str | None = None
    text: str
    timestamp: datetime | None = None
    urls: list[str] = Field(default_factory=list)
    fr_score: float | None = None
    candidate_claim_id: str | None = None
    candidate_claim_text: str | None = None
    claim_link_method: str = "lexical"
    claim_proximity: float = 0.0
    # Sampling-time prior on the SOURCE channel's credibility ("legit" | "suspect"
    # | "other"). Used only to balance label classes in the batch — it is NOT the
    # label; judges assess each message's veracity independently.
    source_credibility: str | None = None

    @field_validator("text")
    @classmethod
    def _text_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("BatchItem.text must be non-empty")
        return v


class JudgeVerdict(BaseModel):
    """One judge's labeling of one item. Schema enforced on every judge file.

    Garde-fous enforced here:
      #3 graded taxonomy (Verdict enum)
      #2 atomic decomposition (atomic_claims non-empty)
      #6 sourced rationale (rationale non-empty AND >=1 named source)
    """

    item_id: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    sources: list[str] = Field(min_length=1)
    atomic_claims: list[str] = Field(min_length=1)

    @field_validator("rationale")
    @classmethod
    def _rationale_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JudgeVerdict.rationale must be non-empty (garde-fou #6)")
        return v

    @field_validator("sources", "atomic_claims")
    @classmethod
    def _entries_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("list must contain at least one non-empty entry")
        return cleaned


class Provenance(BaseModel):
    """Audit trail for one gold label (defensibility — garde-fou #5)."""

    judges: list[str] = Field(default_factory=list)
    n_judges: int = 0
    agreement: str  # "unanimous" | "majority" | "arbitrated"
    pairwise_kappa: float | None = None
    arbitrated: bool = False
    arbiter: str | None = None
    arbiter_note: str | None = None
    methodology_version_hash: str


class GoldLabel(BaseModel):
    """A finalized gold reference label. No gold label without provenance + source."""

    item_id: str
    channel_id: int
    message_id: int
    candidate_claim_id: str | None = None
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    sources: list[str] = Field(min_length=1)
    provenance: Provenance

    @field_validator("rationale")
    @classmethod
    def _rationale_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("GoldLabel.rationale must be non-empty")
        return v

    @field_validator("sources")
    @classmethod
    def _sources_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("GoldLabel requires at least one named source")
        return cleaned
