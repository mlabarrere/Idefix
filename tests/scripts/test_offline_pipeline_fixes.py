"""Regression tests for the fixes that made the offline pipeline run end to end.

Found by running ``scripts/pipeline.py`` on the public corpus (full snapshot at
alembic head). No database: a fake connection records the SQL and its
arguments, so the tests pin the contract that broke.

* ``export_static`` crashed (``KeyError: 'scoring_file'``) as soon as
  ``mine_episodes`` had written ``episodes_discovered.json``.
* ``analyze_porosity`` / ``mine_episodes`` joined ``channel_scores`` without
  its ``mission`` key (PK (mission, channel_id) since alembic 0005/0006): one
  row per scored mission, ``france_targeting`` taken from whichever came last.
* ``mine_episodes`` always loaded the embedding model when the ``embed`` extra
  was installed, so ``pipeline.py --skip-embeddings`` still imported
  sentence-transformers (and needed the network on a cold cache).
* ``analyze_communities --mission`` (the command the webapp's empty state
  prints) did not exist.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    """Load scripts/<name>.py without running __main__ and without reading .env."""
    prev = os.environ.get("PYTHON_DOTENV_DISABLED")
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    try:
        spec = importlib.util.spec_from_file_location(
            f"{name}_fix_under_test", _REPO / "scripts" / f"{name}.py"
        )
        m = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = m
        spec.loader.exec_module(m)
        return m
    finally:
        if prev is None:
            os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        else:
            os.environ["PYTHON_DOTENV_DISABLED"] = prev


export_static = _load("export_static")
analyze_porosity = _load("analyze_porosity")
mine_episodes = _load("mine_episodes")
analyze_communities = _load("analyze_communities")


class FakeConn:
    """Records ``fetch(query, *args)`` and returns canned rows."""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *args):
        self.calls.append((query, args))
        return self.rows


_ROWS = [
    {"channel_id": -1, "username": "ru", "title": "RU", "fr_score": 0.0, "ft": 0.42},
    {"channel_id": -2, "username": "fr", "title": None, "fr_score": 0.5, "ft": None},
]


# --------------------------------------------------------------------------- #
# export_static: discovered episodes get no evidence dossier
# --------------------------------------------------------------------------- #
def test_only_registry_episodes_get_an_evidence_dossier():
    episodes = {
        "dugin_cluster": {"scoring_file": "dugin_cluster.json", "titre": "t"},
        "ep_forward_000": {"id": "ep_forward_000", "label": "x", "n_channels": 2},
        "ep_media_001": {"id": "ep_media_001", "label": "y", "n_channels": 3},
    }
    assert export_static._evidence_episode_ids(episodes) == ["dugin_cluster"]


def test_no_episode_no_dossier():
    assert export_static._evidence_episode_ids({}) == []


# --------------------------------------------------------------------------- #
# channel_scores joins are mission-scoped
# --------------------------------------------------------------------------- #
def _assert_mission_scoped(conn: FakeConn, mission: str) -> None:
    ((query, args),) = conn.calls
    join = query.split("LEFT JOIN channel_scores", 1)[1].split("WHERE", 1)[0]
    assert "s.mission = $1" in join  # in the ON clause: keeps the LEFT JOIN semantics
    assert args == (mission,)


def test_porosity_meta_reads_the_russosphere_scores_only():
    conn = FakeConn(_ROWS)
    meta = asyncio.run(analyze_porosity.load_channel_meta(conn))
    _assert_mission_scoped(conn, "russosphere")
    assert meta[-1]["side"] == "RU" and meta[-1]["france_targeting"] == 0.42
    assert meta[-2]["side"] == "FR" and meta[-2]["france_targeting"] is None


@pytest.mark.parametrize("mission", ["russosphere", "gan"])
def test_episode_sides_read_the_requested_mission_scores(mission):
    conn = FakeConn(_ROWS)
    meta = asyncio.run(mine_episodes.load_sides(conn, mission))
    _assert_mission_scoped(conn, mission)
    assert set(meta) == {-1, -2}


def test_episode_sides_default_to_the_default_mission():
    conn = FakeConn(_ROWS)
    asyncio.run(mine_episodes.load_sides(conn))
    _assert_mission_scoped(conn, "russosphere")


# --------------------------------------------------------------------------- #
# mine_episodes --no-embeddings never touches the encoder
# --------------------------------------------------------------------------- #
@pytest.fixture
def exploding_encoder(monkeypatch):
    """Any import of the embedding encoder fails the test loudly."""
    boom = types.ModuleType("src.embed.encoder")

    def _getattr(name):
        raise AssertionError(f"src.embed.encoder.{name} imported under --no-embeddings")

    boom.__getattr__ = _getattr  # type: ignore[method-assign]
    monkeypatch.setitem(sys.modules, "src.embed.encoder", boom)


def _episodes():
    return [{"appearances": [{"side": "FR", "text": "t", "username": "u"}], "_texts": ["a", "b"]}]


def test_disabled_embeddings_skip_the_encoder(exploding_encoder):
    eps = _episodes()
    mine_episodes.calculate_embeddings(eps, enabled=False)
    assert eps[0]["pourquoi_embedding"] is None


def test_enabled_embeddings_do_reach_the_encoder(exploding_encoder):
    """Sanity check of the sentinel: the default path does import the encoder."""
    with pytest.raises(AssertionError, match="imported under --no-embeddings"):
        mine_episodes.calculate_embeddings(_episodes())


# --------------------------------------------------------------------------- #
# analyze_communities --mission
# --------------------------------------------------------------------------- #
def test_snapshot_path_default_is_the_historical_russosphere_path():
    assert analyze_communities.snapshot_path() == analyze_communities.OUT_PATH
    assert analyze_communities.OUT_PATH == (
        _REPO / "webapp" / "public" / "data" / "russosphere" / "russosphere_snapshot.json"
    )


@pytest.mark.parametrize("mission", ["russosphere", "france_ukraine", "gan"])
def test_snapshot_path_follows_the_mission_bundle(mission):
    expected = _REPO / "webapp" / "public" / "data" / mission / "russosphere_snapshot.json"
    assert analyze_communities.snapshot_path(mission) == expected


def test_snapshot_path_rejects_a_planned_mission():
    with pytest.raises(ValueError):
        analyze_communities.snapshot_path("dircom_minarm")
