"""Tests for the multilingual France-targeting thematic signal (pure, NO DB).

The load-bearing case (CLAUDE.md §2.1): a purely-Russian (or English) text that
attacks the image / integrity / sovereignty of France must score HIGH despite
ZERO French-language density — precisely because the adversary apparatus
(Dugin / Geopolitika / Pravda) attacks France in RU/EN, where the old
``fr_score`` (French-keyword density) is LOW. These tests prove the cross-
language detection and that the signal is a SEVERITY MODULATOR, never a gate.

No database: only the pure core and the pure aggregation helper are exercised.
"""

from src.normalizer.france_targeting import (
    FRANCE_LEXICON,
    FranceTargetingResult,
    _aggregate_channel,
    score_france_targeting,
)

# A "high" France-targeting score for the purposes of these assertions. The
# absolute calibration is the analyst's job; what is load-bearing here is the
# SEPARATION between France-targeting content and off-topic / non-France content.
HIGH = 0.40
LOW = 0.10


class TestFrenchText:
    def test_multi_category_scores_high(self):
        r = score_france_targeting(
            "Macron et l'armée française face à l'élection présidentielle ; "
            "l'Élysée et la République française attaqués.",
            "fr",
        )
        assert r.score >= HIGH
        cats = r.evidence["matched_terms"]
        # Several distinct §2.1 categories must be hit.
        assert len(cats) >= 4
        assert "elected_officials" in cats
        assert "armed_forces" in cats
        assert "electoral_process" in cats

    def test_accent_insensitive(self):
        # No accents on input — must still match accented lexicon terms.
        with_accents = score_france_targeting("l'Élysée et l'armée française", "fr")
        without = score_france_targeting("l'elysee et l'armee francaise", "fr")
        assert with_accents.score == without.score
        assert without.score > 0.0


class TestRussianLoadBearingCase:
    """RU-only attack on France must score HIGH despite zero French density."""

    def test_ru_only_scores_high(self):
        # «Macron / France / elections» entirely in Cyrillic — the exact case
        # the spec calls out as load-bearing.
        r = score_france_targeting("Макрон Франция выборы", "ru")
        assert r.score >= HIGH, f"RU France-attack should be HIGH, got {r.score}"
        assert r.evidence["has_anchor"] is True
        cats = r.evidence["matched_terms"]
        assert "national_cohesion" in cats  # Франция
        assert "elected_officials" in cats  # Макрон
        assert "electoral_process" in cats  # выборы

    def test_ru_realistic_attack_scores_high(self):
        r = score_france_targeting(
            "Макрон лжёт. Армия Франции в Сахеле. Президент Франции готовит "
            "фальсификацию выборов. Французский народ обманут Елисейским дворцом.",
            "ru",
        )
        assert r.score >= HIGH
        # Russian declensions (Франции, выборов) resolve via stems / suffix rule.
        assert "armed_forces" in r.evidence["matched_terms"]

    def test_ru_beats_zero_french_density(self):
        # The whole point: the RU France-attack outscores an off-topic text by a
        # wide margin, even though it contains no French-language keywords.
        ru = score_france_targeting("Макрон и Франция: фальсификация выборов", "ru")
        off = score_france_targeting(
            "Сегодня хорошая погода, мы ходили в кино", "ru"
        )
        assert ru.score >= HIGH
        assert off.score <= LOW
        assert ru.score > off.score

    def test_generic_russian_politics_not_about_france_stays_low(self):
        # Precision guard: generic president/army/election vocabulary with NO
        # France anchor must NOT be inflated (contextual terms gated on anchor).
        r = score_france_targeting(
            "Президент подписал указ. Армия проводит учения. "
            "Выборы в Германии прошли спокойно.",
            "ru",
        )
        assert r.evidence["has_anchor"] is False
        assert r.score <= LOW


class TestEnglishText:
    def test_en_only_attack_scores_high(self):
        r = score_france_targeting(
            "Macron and the French army are destroying the French republic "
            "ahead of the 2027 election.",
            "en",
        )
        assert r.score >= HIGH
        assert "elected_officials" in r.evidence["matched_terms"]


class TestOffTopic:
    def test_no_france_entities_scores_zero(self):
        r = score_france_targeting("The weather in Berlin is nice today.", "en")
        assert r.score == 0.0
        assert r.evidence["matched_terms"] == {}

    def test_other_country_not_matched(self):
        r = score_france_targeting(
            "The German chancellor met the Italian prime minister in Rome.", "en"
        )
        # 'prime minister' is contextual; no France anchor -> must not fire.
        assert r.score <= LOW


