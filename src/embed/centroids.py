"""Zero-shot nearest-centroid classification over mission lexicons.

A mission lexicon (e.g. ``GAN_LEXICON``) is ``{category: [terms...]}`` mixing
specific ANCHORS with generic CONTEXTUAL terms. For embedding-based classification
we want the ANCHORS only (the unambiguous, mission-specific phrases): contextual
generic words ("porte-avions", "frégate"...) would blur the category centroids.

Pipeline:
  1. :func:`anchor_terms`   — drop contextual terms from each category.
  2. :func:`build_centroids`— embed the anchors, mean per category, L2-normalize.
  3. :func:`classify`       — cosine of a channel vector to each centroid; pick best.

No model is loaded here; an :class:`~src.embed.encoder.Embedder` is passed in, so
this module is unit-testable offline with a fake encoder.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np

from src.embed.encoder import Embedder


def anchor_terms(
    lexicon: Mapping[str, Iterable[str]],
    contextual: Iterable[str] | None = None,
) -> dict[str, list[str]]:
    """Return ``{category: [anchor terms]}`` — lexicon terms minus contextual ones.

    Categories left without any anchor are dropped (a centroid needs ≥1 term).
    """
    ctx = {t.lower() for t in (contextual or ())}
    out: dict[str, list[str]] = {}
    for category, terms in lexicon.items():
        anchors = [t for t in terms if t.lower() not in ctx]
        if anchors:
            out[category] = anchors
    return out


def build_centroids(
    embedder: Embedder,
    lexicon: Mapping[str, Iterable[str]],
    contextual: Iterable[str] | None = None,
) -> dict[str, np.ndarray]:
    """Embed anchor terms per category and return one L2-normalized centroid each."""
    anchors = anchor_terms(lexicon, contextual)
    centroids: dict[str, np.ndarray] = {}
    for category, terms in anchors.items():
        vecs = embedder.encode_texts(terms)
        if vecs.shape[0] == 0:
            continue
        mean = vecs.mean(axis=0)
        norm = float(np.linalg.norm(mean))
        if norm == 0.0:
            continue
        centroids[category] = (mean / norm).astype(np.float32)
    return centroids


def classify(
    vec: np.ndarray,
    centroids: Mapping[str, np.ndarray],
) -> tuple[str | None, float, dict[str, float]]:
    """Nearest-centroid classification of one L2-normalized vector.

    Returns ``(best_category, best_score, {category: cosine})``. ``best_category``
    is ``None`` only when ``centroids`` is empty.
    """
    vec = np.asarray(vec, dtype=np.float32).ravel()
    scores: dict[str, float] = {}
    for category, centroid in centroids.items():
        c = np.asarray(centroid, dtype=np.float32).ravel()
        scores[category] = float(np.dot(vec, c))
    if not scores:
        return None, 0.0, {}
    best = max(scores, key=scores.__getitem__)
    return best, scores[best], scores
