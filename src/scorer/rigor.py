"""Orchestration du scoring RIGOUREUX : significativité par famille + combinaison.

Transforme les ScoreResult observés des familles structurelles en scores
SCIENTIFIQUEMENT FONDÉS :

- **(b) cascade_role** et **(d) recidivism** : modèle nul à endpoints randomisés
  sur le graphe de forward (ensemble partagé, calculé UNE fois), p-value empirique
  + IC bootstrap (ré-échantillonnage des arêtes de forward).
- **(c) coordination** : référence de POPULATION (p = part des canaux dont la
  coordination observée ≥ la sienne, add-one) — v1 transparente, marquée pour
  passage à un nul à degré préservé sur le graphe de coordination (itération
  suivante). Pas de modèle nul structurel ⇒ pas d'IC bootstrap (CI = point).

La VALEUR de chaque famille devient ``1 - p`` (significativité), les bornes de
confiance deviennent l'IC bootstrap mappé en significativité, et ``triggered``
devient ``p < alpha``. La combinaison (Stouffer pondéré) et la correction FDR
sont appliquées par ``channel_suspicion`` à partir des p renvoyées ici.

Déterminisme : un seul ``rng`` (seedé) ⇒ sortie reproductible.

References (cf. docs/reference/references.md):
  - Modèle nul + IC bootstrap : Efron (1979), Ann. Statist. 7(1).
  - Significativité (p empirique, FDR, Stouffer) : voir src/scorer/significance.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from src.scorer import significance as sig


@dataclass
class FamilySignificance:
    """Résultat de significativité d'une famille pour un canal."""

    value: float          # 1 - p (significativité ∈ [0,1])
    ci_low: float         # borne IC en significativité
    ci_high: float
    p: float              # p-value unilatérale
    triggered: bool       # p < alpha
    evidence: dict        # observed/null_mean/null_std/z/p/percentile/ci/method


def _bridge_raw_all(graph: nx.DiGraph) -> dict:
    """Statistique cascade = Bridge Score brut par nœud (réutilise compute_bridge_scores)."""
    from src.scorer.cascade_role import compute_bridge_scores

    return {n: m["bridge_raw"] for n, m in compute_bridge_scores(graph).items()}


def _out_strength_all(graph: nx.DiGraph) -> dict:
    """Statistique récidive = forward-influence (somme des poids sortants) par nœud."""
    return {n: float(w) for n, w in graph.out_degree(weight="count")}


def _digraph_from_edges(edges: list[tuple]) -> nx.DiGraph:
    g = nx.DiGraph()
    for u, v, w in edges:
        if g.has_edge(u, v):
            g[u][v]["count"] += w
        else:
            g.add_edge(u, v, count=w)
    return g


def _forward_edge_list(fwd: nx.DiGraph) -> list[tuple]:
    return [(u, v, float(d.get("count", 1) or 1)) for u, v, d in fwd.edges(data=True)]


def _na_significance(reason: str) -> FamilySignificance:
    """Famille non applicable (p=1 ⇒ exclue de la combinaison, jamais déclenchée)."""
    return FamilySignificance(
        value=0.0, ci_low=0.0, ci_high=0.0, p=1.0, triggered=False,
        evidence={"p": 1.0, "null_method": "n/a", "note": reason},
    )


def _family_from_obs(
    observed: float, null_samples: np.ndarray, ci_stat: tuple[float, float],
    *, alpha: float, method: str, extra_ev: dict | None = None,
) -> FamilySignificance:
    s = sig.null_significance(observed, null_samples)
    value = max(0.0, min(1.0, 1.0 - s["p_one_sided"]))
    # IC (espace statistique) mappé en significativité via la même distribution nulle.
    lo = sig.significance_from_value(ci_stat[0], null_samples)
    hi = sig.significance_from_value(ci_stat[1], null_samples)
    lo, hi = min(lo, hi), max(lo, hi)
    lo = min(lo, value)
    hi = max(hi, value)
    degenerate = s["n_null"] <= 1
    ev = {
        "observed": round(float(observed), 6),
        "null_mean": s["null_mean"], "null_std": s["null_std"],
        "z": s["z"], "p": s["p_one_sided"], "percentile": s["percentile"],
        "ci_low": round(lo, 6), "ci_high": round(hi, 6),
        "n_null": s["n_null"], "null_method": method,
        "null_degenerate": degenerate,
    }
    if extra_ev:
        ev.update(extra_ev)
    return FamilySignificance(
        value=round(value, 6), ci_low=round(lo, 6), ci_high=round(hi, 6),
        p=s["p_one_sided"], triggered=(s["p_one_sided"] < alpha and not degenerate),
        evidence=ev,
    )


