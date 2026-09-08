"""Coordination Fabric signal registry.

This module centralizes the status, method and default thresholds for
coordination edge families. It does not derive edges; it prevents later builders
from hard-coding divergent thresholds and labels.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_COORDINATION_WINDOW_SECONDS = 72 * 3600


class CoordinationSignal(BaseModel):
    edge_type: str
    status: Literal["active", "reserved", "future"]
    method: str
    default_window_seconds: int | None = Field(default=DEFAULT_COORDINATION_WINDOW_SECONDS, gt=0)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_field: str
    notes: str


SIGNALS: tuple[CoordinationSignal, ...] = (
    CoordinationSignal(
        edge_type="CO_FORWARD",
        status="active",
        method="same_forward_origin_within_window",
        evidence_field="forward_from_channel_id",
        notes="Two channels relay the same origin within the observation window.",
    ),
    CoordinationSignal(
        edge_type="CO_URL",
        status="active",
        method="same_registrable_domain_within_window",
        evidence_field="canonical_domain",
        notes="Broad domain-level co-citation; weaker than exact URL reuse.",
    ),
    CoordinationSignal(
        edge_type="CO_URL_EXACT",
        status="active",
        method="same_full_url_within_window",
        evidence_field="url",
        notes="Tighter signal than CO_URL: identical deep-link reuse.",
    ),
    CoordinationSignal(
        edge_type="CO_HASHTAG",
        status="active",
        method="same_hashtag_within_window",
        evidence_field="hashtag",
        notes="Weak signal; most useful when combined with another edge family.",
    ),
    CoordinationSignal(
        edge_type="COPYPASTA",
        status="reserved",
        method="d3lta_copypasta_or_equivalent",
        threshold=0.693,
        evidence_field="text",
        notes="D3lta copypasta threshold; activate after calibration on annotated corpus.",
    ),
    CoordinationSignal(
        edge_type="TEXT_SIM",
        status="active",
        method="local_sentence_transformers_rewording_similarity",
        threshold=0.715,
        evidence_field="text_embedding",
        notes="Derived by src.graph.edges.derive_text_sim_edges (local embeddings). "
        "Threshold is a MODEL-SPECIFIC seed — recalibrate via scripts/calibrate_text_sim.py.",
    ),
    CoordinationSignal(
        edge_type="TRANSLATION",
        status="active",
        method="local_sentence_transformers_cross_lingual_similarity",
        threshold=0.85,
        evidence_field="text_embedding",
        notes="Cross-language variant of TEXT_SIM (message languages differ). "
        "Threshold is a MODEL-SPECIFIC seed — recalibrate before trusting.",
    ),
    CoordinationSignal(
        edge_type="MEDIA_REUSE",
        status="reserved",
        method="same_media_hash_within_window",
        evidence_field="media_hash",
        notes="Wired in graph builder but inactive until media_hash is populated.",
    ),
)


def active_signals() -> tuple[CoordinationSignal, ...]:
    return tuple(signal for signal in SIGNALS if signal.status == "active")


def reserved_signals() -> tuple[CoordinationSignal, ...]:
    return tuple(signal for signal in SIGNALS if signal.status == "reserved")


def signal_by_type(edge_type: str) -> CoordinationSignal:
    normalized = edge_type.upper()
    for signal in SIGNALS:
        if signal.edge_type == normalized:
            return signal
    raise KeyError(f"unknown coordination edge type: {edge_type}")
