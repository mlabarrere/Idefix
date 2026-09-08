"""Tests for the anchored-France frontier scoring (scripts/snowball_crawl.py).

Pure-function tests only — no DB, no Telegram. We load the module by file path because
``scripts`` is not an installed package (no __init__.py, no pythonpath entry).
"""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "snowball_crawl",
    Path(__file__).resolve().parents[2] / "scripts" / "snowball_crawl.py",
)
snowball = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(snowball)


class TestFrontierScore:
    def test_france_sum_dominates_volume(self):
        """Critère premier inversé vs in_fwd DESC : un candidat relayé par une graine France
        (somme fr~0.8) bat un candidat de l'appareil non-France (somme fr~0) même si ce dernier
        a un in_fwd bien plus gros."""
        france = snowball._frontier_score(relay_fr_sum=0.8, distinct_relayers=2, in_fwd=5)
        non_france = snowball._frontier_score(relay_fr_sum=0.0, distinct_relayers=2, in_fwd=500)
        assert france > non_france

    def test_single_strong_france_seed_is_not_diluted(self):
        """LE cœur du pivot v2 : la somme (≠ moyenne) ne se dilue PAS. Un candidat relayé par
        UNE seule graine France@0.8 + 50 canaux non-France@0 (somme=0.8, 51 relayeurs) bat un
        candidat relayé par 50 canaux non-France@0 (somme=0). La moyenne v1 (0.8/51≈0.016)
        l'aurait au contraire écrasé."""
        diluted_input = snowball._frontier_score(
            relay_fr_sum=0.8, distinct_relayers=51, in_fwd=300)
        pure_non_france = snowball._frontier_score(
            relay_fr_sum=0.0, distinct_relayers=50, in_fwd=300)
        assert diluted_input > pure_non_france

    def test_france_sum_is_primary_at_comparable_volume(self):
        """À volume/largeur comparables, la somme-France (composante primaire) décide seule :
        plus de relay_fr_sum ⇒ score plus haut."""
        more_fr = snowball._frontier_score(relay_fr_sum=0.6, distinct_relayers=2, in_fwd=10)
        less_fr = snowball._frontier_score(relay_fr_sum=0.1, distinct_relayers=2, in_fwd=10)
        assert more_fr > less_fr

    def test_breadth_breaks_tie_at_equal_france(self):
        """À relay_fr_sum égal, plus de relayeurs distincts (corroboration) = score plus haut."""
        wide = snowball._frontier_score(relay_fr_sum=0.3, distinct_relayers=5, in_fwd=10)
        narrow = snowball._frontier_score(relay_fr_sum=0.3, distinct_relayers=1, in_fwd=10)
        assert wide > narrow

    def test_volume_breaks_tie_at_equal_france_and_breadth(self):
        """Signal secondaire conservé : in_fwd départage à somme-France et largeur égales."""
        heavy = snowball._frontier_score(relay_fr_sum=0.3, distinct_relayers=2, in_fwd=100)
        light = snowball._frontier_score(relay_fr_sum=0.3, distinct_relayers=2, in_fwd=1)
        assert heavy > light

    def test_logs_handle_zero_and_negative_guard(self):
        """log1p sur 0 = 0 ; les gardes max(.,0) évitent toute valeur négative imprévue."""
        assert snowball._frontier_score(0.0, 0, 0) == 0.0
        assert snowball._frontier_score(0.0, -3, -9) == 0.0  # gardes ramènent à log1p(0)=0

    def test_sat_clamped_to_unit_interval(self):
        """_sat est bornée STRICTEMENT à [0,1] aux deux bouts (clamp haut load-bearing)."""
        assert snowball._sat(0, 8) == 0.0
        assert snowball._sat(-5, 8) == 0.0
        assert snowball._sat(8, 8) == 1.0          # x == ref → exactement 1
        assert snowball._sat(10**9, 200) == 1.0    # x >> ref → clampé à 1, ne dépasse JAMAIS

    def test_france_dominates_even_at_pathological_volume(self):
        """Invariant load-bearing (régression du clamp manquant) : un candidat 0-France ne peut
        PAS battre un candidat à somme-France saturée, même avec un in_fwd/largeur astronomiques."""
        france = snowball._frontier_score(relay_fr_sum=snowball.FR_SUM_REF, distinct_relayers=2,
                                          in_fwd=5)
        non_france = snowball._frontier_score(
            relay_fr_sum=0.0, distinct_relayers=10_000, in_fwd=1_000_000)
        assert france > non_france
        # la masse auxiliaire ne peut excéder W_BREADTH + W_VOLUME = 0.30 (< 1)
        assert non_france <= snowball.W_BREADTH + snowball.W_VOLUME + 1e-9