def compute_family_significance(
    fwd: nx.DiGraph,
    cascade: dict,
    recidivism: dict,
    *,
    alpha: float,
    n_null: int,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> dict[str, dict[int, FamilySignificance]]:
    """Significativité rigoureuse des familles STRUCTURELLES (b)/(d) du forward.

    Renvoie ``{"b": {cid: FamilySignificance}, "d": {cid: FamilySignificance}}``.

    La coordination (c) n'est PAS traitée ici : sa valeur est déjà un composite
    principiel (resserrement Δt + diversité de types, règle ≥2 types) — on la
    laisse telle quelle et elle contribue à la combinaison de Stouffer via le
    repli ``p = 1 - value`` (un nul à degré préservé sur le graphe de
    coordination est une itération ultérieure).
    """
    nodes = list(fwd.nodes())
    # --- Ensemble nul PARTAGÉ (b + d) : ENDPOINTS RANDOMISÉS ------------------
    # Compare chaque canal à un canal ALÉATOIRE dans un réseau de même
    # taille/densité/poids. Robuste aux étoiles de forward Telegram (depth-1) où
    # le rewiring à degré préservé est dégénéré.
    ensemble = sig.build_random_endpoint_ensemble(fwd, n_null=n_null, rng=rng)
    null_b = sig.null_from_ensemble(fwd, ensemble, _bridge_raw_all)
    null_d = sig.null_from_ensemble(fwd, ensemble, _out_strength_all)

    # --- Bootstrap des arêtes de forward (b + d), tous nœuds en une passe ----
    edges = _forward_edge_list(fwd)
    boot_b = sig.bootstrap_all_nodes(
        edges, lambda e: _bridge_raw_all(_digraph_from_edges(e)), nodes,
        n_bootstrap=n_bootstrap, rng=rng, alpha=alpha,
    )
    boot_d = sig.bootstrap_all_nodes(
        edges, lambda e: _out_strength_all(_digraph_from_edges(e)), nodes,
        n_bootstrap=n_bootstrap, rng=rng, alpha=alpha,
    )

    out_b: dict[int, FamilySignificance] = {}
    out_d: dict[int, FamilySignificance] = {}
    for cid in nodes:
        # Nœud ISOLÉ (aucune arête de forward) : aucun rôle structurel testable.
        # Le floor de eigenvector_centrality_numpy donnerait sinon une p ~0.5
        # fallacieuse → on force la NON-APPLICABILITÉ (p=1, exclu de la combinaison).
        if fwd.in_degree(cid) == 0 and fwd.out_degree(cid) == 0:
            out_b[cid] = _na_significance("isolé (aucune arête de forward)")
            out_d[cid] = _na_significance("isolé (aucune arête de forward)")
            continue
        obs_b = float(cascade[cid].evidence.get("bridge_raw", 0.0)) if cid in cascade else 0.0
        out_b[cid] = _family_from_obs(
            obs_b, null_b.get(cid, np.zeros(1)), boot_b.get(cid, (obs_b, obs_b)),
            alpha=alpha, method="randomized_endpoints(forward,bridge_raw)",
        )
        obs_d = (
            float(recidivism[cid].evidence.get("forward_influence", 0.0))
            if cid in recidivism else 0.0
        )
        out_d[cid] = _family_from_obs(
            obs_d, null_d.get(cid, np.zeros(1)), boot_d.get(cid, (obs_d, obs_d)),
            alpha=alpha, method="randomized_endpoints(forward,out_strength)",
        )

    return {"b": out_b, "d": out_d}
