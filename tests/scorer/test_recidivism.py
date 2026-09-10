"""Famille (d) — « récidive ». Tests purs, SANS base.

Seconde famille phare sans fichier de test dédié (défaut D17). Ces tests
verrouillent notamment le point que la documentation affirmait à tort pendant
plusieurs versions : **cette famille ne mesure rien d'inter-épisode.** Elle
mesure le degré et la force sortants sur un unique graphe de forward agrégé.

Voir docs/method/03-suspicion-score.md §3.4 et docs/limitations.md D8.
"""
import networkx as nx
import pytest

from src.scorer.recidivism import (
    TRIGGER_THRESHOLD,
    W_INFLUENCE,
    W_RECURRENCE,
    compute_recidivism_metrics,
    score_recidivism,
)


def _graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # 1 est massivement relayé (forte influence + forte récurrence).
    for relay, count in ((2, 10), (3, 8), (4, 6), (5, 4)):
        g.add_edge(1, relay, count=count)
    # 2 est relayé une fois.
    g.add_edge(2, 6, count=1)
    return g


# --------------------------------------------------------------------------- #
# Ce que la famille mesure réellement.
# --------------------------------------------------------------------------- #
def test_metrics_are_out_strength_and_out_degree():
    m = compute_recidivism_metrics(_graph())
    assert m[1]["forward_influence"] == 28.0   # 10 + 8 + 6 + 4
    assert m[1]["source_recurrence"] == 4      # 4 relayeurs distincts
    assert m[2]["forward_influence"] == 1.0
    assert m[2]["source_recurrence"] == 1
    # Un canal qui ne fait que relayer n'a aucune influence sortante.
    assert m[6]["forward_influence"] == 0.0
    assert m[6]["source_recurrence"] == 0


def test_value_is_the_documented_weighted_sum_of_normalized_terms():
    res = score_recidivism(_graph())
    m = compute_recidivism_metrics(_graph())
    max_i = max(v["forward_influence"] for v in m.values())
    max_r = max(v["source_recurrence"] for v in m.values())
    for cid, r in res.items():
        expected = (
            W_INFLUENCE * (m[cid]["forward_influence"] / max_i)
            + W_RECURRENCE * (m[cid]["source_recurrence"] / max_r)
        )
        assert r.value == pytest.approx(expected, abs=1e-5)


def test_family_has_no_episode_component_at_all():
    """Non-régression documentaire : la famille est nommée « récidive » mais
    aucun épisode n'entre dans son calcul. Son évidence doit le dire."""
    res = score_recidivism(_graph())
    ev = res[1].evidence
    assert set(ev) == {
        "forward_influence",
        "source_recurrence",
        "forward_influence_norm",
        "source_recurrence_norm",
        "note",
    }
    assert "épisode" in ev["note"].lower()


def test_scores_are_corpus_relative(capsys):
    """D8 : mêmes arêtes, corpus plus gros -> valeur plus faible."""
    before = score_recidivism(_graph())[2].value

    g = _graph()
    for i in range(100, 140):          # un relayeur bien plus influent
        g.add_edge(99, i, count=50)
    after = score_recidivism(g)[2].value

    assert after < before


# --------------------------------------------------------------------------- #
# Garde-fous.
# --------------------------------------------------------------------------- #
def test_empty_graph_yields_no_scores():
    assert compute_recidivism_metrics(nx.DiGraph()) == {}
    assert score_recidivism(nx.DiGraph()) == {}


def test_graph_without_edges_scores_zero_everywhere():
    g = nx.DiGraph()
    g.add_nodes_from([1, 2, 3])
    res = score_recidivism(g)
    assert all(r.value == 0.0 and r.triggered is False for r in res.values())


def test_values_are_bounded_and_trigger_consistently():
    for r in score_recidivism(_graph()).values():
        assert 0.0 <= r.value <= 1.0
        assert 0.0 <= r.confidence_low <= r.confidence_high <= 1.0
        assert r.triggered == (r.value >= TRIGGER_THRESHOLD)


def test_top_channel_reaches_the_maximum():
    res = score_recidivism(_graph())
    assert res[1].value == pytest.approx(1.0)
    assert res[1].triggered is True
