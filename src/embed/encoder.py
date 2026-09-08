"""Embedder — local sentence-transformers wrapper, deterministic + offline cache.

Mirrors the discipline of ``src/llm/mistral.py`` (deterministic, offline cache,
free re-runs) but for LOCAL embeddings instead of a paid API:

- **Deterministic**: a given (model, text) always maps to the same vector; the
  cache key is ``sha256(model || text)``.
- **Offline cache**: each vector is persisted as ``data/embed_cache/<hash>.npy``;
  a cache hit short-circuits inference (cost 0, reproducible re-runs).
- **Lazy import**: ``sentence_transformers`` is imported only on the first real
  encode, so importing this module does not require the ``embed`` extra.
- **Testable offline**: inject ``encode_fn`` (a ``list[str] -> np.ndarray``
  callable) to bypass the real model entirely in unit tests.

All returned vectors are float32 and L2-normalized, so cosine similarity reduces
to a dot product (see :func:`cosine`).
"""
from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import structlog

log = structlog.get_logger(__name__)

# Fast multilingual default (FR/RU/EN), 384-dim — the "extremely fast locally"
# argument. Override with IDEFIX_EMBED_MODEL (e.g. paraphrase-multilingual-mpnet
# -base-v2 or intfloat/multilingual-e5-base for higher quality).
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CACHE_DIR = _REPO_ROOT / "data" / "embed_cache"


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity. Assumes L2-normalized inputs (then cosine == dot)."""
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=np.float32)
    if mat.ndim == 1:
        mat = mat.reshape(1, -1)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (mat / norms).astype(np.float32)


class Embedder:
    """Load a sentence-transformers model once; batch-encode with an offline cache.

    Usage::

        emb = Embedder()                      # real model (needs the `embed` extra)
        vecs = emb.encode_texts(["a", "b"])   # (2, D) float32, L2-normalized

        # In tests, bypass the model:
        emb = Embedder(encode_fn=fake_encode)
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
        cache_dir: Path | None = None,
        encode_fn: Callable[[list[str]], np.ndarray] | None = None,
        use_cache: bool = True,
    ) -> None:
        self.model_name = model_name or os.environ.get("IDEFIX_EMBED_MODEL") or DEFAULT_MODEL
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self.use_cache = use_cache
        self._encode_fn = encode_fn
        self._model = None  # lazy

    # ── model lifecycle (lazy) ──
    def _ensure_model(self):
        if self._model is None:
            # Lazy import: only require the `embed` extra at first real encode.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _raw_encode(self, texts: list[str]) -> np.ndarray:
        """Encode WITHOUT cache (real model or injected encode_fn)."""
        if self._encode_fn is not None:
            out = np.asarray(self._encode_fn(texts), dtype=np.float32)
        else:
            model = self._ensure_model()
            out = np.asarray(
                model.encode(texts, batch_size=64, show_progress_bar=False),
                dtype=np.float32,
            )
        if out.ndim == 1:
            out = out.reshape(1, -1)
        return _l2_normalize(out)

    # ── cache ──
    def _cache_path(self, text: str) -> Path:
        h = hashlib.sha256(f"{self.model_name}\x00{text}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.npy"

    def _read_cache(self, text: str) -> np.ndarray | None:
        if not self.use_cache:
            return None
        p = self._cache_path(text)
        if not p.exists():
            return None
        try:
            return np.load(p)
        except (OSError, ValueError):
            return None

    def _write_cache(self, text: str, vec: np.ndarray) -> None:
        if not self.use_cache:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            np.save(self._cache_path(text), np.asarray(vec, dtype=np.float32))
        except OSError:  # pragma: no cover - best-effort cache write
            pass

    # ── public ──
    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Return an ``(N, D)`` float32 L2-normalized matrix, one row per text.

        Cached vectors are reused; only cache-misses hit the model. Throughput
        (texts/s) of the encoded miss-batch is logged to substantiate the
        "extremely fast locally" claim.
        """
        items = list(texts)
        if not items:
            return np.zeros((0, 0), dtype=np.float32)

        cached: dict[int, np.ndarray] = {}
        misses: list[int] = []
        for i, t in enumerate(items):
            hit = self._read_cache(t)
            if hit is not None:
                cached[i] = hit.astype(np.float32).ravel()
            else:
                misses.append(i)

        if misses:
            t0 = time.monotonic()
            fresh = self._raw_encode([items[i] for i in misses])
            dt = time.monotonic() - t0
            for k, i in enumerate(misses):
                vec = fresh[k]
                cached[i] = vec
                self._write_cache(items[i], vec)
            rate = (len(misses) / dt) if dt > 0 else float("inf")
            log.info(
                "embed.encode",
                model=self.model_name,
                n=len(items),
                cached=len(items) - len(misses),
                encoded=len(misses),
                texts_per_s=round(rate, 1),
            )

        dim = next(iter(cached.values())).shape[0]
        out = np.zeros((len(items), dim), dtype=np.float32)
        for i, vec in cached.items():
            out[i] = vec
        return out

    def encode_one(self, text: str) -> np.ndarray:
        """Encode a single text into a ``(D,)`` L2-normalized vector."""
        return self.encode_texts([text])[0]