class TestDomainBoost:
    def test_adversary_domain_raises_score(self):
        base = score_france_targeting("Regardez la vidéo ci-dessous", "fr")
        boosted = score_france_targeting(
            "Regardez la vidéo ci-dessous",
            "fr",
            cited_domains=["geopolitika.ru"],
        )
        assert boosted.score > base.score
        assert boosted.evidence["domain_hits"] == ["geopolitika.ru"]

    def test_benign_domain_no_boost(self):
        r = score_france_targeting(
            "Voir l'article", "fr", cited_domains=["lemonde.fr", "wikipedia.org"]
        )
        assert r.evidence["domain_hits"] == []
        assert r.score == 0.0

    def test_domain_compounds_with_lexicon(self):
        # Domain boost stacks on top of a lexical France match.
        r = score_france_targeting(
            "Macron et l'élection présidentielle",
            "fr",
            cited_domains=["pravda-fr.com"],
        )
        lexical_only = score_france_targeting(
            "Macron et l'élection présidentielle", "fr"
        )
        assert r.score > lexical_only.score
        assert "pravda-fr.com" in r.evidence["domain_hits"]


class TestClaimProximityStub:
    def test_none_records_empty_registry_note(self):
        r = score_france_targeting("Macron", "fr")
        assert r.evidence["claim_proximity"] == "N/A — episodes registry empty (v0)"

    def test_provided_proximity_raises_score(self):
        base = score_france_targeting("Macron", "fr")
        with_cp = score_france_targeting("Macron", "fr", claim_proximity=0.9)
        assert with_cp.score > base.score
        assert with_cp.evidence["claim_proximity"] == 0.9

    def test_proximity_clamped(self):
        r = score_france_targeting("Macron", "fr", claim_proximity=5.0)
        assert 0.0 <= r.score <= 1.0


class TestEvidenceExplainability:
    def test_evidence_lists_terms_per_category(self):
        r = score_france_targeting(
            "Macron attaque l'armée française pendant l'élection présidentielle",
            "fr",
        )
        mt = r.evidence["matched_terms"]
        assert isinstance(mt, dict)
        # Each matched category maps to a non-empty list of matched terms.
        for category, terms in mt.items():
            assert category in FRANCE_LEXICON
            assert isinstance(terms, list) and terms
        assert "macron" in mt["elected_officials"]

    def test_evidence_has_components_breakdown(self):
        r = score_france_targeting("Macron", "fr")
        comp = r.evidence["components"]
        assert {"breadth", "depth", "domain_signal", "weights"} <= set(comp)

    def test_language_hint_recorded_not_used(self):
        # The language hint is recorded but never gates matching: a RU text
        # tagged 'en' (mislabel) still matches via the lexicon.
        r = score_france_targeting("Макрон Франция", language="en")
        assert r.evidence["language_hint"] == "en"
        assert r.score > 0.0


class TestEmptyInput:
    def test_none_text(self):
        r = score_france_targeting(None)
        assert r.score == 0.0
        assert r.evidence["matched_terms"] == {}

    def test_empty_string(self):
        assert score_france_targeting("").score == 0.0

    def test_whitespace_only(self):
        assert score_france_targeting("   \n\t ").score == 0.0

    def test_returns_result_dataclass(self):
        r = score_france_targeting("Macron")
        assert isinstance(r, FranceTargetingResult)
        d = r.as_dict()
        assert set(d) == {"score", "evidence"}


class TestNeverActsAsGate:
    """MÉTA-CONTRAINTE 1: a severity modulator, never a filter/exclusion."""

    def test_always_returns_a_result_never_drops(self):
        # Off-topic content is not excluded — it just gets a low score.
        for txt in ["", None, "random off-topic text", "Макрон Франция"]:
            r = score_france_targeting(txt)
            assert isinstance(r, FranceTargetingResult)
            assert 0.0 <= r.score <= 1.0

    def test_score_in_unit_interval(self):
        # Even an extreme France-saturated text stays clamped to [0, 1].
        txt = " ".join(["Macron Françe armée française élection présidentielle"] * 50)
        r = score_france_targeting(txt, "fr", claim_proximity=1.0)
        assert 0.0 <= r.score <= 1.0


class TestChannelAggregation:
    """Pure aggregation helper (no DB) used by the I/O wrapper."""

    def test_empty_channel(self):
        r = _aggregate_channel(123, [])
        assert r.score == 0.0
        assert r.evidence["messages_sampled"] == 0
        assert r.evidence["coverage"] == 0.0

    def test_max_with_coverage(self):
        msgs = [
            score_france_targeting("bonjour tout le monde", "fr"),  # 0
            score_france_targeting("Macron Françe armée française élection", "fr"),
            score_france_targeting("la météo", "fr"),  # 0
        ]
        agg = _aggregate_channel(7, msgs)
        # Channel score = strongest message (a channel that ever attacks France).
        assert agg.score == max(m.score for m in msgs)
        assert agg.evidence["messages_sampled"] == 3
        # Coverage = share of messages with any France hit (1 of 3 here).
        assert agg.evidence["coverage"] == round(1 / 3, 4)
        assert agg.evidence["mean_score"] <= agg.score

    def test_matched_categories_union(self):
        msgs = [
            score_france_targeting("Macron", "fr"),
            score_france_targeting("l'armée française", "fr"),
        ]
        agg = _aggregate_channel(9, msgs)
        cats = set(agg.evidence["matched_categories"])
        assert {"elected_officials", "armed_forces"} <= cats
