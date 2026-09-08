"""Smoke test for alembic/versions/0004 — OFFLINE (no DB, no alembic run).

Loaded by file path (the versions dir is not an importable package). We patch
``alembic.op.execute`` to record statements, then assert upgrade()/downgrade()
are defined, run, and emit idempotent DDL (channel_scores + perf indexes).
"""
import importlib.util
from pathlib import Path

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0004_channel_scores_and_perf_indexes.py"
)


def _load_migration(monkeypatch):
    recorded: list[str] = []

    import alembic.op as op_mod

    monkeypatch.setattr(op_mod, "execute", lambda stmt: recorded.append(str(stmt)))

    spec = importlib.util.spec_from_file_location("mig_0004", _MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, recorded


def test_revision_chain(monkeypatch):
    mod, _ = _load_migration(monkeypatch)
    assert mod.revision == "0004"
    assert mod.down_revision == "0003"


def test_upgrade_emits_idempotent_ddl(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.upgrade)
    mod.upgrade()
    joined = "\n".join(recorded)
    assert "CREATE TABLE IF NOT EXISTS channel_scores" in joined
    assert "CREATE TABLE IF NOT EXISTS scores_run_meta" in joined
    assert "idx_messages_text_notnull" in joined
    assert "idx_channel_scores_suspicion" in joined
    # every emitted CREATE is guarded IF NOT EXISTS
    for stmt in recorded:
        if stmt.strip().upper().startswith("CREATE"):
            assert "IF NOT EXISTS" in stmt


def test_downgrade_defined_and_reverses(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.downgrade)
    mod.downgrade()
    joined = "\n".join(recorded)
    assert "DROP TABLE IF EXISTS channel_scores" in joined
    assert "DROP TABLE IF EXISTS scores_run_meta" in joined
