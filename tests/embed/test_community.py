"""Offline tests for embedding-aware community helpers."""
from __future__ import annotations

import networkx as nx
import numpy as np

from src.embed.community import add_embedding_edges, comparison_block, intra_cohesion

_E0 = np.array([1.0, 0.0], np.float32)
_E1 = np.array([0.0, 1.0], np.float32)


def test_intra_cohesion_perfect_and_zero():
    emb = {1: _E0, 2: _E0, 3: _E1, 4: _E1}
    coherent = {1: 0, 2: 0, 3: 1, 4: 1}  # each community is one direction
    assert intra_cohesion(coherent, emb) == 1.0

    mixed = {1: 0, 2: 0}  # e0 and e1 in same community
    assert intra_cohesion({1: 0, 2: 0}, {1: _E0, 2: _E1}) == 0.0
    assert intra_cohesion(mixed, {1: _E0, 2: _E0}) == 1.0


def test_add_embedding_edges_links_similar_only():
    g = nx.MultiDiGraph()
    g.add_nodes_from([1, 2, 3])
    emb = {1: _E0, 2: _E0, 3: _E1}  # 1~2 similar, 3 orthogonal
    g2 = add_embedding_edges(g, emb, k=5, threshold=0.5)

    assert g2.has_edge(1, 2)
    assert g2.get_edge_data(1, 2)["EMB_SIM"]["edge_type"] == "EMB_SIM"
    assert not g2.has_edge(1, 3) and not g2.has_edge(2, 3)
    # original graph untouched (copy)
    assert g.number_of_edges() == 0
    # unordered pair added once
    assert g2.number_of_edges() == 1


def test_comparison_block_reports_gain():
    w = np.array([1.0, 1.0], np.float32) / np.sqrt(2.0)  # cos 0.707 with e0
    emb = {1: _E0, 2: _E0, 3: w}
    comm_a = {1: 0, 2: 0, 3: 0}  # one loose group (e0, e0, w) -> cohesion < 1
    comm_e = {1: 0, 2: 0, 3: 1}  # split off the odd one -> tight group
    block = comparison_block(emb, comm_a, comm_e, 0.40, 0.55, n_bridges=3)

    assert 0.0 < block["intra_cohesion"]["analytics"] < 1.0
    assert block["intra_cohesion"]["embedding"] == 1.0
    assert block["intra_cohesion"]["gain_pct"] is not None
    assert block["intra_cohesion"]["gain_pct"] > 0
    assert block["modularity"] == {"analytics": 0.4, "embedding": 0.55}
    assert block["n_bridges"] == 3
