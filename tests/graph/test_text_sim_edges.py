"""Offline tests for semantic-similarity edges (TEXT_SIM / TRANSLATION)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from src.embed.encoder import Embedder
from src.graph.edges import derive_text_sim_edges

_T0 = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


def _encode(texts: list[str]) -> np.ndarray:
    # "carrier..." -> e0 ; anything else -> e1 (orthogonal).
    out = []
    for t in texts:
        out.append(np.array([1.0, 0.0], np.float32) if t.startswith("carrier")
                   else np.array([0.0, 1.0], np.float32))
    return np.vstack(out)


def _msg(cid, dt, lang, text):
    return {"channel_id": cid, "message_id": 1, "timestamp": dt, "language": lang, "text": text}


def _edges(messages, **kw):
    emb = Embedder(encode_fn=_encode, use_cache=False)
    return derive_text_sim_edges(messages, emb, **kw)


def test_text_sim_and_translation_split_by_language(tmp_path):
    msgs = [
        _msg(10, _T0, "fr", "carrier deployment alpha one two three four words"),
        _msg(20, _T0 + timedelta(hours=1), "fr", "carrier deployment beta five six seven eight"),
        _msg(30, _T0 + timedelta(hours=2), "ru", "carrier авианосец gamma nine ten eleven twelve"),
        _msg(10, _T0 + timedelta(days=10), "fr", "blabla unrelated content long enough here ok"),
    ]
    edges = _edges(msgs)
    by_type = {(e.src_channel_id, e.dst_channel_id, e.edge_type) for e in edges}

    # same language (fr/fr) -> TEXT_SIM
    assert (10, 20, "TEXT_SIM") in by_type
    # cross language (fr/ru) -> TRANSLATION
    assert (10, 30, "TRANSLATION") in by_type
    assert (20, 30, "TRANSLATION") in by_type
    # the orthogonal "blabla" message links to nobody
    assert all(e.text_sim is not None and e.text_sim >= 0.715 for e in edges)
    # canonical a < b
    assert all(e.src_channel_id < e.dst_channel_id for e in edges)


def test_window_excludes_distant_pairs(tmp_path):
    msgs = [
        _msg(10, _T0, "fr", "carrier deployment alpha one two three four words"),
        _msg(20, _T0 + timedelta(days=30), "fr", "carrier deployment beta five six seven eight"),
    ]
    # 30 days apart, default 72h window -> no edge
    assert _edges(msgs) == []
    # widen the window -> edge appears
    edges = _edges(msgs, window_seconds=40 * 24 * 3600)
    assert len(edges) == 1
    assert edges[0].edge_type == "TEXT_SIM"


def test_same_channel_pairs_ignored(tmp_path):
    msgs = [
        _msg(10, _T0, "fr", "carrier deployment alpha one two three four words"),
        _msg(10, _T0 + timedelta(hours=1), "fr", "carrier deployment beta five six seven"),
    ]
    assert _edges(msgs) == []  # same channel is never coordination


def test_below_threshold_no_edge(tmp_path):
    msgs = [
        _msg(10, _T0, "fr", "carrier deployment alpha one two three four words"),
        _msg(20, _T0 + timedelta(hours=1), "fr", "totally different unrelated message text here"),
    ]
    # e0 vs e1 -> cosine 0 < 0.715
    assert _edges(msgs) == []
