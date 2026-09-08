"""Shared PostgreSQL connection pool (offline scripts + src I/O).

Centralizes connection pooling for all pipeline/analysis scripts. Supabase-optimized:
connection pool reduces latency (~50ms saved per operation) and better utilizes
Supabase Session Pooler.

Usage::

    from src.shared.db import get_pool

    async with get_pool() as pool:
        async with pool.acquire() as conn:
            ...

Legacy one-shot connection (deprecated, use pool):

    from src.shared.db import db_connect

    conn = await db_connect()
    try:
        ...
    finally:
        await conn.close()
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the global connection pool.

    Pool config optimized for Supabase:
    - min_size=2: keep warm connections
    - max_size=10: limit concurrent for Session Pooler
    - command_timeout=60: safe default for long-running analytics
    """
    global _pool
    if _pool is None:
        dsn = os.environ["DATABASE_URL"].replace("+asyncpg", "")
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=60.0,
        )
    return _pool


async def close_pool() -> None:
    """Close the global pool. Call at script exit for clean shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def db_connection() -> AsyncIterator[asyncpg.Connection]:
    """Context manager for acquiring a pooled connection.

    Usage::

        async with db_connection() as conn:
            result = await conn.fetch("SELECT ...")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def db_connect() -> asyncpg.Connection:
    """Open a one-shot asyncpg connection (DEPRECATED).

    Prefer ``db_connection()`` context manager for automatic pool management.
    This function exists for backward compatibility only.
    """
    return await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
