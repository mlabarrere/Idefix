"""One database-backed lock shared by every MTProto collector process."""

from __future__ import annotations

import asyncpg

# Stable signed-bigint namespace: ASCII-ish "IDEFIX".
COLLECTOR_LOCK_ID = 0x494445464958


async def try_acquire_collector_lock(conn: asyncpg.Connection) -> bool:
    """Return immediately; True means this connection owns the collector lock."""
    return bool(await conn.fetchval("SELECT pg_try_advisory_lock($1)", COLLECTOR_LOCK_ID))


async def release_collector_lock(conn: asyncpg.Connection) -> None:
    """Release the session lock. Closing the connection is a second safety net."""
    await conn.fetchval("SELECT pg_advisory_unlock($1)", COLLECTOR_LOCK_ID)
