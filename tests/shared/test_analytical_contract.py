from pathlib import Path

import pytest
from pydantic import ValidationError

from src.registry.claims import claim_to_episode, load_seed_claims, normalize_claim
from src.shared.analytical_contract import (
    ClaimRecord,
    CoordinationEdgeEvidence,
    MethodVersion,
    PocketRecord,
    ScoreRunRecord,
)


def test_claim_record_requires_non_empty_text():
    with pytest.raises(ValidationError):
        ClaimRecord(claim_id="CLAIM-X", canonical_text="")


def test_seed_claims_load_as_contract_objects():
    claims = load_seed_claims()

    assert claims
    assert all(c.claim_id for c in claims)
    assert all(c.canonical_text for c in claims)
    assert {c.target_entity for c in claims} == {"FR_integrity"}


def test_normalize_claim_accepts_legacy_jsonl_shape():
    claim = normalize_claim(
        {
            "id": "CLAIM-TEST",
            "claim_text": "La France cacherait des pertes militaires.",
            "theme": "Forces armées",
            "target": "FR_integrity",
            "source": "fixture",
        }
    )

    assert claim.claim_id == "CLAIM-TEST"
    assert claim.theme == "Forces armées"
    assert claim.source_name == "fixture"


def test_claim_to_episode_preserves_registry_identity():
    claim = ClaimRecord(claim_id="CLAIM-001", canonical_text="Claim text", theme="Theme")

    episode = claim_to_episode(claim)

    assert episode.episode_id == "episode:CLAIM-001"
    assert episode.canonical_claim_id == "CLAIM-001"
    assert episode.claim_ids == ["CLAIM-001"]


def test_coordination_edge_requires_method_and_bounded_score():
    with pytest.raises(ValidationError):
        CoordinationEdgeEvidence(
            edge_type="TEXT_SIM",
            source_channel_id=1,
            target_channel_id=2,
            score=1.2,
            method="bge-m3",
        )

    with pytest.raises(ValidationError):
        CoordinationEdgeEvidence(
            edge_type="TEXT_SIM",
            source_channel_id=1,
            target_channel_id=2,
            score=0.8,
            method="",
        )


def test_pocket_requires_members_and_bounded_score():
    with pytest.raises(ValidationError):
        PocketRecord(
            pocket_id="pocket-1",
            pocket_type="coordination",
            window_start="2026-06-01T00:00:00Z",
            window_end="2026-06-02T00:00:00Z",
            member_channel_ids=[],
            pocket_score=0.5,
        )


def test_score_run_metadata_is_mission_scoped():
    run = ScoreRunRecord(
        run_id="run-1",
        mission="russosphere",
        created_at="2026-06-15T00:00:00Z",
        method_versions=MethodVersion(methodology_version_hash="abc123"),
        channel_count=10,
        top_k=5,
    )

    assert run.mission == "russosphere"


def test_registry_loader_accepts_utf8_sig_jsonl(tmp_path: Path):
    path = tmp_path / "claims.jsonl"
    path.write_text(
        '\ufeff{"id":"CLAIM-X","claim_text":"Texte","target":"FR_integrity"}\n',
        encoding="utf-8",
    )

    claims = load_seed_claims(path)

    assert claims[0].claim_id == "CLAIM-X"
