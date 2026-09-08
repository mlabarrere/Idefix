"""Test de FORME de l'exporteur statique — SANS base de données.

> Architecture 2026-06-08 : le livrable est un explorateur STATIQUE (HTML/CSS/JS
> lisant des JSON précalculés produits hors-ligne par ``scripts/export_static.py``
> sous ``data/``). Python = pipeline OFFLINE uniquement ; il n'y a plus de
> backend web cible (``src/api/`` est LEGACY/transitoire).

Ce test épingle le **contrat de sérialisation** de l'exporteur — risque R4
(fidélité des champs). Le front Cytoscape lit des noms de champs EXACTS ; un
renommage silencieux côté Python casserait le rendu sans qu'aucun test ne le
voie. On exerce donc ``_serialize_graph`` (fonction PURE) sur un petit graphe
``networkx.MultiDiGraph`` synthétique et on assoit les noms de champs attendus.

Aucune base, aucun Telegram, aucun réseau : on charge ``scripts/export_static.py``
via ``importlib`` (script hors package — même motif que
``tests/labeling/test_batch.py``), puis on appelle ``_serialize_graph`` directement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import networkx as nx

# ---------------------------------------------------------------------------
# Chargement du module scripts/export_static.py sans exécuter __main__.
# (export_static.py insère lui-même _REPO dans sys.path à l'import, donc les
#  imports ``src.*`` qu'il fait au niveau module se résolvent sans DB.)
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_static.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("export_static", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()

_serialize_graph = _mod._serialize_graph


# ---------------------------------------------------------------------------
# Graphe synthétique : 2 canaux + 1 domaine ; 1 arête FORWARD (propagation) et
# 1 arête CO_FORWARD (coordination). Attributs de nœud/arête posés EXACTEMENT
# comme build_graph (src/graph/loader.py) les pose — c'est le contrat réel.
# ---------------------------------------------------------------------------


def _make_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    # Nœuds canal (int) avec features, comme build_graph.
    g.add_node(
        1001,
        kind="channel",
        username="@dugin",
        title="Dugin",
        member_count=0,
        fr_score=0.06,
        credibility_prior="suspect",
        engagement=100,
    )
    g.add_node(
        1002,
        kind="channel",
        username="@relay",
        title="Relay",
        member_count=0,
        fr_score=0.50,
        credibility_prior="other",
        engagement=50,
    )
    # Nœud domaine (str), cible de CITES_DOMAIN.
    g.add_node("pravda-fr.com", kind="domain")

    # Arête de propagation (FORWARD) : 1001 -> 1002, avec delay_seconds.
    g.add_edge(
        1001,
        1002,
        key="FORWARD",
        edge_type="FORWARD",
        family="propagation",
        count=9,
        weight=None,
        delay_seconds=3600,
        text_sim=None,
        window_delta_seconds=None,
        attrs=None,
    )
    # Arête d'influence (CITES_DOMAIN) : 1001 -> domaine (pas de delay_seconds).
    g.add_edge(
        1001,
        "pravda-fr.com",
        key="CITES_DOMAIN",
        edge_type="CITES_DOMAIN",
        family="influence",
        count=4,
        weight=None,
        delay_seconds=None,
        text_sim=None,
        window_delta_seconds=None,
        attrs=None,
    )
    # Arête de coordination (CO_FORWARD) : 1001 <-> 1002, fenêtrée Δt.
    g.add_edge(
        1001,
        1002,
        key="CO_FORWARD",
        edge_type="CO_FORWARD",
        family="coordination",
        count=3,
        weight=None,
        delay_seconds=None,
        text_sim=None,
        window_delta_seconds=120,
        attrs=None,
    )
    return g


# ---------------------------------------------------------------------------
# Sérialisation : pure, aucun archétype (dict vide).
# ---------------------------------------------------------------------------


def _serialize():
    nodes, edges = _serialize_graph(_make_graph(), archetypes={})
    return nodes, edges


# ---------------------------------------------------------------------------
# Tests : nœuds.
# ---------------------------------------------------------------------------


class TestNodeContract:
    """Pin des noms de champs lus par le front Cytoscape sur les nœuds."""

    def test_returns_two_lists(self):
        nodes, edges = _serialize()
        assert isinstance(nodes, list)
        assert isinstance(edges, list)

    def test_channel_node_carries_exact_keys(self):
        nodes, _ = _serialize()
        chan = next(n for n in nodes if n.get("channel_id") == 1001)
        # Le front lit EXACTEMENT ces clés sur un nœud canal.
        assert set(chan) == {
            "channel_id",
            "username",
            "title",
            "archetype",
            "credibility_prior",
            "engagement",
            "fr_score",
            "confidence",
        }

    def test_channel_node_values_passthrough(self):
        nodes, _ = _serialize()
        chan = next(n for n in nodes if n.get("channel_id") == 1001)
        assert chan["username"] == "@dugin"
        assert chan["title"] == "Dugin"
        assert chan["credibility_prior"] == "suspect"
        assert chan["engagement"] == 100
        assert chan["fr_score"] == 0.06

    def test_archetype_is_none_when_not_precomputed(self):
        """archetypes={} -> archetype None (renseigné sinon par channel_scores)."""
        nodes, _ = _serialize()
        chan = next(n for n in nodes if n.get("channel_id") == 1001)
        assert chan["archetype"] is None

    def test_archetype_applied_when_provided(self):
        nodes, _ = _serialize_graph(_make_graph(), archetypes={1001: "reactivator"})
        chan = next(n for n in nodes if n.get("channel_id") == 1001)
        assert chan["archetype"] == "reactivator"

    def test_domain_node_is_single_key(self):
        """Un nœud domaine est strictement {"domain": <str>}."""
        nodes, _ = _serialize()
        dom = next(n for n in nodes if "domain" in n)
        assert dom == {"domain": "pravda-fr.com"}
        assert isinstance(dom["domain"], str)

    def test_node_count(self):
        nodes, _ = _serialize()
        # 2 canaux + 1 domaine.
        assert len(nodes) == 3


# ---------------------------------------------------------------------------
# Tests : arêtes.
# ---------------------------------------------------------------------------


def _edge_by_type(edges, etype):
    return next(e for e in edges if e.get("type") == etype)


class TestEdgeContract:
    """Pin des noms de champs lus par le front Cytoscape sur les arêtes."""

    def test_propagation_edge_uses_source_target(self):
        _, edges = _serialize()
        fwd = _edge_by_type(edges, "FORWARD")
        # Propagation/influence : orientée -> source/target.
        assert set(fwd) == {"family", "type", "source", "target", "count", "delay_seconds"}
        assert fwd["family"] == "propagation"
        assert fwd["source"] == 1001
        assert fwd["target"] == 1002
        assert fwd["count"] == 9
        assert fwd["delay_seconds"] == 3600

    def test_influence_edge_omits_delay_when_absent(self):
        """delay_seconds n'est ajouté que s'il est présent (CITES_DOMAIN: None)."""
        _, edges = _serialize()
        cite = _edge_by_type(edges, "CITES_DOMAIN")
        assert set(cite) == {"family", "type", "source", "target", "count"}
        assert "delay_seconds" not in cite
        assert cite["family"] == "influence"
        assert cite["source"] == 1001
        assert cite["target"] == "pravda-fr.com"
        assert cite["count"] == 4

    def test_coordination_edge_uses_a_b_dt(self):
        _, edges = _serialize()
        coord = _edge_by_type(edges, "CO_FORWARD")
        # Coordination : non orientée + Δt -> a/b/dt_seconds (PAS source/target).
        assert set(coord) == {"family", "type", "a", "b", "dt_seconds", "count"}
        assert coord["family"] == "coordination"
        assert coord["a"] == 1001
        assert coord["b"] == 1002
        assert coord["dt_seconds"] == 120
        assert coord["count"] == 3
        # Garde-fou : une arête de coordination n'expose JAMAIS source/target.
        assert "source" not in coord
        assert "target" not in coord

    def test_edge_count(self):
        _, edges = _serialize()
        # FORWARD + CITES_DOMAIN + CO_FORWARD.
        assert len(edges) == 3


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__, "-q"])
