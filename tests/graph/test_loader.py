"""Tests du chargeur graphe (src/graph/loader.py).

PUR — aucun I/O DB. On construit de PETITS graphes synthétiques en mémoire à
partir de lignes ``edges``/``channels`` simulées, puis on assert : le multiplex
(plusieurs edge_types entre 2 nœuds), les nœuds domaine pour CITES_DOMAIN, et
les dérivations de features de nœud.
"""
import networkx as nx

from src.graph.loader import (
    DOMAIN_EDGE_TYPES,
    build_graph,
    credibility_prior,
    edge_family,
)


# --------------------------------------------------------------------------- #
# Fabriques de lignes simulées (forme = sortie de fetch_edge_rows/channel_rows).
# --------------------------------------------------------------------------- #
def edge_row(src, *, dst_channel=None, dst_domain=None, etype="FORWARD",
             count=1, weight=None, delay_seconds=None, window_delta_seconds=None):
    return {
        "src_channel_id": src,
        "dst_channel_id": dst_channel,
        "dst_domain": dst_domain,
        "edge_type": etype,
        "count": count,
        "weight": weight,
        "delay_seconds": delay_seconds,
        "text_sim": None,
        "window_delta_seconds": window_delta_seconds,
        "attrs": None,
    }


def channel_row(cid, *, username="", title="", member_count=0,
                fr_score=None, engagement=0):
    return {
        "channel_id": cid,
        "username": username,
        "title": title,
        "member_count": member_count,
        "fr_score": fr_score,
        "engagement": engagement,
    }


# --------------------------------------------------------------------------- #
# Dérivations de features de nœud.
# --------------------------------------------------------------------------- #
def test_credibility_prior_is_evidence_based():
    """Défaut D1 : le prior suit la preuve adverse, jamais la langue."""
    assert credibility_prior({"adversary_domain_citations": 1}) == "suspect"
    assert credibility_prior({"catalogued_adversary": True}) == "suspect"
    assert credibility_prior({"adversary_domain_citations": 0}) == "other"
    assert credibility_prior({}) == "other"


def test_edge_family_mapping():
    assert edge_family("FORWARD") == "propagation"
    assert edge_family("MENTIONS") == "influence"
    assert edge_family("CITES_DOMAIN") == "influence"
    assert edge_family("CO_FORWARD") == "coordination"


# --------------------------------------------------------------------------- #
# Construction du graphe + multiplex.
# --------------------------------------------------------------------------- #
def test_empty_graph_is_ok():
    """Table edges vide -> graphe vide (cas accepté, graph-model)."""
    g = build_graph([], [])
    assert isinstance(g, nx.MultiDiGraph)
    assert g.number_of_nodes() == 0


def test_channel_node_attributes():
    g = build_graph(
        [],
        [channel_row(1, username="france24_fr", title="France 24",
                     fr_score=0.8, engagement=4242)],
    )
    n = g.nodes[1]
    assert n["kind"] == "channel"
    assert n["username"] == "france24_fr"
    assert n["engagement"] == 4242          # poids de NŒUD (graph-model §2.2)
    assert n["credibility_prior"] == "other"


def test_multiplex_two_edge_types_between_same_pair():
    """Plusieurs types d'arête entre 2 mêmes canaux coexistent (multiplex)."""
    edges = [
        edge_row(1, dst_channel=2, etype="FORWARD", count=5),
        edge_row(1, dst_channel=2, etype="MENTIONS", count=3),
    ]
    g = build_graph(edges, [channel_row(1), channel_row(2)])
    # MultiDiGraph : 2 arêtes parallèles 1->2, clés = type.
    assert g.number_of_edges(1, 2) == 2
    keys = set(g[1][2].keys())
    assert keys == {"FORWARD", "MENTIONS"}
    assert g[1][2]["FORWARD"]["family"] == "propagation"
    assert g[1][2]["MENTIONS"]["family"] == "influence"


def test_cites_domain_creates_string_node():
    """CITES_DOMAIN -> nœud domaine string distinct (graph-model §2.2)."""
    edges = [edge_row(1, dst_domain="news-pravda.com", etype="CITES_DOMAIN", count=12)]
    g = build_graph(edges, [channel_row(1)])
    assert "news-pravda.com" in g
    assert g.nodes["news-pravda.com"]["kind"] == "domain"
    assert g.has_edge(1, "news-pravda.com")
    assert "CITES_DOMAIN" in DOMAIN_EDGE_TYPES


def test_discovered_channel_has_minimal_node():
    """Canal présent seulement dans une arête (non catalogué) -> nœud minimal."""
    g = build_graph([edge_row(1, dst_channel=99, etype="FORWARD")], [channel_row(1)])
    assert 99 in g
    assert g.nodes[99].get("kind") == "channel"
    assert "username" not in g.nodes[99] or g.nodes[99]["username"] == ""


def test_incoherent_rows_skipped():
    """Ligne sans cible canal ni domaine -> ignorée (pas de crash)."""
    bad = edge_row(1, etype="FORWARD")  # ni dst_channel ni dst_domain
    g = build_graph([bad], [channel_row(1)])
    assert g.number_of_edges() == 0
