"""Famille (b) — rôle en cascade. Tests purs, SANS base.

Ce module portait l'une des deux familles phares du score et n'avait **aucun
fichier de test dédié** (défaut D17). Les tests ci-dessous verrouillent ce que
le code fait réellement, y compris ses propriétés inconfortables :
l'échelle de la normalisation et la dégénérescence du terme vecteur propre.

Voir docs/method/03-suspicion-score.md §3.2 et docs/limitations.md D8/D9.
"""
import random
import statistics

import networkx as nx
import pytest

from src.scorer.cascade_role import (
    TRIGGER_THRESHOLD,
    W_CLUSTERING,
    W_EIGENVECTOR,
    W_IN_DEGREE,
    classify_archetype,
    compute_bridge_scores,
    score_cascade_role,
)


def _star(n_leaves: int = 5) -> nx.DiGraph:
    """Une étoile de forward : 0 est l'origine, les feuilles relaient."""
    g = nx.DiGraph()
    for i in range(1, n_leaves + 1):
        g.add_edge(0, i, weight=float(n_leaves - i + 1))
    return g


# --------------------------------------------------------------------------- #
# La formule.
# --------------------------------------------------------------------------- #
def test_bridge_raw_is_the_documented_linear_combination():
    g = _star(4)
    m = compute_bridge_scores(g)
    for cid, rec in m.items():
        expected = (
            W_IN_DEGREE * rec["in_centrality"]
            + W_EIGENVECTOR * rec["eigenvector"]
            + W_CLUSTERING * rec["clustering"]
        )
        assert rec["bridge_raw"] == pytest.approx(expected, abs=1e-5)


def test_bridge_norm_is_max_scaled_within_the_corpus():
    """D8 : la normalisation est relative au corpus, donc non comparable."""
    m = compute_bridge_scores(_star(4))
    norms = [r["bridge_norm"] for r in m.values()]
    assert max(norms) == pytest.approx(1.0)
    assert all(0.0 <= v <= 1.0 for v in norms)


def test_adding_a_bigger_hub_rescales_everyone_else():
    """Le test de non-régression de D8 : le score n'est pas une mesure.

    Le MÊME canal, dans le MÊME rôle structurel, obtient une valeur plus faible
    dès qu'un hub plus gros entre dans le corpus. C'est pourquoi les valeurs ne
    peuvent pas être comparées entre deux exports.
    """
    before = compute_bridge_scores(_star(3))[1]["bridge_norm"]

    g = _star(3)
    # Composante disjointe, bien plus dense : elle capte le maximum du corpus.
    for i in range(100, 130):
        for j in range(100, 130):
            if i != j:
                g.add_edge(i, j, count=1)
    after = compute_bridge_scores(g)[1]["bridge_norm"]

    assert before == pytest.approx(1.0)
    assert after < before


def _core_and_tail(n_tail: int) -> nx.DiGraph:
    """Noyau dense + longue traîne : topologie FIXE, seule la taille varie."""
    rng = random.Random(1312)
    g = nx.DiGraph()
    core = list(range(10))
    for i in core:
        for j in core:
            if i != j:
                g.add_edge(i, j, count=5)
    for n in range(100, 100 + n_tail):
        g.add_edge(rng.choice(core), n, count=1)
    return g


def test_term_scaling_crossover():
    """D9 : les composantes ne changent pas d'échelle au même rythme.

    ``in_degree_centrality`` est normalisée par ``n-1`` et décroît donc en
    ``1/n`` ; le vecteur propre L2-normalisé, non. À topologie CONSTANTE, faire
    seulement grossir le corpus renverse la composante dominante — le composite
    change de nature avec la taille du corpus, ce qui ruine la comparabilité
    entre deux runs (et compose avec D8).
    """
    def medians(n_tail):
        m = compute_bridge_scores(_core_and_tail(n_tail))
        return (
            statistics.median(W_IN_DEGREE * r["in_centrality"] for r in m.values()),
            statistics.median(W_EIGENVECTOR * r["eigenvector"] for r in m.values()),
        )

    small_in, small_eig = medians(100)    # ~110 nœuds
    large_in, large_eig = medians(2000)   # ~2010 nœuds

    # Petit corpus : le degré entrant domine.
    assert small_in > small_eig
    # Grand corpus : il est devenu négligeable — la domination s'est inversée.
    assert large_in < large_eig
    # Le terme de degré entrant s'effondre en ~1/n…
    assert large_in < small_in / 10
    # …tandis que le terme vecteur propre reste du même ordre.
    assert large_eig == pytest.approx(small_eig, rel=0.5)


# --------------------------------------------------------------------------- #
# Garde-fous.
# --------------------------------------------------------------------------- #
def test_empty_graph_yields_no_scores():
    assert compute_bridge_scores(nx.DiGraph()) == {}
    assert score_cascade_role(nx.DiGraph()) == {}


def test_isolated_channel_scores_zero_and_never_triggers():
    """Garde centralité dégénérée — BUG TROUVÉ ET CORRIGÉ (2026-09).

    networkx renvoie une centralité de 1 pour l'unique nœud d'un graphe
    singleton : le canal isolé obtenait ``bridge_raw = 17``, devenait le maximum
    du corpus, donc ``bridge_norm = 1.0`` et ``triggered = True`` — le score
    MAXIMAL pour un canal sans la moindre arête. ``scripts/build_dossier.py``
    consomme cette famille sans la couche rigoureuse qui masquait le symptôme.
    """
    g = nx.DiGraph()
    g.add_node(42)
    res = score_cascade_role(g)
    assert res[42].value == 0.0
    assert res[42].triggered is False
    assert res[42].evidence["archetype"] is None


def test_isolated_channel_inside_a_real_corpus_also_scores_zero():
    g = _star(4)
    g.add_node(999)  # catalogué mais sans aucune arête
    res = score_cascade_role(g)
    assert res[999].value == 0.0
    assert res[999].triggered is False
    # …sans écraser les canaux qui ont un vrai rôle.
    assert max(r.value for r in res.values()) == pytest.approx(1.0)


def test_scores_are_bounded_and_carry_their_evidence():
    res = score_cascade_role(_star(5))
    assert res
    for r in res.values():
        assert 0.0 <= r.value <= 1.0
        assert 0.0 <= r.confidence_low <= r.confidence_high <= 1.0
        assert r.triggered == (r.value >= TRIGGER_THRESHOLD)
        # Le dossier doit pouvoir justifier le rang sans rejouer le pipeline.
        for key in ("archetype", "bridge_raw", "bridge_norm", "in_degree_centrality"):
            assert key in r.evidence


def test_archetype_is_one_of_the_four_documented_labels():
    labels = {"seeding-source", "forward-hub", "cross-channel-bridge", "reactivator"}
    for r in score_cascade_role(_star(5)).values():
        assert r.evidence["archetype"] in labels


def test_reactivator_wins_on_long_delay():
    """La cascade de priorité place ``reactivator`` en premier."""
    metrics = {
        "bridge_norm": 0.9, "in_degree": 3, "out_degree": 1,
        "max_in_delay_s": 30 * 24 * 3600,
    }
    assert classify_archetype(metrics, 0.5, 2) == "reactivator"


def test_seeding_source_when_out_exceeds_in_without_hub_scale():
    metrics = {
        "bridge_norm": 0.0, "in_degree": 0, "out_degree": 1, "max_in_delay_s": 0,
    }
    assert classify_archetype(metrics, 0.5, 99) == "seeding-source"
