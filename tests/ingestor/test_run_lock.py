"""Collector advisory lock contract tests."""

import pytest

from src.ingestor.run_lock import (
    COLLECTOR_LOCK_ID,
    release_collector_lock,
    try_acquire_collector_lock,
)


class _FakeConn:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = []

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return next(self.values)


@pytest.mark.asyncio
async def test_acquire_returns_database_decision():
    conn = _FakeConn([False])
    assert await try_acquire_collector_lock(conn) is False
    assert "pg_try_advisory_lock" in conn.calls[0][0]
    assert conn.calls[0][1] == (COLLECTOR_LOCK_ID,)


@pytest.mark.asyncio
async def test_release_uses_same_lock_id():
    conn = _FakeConn([True])
    await release_collector_lock(conn)
    assert "pg_advisory_unlock" in conn.calls[0][0]
    assert conn.calls[0][1] == (COLLECTOR_LOCK_ID,)
