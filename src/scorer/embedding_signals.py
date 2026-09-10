"""Score family (f) — embedding semantic coherence.

Mesure la distance sémantique d'un canal à une baseline organique (médias FR légitimes)
et sa proximité à des canaux adversaires connus (RT, Sputnik, Geopolitika...).

Réutilise Embedder (src/embed/encoder.py) : cache offline, L2-normalisé, lazy import.

Logic:
    - baseline_distance  : cosine vs mean embedding de canaux FR organiques (0 = identique)
    - adversary_proximity: cosine max vs embeddings de canaux à revendication connue
    - score (f)          : weighted sum, normalisé [0,1]
                           high if proche adversaire ET loin baseline

Usage:
    chan_emb = await compute_channel_embeddings(conn, embedder)
    scores = await score_embedding_coherence(conn, chan_emb, baseline_emb, adversary_emb)

ponytail: baseline=100 canaux, étendre à 500 si recall < 0.5 (Phase 3 validation).

References (cf. docs/reference/references.md):
  - Sentence embeddings (SBERT) : Reimers & Gurevych (2019), arXiv:1908.10084.
  - Modèle d'encodeur (MiniLM) : Wang et al. (2020), arXiv:2002.10957.
"""
from __future__ import annotations

import numpy as np

from src.embed.encoder import Embedder, cosine
from src.shared.dossier import ScoreResult

# Poids de la composition (baseline_distance + adversary_proximity)
W_BASELINE_DISTANCE = 0.4
W_ADVERSARY_PROXIMITY = 0.6

# Seuil de déclenchement (sur la valeur normalisée [0,1])
TRIGGER_THRESHOLD = 0.3


async def compute_channel_embeddings(
    conn, embedder: Embedder, sample_size: int = 15
) -> dict[int, np.ndarray]:
    """Mean embedding per channel from longest `sample_size` messages.

    Réutilise la logique de analyze_communities_embed.py::_channel_embeddings.

    Returns:
        {channel_id: np.ndarray (L2-normalized, float32)}
    """
    import heapq
    from collections import defaultdict

    rows = await conn.fetch(
        "SELECT channel_id, text FROM messages "
        "WHERE text IS NOT NULL AND length(text) > 20"
    )

    # Garde les `sample_size` textes les plus longs par canal (mémoire bornée)
    best: dict[int, list] = defaultdict(list)  # channel_id -> min-heap (len, text)
    for row in rows:
        cid, txt = row["channel_id"], row["text"]
        h = best[cid]
        if len(h) < sample_size:
            heapq.heappush(h, (len(txt), txt))
        elif len(txt) > h[0][0]:
            heapq.heapreplace(h, (len(txt), txt))

    # Encode tous les textes (batch par canal pour efficacité)
    chan_emb = {}
    for cid, heap in best.items():
        texts = [txt for _, txt in heap]
        if not texts:
            continue
        vecs = embedder.encode_texts(texts)  # (N, D) float32 L2-normalized
        chan_emb[cid] = vecs.mean(axis=0).astype(np.float32)  # mean embedding
        # Re-normalize (mean peut dériver légèrement)
        norm = float(np.linalg.norm(chan_emb[cid]))
        if norm > 0:
            chan_emb[cid] = (chan_emb[cid] / norm).astype(np.float32)

    return chan_emb


async def build_baseline_embedding(
    conn, embedder: Embedder, baseline_channel_ids: list[int]
) -> np.ndarray:
    """Mean embedding de canaux baseline (médias FR organiques).

    Args:
        baseline_channel_ids: IDs de canaux légitimes (ex. @RFI_fr, @France24_fr)

    Returns:
        np.ndarray (D,) L2-normalized centroïde
    """
    chan_emb = await compute_channel_embeddings(conn, embedder, sample_size=20)
    baseline_vecs = [chan_emb[cid] for cid in baseline_channel_ids if cid in chan_emb]
    if not baseline_vecs:
        # Fallback : vecteur neutre (ne pénalise personne)
        return np.zeros(384, dtype=np.float32)  # 384-dim = paraphrase-multilingual-MiniLM

    mean_vec = np.mean(baseline_vecs, axis=0).astype(np.float32)
    norm = float(np.linalg.norm(mean_vec))
    if norm == 0:
        return mean_vec
    return (mean_vec / norm).astype(np.float32)


async def build_adversary_embeddings(
    conn, embedder: Embedder, adversary_channel_ids: list[int]
) -> dict[int, np.ndarray]:
    """Embeddings de canaux adversaires connus (RT, Sputnik, Geopolitika...).

    Args:
        adversary_channel_ids: IDs de canaux à revendication connue

    Returns:
        {channel_id: np.ndarray (D,) L2-normalized}
    """
    chan_emb = await compute_channel_embeddings(conn, embedder, sample_size=20)
    return {cid: chan_emb[cid] for cid in adversary_channel_ids if cid in chan_emb}


async def score_embedding_coherence(
    conn,
    chan_emb: dict[int, np.ndarray],
    baseline_emb: np.ndarray,
    adversary_emb: dict[int, np.ndarray],
) -> dict[int, ScoreResult]:
    """Famille (f) : distance sémantique à baseline + proximité adversaire.

    Logic:
        baseline_distance   = 1 - cosine(chan, baseline)  # 0=identique, 1=opposé
        adversary_proximity = max(cosine(chan, adv_i))    # 0=loin, 1=identique
        score = W_BASELINE * baseline_distance + W_ADVERSARY * adversary_proximity

    Returns:
        {channel_id: ScoreResult(family="embedding_coherence", value, ...)}

        value : score normalisé [0,1]
        confidence_low/high : intervalle de confiance (±10% par défaut, TODO calibrer)
        evidence : {"baseline_distance": ..., "adversary_proximity": ...,
                    "closest_adversary_id": ...}
    """
    scores = {}

    for cid, vec in chan_emb.items():
        # Distance à baseline (1 - cosine)
        baseline_dist = 1.0 - cosine(vec, baseline_emb)

        # Proximité max à adversaires
        adversary_prox = 0.0
        closest_adv = None
        for adv_id, adv_vec in adversary_emb.items():
            sim = cosine(vec, adv_vec)
            if sim > adversary_prox:
                adversary_prox = sim
                closest_adv = adv_id

        # Combinaison pondérée
        raw = W_BASELINE_DISTANCE * baseline_dist + W_ADVERSARY_PROXIMITY * adversary_prox
        # Normalisation : [0, W_BASELINE + W_ADVERSARY] → [0, 1]
        v = raw / (W_BASELINE_DISTANCE + W_ADVERSARY_PROXIMITY)
        v = max(0.0, min(1.0, v))  # clamp

        # Intervalle de confiance (±10%, ponytail: calibrer avec gold en Phase 3)
        lo = max(0.0, v - 0.1)
        hi = min(1.0, v + 0.1)

        scores[cid] = ScoreResult(
            family="embedding_coherence",
            value=v,
            confidence_low=lo,
            confidence_high=hi,
            triggered=v >= TRIGGER_THRESHOLD,
            evidence={
                "baseline_distance": float(baseline_dist),
                "adversary_proximity": float(adversary_prox),
                "closest_adversary_id": closest_adv,
            },
        )

    return scores
