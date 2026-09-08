"""Tests de la logique PURE du mineur d'épisodes (sans base).

Épingle le contrat : un épisode est RU→FR uniquement (origine russophile,
reprise FR), porte vélocité + canaux, et la corroboration compte les TYPES de
pivot distincts reliant une paire RU→FR (verrou multi-signal, ≥2 ⇒ T2).
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mine_episodes.py"


def _load():
    spec = importlib.util.spec_from_file_location("mine_episodes", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load()
_T0 = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


def _meta():
    return {
        -1: {"username": "ru_src", "title": "RU", "fr_score": 0.02,
             "france_targeting": 0.1, "side": "RU"},
        -2: {"username": "fr_recv", "title": "FR", "fr_score": 0.40,
             "france_targeting": 0.5, "side": "FR"},
        -3: {"username": "ru_other", "title": "RU2", "fr_score": 0.0,
             "france_targeting": 0.0, "side": "RU"},
    }


def test_assemble_ru_to_fr_with_velocity():
    meta = _meta()
    evs = [
        (-1, _T0, "texte source"),
        (-2, _T0 + timedelta(hours=3), "reprise FR"),
    ]
    ep = _mod._assemble(meta, "media", "h1", "média", evs)
    assert ep is not None
    assert ep["ru_seeders"] == ["ru_src"]
    assert ep["fr_receivers"] == ["fr_recv"]
    assert ep["velocity_hours"] == 3.0


def test_assemble_rejects_fr_origin():
    """Origine FR (puis RU) n'est PAS une production russophile reprise — exclu."""
    meta = _meta()
    evs = [
        (-2, _T0, "origine FR"),
        (-1, _T0 + timedelta(hours=1), "RU ensuite"),
    ]
    assert _mod._assemble(meta, "media", "h", "m", evs) is None


def test_assemble_rejects_same_side_only():
    meta = _meta()
    evs = [(-1, _T0, "a"), (-3, _T0 + timedelta(hours=1), "b")]  # RU + RU
    assert _mod._assemble(meta, "media", "h", "m", evs) is None


def test_group_by_pair_merges_same_relation_and_counts_signals():
    meta = _meta()
    base = [(-1, _T0, "x"), (-2, _T0 + timedelta(hours=1), "y")]
    base2 = [(-1, _T0, "z"), (-2, _T0 + timedelta(hours=5), "w")]
    raw = [
        _mod._assemble(meta, "media", "h1", "m", base),
        _mod._assemble(meta, "media", "h2", "m", base2),   # même paire, 2e média
        _mod._assemble(meta, "forward", "f1", "f", base),  # même paire, forward
    ]
    grouped = _mod.group_by_pair(raw, meta)
    # 3 pivots bruts ru_src→fr_recv ⇒ 1 SEUL épisode (la relation)
    assert len(grouped) == 1
    g = grouped[0]
    assert g["n_pivots"] == 3
    assert g["corroboration"] == 2  # media + forward = 2 types distincts
    assert set(g["corroborating_signals"]) == {"media", "forward"}
    assert g["velocity_hours"] == 1.0  # meilleure (min) des reprises


def test_finalize_tiers_and_sort():
    meta = _meta()
    base = [(-1, _T0, "x"), (-2, _T0 + timedelta(hours=1), "y")]
    grouped = _mod.group_by_pair([_mod._assemble(meta, "media", "h1", "m", base)], meta)
    out = _mod.finalize(grouped, meta)
    assert out[0]["tier"] == "T1"  # 1 seul type de signal
    assert out[0]["id"].startswith("ep_media_")
    assert out[0]["fr_targeting_max"] == 0.5
    assert set(out[0]["channel_ids"]) == {-1, -2}
