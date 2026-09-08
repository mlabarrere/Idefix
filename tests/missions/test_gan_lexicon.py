"""Tests du lexique GAN sur le moteur générique (pur, SANS DB).

Vérifie les 4 niveaux de détection (domaine §5.2) : (1) directe, (3) gate
contextuel, (4) cooccurrence → mention implicite ; + précision (sigles ambigus
GAN/CSG gatés) et MÉTA-CONTRAINTE 1 (modulateur, jamais gate).
"""
from src.missions.gan import MISSION
from src.normalizer.targeting import score_targeting

_LEX = MISSION.lexicon
_W = MISSION.targeting

HIGH = 0.40
LOW = 0.12


def _score(text, lang=None, cited_domains=None):
    return score_targeting(text, lang, cited_domains, lexicon=_LEX, weights=_W)


class TestDirect:
    def test_named_carrier_scores_high(self):
        r = _score(
            "Le porte-avions Charles de Gaulle a quitté Toulon avec son escorte "
            "(frégate Forbin, frégate Provence) pour la mission Clemenceau 25.",
            "fr",
        )
        assert r.score >= HIGH
        assert r.evidence["has_anchor"] is True
        cats = r.evidence["matched_terms"]
        assert "carrier_named" in cats
        assert "deployment" in cats

    def test_cyrillic_named_carrier(self):
        # « Авианосец Шарль де Голль » — RU, doit matcher via les ancres cyrilliques.
        r = _score("Французский авианосец «Шарль де Голль» в Средиземном море", "ru")
        assert r.score > 0.0
        assert r.evidence["has_anchor"] is True
        assert "carrier_named" in r.evidence["matched_terms"]

    def test_hull_number_anchor(self):
        r = _score("Le R91 est de retour à Toulon", "fr")
        assert r.evidence["has_anchor"] is True
        assert r.score > 0.0


class TestContextualGate:
    def test_generic_carrier_no_france_anchor_stays_low(self):
        # Porte-avions générique (US/chinois), aucune ancre FR -> ne doit pas gonfler.
        r = _score("A US aircraft carrier and its destroyer escort entered the bay.", "en")
        assert r.evidence["has_anchor"] is False
        assert r.score <= LOW

    def test_porte_avions_alone_is_contextual(self):
        r = _score("Un porte-avions a été aperçu au loin.", "fr")
        assert r.evidence["has_anchor"] is False
        assert r.score <= LOW

    def test_ambiguous_acronyms_gated(self):
        # « CSG » (cotisation sociale) et « GAN » (assureur) seuls : contextuels,
        # aucune ancre -> ne déclenchent pas (précision).
        r = _score("La CSG augmente et le GAN propose une nouvelle assurance.", "fr")
        assert r.evidence["has_anchor"] is False
        assert r.score <= LOW


class TestCooccurrenceImplicit:
    def test_implicit_mention_without_ship_name(self):
        # Niveau 4 : « porte-avions français » + « Toulon » + « escorte » couvre
        # plusieurs catégories ⇒ score élevé SANS nommer « Charles de Gaulle ».
        r = _score(
            "Le porte-avions français appareille de Toulon ; son escorte et son "
            "groupe aérien embarqué l'accompagnent en Méditerranée orientale.",
            "fr",
        )
        assert r.evidence["has_anchor"] is True
        assert r.score >= HIGH
        # Plusieurs catégories couvertes (cooccurrence).
        assert len(r.evidence["matched_terms"]) >= 2


class TestOffTopicAndGate:
    def test_off_topic_scores_zero(self):
        r = _score("The weather in Berlin is nice today.", "en")
        assert r.score == 0.0
        assert r.evidence["matched_terms"] == {}

    def test_adversary_domain_compounds(self):
        base = _score("Le porte-avions Charles de Gaulle", "fr")
        boosted = _score(
            "Le porte-avions Charles de Gaulle", "fr", cited_domains=["geopolitika.ru"]
        )
        assert boosted.score > base.score
        assert "geopolitika.ru" in boosted.evidence["domain_hits"]

    def test_never_drops_always_unit_interval(self):
        for txt in ["", None, "random", "Шарль де Голль Тулон"]:
            r = _score(txt)
            assert 0.0 <= r.score <= 1.0
