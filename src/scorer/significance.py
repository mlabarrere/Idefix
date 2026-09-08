"""Socle statistique du scoring rigoureux — modèle nul, significativité, bootstrap.

Module PUR (networkx + numpy + scipy + statsmodels ; ni DB ni Telegram), pensé
pour rendre le score de suspicion par canal SCIENTIFIQUEMENT FONDÉ plutôt
qu'heuristique :

- **Modèle nul à endpoints randomisés** : on compare la statistique observée d'un
  canal (Bridge Score, forward-influence) à sa distribution sous des réseaux
  ALÉATOIRES de même taille/densité/poids (``randomize_endpoints``). Répond à
  « ce canal gagne-t-il plus de forwards qu'un canal quelconque ? » — robuste aux
  topologies en étoile (forward Telegram depth-1) où le rewiring à degré préservé
  est dégénéré.
- **Significativité** : z-score + p-value empirique unilatérale **add-one**
  ``(1+#{null≥obs})/(n+1)`` (jamais 0 ⇒ pas de sur-affirmation).
- **Bootstrap** : vrais intervalles de confiance par ré-échantillonnage des arêtes,
  en remplacement des bandes ±0.15 factices.
- **Combinaison de Stouffer pondérée** des p-values par-famille + FDR (BH).

DÉTERMINISME / EIP : toute fonction stochastique prend un ``numpy.random.Generator``
explicite (jamais le RNG global) ⇒ sortie reproductible pour un ``rng_seed`` donné.

References (cf. docs/references.md):
  - Bootstrap (IC par ré-échantillonnage) : Efron (1979), Ann. Statist. 7(1).
  - Tests de permutation / nul empirique : Good (2000), Permutation Tests.
  - Combinaison de p-values : Stouffer et al. (1949), The American Soldier.
  - Correction multiple FDR : Benjamini & Hochberg (1995), JRSS B 57(1).
"""
from __future__ import annotations

from typing import Callable, Hashable, Sequence

import networkx as nx
import numpy as np
from scipy import stats


def make_rng(seed: int) -> np.random.Generator:
    """Générateur numpy seedé (déterminisme : jamais le RNG global)."""
    return np.random.default_rng(seed)


def randomize_endpoints(
    graph: nx.DiGraph, rng: np.random.Generator, *, weight: str = "count"
) -> nx.DiGraph:
    """Graphe NUL : mêmes nœuds, même nombre d'arêtes et même multiset de poids,
    mais endpoints (origine, cible) RÉAFFECTÉS aléatoirement sur tout l'ensemble
    des nœuds (poids permutés). Compare un canal à « un canal ALÉATOIRE » dans un
    réseau de même taille/densité/poids — le bon nul pour « ce canal gagne-t-il
    plus de forwards qu'un canal quelconque ? », robuste aux étoiles.
    """
    nodes = list(graph.nodes())
    es = list(graph.edges(data=True))
    m = len(es)
    H = nx.DiGraph()  # noqa: N806
    H.add_nodes_from(nodes)
    if m == 0 or len(nodes) < 2:
        return H
    weights = np.array([float(d.get(weight, 1.0) or 1.0) for _, _, d in es], dtype=float)
    weights = rng.permutation(weights)
    n = len(nodes)
    for k in range(m):
        u = nodes[int(rng.integers(n))]
        v = nodes[int(rng.integers(n))]
        tries = 0
        while v == u and tries < 8:
            v = nodes[int(rng.integers(n))]
            tries += 1
        if v == u:
            continue
        w = float(weights[k])
        if H.has_edge(u, v):
            H[u][v][weight] += w
        else:
            H.add_edge(u, v, **{weight: w})
    return H


def build_random_endpoint_ensemble(
    graph: nx.DiGraph, *, n_null: int, rng: np.random.Generator, weight: str = "count"
) -> list[nx.DiGraph] | None:
    """Ensemble de N graphes nuls à endpoints randomisés (partagé entre familles).

    ``None`` si trop peu d'arêtes/nœuds pour un nul informatif (⇒ p≈1).
    """
    if n_null <= 0 or graph.number_of_edges() < 2 or graph.number_of_nodes() < 3:
        return None
    return [randomize_endpoints(graph, rng, weight=weight) for _ in range(n_null)]


def null_from_ensemble(
    graph: nx.DiGraph,
    ensemble: list[nx.DiGraph] | None,
    statistic: Callable[[nx.DiGraph], dict[Hashable, float]],
) -> dict[Hashable, np.ndarray]:
    """Distribution nulle par-nœud d'une statistique sur un ensemble PRÉ-CALCULÉ.

    ``ensemble=None`` (dégénéré) ⇒ null = statistique observée (longueur 1) ⇒ p≈1.
    """
    nodes = list(graph.nodes())
    if ensemble is None:
        obs = statistic(graph)
        return {n: np.full(1, float(obs.get(n, 0.0)), dtype=float) for n in nodes}
    samples: dict[Hashable, np.ndarray] = {n: np.zeros(len(ensemble), dtype=float) for n in nodes}
    for i, H in enumerate(ensemble):  # noqa: N806
        st = statistic(H)
        for n in nodes:
            samples[n][i] = float(st.get(n, 0.0))
    return samples


