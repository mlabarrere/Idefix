"""Smoke test for alembic/versions/0003 — OFFLINE (no DB, no alembic run).

Loaded by file path (the versions dir is not an importable package). We patch
``alembic.op.execute`` to record statements instead of touching a database, then
assert upgrade()/downgrade() are defined, run, and emit idempotent DDL.
"""
import importlib.util
from pathlib import Path

import pytest

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0003_enrich_media_description_comments.py"
)


def _load_migration(monkeypatch):
    """Import the migration with alembic.op.execute patched to record SQL."""
    recorded: list[str] = []

    import alembic.op as op_mod

    monkeypatch.setattr(op_mod, "execute", lambda stmt: recorded.append(str(stmt)))

    spec = importlib.util.spec_from_file_location("mig_0003", _MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, recorded


def test_revision_chain(monkeypatch):
    mod, _ = _load_migration(monkeypatch)
    assert mod.revision == "0003"
    assert mod.down_revision == "0002"


def test_upgrade_emits_idempotent_ddl(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.upgrade)
    mod.upgrade()
    joined = "\n".join(recorded)
    # comments table, description column, media_hash index — all IF NOT EXISTS
    assert "CREATE TABLE IF NOT EXISTS comments" in joined
    assert "ADD COLUMN IF NOT EXISTS description" in joined
    assert "idx_messages_media_hash" in joined
    assert "ADD COLUMN" not in joined.replace("ADD COLUMN IF NOT EXISTS", "")
    # every emitted CREATE is guarded
    for stmt in recorded:
        if stmt.strip().upper().startswith("CREATE"):
            assert "IF NOT EXISTS" in stmt


def test_downgrade_defined_and_reverses(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    assert callable(mod.downgrade)
    mod.downgrade()
    joined = "\n".join(recorded)
    assert "DROP TABLE IF EXISTS comments" in joined
    assert "DROP COLUMN IF EXISTS description" in joined


def test_comments_unique_key_matches_insert(monkeypatch):
    """The comments UNIQUE key must match queries.insert_comment's ON CONFLICT
    target, or upserts would error at runtime."""
    mod, recorded = _load_migration(monkeypatch)
    mod.upgrade()
    joined = "\n".join(recorded)
    assert "UNIQUE(channel_id, message_id, commenter_id, timestamp)" in joined


@pytest.mark.asyncio
async def test_handlers_fetch_comments_no_linked_group_returns_zero(monkeypatch):
    """fetch_comments is graceful when the channel has no linked discussion
    group — returns 0 without iterating history. (Light integration of the
    handler with a fake client, still fully offline.)"""
    from src.ingestor import handlers

    class _Chat:
        id = 100
        linked_chat = None

    class _Client:
        async def get_channel_info(self, channel):
            return _Chat()

    n = await handlers.fetch_comments(_Client(), conn=None, channel="@x", limit=10)
    assert n == 0
