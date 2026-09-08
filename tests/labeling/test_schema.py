"""Tests for the labeling schema (Story 1.1, T1)."""

import pytest
from pydantic import ValidationError

from src.labeling.schema import (
    BatchItem,
    GoldLabel,
    JudgeVerdict,
    Provenance,
    Verdict,
    make_item_id,
)


def test_make_item_id_is_deterministic():
    a = make_item_id(123, 456, "batch-001")
    b = make_item_id(123, 456, "batch-001")
    assert a == b
    assert a.startswith("batch-001-")


def test_make_item_id_varies_by_message():
    assert make_item_id(1, 1, "b") != make_item_id(1, 2, "b")
    assert make_item_id(1, 1, "b") != make_item_id(2, 1, "b")


def test_verdict_taxonomy_is_graded():
    # Garde-fou #3: five graded grades, never binary.
    values = {v.value for v in Verdict}
    assert values == {"Vrai", "Faux", "Trompeur", "Décontextualisé", "Non-étayé"}


def test_judge_verdict_rejects_out_of_taxonomy():
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict="MaybeTrue",  # not in enum
            confidence=0.5,
            rationale="r",
            sources=["AFP"],
            atomic_claims=["c"],
        )


def test_judge_verdict_requires_a_named_source():
    # Garde-fou #6: a verdict without a source is invalid.
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict=Verdict.FAUX,
            confidence=0.9,
            rationale="contredit par AFP Factuel",
            sources=[],
            atomic_claims=["la France enverrait des soldats"],
        )


def test_judge_verdict_rejects_blank_only_sources():
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict=Verdict.FAUX,
            confidence=0.9,
            rationale="r",
            sources=["   "],
            atomic_claims=["c"],
        )


def test_judge_verdict_requires_atomic_decomposition():
    # Garde-fou #2: atomic claim decomposition required.
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict=Verdict.TROMPEUR,
            confidence=0.6,
            rationale="r",
            sources=["VIGINUM"],
            atomic_claims=[],
        )


def test_judge_verdict_rejects_blank_rationale():
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict=Verdict.VRAI,
            confidence=0.6,
            rationale="   ",
            sources=["Les Décodeurs"],
            atomic_claims=["c"],
        )


def test_judge_verdict_confidence_bounds():
    with pytest.raises(ValidationError):
        JudgeVerdict(
            item_id="x",
            verdict=Verdict.VRAI,
            confidence=1.5,
            rationale="r",
            sources=["AFP"],
            atomic_claims=["c"],
        )


def test_valid_judge_verdict_roundtrips():
    jv = JudgeVerdict(
        item_id="batch-001-abc",
        verdict=Verdict.DECONTEXTUALISE,
        confidence=0.7,
        rationale="L'image est réelle mais sortie de son contexte de 2022 (CLEF CheckThat! FR).",
        sources=["CLEF CheckThat! 2025 FR", "AFP Factuel"],
        atomic_claims=["l'image montre des soldats français", "la scène daterait de 2025"],
    )
    assert jv.verdict is Verdict.DECONTEXTUALISE
    assert "AFP Factuel" in jv.sources


def test_batch_item_requires_text():
    with pytest.raises(ValidationError):
        BatchItem(item_id="i", batch_id="b", channel_id=1, message_id=1, text="  ")


def test_gold_label_requires_source_and_provenance():
    prov = Provenance(
        judges=["alpha", "beta"],
        n_judges=2,
        agreement="unanimous",
        methodology_version_hash="UNVERSIONED-2026-06-04",
    )
    gold = GoldLabel(
        item_id="batch-001-abc",
        channel_id=1,
        message_id=2,
        candidate_claim_id="CLAIM-001",
        verdict=Verdict.FAUX,
        confidence=0.95,
        rationale="Démenti par AFP Factuel et VIGINUM.",
        sources=["AFP Factuel"],
        provenance=prov,
    )
    assert gold.provenance.methodology_version_hash.startswith("UNVERSIONED")

    with pytest.raises(ValidationError):
        GoldLabel(
            item_id="x",
            channel_id=1,
            message_id=2,
            verdict=Verdict.FAUX,
            confidence=0.9,
            rationale="r",
            sources=[],
            provenance=prov,
        )
