"""Seed claim registry loader.

The current PoC ships a JSONL seed registry in ``data/claims/claims_fr.jsonl``.
This module normalizes that file into the canonical analytical contract. It is
the bridge from the historical labeling helper to the production registry work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from src.shared.analytical_contract import ClaimRecord, ClaimVariant, EpisodeRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLAIMS_PATH = REPO_ROOT / "data" / "claims" / "claims_fr.jsonl"


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalize_claim(row: dict[str, Any]) -> ClaimRecord:
    """Normalize one seed JSONL row into a ClaimRecord."""

    claim_id = str(row.get("claim_id") or row.get("id") or "").strip()
    canonical_text = str(row.get("canonical_text") or row.get("claim_text") or "").strip()
    variants = row.get("variants") or row.get("claim_variants") or []
    normalized_variants: list[ClaimVariant] = []
    for variant in variants:
        if isinstance(variant, str):
            normalized_variants.append(ClaimVariant(text=variant))
        elif isinstance(variant, dict):
            normalized_variants.append(
                ClaimVariant(
                    text=str(variant.get("text") or variant.get("claim_text") or ""),
                    language=str(variant.get("language") or "fr"),
                    source=variant.get("source"),
                )
            )

    return ClaimRecord(
        claim_id=claim_id,
        canonical_text=canonical_text,
        target_entity=str(row.get("target_entity") or row.get("target") or "FR_integrity"),
        theme=row.get("theme") or row.get("thematic_category"),
        language=str(row.get("language") or "fr"),
        variants=normalized_variants,
        source_name=row.get("source") or row.get("source_factchecker"),
        source_url=row.get("source_url"),
        source_date=row.get("source_date"),
        status=row.get("status") or "active",
        embedding_model=row.get("embedding_model"),
        embedding_ref=row.get("embedding_ref"),
    )


def load_seed_claims(path: str | Path | None = None) -> list[ClaimRecord]:
    """Load the seed claim registry as canonical ClaimRecord objects."""

    claims_path = Path(path) if path is not None else DEFAULT_CLAIMS_PATH
    return [normalize_claim(row) for row in _read_jsonl(claims_path)]


def claim_to_episode(claim: ClaimRecord, mission: str = "russosphere") -> EpisodeRecord:
    """Create a minimal EpisodeRecord wrapper around one canonical claim."""

    return EpisodeRecord(
        episode_id=f"episode:{claim.claim_id}",
        title=claim.canonical_text[:120],
        mission=mission,
        claim_ids=[claim.claim_id],
        canonical_claim_id=claim.claim_id,
        thematic_category=claim.theme,
        target_entity=claim.target_entity,
        status=claim.status,
        source_refs=[ref for ref in (claim.source_name, claim.source_url) if ref],
    )
