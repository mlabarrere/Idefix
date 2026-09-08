"""
Score family (d) — cross-episode recidivism.

PRD : épine dorsale = forward-influence + récurrence de canal-source
(analogue Telegram du « low-credibility h-index » / Foreign Information
Manipulation, cf. CLAUDE.md §3 hyp. 3 et §6 score (d)).

Composantes (calculées sur le graphe de forward EXISTANT, sans appel Telegram) :

  - forward-influence    : nombre de forwards GAGNÉS par le canal, c.-à-d. la
                           somme des poids des arêtes SORTANTES (origine ->
                           relayeur). Mesure combien le contenu d'un canal est
                           repris par d'autres canaux.
  - source-recurrence    : nombre de canaux-relayeurs DISTINCTS qui reprennent
                           ce canal (out-degree). Approxime la récurrence comme
                           source de propagation à travers les épisodes
                           observés dans le graphe.

ATTENTION orientation des arêtes (cf. scripts/build_graph.py) :
    arête = ORIGINE -> RELAYEUR. Le « forward-influence » d'un canal est donc
    porté par ses arêtes SORTANTES.

Library-first : agrégation via networkx.

NB PoC : faute de table d'épisodes peuplée, la « récidive cross-épisode » est
approximée par la récurrence structurelle dans le graphe de forward agrégé.
La métrique est portable vers une vraie agrégation multi-épisode sans changer
la signature publique.

Reference (cf. docs/references.md): approximation structurelle, sans référence
externe forte ; inspirée de la notion de « low-credibility h-index » (récurrence
d'une source à travers les épisodes).
"""

from __future__ import annotations

import networkx as nx

from src.shared.dossier import ScoreResult

# Poids de combinaison entre influence (volume) et récurrence (étendue).
W_INFLUENCE = 0.6
W_RECURRENCE = 0.4

TRIGGER_THRESHOLD = 0.3


def compute_recidivism_metrics(graph: nx.DiGraph) -> dict[int, dict]:
    """
    Calcule, pour chaque canal :
      - forward_influence  : somme des poids des arêtes sortantes (forwards gagnés)
      - source_recurrence  : nb de relayeurs distincts (out-degree)
    """
    if graph.number_of_nodes() == 0:
        return {}

    # forward-influence = somme pondérée des arêtes sortantes (networkx traite un
    # poids "count" manquant comme 1) ; source-recurrence = out-degree (nombre de
    # relayeurs distincts).
    influence = dict(graph.out_degree(weight="count"))
    recurrence = dict(graph.out_degree())
    return {
        n: {
            "forward_influence": float(influence.get(n, 0)),
            "source_recurrence": recurrence.get(n, 0),
        }
        for n in graph.nodes
    }


def score_recidivism(graph: nx.DiGraph) -> dict[int, ScoreResult]:
    """
    Calcule la famille (d) « récidivisme » pour tous les canaux du graphe.

    `value` ∈ [0,1] combine forward-influence et récurrence de canal-source,
    chacune normalisée par son maximum observé.
    """
    metrics = compute_recidivism_metrics(graph)
    if not metrics:
        return {}

    max_influence = max((m["forward_influence"] for m in metrics.values()), default=0.0)
    max_recurrence = max((m["source_recurrence"] for m in metrics.values()), default=0)

    results: dict[int, ScoreResult] = {}
    for channel_id, m in metrics.items():
        infl_norm = (m["forward_influence"] / max_influence) if max_influence > 0 else 0.0
        recur_norm = (m["source_recurrence"] / max_recurrence) if max_recurrence > 0 else 0.0
        value = W_INFLUENCE * infl_norm + W_RECURRENCE * recur_norm

        results[channel_id] = ScoreResult(
            family="recidivism",
            value=round(value, 6),
            confidence_low=round(max(0.0, value - 0.15), 6),
            confidence_high=round(min(1.0, value + 0.15), 6),
            triggered=value >= TRIGGER_THRESHOLD,
            evidence={
                "forward_influence": m["forward_influence"],
                "source_recurrence": m["source_recurrence"],
                "forward_influence_norm": round(infl_norm, 6),
                "source_recurrence_norm": round(recur_norm, 6),
                "note": (
                    "Récidive approximée par la récurrence structurelle dans le "
                    "graphe de forward agrégé (table d'épisodes non peuplée en PoC)."
                ),
            },
        )
    return results
