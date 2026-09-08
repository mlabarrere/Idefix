"""Embedding-aware community helpers — pure, numpy-only, unit-testable.

Used by ``scripts/analyze_communities_embed.py`` to (a) pull semantically similar
channels together before Leiden, and (b) quantify HOW MUCH more coherent the
resulting groups are — the factual numbers shown by the galaxy's
Analytics↔Embedding toggle (no hand-wavy "it's better").

References (cf. docs/references.md):
  - Leiden community detection: Traag, Waltman & van Eck (2019), Sci. Rep. 9:5233.
  - Modularity (community quality on the link graph): Newman & Girvan (2004);
    Newman (2006), PNAS 103(23).
  - Silhouette (cluster cohesion/separation): Rousseeuw (1987), J. Comput. Appl. Math.
  - Partition agreement NMI / ARI: Danon et al. (2005); Hubert & Arabie (1985).
  - Sentence embeddings: Reimers & Gurevych (2019, SBERT); model MiniLM, Wang et al. (2020).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

import numpy as np


def intra_cohesion(membership: Mapping, chan_emb: Mapping[int, np.ndarray]) -> float:
    """Mean intra-community cosine over channel pairs (L2-normalized vectors).

    A higher value means tighter, more thematically coherent groups. Only int
    channel nodes that have an embedding are considered.
    """
    groups: dict[int, list[np.ndarray]] = defaultdict(list)
    for node, c in membership.items():
        if isinstance(node, int) and node in chan_emb:
            groups[c].append(chan_emb[node])
    sims: list[float] = []
    for vecs in groups.values():
        if len(vecs) < 2:
            continue
        m = np.vstack(vecs)
        s = m @ m.T
        iu = np.triu_indices(len(vecs), k=1)
        sims.extend(s[iu].tolist())
    return round(float(np.mean(sims)), 4) if sims else 0.0


def add_embedding_edges(
    g,
    chan_emb: Mapping[int, np.ndarray],
    *,
    k: int = 5,
    threshold: float = 0.5,
    weight_scale: float = 3.0,
):
    """Return a COPY of ``g`` with top-k nearest-neighbour embedding edges added.

    These in-memory ``EMB_SIM`` edges (never persisted) give Leiden a continuous
    semantic signal so it forms thematically coherent communities even where the
    structural graph is sparse. Edge weight = ``weight_scale * cosine`` so
    ``to_igraph``/``_edge_weight`` picks them up. Each unordered pair is added once.
    """
    g2 = g.copy()
    ids = [c for c in chan_emb if c in g2.nodes]
    if len(ids) < 2:
        return g2
    m = np.vstack([np.asarray(chan_emb[c], dtype=np.float32) for c in ids])
    sim = m @ m.T
    np.fill_diagonal(sim, -1.0)

    seen: set[tuple[int, int]] = set()
    for i, ci in enumerate(ids):
        row = sim[i]
        for j in np.argsort(-row)[:k].tolist():
            s = float(row[j])
            if s < threshold:
                break
            cj = ids[j]
            a, b = (ci, cj) if ci < cj else (cj, ci)
            if a == b or (a, b) in seen:
                continue
            seen.add((a, b))
            w = round(s * weight_scale, 3)
            g2.add_edge(a, b, key="EMB_SIM", edge_type="EMB_SIM",
                        family="coordination", count=w, weight=w)
    return g2


def _kept_count(membership: Mapping, min_size: int = 2) -> int:
    """Communautés CONSERVÉES (≥ min_size canaux int) — cohérent avec le snapshot.

    L'ancien comptage prenait TOUTES les communautés (singletons inclus), d'où
    l'incohérence 512 vs 27 entre comparison et le snapshot. On expose le compte
    conservé (par défaut) et le compte brut séparément.
    """
    sizes: dict = defaultdict(int)
    for n, c in membership.items():
        if isinstance(n, int):
            sizes[c] += 1
    return sum(1 for s in sizes.values() if s >= min_size)


def _silhouette(membership: Mapping, chan_emb: Mapping[int, np.ndarray]) -> float | None:
    """Silhouette (cosine) de la partition sur les embeddings [Rousseeuw, 1987].

    None si indisponible (sklearn absent, <2 clusters, ou <3 points)."""
    try:
        from sklearn.metrics import silhouette_score
    except Exception:
        return None
    nodes = [n for n in membership if isinstance(n, int) and n in chan_emb]
    if len(nodes) < 3:
        return None
    labels = [membership[n] for n in nodes]
    if len(set(labels)) < 2 or len(set(labels)) >= len(nodes):
        return None
    X = np.vstack([np.asarray(chan_emb[n], dtype=np.float32) for n in nodes])  # noqa: N806  # matrice de features (convention ML)
    try:
        return round(float(silhouette_score(X, labels, metric="cosine")), 4)
    except Exception:
        return None


def _partition_agreement(comm_a: Mapping, comm_b: Mapping) -> dict:
    """NMI [Danon, 2005] + ARI [Hubert & Arabie, 1985] entre les deux partitions.

    Mesure à quel point l'embedding RÉORGANISE la galaxie (1 = partitions identiques,
    ~0 = sans rapport). Calculé sur les canaux int présents dans les deux."""
    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    except Exception:
        return {"nmi": None, "ari": None}
    common = [n for n in comm_a if isinstance(n, int) and n in comm_b]
    if len(common) < 2:
        return {"nmi": None, "ari": None}
    la = [comm_a[n] for n in common]
    lb = [comm_b[n] for n in common]
    return {
        "nmi": round(float(normalized_mutual_info_score(la, lb)), 4),
        "ari": round(float(adjusted_rand_score(la, lb)), 4),
        "n_common": len(common),
    }


def comparison_block(
    chan_emb: Mapping[int, np.ndarray],
    comm_analytics: Mapping,
    comm_embedding: Mapping,
    modularity_analytics: float,
    modularity_embedding: float,
    n_bridges: int,
) -> dict:
    """Deltas factuels Analytics vs LLM-Embedding pour le callout galaxie.

    Métriques (cf. docs/references.md) :
      - intra_cohesion : cosinus moyen intra-communauté (cohésion sémantique).
      - silhouette : Rousseeuw (1987), cohésion/séparation des clusters.
      - modularity : Newman (2006), qualité de partition sur le GRAPHE DE LIENS.
      - partition_agreement : NMI [Danon 2005] / ARI [Hubert & Arabie 1985].
      - n_communities : communautés CONSERVÉES (≥2 canaux) ; *_raw = brut (singletons inclus).

    TRADE-OFF (load-bearing) : l'embedding AUGMENTE la cohésion intra (les arêtes
    EMB_SIM rapprochent les canaux qui « parlent pareil ») mais BAISSE la modularité,
    car ces arêtes TRAVERSENT les communautés structurelles (déf. Newman, basée sur
    les liens observés). Ce n'est PAS une régression : deux objectifs distincts —
    structure de diffusion (modularité) vs sémantique de contenu (cohésion).
    """
    coh_a = intra_cohesion(comm_analytics, chan_emb)
    coh_e = intra_cohesion(comm_embedding, chan_emb)
    gain = round((coh_e - coh_a) / coh_a * 100, 1) if coh_a > 0 else None
    return {
        "intra_cohesion": {"analytics": coh_a, "embedding": coh_e, "gain_pct": gain},
        "silhouette": {"analytics": _silhouette(comm_analytics, chan_emb),
                       "embedding": _silhouette(comm_embedding, chan_emb)},
        "modularity": {"analytics": round(float(modularity_analytics), 4),
                       "embedding": round(float(modularity_embedding), 4)},
        "n_communities": {"analytics": _kept_count(comm_analytics),
                          "embedding": _kept_count(comm_embedding)},
        "n_communities_raw": {
            "analytics": len({c for n, c in comm_analytics.items() if isinstance(n, int)}),
            "embedding": len({c for n, c in comm_embedding.items() if isinstance(n, int)}),
        },
        "partition_agreement": _partition_agreement(comm_analytics, comm_embedding),
        "n_bridges": n_bridges,
        "metric_note": (
            "intra_cohesion = cosinus moyen intra-communauté (embeddings locaux), plus haut "
            "= groupes plus cohérents. silhouette (Rousseeuw 1987) = cohésion/séparation. "
            "modularité (Newman 2006) sur le graphe de LIENS. n_communities = communautés "
            "conservées (≥2 canaux). TRADE-OFF : l'embedding monte la cohésion sémantique mais "
            "baisse la modularité (les arêtes sémantiques traversent les communautés "
            "structurelles) — deux objectifs distincts, pas une régression."
        ),
    }


def demo() -> None:
    """Self-check : bornes des métriques sur vecteurs synthétiques (assert-based)."""
    rng = np.random.default_rng(0)
    # 2 groupes nets de 6 canaux en 8D, L2-normalisés.
    emb = {}
    for i in range(6):
        v = np.r_[rng.normal(2, 0.05, 4), rng.normal(0, 0.05, 4)].astype(np.float32)
        emb[i] = v / np.linalg.norm(v)
    for i in range(6, 12):
        v = np.r_[rng.normal(0, 0.05, 4), rng.normal(2, 0.05, 4)].astype(np.float32)
        emb[i] = v / np.linalg.norm(v)
    part_a = {i: (0 if i < 6 else 1) for i in range(12)}          # partition correcte
    part_b = {i: (i % 2) for i in range(12)}                       # partition aléatoire
    cb = comparison_block(emb, part_a, part_b, 0.7, 0.4, 3)
    assert 0.0 <= cb["intra_cohesion"]["analytics"] <= 1.0
    sil = cb["silhouette"]["analytics"]
    assert sil is None or -1.0 <= sil <= 1.0
    pa = cb["partition_agreement"]
    if pa["nmi"] is not None:
        assert 0.0 <= pa["nmi"] <= 1.0 and -0.5 <= pa["ari"] <= 1.0
        # part_a (vraie) doit être plus cohérente que part_b (aléatoire).
        assert cb["intra_cohesion"]["analytics"] >= cb["intra_cohesion"]["embedding"]
    assert cb["n_communities"]["analytics"] == 2
    _keys = ("intra_cohesion", "silhouette", "partition_agreement")
    print("community.demo OK:", {k: cb[k] for k in _keys})


if __name__ == "__main__":
    demo()
