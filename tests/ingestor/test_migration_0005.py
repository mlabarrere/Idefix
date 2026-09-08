"""Smoke test for alembic/versions/0005 — OFFLINE (no DB, no alembic run).

Loaded by file path (the versions dir is not an importable package). We patch
``alembic.op.execute`` to record statements, then assert upgrade()/downgrade()
are defined, run, and emit idempotent, additive mission-scoping DDL.
"""
import importlib.util
from pathlib import Path

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0005_mission_scoped_scores.py"
)


def _load_migration(monkeypatch):
    recorded: list[str] = []

    import alembic.op as op_mod

    monkeypatch.setattr(op_mod, "execute", lambda stmt: recorded.append(str(stmt)))

    spec = importlib.util.spec_from_file_location("mig_0005", _MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, recorded


def test_revision_chain(monkeypatch):
    mod, _ = _load_migration(monkeypatch)
    assert mod.revision == "0005"
    assert mod.down_revision == "0004"


def test_upgrade_emits_additive_mission_column(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.upgrade)
    mod.upgrade()
    joined = "\n".join(recorded)
    # additive mission column on BOTH score tables, default = russosphere
    assert "channel_scores" in joined and "scores_run_meta" in joined
    assert joined.count("ADD COLUMN IF NOT EXISTS mission") == 2
    assert "DEFAULT 'russosphere'" in joined
    assert "idx_channel_scores_mission_suspicion" in joined
    # additive only — NO primary-key / constraint changes in this revision
    assert "PRIMARY KEY" not in joined.upper()
    assert "DROP CONSTRAINT" not in joined.upper()


def test_downgrade_defined_and_reverses(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.downgrade)
    mod.downgrade()
    joined = "\n".join(recorded)
    assert "DROP COLUMN IF EXISTS mission" in joined
    assert "idx_channel_scores_mission_suspicion" in joined