class TestRankFrontier:
    def _row(self, cid, uname, fr_sum, relayers, in_fwd, france_relayers=0):
        return {
            "channel_id": cid,
            "username": uname,
            "relay_fr_sum": fr_sum,
            "distinct_relayers": relayers,
            "in_fwd": in_fwd,
            "france_relayers": france_relayers,
        }

    def test_orders_by_france_proximity_and_caps(self):
        rows = [
            self._row(1, "non_france_hub", 0.0, 3, 800),       # gros in_fwd, 0 France
            self._row(2, "france_relayed", 0.7, 2, 4, france_relayers=1),
            self._row(3, "mixed", 0.2, 1, 50, france_relayers=1),
        ]
        ranked, anchored = snowball._rank_frontier(rows, cap=2, anchor_threshold=0.0)
        assert [r["username"] for r in ranked] == ["france_relayed", "mixed"]
        assert len(ranked) == 2  # cap respecté
        assert all(r["username"] != "non_france_hub" for r in ranked)

    def test_one_france_seed_beats_fifty_non_france_whatever_volume(self):
        """Exigence d'ancrage (Micky) : un candidat relayé par 1 graine France@0.8 doit battre
        un candidat relayé par 50 canaux non-France@0, quel que soit le volume. Vrai SANS même
        avoir besoin du filtre dur — la somme saturée suffit ; le filtre dur (ci-dessous) ne fait
        que retirer carrément le second."""
        rows = [
            self._row(1, "fifty_non_france", 0.0, 50, 10_000, france_relayers=0),
            self._row(2, "one_france_seed", 0.8, 1, 2, france_relayers=1),
        ]
        ranked, _ = snowball._rank_frontier(rows, cap=2, anchor_threshold=0.0)
        assert ranked[0]["username"] == "one_france_seed"

    def test_hard_anchor_drops_non_anchored_candidates(self):
        """Filtre dur : avec θ>0, un candidat sans aucune graine France (france_relayers=0) est
        EXCLU de la frontière, même s'il a le meilleur score brut."""
        rows = [
            self._row(1, "non_anchored", 0.0, 50, 10_000, france_relayers=0),
            self._row(2, "anchored", 0.5, 1, 2, france_relayers=1),
        ]
        ranked, anchored = snowball._rank_frontier(rows, cap=10, anchor_threshold=0.15)
        assert anchored is True
        assert [r["username"] for r in ranked] == ["anchored"]

    def test_anchor_fallback_when_no_candidate_anchored(self):
        """Fallback propre : si l'ancrage vide la frontière (aucun candidat ancré), on retombe
        sur le tri global non ancré et anchored=False (l'appelant émet le warning)."""
        rows = [
            self._row(1, "a", 0.0, 5, 100, france_relayers=0),
            self._row(2, "b", 0.0, 2, 10, france_relayers=0),
        ]
        ranked, anchored = snowball._rank_frontier(rows, cap=10, anchor_threshold=0.15)
        assert anchored is False
        assert len(ranked) == 2  # rien n'a été perdu — le crawl n'est pas bloqué

    def test_score_field_present_and_enriched(self):
        ranked, _ = snowball._rank_frontier(
            [self._row(9, "c", 0.4, 2, 10, france_relayers=1)], cap=10, anchor_threshold=0.0)
        r = ranked[0]
        assert {"channel_id", "username", "in_fwd", "distinct_relayers",
                "relay_fr_sum", "france_relayers", "score"}.issubset(r.keys())
        assert isinstance(r["score"], float)

    def test_breadth_and_volume_break_ties_at_equal_france(self):
        # à relay_fr_sum égal, a (relai unique, volume 1) finit dernier ; b et c (corroborés
        # par volume ou largeur) passent devant. Ordre déterministe et stable.
        rows = [
            self._row(1, "a", 0.3, 1, 1),
            self._row(2, "b", 0.3, 2, 100),
            self._row(3, "c", 0.3, 5, 1),
        ]
        ranked, _ = snowball._rank_frontier(rows, cap=3, anchor_threshold=0.0)
        assert ranked[-1]["username"] == "a"
        assert {ranked[0]["username"], ranked[1]["username"]} == {"b", "c"}
