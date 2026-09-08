"""Tests des familles d'empreinte Telegram (mission GAN) + rubrique EEFI (purs, SANS DB)."""
import networkx as nx

from src.scorer.eefi_rubric import (
    eefi_disclosure_detail,
    eefi_disclosure_precision,
    null_rubric,
)
from src.scorer.telegram_footprint import (
    score_telegram_adverse_attention,
    score_telegram_disclosure_precision,
    score_telegram_propagation,
    score_telegram_source_diversity,
    score_telegram_velocity,
    score_telegram_visibility,
)


def _graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node(1, engagement=1000)
    g.add_node(2, engagement=10)
    g.add_node(3, engagement=0)
    g.add_node(4, engagement=5)
    g.add_node(5, engagement=0)  # isolé
    g.add_edge(1, 2, count=5, min_delay_s=60)
    g.add_edge(1, 3, count=2, min_delay_s=7200)
    g.add_edge(1, 4, count=1, min_delay_s=120)
    g.add_edge(2, 3, count=1, min_delay_s=100000)
    return g


class TestEefiRubric:
    def test_exact_position_scores_max(self):
        assert eefi_disclosure_precision("Position 43.12 N coordonnées exactes", "fr") == 1.0

    def test_escort_composition_mid(self):
        a = eefi_disclosure_precision("Le groupe est escorté de la frégate Forbin", "fr")
        assert 0.8 <= a <= 0.95

    def test_off_topic_zero(self):
        assert eefi_disclosure_precision("La météo est belle aujourd'hui", "fr") == 0.0

    def test_none_zero_and_null_rubric(self):
        assert eefi_disclosure_precision(None) == 0.0
        assert null_rubric("Position 43.12 N coordonnées", "fr") == 0.0

    def test_detail_lists_indicators(self):
        d = eefi_disclosure_detail("coordonnées GPS, prochaine escale à Suez", "fr")
        assert d["adi"] == 1.0
        assert "exact_position" in d["indicators"]


class TestVisibility:
    def test_max_engagement_is_one(self):
        r = score_telegram_visibility(_graph())
        assert r[1].value == 1.0
        assert r[3].value == 0.0
        assert r[1].value > r[2].value > r[3].value


class TestPropagation:
    def test_reach_from_out_forwards(self):
        r = score_telegram_propagation(_graph())
        assert r[1].value == 1.0          # reach 8 = max
        assert r[3].value == 0.0          # aucune arête sortante
        assert r[1].value > r[2].value


class TestSourceDiversity:
    def test_hub_has_most_partners(self):
        r = score_telegram_source_diversity(_graph())
        assert r[1].value == 1.0          # partenaires {2,3,4} = 3 = max
        assert r[4].value < r[1].value    # feuille


class TestVelocity:
    def test_fast_relay_high_isolated_zero(self):
        r = score_telegram_velocity(_graph())
        assert r[2].value > 0.5           # min_delay 60s -> rapide
        assert r[5].value == 0.0          # isolé : aucun signal
        # un relai lent (100000s sur 2->3) reste plus bas qu'un rapide
        assert r[2].value > 0.0


class TestAdverseAttention:
    def test_inbound_from_adversary(self):
        r = score_telegram_adverse_attention(_graph(), adversary_channel_ids={1})
        assert r[2].value == 1.0          # 100% des forwards entrants viennent de 1 (adverse)
        assert abs(r[3].value - (2 / 3)) < 1e-6  # 2 de #1 (adverse) / 3 total
        assert r[1].value == 0.0          # aucun forward entrant

    def test_no_adversary_set(self):
        r = score_telegram_adverse_attention(_graph(), adversary_channel_ids=set())
        assert all(res.value == 0.0 for res in r.values())


class TestDisclosurePrecision:
    def test_max_with_coverage(self):
        msgs = {
            1: [("Position 43.12 N coordonnées", "fr"), ("rien", "fr")],
            2: [("la météo", "fr")],
            3: [],
        }
        r = score_telegram_disclosure_precision(msgs, eefi_disclosure_precision)
        assert r[1].value == 1.0
        assert r[1].evidence["coverage"] == 0.5
        assert r[2].value == 0.0
        assert r[3].value == 0.0

    def test_injected_null_rubric_degrades(self):
        msgs = {1: [("Position 43.12 N coordonnées", "fr")]}
        r = score_telegram_disclosure_precision(msgs, null_rubric)
        assert r[1].value == 0.0


def test_empty_graph_safe():
    empty = nx.DiGraph()
    for fn in (score_telegram_visibility, score_telegram_propagation,
               score_telegram_source_diversity, score_telegram_velocity):
        assert fn(empty) == {}
    assert score_telegram_adverse_attention(empty, {1}) == {}
