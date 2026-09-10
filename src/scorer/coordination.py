"""
Score family (c) — coordination (co-forwarding structurel).

docs/method/03-suspicion-score.md §3.3 : la détection de coordination de référence est VIGINUM
D3lta (similarité textuelle copypasta / reformulation / traduction). D3lta est
DIFFÉRÉ pour le PoC ; en attendant, cette implémentation s'appuie sur le signal
de coordination STRUCTUREL réellement présent dans le graphe de forward :

    co-forwarding = deux canaux relaient le MÊME ensemble de canaux-origine.

Intuition : des canaux qui, de façon récurrente, repartagent les mêmes sources
adoptent un comportement de relai convergent — un des signaux faibles de
coordination de §7-2 (« co-forward recurrence »). On le mesure par la
similarité de Jaccard des ensembles d'origines de forward entre paires de
canaux.

ATTENTION orientation des arêtes (cf. scripts/build_graph.py / score_channels.py):
    arête = ORIGINE -> RELAYEUR.
    L'ensemble des origines relayées par un canal `r` = ses prédécesseurs dans
    le DiGraph (predecessors(r)).

Métriques par canal :
  - jaccard_max         : meilleure similarité de Jaccard de ses origines avec
                          un autre canal co-forwardant (force du lien le plus
                          fort).
  - jaccard_mean        : moyenne des Jaccard > 0 avec ses pairs (largeur).
  - coforward_partners  : nb de canaux avec lesquels il partage >=1 origine.
  - shared_origin_pairs : nb de paires (canal, origine) co-relayées avec un pair.

Le `value` ∈ [0,1] combine la force du lien le plus fort (jaccard_max) et la
largeur du voisinage co-forwardant (partners normalisés).

Library-first : voisinages et agrégations via networkx ; pas de dépendance
externe au-delà de celles déjà utilisées par les autres scorers.

References (cf. docs/reference/references.md):
  - Coordinated Inauthentic Behavior : Pacheco et al. (2021), ICWSM ;
    Giglietto et al. (2020), Information, Communication & Society.
  - Cible texte (différée) : VIGINUM D3lta (similarité copypasta/reformulation).
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import networkx as nx

from src.graph.loader import COORDINATION_EDGE_TYPES
from src.shared.dossier import ScoreResult

# Poids de combinaison entre force du lien (jaccard_max) et étendue (partners).
W_STRENGTH = 0.7
W_BREADTH = 0.3

# Une origine n'est comptée comme co-relayée que si au moins ce nombre de
# relayeurs distincts la partagent (filtre le bruit des origines à relayeur unique).
MIN_SHARERS = 2

TRIGGER_THRESHOLD = 0.3


def _origins_by_channel(graph: nx.DiGraph) -> dict[int, set[int]]:
    """Ensemble des canaux-origine relayés par chaque canal (= ses prédécesseurs)."""
    origins: dict[int, set[int]] = {}
    for n in graph.nodes:
        preds = set(graph.predecessors(n))
        if preds:
            origins[n] = preds
    return origins


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union if union else 0.0


def compute_coordination_metrics(graph: nx.DiGraph) -> tuple[dict[int, dict], int]:
    """
    Calcule les métriques de co-forwarding par canal.

    Retourne (metrics, coforward_pair_count) où :
      - metrics[channel_id] = {jaccard_max, jaccard_mean, coforward_partners,
                               shared_origins, origins_relayed}
      - coforward_pair_count = nb de paires de canaux partageant >= 1 origine
        (chaque origine partagée comptant au-delà du seuil MIN_SHARERS).
    """
    if graph.number_of_nodes() == 0:
        return {}, 0

    origins = _origins_by_channel(graph)

    # Filtre des origines : ne garder, par canal, que les origines effectivement
    # co-relayées (partagées par >= MIN_SHARERS relayeurs distincts).
    sharer_count = Counter(o for origs in origins.values() for o in origs)
    shared_origins_universe = {o for o, c in sharer_count.items() if c >= MIN_SHARERS}

    filtered: dict[int, set[int]] = {
        r: (origs & shared_origins_universe) for r, origs in origins.items()
    }

    metrics: dict[int, dict] = {
        n: {
            "jaccard_max": 0.0,
            "jaccard_sum": 0.0,
            "coforward_partners": 0,
            "shared_origins": 0,
            "origins_relayed": len(origins.get(n, set())),
        }
        for n in graph.nodes
    }

    coforward_pairs = 0
    # Paires de canaux qui relaient des origines (Jaccard sur ensembles filtrés).
    channels_with_shared = [r for r, s in filtered.items() if s]
    for r1, r2 in combinations(channels_with_shared, 2):
        s1, s2 = filtered[r1], filtered[r2]
        shared = s1 & s2
        if not shared:
            continue
        coforward_pairs += 1
        j = _jaccard(s1, s2)
        for r in (r1, r2):
            m = metrics[r]
            m["coforward_partners"] += 1
            m["jaccard_sum"] += j
            m["shared_origins"] = max(m["shared_origins"], len(shared))
            if j > m["jaccard_max"]:
                m["jaccard_max"] = j

    for n, m in metrics.items():
        partners = m["coforward_partners"]
        m["jaccard_mean"] = (m["jaccard_sum"] / partners) if partners else 0.0
        del m["jaccard_sum"]

    return metrics, coforward_pairs


def score_coordination(graph: nx.DiGraph) -> dict[int, ScoreResult]:
    """
    Calcule la famille (c) « coordination » pour tous les canaux du graphe.

    `value` ∈ [0,1] combine la force du lien co-forwardant le plus fort
    (jaccard_max) et l'étendue du voisinage co-forwardant (nb de pairs,
    normalisé par le max observé).
    """
    metrics, coforward_pairs = compute_coordination_metrics(graph)
    if not metrics:
        return {}

    max_partners = max((m["coforward_partners"] for m in metrics.values()), default=0)

    results: dict[int, ScoreResult] = {}
    for channel_id, m in metrics.items():
        strength = m["jaccard_max"]  # déjà dans [0,1]
        breadth = (m["coforward_partners"] / max_partners) if max_partners > 0 else 0.0
        value = W_STRENGTH * strength + W_BREADTH * breadth

        results[channel_id] = ScoreResult(
            family="coordination",
            value=round(value, 6),
            confidence_low=round(max(0.0, value - 0.15), 6),
            confidence_high=round(min(1.0, value + 0.15), 6),
            triggered=value >= TRIGGER_THRESHOLD,
            evidence={
                "jaccard_max": round(m["jaccard_max"], 6),
                "jaccard_mean": round(m["jaccard_mean"], 6),
                "coforward_partners": m["coforward_partners"],
                "shared_origins": m["shared_origins"],
                "origins_relayed": m["origins_relayed"],
                "coforward_pair_count_graph": coforward_pairs,
                "method": (
                    "Co-forwarding structurel (Jaccard des canaux-origine "
                    "partagés). D3lta texte différé en PoC "
                    "(docs/method/03-suspicion-score.md §3.3)."
                ),
            },
        )
    return results


# --------------------------------------------------------------------------- #
# Variante (c) FONDÉE SUR LES ARÊTES DE COORDINATION MATÉRIALISÉES.            #
#                                                                             #
# ``score_coordination`` ci-dessus reconstruit la coordination À PARTIR DU    #
# graphe de forward (Jaccard des origines). ``score_coordination_edges``      #
# ci-dessous lit au contraire les arêtes de coordination DÉJÀ MATÉRIALISÉES   #
# dans le graphe multiplex (CO_FORWARD / CO_URL / … — COORDINATION_EDGE_TYPES #
# du loader), chacune portant son Δt observé (``window_delta_seconds``).      #
#                                                                             #
# Règle des ≥2 types de coordination distincts (graph-model §2.3.3) : la      #
# coordination est RENFORCÉE (confiance plus haute, éligible au verrou        #
# multi-source) quand un canal participe à >= 2 types de coordination         #
# distincts. Un seul type isolé reste un signal faible.                       #
#                                                                             #
# Les arêtes de coordination sont NON ORIENTÉES (canonicalisées a<b dans      #
# edges.py) : on attribue donc la participation aux DEUX extrémités canal.    #
# --------------------------------------------------------------------------- #

# Poids de combinaison (variante par arêtes) : force du lien Δt-pondéré +
# diversité des types de coordination (le renfort multi-type est le signal clé).
W_EDGE_TIGHTNESS = 0.5
W_EDGE_DIVERSITY = 0.5

# Seuil de types de coordination distincts pour « renfort » (graph-model §2.3.3).
MIN_DISTINCT_COORD_TYPES = 2


def _tightness_from_delta(delta_seconds: int | None, window_seconds: int) -> float:
    """Resserrement temporel d'une arête de coordination dans [0,1].

    Δt = 0 (quasi-simultané) -> 1.0 ; Δt >= fenêtre -> 0.0. Linéaire entre les
    deux. Un Δt absent (ne devrait pas arriver : rule 2 d'edges.py) -> 0.0.
    """
    if delta_seconds is None or window_seconds <= 0:
        return 0.0
    d = max(0, int(delta_seconds))
    if d >= window_seconds:
        return 0.0
    return 1.0 - (d / window_seconds)


def score_coordination_edges(
    multi: nx.MultiDiGraph,
    *,
    window_delta_seconds: int = 72 * 3600,
    coordination_edge_types: frozenset[str] = COORDINATION_EDGE_TYPES,
) -> dict[int, ScoreResult]:
    """Famille (c) calculée sur les arêtes de coordination MATÉRIALISÉES.

    Fonction PURE et ADDITIVE : ne modifie ni ``score_coordination`` ni ses
    tests. Lit les arêtes des types ``coordination_edge_types`` présentes dans
    le ``MultiDiGraph`` multiplex (clés d'arête = ``edge_type``), fenêtrées par
    ``window_delta_seconds`` (les arêtes au-delà de la fenêtre sont ignorées —
    cohérent avec le fenêtrage d'edges.py).

    Pour chaque canal on agrège :
      - ``coord_types``        : ensemble des types de coordination distincts
                                 auxquels il participe (CO_FORWARD, CO_URL, …) ;
      - ``per_type``           : {type: {pairs, count, min_dt, max_dt}} ;
      - ``tightness_max``      : meilleur resserrement Δt observé ([0,1]) ;
      - ``partners``           : nb de canaux co-coordonnés distincts.

    ``value`` ∈ [0,1] = W_EDGE_TIGHTNESS * tightness_max
                       + W_EDGE_DIVERSITY * diversité_types
    où diversité_types = min(len(coord_types), 2) / 2 (le renfort multi-type
    sature à 2 types — graph-model §2.3.3).

    ``triggered`` ne passe à True que si le canal franchit le seuil ET respecte
    la règle des ≥2 types distincts (gate-eligible). Un seul type isolé peut
    avoir un ``value`` non nul mais reste sous le seuil de déclenchement.
    """
    allowed = frozenset(coordination_edge_types)

    # Agrégat par canal.
    agg: dict[int, dict] = {}

    def _bucket(cid: int) -> dict:
        return agg.setdefault(
            cid,
            {
                "coord_types": set(),
                "per_type": {},
                "tightness_max": 0.0,
                "partners": set(),
            },
        )

    for u, v, key, data in multi.edges(keys=True, data=True):
        etype = data.get("edge_type", key)
        if etype not in allowed:
            continue
        # Une arête de coordination relie deux CANAUX (jamais un domaine).
        if multi.nodes.get(u, {}).get("kind") == "domain":
            continue
        if multi.nodes.get(v, {}).get("kind") == "domain":
            continue
        dt = data.get("window_delta_seconds")
        if dt is None:
            # edges.py garantit un Δt non-NULL (rule 2). Une arête de coordination
            # sans Δt n'a AUCUNE preuve temporelle probante : elle ne doit pas
            # alimenter le verrou >= 2 types. On l'ignore (défensif).
            continue
        if dt > window_delta_seconds:
            continue  # hors fenêtre Δt -> pas de valeur probante
        tight = _tightness_from_delta(dt, window_delta_seconds)
        cnt = int(data.get("count") or 1)

        for a, b in ((u, v), (v, u)):
            bk = _bucket(a)
            bk["coord_types"].add(etype)
            bk["partners"].add(b)
            if tight > bk["tightness_max"]:
                bk["tightness_max"] = tight
            pt = bk["per_type"].setdefault(
                etype,
                {"pairs": 0, "count": 0, "min_dt": None, "max_dt": None},
            )
            pt["pairs"] += 1
            pt["count"] += cnt
            if dt is not None:
                pt["min_dt"] = dt if pt["min_dt"] is None else min(pt["min_dt"], dt)
                pt["max_dt"] = dt if pt["max_dt"] is None else max(pt["max_dt"], dt)

    results: dict[int, ScoreResult] = {}
    for cid, bk in agg.items():
        n_types = len(bk["coord_types"])
        diversity = min(n_types, MIN_DISTINCT_COORD_TYPES) / MIN_DISTINCT_COORD_TYPES
        value = W_EDGE_TIGHTNESS * bk["tightness_max"] + W_EDGE_DIVERSITY * diversity
        value = max(0.0, min(1.0, value))
        reinforced = n_types >= MIN_DISTINCT_COORD_TYPES

        # Déclenchement : seuil de valeur ET renfort multi-type (gate-eligible).
        triggered = value >= TRIGGER_THRESHOLD and reinforced

        # Confiance resserrée si renfort multi-type (graph-model §2.3.3).
        band = 0.1 if reinforced else 0.2

        per_type_ev = {
            t: {
                "pairs": d["pairs"],
                "count": d["count"],
                "min_dt_seconds": d["min_dt"],
                "max_dt_seconds": d["max_dt"],
            }
            for t, d in sorted(bk["per_type"].items())
        }

        results[cid] = ScoreResult(
            family="coordination",
            value=round(value, 6),
            confidence_low=round(max(0.0, value - band), 6),
            confidence_high=round(min(1.0, value + band), 6),
            triggered=triggered,
            evidence={
                "source": "materialized_edges",
                "coordination_types": sorted(bk["coord_types"]),
                "distinct_type_count": n_types,
                "multi_type_reinforced": reinforced,
                "tightness_max": round(bk["tightness_max"], 6),
                "coforward_partners": len(bk["partners"]),
                "per_type": per_type_ev,
                "window_delta_seconds": window_delta_seconds,
                "method": (
                    "Coordination depuis les arêtes matérialisées du multiplex "
                    "(CO_FORWARD / CO_URL …), fenêtrée Δt. Renfort si >= 2 types "
                    "distincts (graph-model §2.3.3)."
                ),
            },
        )

    # Tous les nœuds CANAL reçoivent un résultat (valeur 0 si aucune arête de
    # coordination), pour un dénominateur de combinaison UNIFORME en aval
    # (channel_suspicion._combine_suspicion). Sinon un canal SANS arête de
    # coordination serait exclu du dénominateur et verrait son score gonflé
    # par rapport à un canal qui a une arête de coordination non déclenchée.
    # Cohérent avec cascade_role/recidivism qui couvrent tous les nœuds reçus.
    for cid, d in multi.nodes(data=True):
        if d.get("kind") == "domain" or cid in results:
            continue
        results[cid] = ScoreResult(
            family="coordination",
            value=0.0,
            confidence_low=0.0,
            confidence_high=0.0,
            triggered=False,
            evidence={
                "source": "materialized_edges",
                "coordination_types": [],
                "distinct_type_count": 0,
                "multi_type_reinforced": False,
                "tightness_max": 0.0,
                "coforward_partners": 0,
                "per_type": {},
                "window_delta_seconds": window_delta_seconds,
                "method": (
                    "Aucune arête de coordination matérialisée pour ce canal "
                    "(valeur 0, présente pour un dénominateur de combinaison uniforme)."
                ),
            },
        )
    return results
