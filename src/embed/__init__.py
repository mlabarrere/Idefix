"""Local sentence-transformers embedding layer — parallel track to the Mistral LLM.

This package provides a free, fast, deterministic LOCAL alternative to the paid
Mistral classification track. It is imported LAZILY (``sentence_transformers`` is
only loaded when an :class:`Embedder` actually encodes with the real model), so
the default offline pipeline (ingest -> score -> export -> golden test) never
pulls torch.

Public API:
  * :class:`Embedder`         — load once, batch-encode (L2-normalized), offline cache.
  * :func:`cosine`            — cosine similarity for L2-normalized vectors (= dot).
  * :data:`DEFAULT_MODEL`     — the fast multilingual default.
  * :func:`anchor_terms`,
    :func:`build_centroids`,
    :func:`classify`          — zero-shot nearest-centroid over mission lexicons.
"""
from __future__ import annotations

from src.embed.centroids import anchor_terms, build_centroids, classify
from src.embed.encoder import DEFAULT_MODEL, Embedder, cosine

__all__ = [
    "Embedder",
    "cosine",
    "DEFAULT_MODEL",
    "anchor_terms",
    "build_centroids",
    "classify",
]