def bootstrap_all_nodes(
    edges: Sequence[tuple],
    statistic_all: Callable[[Sequence[tuple]], dict[Hashable, float]],
    nodes: Sequence[Hashable],
    *,
    n_bootstrap: int,
    rng: np.random.Generator,
    alpha: float = 0.05,
) -> dict[Hashable, tuple[float, float]]:
    """IC bootstrap percentile par-nœud, en ré-échantillonnant les ARÊTES une fois
    par tirage et en recalculant la statistique pour TOUS les nœuds (coût =
    B × un calcul). Renvoie ``{node: (ci_low, ci_high)}`` dans l'espace de la
    statistique. ≤1 arête ou n_bootstrap<=0 ⇒ CI = point (statistique observée)."""
    e = list(edges)
    m = len(e)
    if m <= 1 or n_bootstrap <= 0:
        obs = statistic_all(e)
        return {n: (float(obs.get(n, 0.0)), float(obs.get(n, 0.0))) for n in nodes}
    cols: dict[Hashable, np.ndarray] = {n: np.zeros(n_bootstrap, dtype=float) for n in nodes}
    for i in range(n_bootstrap):
        idx = rng.integers(0, m, size=m)
        resampled = [e[j] for j in idx]
        st = statistic_all(resampled)
        for n in nodes:
            cols[n][i] = float(st.get(n, 0.0))
    out: dict[Hashable, tuple[float, float]] = {}
    for n in nodes:
        lo = float(np.quantile(cols[n], alpha / 2.0))
        hi = float(np.quantile(cols[n], 1.0 - alpha / 2.0))
        out[n] = (lo, hi)
    return out


def significance_from_value(observed: float, null_samples: np.ndarray) -> float:
    """Convertit une valeur observée en SCORE de significativité ``1 - p`` ∈ [0,1].

    Helper pour mapper les bornes d'IC (espace statistique) vers l'espace
    significativité, en réutilisant la même distribution nulle.
    """
    p = null_significance(observed, null_samples)["p_one_sided"]
    return max(0.0, min(1.0, 1.0 - p))


def null_significance(observed: float, null_samples: np.ndarray) -> dict[str, float]:
    """z-score + p-value empirique unilatérale (upper tail) + percentile.

    p add-one ``(1+#{null≥obs})/(n+1)`` : jamais 0, borne supérieure honnête.
    ``std==0`` ⇒ ``z=0`` (pas de NaN). Distribution vide ⇒ p=1, z=0.
    """
    arr = np.asarray(null_samples, dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"z": 0.0, "p_one_sided": 1.0, "percentile": 0.0,
                "null_mean": 0.0, "null_std": 0.0, "n_null": 0}
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    z = (observed - mean) / std if std > 0 else 0.0
    p = (1 + int(np.count_nonzero(arr >= observed))) / (n + 1)
    percentile = float(np.count_nonzero(arr <= observed) / n)
    return {
        "z": round(z, 6),
        "p_one_sided": round(p, 6),
        "percentile": round(percentile, 6),
        "null_mean": round(mean, 6),
        "null_std": round(std, 6),
        "n_null": n,
    }


def stouffer_combine(
    pvalues: Sequence[float], weights: Sequence[float]
) -> tuple[float, float]:
    """Combinaison de Stouffer pondérée (unilatérale) → ``(Z_combined, p_combined)``.

    ``z_i = norm.isf(p_i)`` ; ``Z = Σ(w_i·z_i)/sqrt(Σ w_i²)`` ; ``p = norm.sf(Z)``.
    p clampées dans (0,1) pour éviter ±inf. Listes vides / poids nuls ⇒ (0, 1).
    """
    p = np.clip(np.asarray(pvalues, dtype=float), 1e-12, 1.0 - 1e-12)
    w = np.asarray(weights, dtype=float)
    if p.size == 0 or float(np.sum(w * w)) <= 0.0:
        return 0.0, 1.0
    z = stats.norm.isf(p)
    Z = float(np.sum(w * z) / np.sqrt(np.sum(w * w)))  # noqa: N806
    return round(Z, 6), round(float(stats.norm.sf(Z)), 6)


def benjamini_hochberg(
    pvalues: Sequence[float], alpha: float = 0.05
) -> tuple[list[bool], list[float]]:
    """Correction FDR Benjamini-Hochberg sur un ENSEMBLE de canaux.

    Renvoie ``(rejected, qvalues)`` (mêmes longueurs que ``pvalues``). Liste vide
    ⇒ ([], []). Délègue à ``statsmodels.stats.multitest.multipletests``.
    """
    p = list(pvalues)
    if not p:
        return [], []
    from statsmodels.stats.multitest import multipletests

    rejected, qvals, _, _ = multipletests(p, alpha=alpha, method="fdr_bh")
    return [bool(x) for x in rejected], [round(float(q), 6) for q in qvals]
