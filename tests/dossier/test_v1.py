import pytest
from pydantic import ValidationError

from src.dossier.v1 import build_evidence_dossier_v1
from src.pockets.scoring import PocketInput, PocketMetrics, build_pocket_record
from src.shared.analytical_contract import EpisodeRecord, MethodVersion


def _episode():
    return EpisodeRecord(
        episode_id="episode:test",
        title="Episode test",
        mission="russosphere",
        claim_ids=["CLAIM-001"],
    )


def test_build_evidence_dossier_v1_embeds_episode_and_pockets():
    pocket = build_pocket_record(
        PocketInput(
            pocket_id="pocket-1",
            window_start="2026-06-01T00:00:00Z",
            window_end="2026-06-02T00:00:00Z",
            member_channel_ids=[1, 2],
            metrics=PocketMetrics(claim_exposure=0.8, coordination_density=0.8),
            claim_ids=["CLAIM-001"],
        )
    )

    dossier = build_evidence_dossier_v1(
        dossier_id="dossier-1",
        episode=_episode(),
        attribution_tier="T2",
        method_versions=MethodVersion(methodology_version_hash="abc123"),
        pockets=[pocket],
    )

    assert dossier.schema_version == "evidence-dossier/v1"
    assert dossier.mission == "russosphere"
    assert dossier.pockets[0].pocket_id == "pocket-1"
    assert dossier.coverage_callout


def test_dossier_rejects_t3_attribution():
    with pytest.raises(ValidationError):
        build_evidence_dossier_v1(
            dossier_id="dossier-1",
            episode=_episode(),
            attribution_tier="T3",  # type: ignore[arg-type]
            method_versions=MethodVersion(methodology_version_hash="abc123"),
        )
