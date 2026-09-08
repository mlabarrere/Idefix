"""
Score family (b) — cascade role via Bridge Score.

Reference: Bridge Score (arXiv:2411.05922), PRD FR-5 / FR-9.

    bridge_raw = 10 * in_degree_centrality
               +  7 * eigenvector_centrality
               +  7 * clustering_coefficient

Computed on the forward graph (DiGraph, edge = origin -> reposter, weight = count).

IMPORTANT — orientation des arêtes (cf. scripts/build_graph.py) :
    une arête va de l'ORIGINE (canal dont le message est relayé)
    vers le RELAYEUR (canal qui republie).
    Donc :
      - out-degree  d'un nœud = nombre de canaux qui le relaient  -> fan-out / influence
      - in-degree   d'un nœud = nombre d'origines distinctes qu'il relaie

Archetypes (un par canal) :
    seeding-source        : relayé tôt et largement, relaie peu lui-même
                            (out fort, in faible)
    forward-hub           : très fort fan-out (out_weight élevé)
    cross-channel-bridge  : Bridge Score élevé (rôle structurel de pont)
    reactivator           : republie avec un délai élevé (réactivation
                            d'un narratif ancien)

Library-first : centralités et clustering via networkx.
"""

from __future__ import annotations

import networkx as nx

from src.shared.dossier import ScoreResult

# Coefficients du Bridge Score (arXiv:2411.05922)
W_IN_DEGREE = 10.0
W_EIGENVECTOR = 7.0
W_CLUSTERING = 7.0

# Seuil de déclenchement (sur la valeur normalisée [0,1])
TRIGGER_THRESHOLD = 0.3

# Délai (secondes) au-delà duquel un relai est considéré comme une réactivation
REACTIVATION_DELAY_S = 7 * 24 * 3600  # 7 jours


def _eigenvector_centrality(graph: nx.DiGraph) -> dict[int, float]:
    """Centralité de vecteur propre, robuste aux graphes peu connexes."""
    try:
        return nx.eigenvector_centrality_numpy(graph, weight="count")
    except Exception:
        try:
            return nx.eigenvector_centrality(
                graph, max_iter=1000, weight="count"
            )
        except Exception:
            # Graphe dégénéré : repli neutre
            return {n: 0.0 for n in graph.nodes}


def compute_bridge_scores(graph: nx.DiGraph) -> dict[int, dict]:
    """
    Calcule le Bridge Score brut et normalisé pour chaque nœud, ainsi que
    les composantes nécessaires à l'attribution d'archétype.

    Retourne : {channel_id: {bridge_raw, bridge_norm, in_centrality,
                eigenvector, clustering, in_degree, out_degree,
                in_weight, out_weight, max_in_delay}}
    """
    if graph.number_of_nodes() == 0:
        return {}

    in_centrality = nx.in_degree_centrality(graph)
    eigen = _eigenvector_centrality(graph)
    # Coefficient de clustering : sur la version non-orientée (définition standard)
    clustering = nx.clustering(graph.to_undirected())

    # Poids entrants / sortants (forwards) et délai max sur les arêtes entrantes
    in_weight: dict[int, float] = {n: 0.0 for n in graph.nodes}
    out_weight: dict[int, float] = {n: 0.0 for n in graph.nodes}
    max_in_delay: dict[int, int] = {n: 0 for n in graph.nodes}
    for origin, reposter, data in graph.edges(data=True):
        w = float(data.get("count", 1))
        out_weight[origin] += w          # forwards que l'origine fait gagner
        in_weight[reposter] += w         # forwards émis par le relayeur
        delay = int(data.get("min_delay_s", 0) or 0)
        if delay > max_in_delay[reposter]:
            max_in_delay[reposter] = delay

    raw: dict[int, float] = {}
    for n in graph.nodes:
        raw[n] = (
            W_IN_DEGREE * in_centrality.get(n, 0.0)
            + W_EIGENVECTOR * eigen.get(n, 0.0)
            + W_CLUSTERING * clustering.get(n, 0.0)
        )

    max_raw = max(raw.values()) if raw else 0.0

    result: dict[int, dict] = {}
    for n in graph.nodes:
        bridge_norm = (raw[n] / max_raw) if max_raw > 0 else 0.0
        result[n] = {
            "bridge_raw": round(raw[n], 6),
            "bridge_norm": round(bridge_norm, 6),
            "in_centrality": round(in_centrality.get(n, 0.0), 6),
            "eigenvector": round(eigen.get(n, 0.0), 6),
            "clustering": round(clustering.get(n, 0.0), 6),
            "in_degree": graph.in_degree(n),
            "out_degree": graph.out_degree(n),
            "in_weight": in_weight[n],
            "out_weight": out_weight[n],
            "max_in_delay_s": max_in_delay[n],
        }
    return result


