import pytest
from pydantic import ValidationError

from src.pockets.scoring import PocketInput, PocketMetrics, build_pocket_record, score_pocket


def test_score_pocket_uses_weighted_bounded_metrics():
    metrics = PocketMetrics(
        claim_exposure=1.0,
        coordination_density=0.8,
        bridge_presence=0.5,
        recidivism=0.4,
        stability=0.3,
        volume=0.2,
        coverage=1.0,
    )

    assert score_pocket(metrics) == 0.635


def test_coverage_can_only_reduce_score():
    full = PocketMetrics(claim_exposure=1.0, coordination_density=1.0, coverage=1.0)
    partial = PocketMetrics(claim_exposure=1.0, coordination_density=1.0, coverage=0.5)

    assert score_pocket(partial) == score_pocket(full) * 0.5


def test_build_pocket_record_infers_coordination_type():
    pocket = build_pocket_record(
        PocketInput(
            pocket_id="pocket-1",
            window_start="2026-06-01T00:00:00Z",
            window_end="2026-06-02T00:00:00Z",
            member_channel_ids=[1, 2, 3],
            metrics=PocketMetrics(coordination_density=0.9, claim_exposure=0.2),
            claim_ids=["CLAIM-001"],
            coordination_edge_refs=["edge-1"],
        )
    )

    assert pocket.pocket_type == "coordination"
    assert pocket.pocket_score > 0
    assert pocket.member_channel_ids == [1, 2, 3]


def test_build_pocket_record_marks_mixed_when_signals_are_close():
    pocket = build_pocket_record(
        PocketInput(
            pocket_id="pocket-2",
            window_start="2026-06-01T00:00:00Z",
            window_end="2026-06-02T00:00:00Z",
            member_channel_ids=[1, 2],
            metrics=PocketMetrics(claim_exposure=0.8, coordination_density=0.75),
        )
    )

    assert pocket.pocket_type == "mixed"


def test_pocket_input_validates_required_fields():
    with pytest.raises(ValidationError):
        PocketInput(
            pocket_id="",
            window_start="2026-06-01T00:00:00Z",
            window_end="2026-06-02T00:00:00Z",
            member_channel_ids=[1],
            metrics=PocketMetrics(),
        )
