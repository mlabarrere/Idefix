import pytest

from src.readiness.advanced_capabilities import (
    CapabilityReadinessInput,
    assess_capability_readiness,
)


def test_advanced_capability_is_blocked_by_default():
    decision = assess_capability_readiness(
        CapabilityReadinessInput(capability="gnn_misinfotelegraph_fr")
    )

    assert decision.status == "blocked"
    assert decision.can_activate is False
    assert "gold_set_available" in decision.missing_requirements


def test_media_reuse_can_be_activated_when_all_requirements_are_met():
    decision = assess_capability_readiness(
        CapabilityReadinessInput(
            capability="media_reuse",
            evidence={
                "media_hash_populated": True,
                "non_empty_edges": True,
                "threshold_documented": True,
                "organic_control_checked": True,
                "sponsor_need_confirmed": True,
            },
        )
    )

    assert decision.status == "ready"
    assert decision.can_activate is True
    assert decision.missing_requirements == []


def test_unknown_capability_is_rejected():
    with pytest.raises(ValueError):
        assess_capability_readiness(
            CapabilityReadinessInput(capability="persuasion_automation")
        )
