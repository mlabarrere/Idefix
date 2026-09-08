"""Offline tests for zero-shot nearest-centroid classification."""
from __future__ import annotations

import numpy as np

from src.embed.centroids import anchor_terms, build_centroids, classify
from src.embed.encoder import Embedder

# A controlled lexicon: each category's anchors map to a distinct basis direction.
_LEXICON = {
    "navy": ["aircraft carrier anchor", "naval fleet anchor"],
    "politics": ["election anchor", "parliament anchor"],
    "generic": ["porte-avions"],  # contextual -> dropped
}
_CONTEXTUAL = {"porte-avions"}

# term -> fixed 3-d basis vector (so centroids are deterministic)
_VECTORS = {
    "aircraft carrier anchor": np.array([1.0, 0.0, 0.0], np.float32),
    "naval fleet anchor": np.array([1.0, 0.0, 0.0], np.float32),
    "election anchor": np.array([0.0, 1.0, 0.0], np.float32),
    "parliament anchor": np.array([0.0, 1.0, 0.0], np.float32),
}


def _fixed_encode(texts: list[str]) -> np.ndarray:
    return np.vstack([_VECTORS.get(t, np.array([0.0, 0.0, 1.0], np.float32)) for t in texts])


def test_anchor_terms_drops_contextual():
    anchors = anchor_terms(_LEXICON, _CONTEXTUAL)
    assert "generic" not in anchors  # only contextual term -> category dropped
    assert anchors["navy"] == ["aircraft carrier anchor", "naval fleet anchor"]


def test_build_centroids_one_per_category(tmp_path):
    emb = Embedder(encode_fn=_fixed_encode, cache_dir=tmp_path)
    centroids = build_centroids(emb, _LEXICON, _CONTEXTUAL)
    assert set(centroids) == {"navy", "politics"}
    for c in centroids.values():
        assert abs(float(np.linalg.norm(c)) - 1.0) < 1e-5


def test_classify_picks_nearest(tmp_path):
    emb = Embedder(encode_fn=_fixed_encode, cache_dir=tmp_path)
    centroids = build_centroids(emb, _LEXICON, _CONTEXTUAL)

    navy_probe = np.array([1.0, 0.0, 0.0], np.float32)
    best, score, scores = classify(navy_probe, centroids)
    assert best == "navy"
    assert score > 0.99
    assert scores["politics"] < 0.5


def test_classify_empty_centroids():
    best, score, scores = classify(np.array([1.0, 0.0], np.float32), {})
    assert best is None
    assert score == 0.0
    assert scores == {}
