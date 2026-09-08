"""
Backfill a Telegram channel into PostgreSQL.

Usage:
    python scripts/backfill.py --channel @Vbachir --limit 500
"""

import argparse
import asyncio
import os

import asyncpg
import structlog
from dotenv import load_dotenv

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
log = structlog.get_logger(__name__)


async def run(channel: str, limit: int) -> None:
    from src.ingestor.client import TelegramClient
    from src.ingestor.handlers import backfill_channel
    from src.ingestor.run_lock import release_collector_lock, try_acquire_collector_lock

    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    log.info("backfill_start", channel=channel, limit=limit)

    conn = await asyncpg.connect(db_url)
    lock_acquired = await try_acquire_collector_lock(conn)
    if not lock_acquired:
        log.info("collector_already_running")
        await conn.close()
        return
    client = TelegramClient.from_env()
    try:
        async with client:
            inserted = await backfill_channel(client, conn, channel, limit=limit)
            log.info("done", inserted=inserted, channel=channel)
    finally:
        await release_collector_lock(conn)
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(run(args.channel, args.limit))
