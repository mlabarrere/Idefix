"""Tests for src/labeling/aggregate.py (Story 1.1, T5/T7)."""

from __future__ import annotations

import re

from src.labeling.aggregate import (
    _redact_providers,
    aggregate_batch,
    anonymize_and_shuffle,
    build_matrix,
    compute_agreement,
    compute_kappa,
)
from src.labeling.schema import JudgeVerdict, Verdict

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _jv(
    item_id: str,
    verdict: Verdict,
    confidence: float = 0.8,
    rationale: str = "Confirmé par AFP Factuel.",
    sources: list[str] | None = None,
    atomic_claims: list[str] | None = None,
) -> JudgeVerdict:
    return JudgeVerdict(
        item_id=item_id,
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
        sources=sources or ["AFP Factuel"],
        atomic_claims=atomic_claims or ["claim A"],
    )


def _three_judge_fixture() -> dict[str, list[JudgeVerdict]]:
    """
    3 judges, 3 items:
      item-1 : all agree → FAUX (unanimous)
      item-2 : 2 vs 1   → TROMPEUR majority (claude+gemini vs gpt)
      item-3 : 3-way tie → disagreement (one each: VRAI / FAUX / TROMPEUR)
    """
    return {
        "claude": [
            _jv(
                "item-1",
                Verdict.FAUX,
                0.9,
                sources=["AFP Factuel"],
                rationale="AFP Factuel confirme.",
            ),
            _jv(
                "item-2",
                Verdict.TROMPEUR,
                0.7,
                sources=["Les Décodeurs"],
                rationale="Trompeur selon Les Décodeurs.",
            ),
            _jv("item-3", Verdict.VRAI, 0.6, rationale="Jugé vrai par claude."),
        ],
        "gemini": [
            _jv(
                "item-1",
                Verdict.FAUX,
                0.85,
                sources=["VIGINUM"],
                rationale="VIGINUM confirme le faux.",
            ),
            _jv(
                "item-2",
                Verdict.TROMPEUR,
                0.75,
                sources=["CheckNews"],
                rationale="Trompeur selon CheckNews.",
            ),
            _jv("item-3", Verdict.FAUX, 0.5, rationale="Jugé faux par gemini."),
        ],
        "gpt": [
            _jv(
                "item-1",
                Verdict.FAUX,
                0.95,
                sources=["AFP Factuel", "VIGINUM"],
                rationale="Double source AFP et VIGINUM.",
            ),
            _jv("item-2", Verdict.NON_ETAYE, 0.4, rationale="Non étayé selon gpt."),
            _jv("item-3", Verdict.TROMPEUR, 0.65, rationale="Jugé trompeur par gpt."),
        ],
    }


# ---------------------------------------------------------------------------
# build_matrix
# ---------------------------------------------------------------------------