def classify_archetype(
    metrics: dict,
    bridge_norm_p75: float,
    fanout_hub_threshold: int,
) -> str | None:
    """
    Attribue un archétype de rôle de cascade à un canal à partir de ses métriques.

    Rappel orientation : out_degree = nb de canaux qui RELAIENT ce canal (fan-out) ;
    in_degree = nb d'origines distinctes que ce canal RELAIE.

    Priorité d'attribution :
      1. reactivator         — relaie avec un délai >= REACTIVATION_DELAY_S
      2. cross-channel-bridge— Bridge Score normalisé dans le quartile supérieur
                               ET joue un rôle de relais (in_degree > 0)
      3. forward-hub         — fort fan-out (out_degree >= seuil P-élevé)
      4. seeding-source      — relayé mais ne relaie pas (out>0, in==0) :
                               origine de propagation
    Retourne None pour un canal isolé (aucune arête).
    """
    in_deg = metrics["in_degree"]
    out_deg = metrics["out_degree"]

    if in_deg == 0 and out_deg == 0:
        return None

    # 1. Réactivateur : republie un contenu avec un délai élevé.
    if metrics["max_in_delay_s"] >= REACTIVATION_DELAY_S:
        return "reactivator"

    # 2. Pont inter-canaux : rôle structurel fort ET relaie effectivement
    #    (un pont fait transiter le contenu, donc in_degree > 0).
    if (
        bridge_norm_p75 > 0
        and metrics["bridge_norm"] >= bridge_norm_p75
        and in_deg > 0
    ):
        return "cross-channel-bridge"

    # 3. Forward-hub : fan-out marqué (relayé par un nombre élevé de canaux).
    if out_deg >= fanout_hub_threshold and out_deg > in_deg:
        return "forward-hub"

    # 4. Seeding-source : relayé alors qu'il ne relaie pas/peu -> origine.
    if out_deg > in_deg:
        return "seeding-source"

    # Cas restant : relaie au moins autant qu'il n'est relayé -> relayeur.
    return "forward-hub"


def _percentile(values: list[float], pct: float) -> float:
    """Percentile simple (interpolation linéaire), sans dépendance numpy directe."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def score_cascade_role(graph: nx.DiGraph) -> dict[int, ScoreResult]:
    """
    Calcule la famille (b) « rôle de cascade » pour tous les canaux du graphe.

    Retourne {channel_id: ScoreResult(family="cascade_role", ...)} où
    `value` est le Bridge Score normalisé dans [0,1] et `evidence` détaille
    les composantes et l'archétype attribué.
    """
    metrics = compute_bridge_scores(graph)
    if not metrics:
        return {}

    bridge_norms = [m["bridge_norm"] for m in metrics.values()]
    p75 = _percentile(bridge_norms, 0.75)

    # Seuil de fan-out pour qualifier un forward-hub : P90 des out-degrees > 1.
    out_degrees = [m["out_degree"] for m in metrics.values() if m["out_degree"] > 1]
    fanout_hub_threshold = max(2, round(_percentile(out_degrees, 0.90))) if out_degrees else 2

    results: dict[int, ScoreResult] = {}
    for channel_id, m in metrics.items():
        value = m["bridge_norm"]
        archetype = classify_archetype(m, p75, fanout_hub_threshold)
        results[channel_id] = ScoreResult(
            family="cascade_role",
            value=value,
            # Bande de confiance : largeur fonction de la rareté des arêtes
            # (un nœud peu connecté a un score moins fiable).
            confidence_low=round(max(0.0, value - 0.15), 6),
            confidence_high=round(min(1.0, value + 0.15), 6),
            triggered=value >= TRIGGER_THRESHOLD,
            evidence={
                "archetype": archetype,
                "bridge_raw": m["bridge_raw"],
                "bridge_norm": m["bridge_norm"],
                "in_degree_centrality": m["in_centrality"],
                "eigenvector_centrality": m["eigenvector"],
                "clustering_coefficient": m["clustering"],
                "in_degree": m["in_degree"],
                "out_degree": m["out_degree"],
                "in_weight": m["in_weight"],
                "out_weight": m["out_weight"],
                "max_in_delay_s": m["max_in_delay_s"],
            },
        )
    return results
