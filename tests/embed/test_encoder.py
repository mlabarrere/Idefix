"""Offline tests for the Embedder — no model download (injected encode_fn)."""
from __future__ import annotations

import numpy as np

from src.embed.encoder import Embedder, cosine


def _fake_encode(texts: list[str]) -> np.ndarray:
    """Deterministic pseudo-embedding: seed an RNG per text -> stable unit-ish vec."""
    out = []
    for t in texts:
        seed = abs(hash(t)) % (2**32)
        rng = np.random.default_rng(seed)
        out.append(rng.standard_normal(8).astype(np.float32))
    return np.vstack(out)


def test_encode_returns_l2_normalized_rows(tmp_path):
    emb = Embedder(encode_fn=_fake_encode, cache_dir=tmp_path)
    vecs = emb.encode_texts(["alpha", "beta", "gamma"])
    assert vecs.shape == (3, 8)
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_empty_input_returns_empty(tmp_path):
    emb = Embedder(encode_fn=_fake_encode, cache_dir=tmp_path)
    out = emb.encode_texts([])
    assert out.shape == (0, 0)


def test_cache_hit_skips_encode(tmp_path):
    calls = {"n": 0}

    def counting(texts: list[str]) -> np.ndarray:
        calls["n"] += len(texts)
        return _fake_encode(texts)

    emb = Embedder(encode_fn=counting, cache_dir=tmp_path)
    first = emb.encode_texts(["x", "y"])
    assert calls["n"] == 2

    # Second call (same texts) must be served from the on-disk cache.
    emb2 = Embedder(encode_fn=counting, cache_dir=tmp_path)
    second = emb2.encode_texts(["x", "y"])
    assert calls["n"] == 2  # unchanged -> no re-encode
    assert np.allclose(first, second)


def test_cache_is_model_scoped(tmp_path):
    """Same text, different model name -> different cache key (no collision)."""
    a = Embedder(encode_fn=lambda ts: np.ones((len(ts), 4), np.float32),
                 cache_dir=tmp_path, model_name="model-a")
    b = Embedder(encode_fn=lambda ts: np.full((len(ts), 4), 2.0, np.float32),
                 cache_dir=tmp_path, model_name="model-b")
    va = a.encode_one("same")
    vb = b.encode_one("same")
    # Both normalized to unit length but distinct cache files; values are equal
    # after normalization here (constant vectors) — assert files are separate.
    assert a._cache_path("same") != b._cache_path("same")
    assert va.shape == vb.shape == (4,)


def test_cosine_bounds():
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    w = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert cosine(v, v) == 1.0
    assert abs(cosine(v, w)) < 1e-6
    assert cosine(v, np.zeros(3, np.float32)) == 0.0