class TestBuildMatrix:
    def test_structure(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        assert "item-1" in matrix
        assert "item-2" in matrix
        assert "item-3" in matrix
        assert set(matrix["item-1"].keys()) == {"claude", "gemini", "gpt"}

    def test_preserves_verdict(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        assert matrix["item-1"]["claude"].verdict == Verdict.FAUX
        assert matrix["item-2"]["gpt"].verdict == Verdict.NON_ETAYE


# ---------------------------------------------------------------------------
# compute_agreement
# ---------------------------------------------------------------------------


class TestComputeAgreement:
    def test_unanimous(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        agr = compute_agreement(matrix)
        assert agr["item-1"] == "unanimous"

    def test_majority(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        agr = compute_agreement(matrix)
        assert agr["item-2"] == "majority"

    def test_disagreement_three_way_tie(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        agr = compute_agreement(matrix)
        assert agr["item-3"] == "disagreement"

    def test_two_judges_tie(self):
        data = {
            "j1": [_jv("x", Verdict.VRAI)],
            "j2": [_jv("x", Verdict.FAUX)],
        }
        matrix = build_matrix(data)
        agr = compute_agreement(matrix)
        assert agr["x"] == "disagreement"


# ---------------------------------------------------------------------------
# anonymize_and_shuffle
# ---------------------------------------------------------------------------


class TestAnonymizeAndShuffle:
    def test_no_real_slugs_leak(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        anon = anonymize_and_shuffle(matrix)
        for item_id, judges in anon.items():
            for anon_label in judges:
                assert "claude" not in anon_label
                assert "gemini" not in anon_label
                assert "gpt" not in anon_label
                assert anon_label.startswith("Juge ")

    def test_deterministic_under_fixed_seed(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        anon1 = anonymize_and_shuffle(matrix, seed=42)
        anon2 = anonymize_and_shuffle(matrix, seed=42)
        # Same mapping
        for item_id in anon1:
            assert list(anon1[item_id].keys()) == list(anon2[item_id].keys())

    def test_different_seed_may_differ(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        anon1 = anonymize_and_shuffle(matrix, seed=42)
        anon2 = anonymize_and_shuffle(matrix, seed=99)
        # The anonymous label assigned to each slug may differ between seeds
        # (at least for some item; not guaranteed to always differ if only 1 item)
        # We just verify neither raises and both have 3 judges per item
        for item_id in anon1:
            assert len(anon1[item_id]) == len(anon2[item_id])

    def test_preserves_all_verdicts(self):
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        anon = anonymize_and_shuffle(matrix)
        # Every item still has 3 judges
        for item_id in matrix:
            assert len(anon[item_id]) == len(matrix[item_id])

    def test_anon_labels_scale_past_26_judges(self):
        # base-26 scheme must not break past Z (old chr(ord('A')+i) overflowed).
        data = {f"judge-{i}": [_jv("shared", Verdict.FAUX)] for i in range(27)}
        matrix = build_matrix(data)
        anon = anonymize_and_shuffle(matrix)
        labels = list(anon["shared"].keys())
        assert len(labels) == 27
        assert len(set(labels)) == 27  # all unique
        for lab in labels:
            assert re.match(r"^Juge [A-Z]+$", lab), lab
        # The two-letter range must appear (only 26 single letters exist).
        assert any(re.match(r"^Juge [A-Z]{2}$", lab) for lab in labels)

    def test_consistent_mapping_across_items(self):
        """The same slug maps to the same anon label for all items in one run."""
        data = _three_judge_fixture()
        matrix = build_matrix(data)
        anon = anonymize_and_shuffle(matrix, seed=42)

        # For each real slug, find what anon label it got by checking a JudgeVerdict
        # Reconstruct slug → anon mapping by cross-referencing original matrix
        seen: dict[str, set[str]] = {}
        for item_id, anon_judges in anon.items():
            orig_judges = matrix[item_id]
            # Both dicts have the same JudgeVerdict objects (same identity or equal)
            for anon_label, anon_jv in anon_judges.items():
                # Find which slug owns this JudgeVerdict
                for slug, orig_jv in orig_judges.items():
                    if (
                        orig_jv.item_id == anon_jv.item_id
                        and orig_jv.verdict == anon_jv.verdict
                        and orig_jv.confidence == anon_jv.confidence
                    ):
                        seen.setdefault(slug, set()).add(anon_label)
                        break

        # Each slug maps to exactly one anon label
        for slug, labels in seen.items():
            assert len(labels) == 1, f"Slug '{slug}' mapped to multiple anon labels: {labels}"


# ---------------------------------------------------------------------------
# compute_kappa
# ---------------------------------------------------------------------------


class TestComputeKappa:
    def test_identical_judges_kappa_is_one(self):
        """When all judges give identical verdicts, Cohen kappa should be 1.0."""
        verdicts = [Verdict.FAUX, Verdict.TROMPEUR, Verdict.VRAI, Verdict.DECONTEXTUALISE]
        j1 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        j2 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        j3 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]

        result = compute_kappa({"j1": j1, "j2": j2, "j3": j3})
        assert result["n_judges"] == 3
        assert result["mean_pairwise_cohen"] is not None
        assert abs(result["mean_pairwise_cohen"] - 1.0) < 1e-6
        # Fleiss kappa should also be near 1.0
        if result["fleiss_kappa"] is not None:
            assert abs(result["fleiss_kappa"] - 1.0) < 1e-6

    def test_disagreeing_judges_kappa_lower_than_one(self):
        """Disagreeing judges should yield kappa < 1.0."""
        j1 = [_jv("a", Verdict.FAUX), _jv("b", Verdict.VRAI), _jv("c", Verdict.TROMPEUR)]
        j2 = [_jv("a", Verdict.VRAI), _jv("b", Verdict.FAUX), _jv("c", Verdict.DECONTEXTUALISE)]

        result = compute_kappa({"j1": j1, "j2": j2})
        assert result["mean_pairwise_cohen"] is not None
        assert result["mean_pairwise_cohen"] < 1.0

    def test_single_judge_returns_none(self):
        j1 = [_jv("a", Verdict.FAUX)]
        result = compute_kappa({"j1": j1})
        assert result["mean_pairwise_cohen"] is None
        assert result["fleiss_kappa"] is None
        assert result["n_judges"] == 1

    def test_no_common_items_returns_none(self):
        j1 = [_jv("a", Verdict.FAUX)]
        j2 = [_jv("b", Verdict.VRAI)]  # different item → no overlap
        result = compute_kappa({"j1": j1, "j2": j2})
        # mean_pairwise_cohen may be None (< 2 common items for pair)
        # fleiss requires all judges to have common items
        assert result["fleiss_kappa"] is None

    def test_kappa_result_has_expected_keys(self):
        j1 = [_jv("a", Verdict.FAUX), _jv("b", Verdict.VRAI)]
        j2 = [_jv("a", Verdict.FAUX), _jv("b", Verdict.VRAI)]
        result = compute_kappa({"j1": j1, "j2": j2})
        assert "mean_pairwise_cohen" in result
        assert "fleiss_kappa" in result
        assert "n_common_items" in result
        assert "n_judges" in result

    def test_two_identical_judges_three_items_cohen_is_one(self):
        # Degenerate-agreement: identical vectors must yield 1.0, not None
        # (sklearn returns NaN on constant input → previously dropped).
        verdicts = [Verdict.FAUX, Verdict.FAUX, Verdict.FAUX]
        j1 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        j2 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        result = compute_kappa({"j1": j1, "j2": j2})
        assert result["mean_pairwise_cohen"] == 1.0

    def test_single_observed_category_fleiss_is_none_not_nan(self):
        # All judges, all items → same single category. Fleiss is undefined
        # (NaN); must be normalized to None (NaN is invalid JSON).
        import math

        verdicts = [Verdict.FAUX, Verdict.FAUX]
        j1 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        j2 = [_jv(f"item-{i}", v) for i, v in enumerate(verdicts)]
        result = compute_kappa({"j1": j1, "j2": j2})
        assert result["fleiss_kappa"] is None
        # Explicitly never a NaN float.
        if result["fleiss_kappa"] is not None:
            assert not math.isnan(result["fleiss_kappa"])


# ---------------------------------------------------------------------------
# aggregate_batch
# ---------------------------------------------------------------------------


class TestAggregateBatch:
    def test_unanimous_item_goes_to_gold_candidates(self):
        data = _three_judge_fixture()
        report, gold, arb = aggregate_batch(data)

        gold_ids = [g["item_id"] for g in gold]
        assert "item-1" in gold_ids

        item1 = next(g for g in gold if g["item_id"] == "item-1")
        assert item1["verdict"] == "Faux"
        assert item1["agreement"] == "unanimous"
        # Sources are a union of all agreeing judges' sources
        assert len(item1["sources"]) >= 1

    def test_majority_item_goes_to_gold_candidates(self):
        data = _three_judge_fixture()
        _, gold, _ = aggregate_batch(data)

        gold_ids = [g["item_id"] for g in gold]
        assert "item-2" in gold_ids

        item2 = next(g for g in gold if g["item_id"] == "item-2")
        assert item2["verdict"] == "Trompeur"
        assert item2["agreement"] == "majority"

    def test_disagreement_item_goes_to_arbitration(self):
        data = _three_judge_fixture()
        _, gold, arb = aggregate_batch(data)

        arb_ids = [a["item_id"] for a in arb]
        assert "item-3" in arb_ids

        gold_ids = [g["item_id"] for g in gold]
        assert "item-3" not in gold_ids

    def test_arbitration_record_is_anonymized(self):
        data = _three_judge_fixture()
        _, _, arb = aggregate_batch(data)

        item3_arb = next(a for a in arb if a["item_id"] == "item-3")
        for anon_label in item3_arb["judges"]:
            assert "claude" not in anon_label
            assert "gemini" not in anon_label
            assert "gpt" not in anon_label

    def test_sources_union_for_unanimous(self):
        """Gold candidate sources are the union of all agreeing judges' sources."""
        data = _three_judge_fixture()
        _, gold, _ = aggregate_batch(data)

        item1 = next(g for g in gold if g["item_id"] == "item-1")
        # claude had ["AFP Factuel"], gemini ["VIGINUM"], gpt ["AFP Factuel", "VIGINUM"]
        sources = set(item1["sources"])
        assert "AFP Factuel" in sources
        assert "VIGINUM" in sources

    def test_confidence_is_mean_of_agreeing_judges(self):
        data = _three_judge_fixture()
        _, gold, _ = aggregate_batch(data)

        item1 = next(g for g in gold if g["item_id"] == "item-1")
        # All three agree on FAUX; confidences are 0.9, 0.85, 0.95
        expected_conf = round((0.9 + 0.85 + 0.95) / 3, 4)
        assert abs(item1["confidence"] - expected_conf) < 1e-4

    def test_report_structure(self):
        data = _three_judge_fixture()
        report, _, _ = aggregate_batch(data)
        assert "judges" in report
        assert "n_judges" in report
        assert "n_items" in report
        assert "agreement_counts" in report
        assert "kappa" in report
        assert report["n_judges"] == 3
        assert report["n_items"] == 3
        assert report["agreement_counts"]["unanimous"] == 1
        assert report["agreement_counts"]["majority"] == 1
        assert report["agreement_counts"]["disagreement"] == 1

    def test_two_judges_full_agreement(self):
        """Simple 2-judge, 2-item unanimous scenario — smoke test."""
        data = {
            "j1": [_jv("a", Verdict.FAUX), _jv("b", Verdict.VRAI)],
            "j2": [_jv("a", Verdict.FAUX), _jv("b", Verdict.VRAI)],
        }
        report, gold, arb = aggregate_batch(data)
        assert len(gold) == 2
        assert len(arb) == 0
        assert report["agreement_counts"]["unanimous"] == 2


# ---------------------------------------------------------------------------
# Review fixes (B2 min_judges gate, B3 redaction + context, #5 rationale merge)
# ---------------------------------------------------------------------------


class TestReviewFixes:
    def test_single_judge_item_is_insufficient_not_gold(self):
        # B2: one judge must NOT yield a spurious "unanimous" gold label.
        matrix = build_matrix({"claude": [_jv("solo", Verdict.FAUX)]})
        agr = compute_agreement(matrix, min_judges=2)
        assert agr["solo"] == "insufficient_judges"

        report, gold, arb = aggregate_batch({"claude": [_jv("solo", Verdict.FAUX)]})
        assert [g["item_id"] for g in gold] == []  # never gold
        assert any(a["item_id"] == "solo" for a in arb)
        assert report["agreement_counts"]["insufficient_judges"] == 1

    def test_min_judges_three_routes_two_judge_item_to_arbitration(self):
        data = {
            "j1": [_jv("x", Verdict.FAUX)],
            "j2": [_jv("x", Verdict.FAUX)],
        }
        report, gold, arb = aggregate_batch(data, min_judges=3)
        assert [g["item_id"] for g in gold] == []
        assert arb[0]["item_id"] == "x"
        assert arb[0]["agreement"] == "insufficient_judges"

    def test_rationale_merged_from_all_agreeing(self):
        # #5: gold rationale must merge all agreeing judges' rationales, not keep one.
        data = {
            "j1": [_jv("a", Verdict.FAUX, rationale="Réfuté par AFP Factuel.")],
            "j2": [_jv("a", Verdict.FAUX, rationale="VIGINUM documente ce narratif.")],
        }
        _, gold, _ = aggregate_batch(data)
        rationale = gold[0]["rationale"]
        assert "AFP Factuel" in rationale and "VIGINUM" in rationale

    def test_arbitration_rationale_redacts_provider_names(self):
        # B3: a self-naming rationale must not leak the provider into the queue.
        data = {
            "claude": [_jv("d", Verdict.VRAI, rationale="Jugé vrai par claude après recherche.")],
            "gemini": [_jv("d", Verdict.FAUX, rationale="Gemini conclut au faux.")],
        }
        _, _, arb = aggregate_batch(data)  # tie → arbitration
        rec = next(a for a in arb if a["item_id"] == "d")
        blob = str(rec["judges"]).lower()
        assert "claude" not in blob
        assert "gemini" not in blob
        assert "[juge]" in str(rec["judges"])

    def test_arbitration_record_includes_atomic_claims(self):
        # B3: arbiter needs the decomposition in the record.
        data = {
            "j1": [_jv("e", Verdict.VRAI, atomic_claims=["affirmation 1", "affirmation 2"])],
            "j2": [_jv("e", Verdict.FAUX, atomic_claims=["affirmation 1"])],
        }
        _, _, arb = aggregate_batch(data)
        rec = next(a for a in arb if a["item_id"] == "e")
        for judge_data in rec["judges"].values():
            assert "atomic_claims" in judge_data
            assert len(judge_data["atomic_claims"]) >= 1


# ---------------------------------------------------------------------------
# Review-fix #1 — redaction robustness (garde-fou #6)
# ---------------------------------------------------------------------------


class TestRedactionRobustness:
    def test_plain_names_still_redacted(self):
        # Preserve existing behavior for plain brand names.
        assert _redact_providers("Selon claude, c'est faux.") == "Selon [juge], c'est faux."
        assert _redact_providers("Gemini conclut.") == "[juge] conclut."
        assert _redact_providers("Réponse de gpt.") == "Réponse de [juge]."

    def test_accented_variant_redacted(self):
        # Accent-insensitive: "Gémini" must match token "gemini".
        out = _redact_providers("Selon Gémini, l'affirmation est trompeuse.")
        assert "Gémini" not in out
        assert "[juge]" in out

    def test_versioned_name_no_tail_leak(self):
        # The whole model name is redacted, not just the brand.
        assert _redact_providers("Analyse par gpt-4o ici.") == "Analyse par [juge] ici."
        assert _redact_providers("claude-3.5 dit non.") == "[juge] dit non."
        out = _redact_providers("Utilise gemini 1.5 pro")
        assert "1.5" not in out
        out2 = _redact_providers("grok_v2 répond")
        assert "v2" not in out2.lower()

    def test_no_version_tail_does_not_overmatch(self):
        # A version suffix is optional; following words are untouched.
        out = _redact_providers("claude a raison")
        assert out == "[juge] a raison"

    def test_extra_slug_substring_match(self):
        # Fused multi-char slug must be caught even without a word boundary.
        out = _redact_providers("Origine: claudeopus-4 ici.", extra_slugs=["claudeopus"])
        assert "claudeopus" not in out
        assert "[juge]" in out

    def test_short_slug_not_substring_redacted(self):
        # Conservative: a 1-char slug must not nuke normal words.
        out = _redact_providers("La table est belle.", extra_slugs=["a"])
        assert out == "La table est belle."

    def test_does_not_redact_unrelated_words(self):
        # Fixed token list must not hit ordinary French text.
        text = "Le narratif vise les institutions de la République."
        assert _redact_providers(text) == text

    def test_empty_text(self):
        assert _redact_providers("") == ""
