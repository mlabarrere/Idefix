"""Backfill the accessible seed set in a single Telegram session (account hygiene).
Hop-0 of the snowball: legitimate FR news hubs + one accessible adversary anchor."""
import asyncio
import sys

from dotenv import load_dotenv

from src.shared.db import db_connect

load_dotenv()

_DEFAULT_SEEDS = [
    # Legit / aggregator hubs (snowball anchor)
    "@RFI_fr", "@euronewsfr", "@france24_fr", "@actu17", "@Mediavenir", "@CerfiaFR",
    # Accessible adversary anchor (documented pro-Kremlin)
    "@Geopolitika_fr",
]
# Pass channels as CLI args to backfill an arbitrary set (e.g. snowball hop-2).
SEEDS = sys.argv[1:] or _DEFAULT_SEEDS
LIMIT = 300

async def main():
    from src.ingestor.client import TelegramClient
    from src.ingestor.handlers import backfill_channel
    from src.ingestor.run_lock import release_collector_lock, try_acquire_collector_lock

    conn = await db_connect()
    lock_acquired = await try_acquire_collector_lock(conn)
    if not lock_acquired:
        print("Another Telegram collector is already running; exiting.")
        await conn.close()
        return
    client = TelegramClient.from_env()
    total = 0
    try:
        async with client:
            for ch in SEEDS:
                try:
                    n = await backfill_channel(client, conn, ch, limit=LIMIT)
                    total += n
                    print(f"  {ch:16s} -> {n} messages")
                except Exception as e:
                    print(f"  {ch:16s} -> ERROR {type(e).__name__}: {str(e)[:60]}")
    finally:
        await release_collector_lock(conn)
        await conn.close()
    print(f"TOTAL inserted: {total}")

asyncio.run(main())
