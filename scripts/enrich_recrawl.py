"""Enrichment re-crawl — capture media file_unique_id, channel bio, and public
discussion-group commenters for an EXISTING set of channels, in ONE serialized
Telegram session.

What this pass adds (vs. the original backfill):
  * messages.media_hash  <- file_unique_id of attached media (no download)
  * channels.description <- channel bio (chat.description)
  * comments table       <- commenters of the channel's PUBLIC linked group

RGPD SCOPE DECISION (validated by Micky, 2026-06-05) — load-bearing:
  fetch_comments collects INDIVIDUAL commenters (id + username + text + timestamp)
  of PUBLIC linked discussion groups. This is personal data of natural persons,
  not just channel-admin publishers. Legal basis: public-interest mission
  (docs/method/07-tiers-and-governance.md §7.3, RGPD Art. 6.1.e, loi 2024-850); purpose: derive co-commenter
  coordination edges downstream. Minimization, retention bounds (13/36 months),
  access journal and deletion propagation per docs/method/07-tiers-and-governance.md §7.3 apply to the comments
  table. Public groups ONLY — no private content, no member scraping.

OPERATIONAL RULE (account hygiene) — NEVER run in parallel:
  A SINGLE serialized session on the ONE FR (+33) account. Do not launch two
  copies, do not parallelize across accounts. Channels are processed one at a
  time, re-backfill then comments, FLOOD_WAIT handled by the client. Running this
  concurrently with any other crawl risks a ban (docs/method/07-tiers-and-governance.md §7.3 account hygiene).

USAGE (a human launches this — it is NOT run by the agent that wrote it):
    # default seed set (same anchors as backfill_seeds.py):
    .venv\\Scripts\\python.exe scripts\\enrich_recrawl.py
    # or an explicit channel set (e.g. the catalogue, or a snowball hop):
    .venv\\Scripts\\python.exe scripts\\enrich_recrawl.py @RFI_fr @Geopolitika_fr ...
  Set PYTHONUTF8=1 on Windows. One process only.
"""
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
# Pass channels as CLI args to enrich an arbitrary set (e.g. the full catalogue).
CHANNELS = sys.argv[1:] or _DEFAULT_SEEDS
LIMIT = 300            # history depth per channel (messages)
COMMENT_LIMIT = 500    # comments depth per linked group


async def main():
    from src.ingestor.client import TelegramClient
    from src.ingestor.handlers import backfill_channel, fetch_comments
    from src.ingestor.run_lock import release_collector_lock, try_acquire_collector_lock

    conn = await db_connect()
    lock_acquired = await try_acquire_collector_lock(conn)
    if not lock_acquired:
        print("Another Telegram collector is already running; exiting.")
        await conn.close()
        return
    client = TelegramClient.from_env()
    total_msgs = 0
    total_comments = 0
    try:
        # ONE session, channels processed strictly one after another.
        async with client:
            for ch in CHANNELS:
                try:
                    n = await backfill_channel(client, conn, ch, limit=LIMIT)
                    total_msgs += n
                except Exception as e:
                    n = 0
                    print(f"  {ch:18s} backfill ERROR {type(e).__name__}: {str(e)[:60]}")
                try:
                    c = await fetch_comments(client, conn, ch, limit=COMMENT_LIMIT)
                    total_comments += c
                except Exception as e:
                    c = 0
                    print(f"  {ch:18s} comments ERROR {type(e).__name__}: {str(e)[:60]}")
                print(f"  {ch:18s} -> {n} messages, {c} comments")
    finally:
        await release_collector_lock(conn)
        await conn.close()
    print(f"TOTAL: {total_msgs} messages, {total_comments} comments")


asyncio.run(main())
