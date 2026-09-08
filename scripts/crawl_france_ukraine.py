"""Bounded France–Ukraine acquisition campaign in russophone Telegram networks.

This is an acquisition lens over the shared Telegram graph, not an attribution
classifier and not a new scoring mission. ``--dry-run`` is DB-only. Live runs
are serialized by the global PostgreSQL collector lock and write directly to the
database selected by ``DATABASE_URL`` (Supabase in normal operation).
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.ingestor.handlers import backfill_channel  # noqa: E402
from src.ingestor.run_lock import (  # noqa: E402
    release_collector_lock,
    try_acquire_collector_lock,
)
from src.ingestor.session import session_preflight  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

STOP_FILE = ROOT / "scripts" / ".stop_france_ukraine"

FRANCE_PATTERN = (
    r"(france|français|francais|french|macron|paris|armée française|"
    r"франци|француз|макрон|париж)"
)
UKRAINE_PATTERN = (
    r"(ukrain|ukraine|ukrainian|zelensk|kiev|kyiv|donbas|donbass|"
    r"украин|зеленск|киев|донбасс|донбас)"
)
CYRILLIC_PATTERN = r"[А-Яа-яЁё]"

_REFRESH_Q = """
    WITH topical AS (
        SELECT channel_id,
               count(*) AS topic_hits,
               max(timestamp) AS latest_topic
        FROM messages
        WHERE COALESCE(text, '') ~* $1
          AND COALESCE(text, '') ~* $2
          AND COALESCE(text, '') ~ $3
        GROUP BY channel_id
    )
    SELECT c.channel_id, c.username, c.title,
           t.topic_hits, t.latest_topic, c.last_polled_at
    FROM topical t
    JOIN channels c USING (channel_id)
    WHERE c.username IS NOT NULL AND c.username <> ''
      AND COALESCE(c.last_polled_at, 'epoch'::timestamptz)
          < NOW() - ($4 * INTERVAL '1 hour')
    ORDER BY t.topic_hits DESC, c.last_polled_at ASC NULLS FIRST, c.channel_id
    LIMIT $5
"""

_DISCOVERY_Q = """
    WITH backfilled AS (SELECT DISTINCT channel_id FROM messages),
    topical_origins AS (
        SELECT forward_from_channel_id AS channel_id,
               count(*) AS topic_forwards,
               count(DISTINCT channel_id) AS distinct_relayers,
               max(timestamp) AS latest_evidence
        FROM messages
        WHERE forward_from_channel_id IS NOT NULL
          AND COALESCE(text, '') ~* $1
          AND COALESCE(text, '') ~* $2
          AND COALESCE(text, '') ~ $3
        GROUP BY forward_from_channel_id
    )
    SELECT c.channel_id, c.username, c.title,
           o.topic_forwards, o.distinct_relayers, o.latest_evidence
    FROM topical_origins o
    JOIN channels c USING (channel_id)
    WHERE c.channel_id NOT IN (SELECT channel_id FROM backfilled)
      AND c.username IS NOT NULL AND c.username <> ''
    ORDER BY o.topic_forwards DESC, o.distinct_relayers DESC,
             o.latest_evidence DESC, c.channel_id
    LIMIT $4
"""


@dataclass(frozen=True)
class QueueItem:
    kind: str
    channel_id: int
    username: str
    title: str | None
    evidence_count: int
    relayer_count: int = 0


def is_france_ukraine_cyrillic(text: str | None) -> bool:
    """Observable acquisition gate; it is not a claim or attribution label."""
    if not text or not re.search(CYRILLIC_PATTERN, text):
        return False
    return bool(
        re.search(FRANCE_PATTERN, text, re.IGNORECASE)
        and re.search(UKRAINE_PATTERN, text, re.IGNORECASE)
    )


def rank_discovery_rows(rows: Sequence[Mapping], cap: int) -> list[QueueItem]:
    """Deterministic pure ranking used by DB and unit-test paths."""
    ordered = sorted(
        rows,
        key=lambda r: (
            -int(r["topic_forwards"]),
            -int(r["distinct_relayers"]),
            int(r["channel_id"]),
        ),
    )
    return [
        QueueItem(
            kind="discover",
            channel_id=int(r["channel_id"]),
            username=str(r["username"]),
            title=r.get("title"),
            evidence_count=int(r["topic_forwards"]),
            relayer_count=int(r["distinct_relayers"]),
        )
        for r in ordered[:cap]
    ]


async def build_queues(
    conn,
    *,
    refresh_cap: int,
    discovery_cap: int,
    stale_hours: int,
) -> tuple[list[QueueItem], list[QueueItem]]:
    refresh_rows = await conn.fetch(
        _REFRESH_Q,
        FRANCE_PATTERN,
        UKRAINE_PATTERN,
        CYRILLIC_PATTERN,
        stale_hours,
        refresh_cap,
    )
    discovery_rows = await conn.fetch(
        _DISCOVERY_Q,
        FRANCE_PATTERN,
        UKRAINE_PATTERN,
        CYRILLIC_PATTERN,
        discovery_cap,
    )
    refresh = [
        QueueItem(
            kind="refresh",
            channel_id=int(r["channel_id"]),
            username=str(r["username"]),
            title=r["title"],
            evidence_count=int(r["topic_hits"]),
        )
        for r in refresh_rows
    ]
    return refresh, rank_discovery_rows(discovery_rows, discovery_cap)


def print_queue(refresh: list[QueueItem], discovery: list[QueueItem]) -> None:
    print(f"[fr-ua] refresh={len(refresh)} discovery={len(discovery)}")
    for item in [*refresh, *discovery]:
        extra = f" relayers={item.relayer_count}" if item.kind == "discover" else ""
        print(
            f"  {item.kind:8s} @{item.username:<28} "
            f"evidence={item.evidence_count}{extra} | {item.title or '-'}"
        )


async def run(args: argparse.Namespace) -> None:
    if args.refresh_cap + args.discovery_cap > 20:
        raise SystemExit("Safety cap exceeded: refresh-cap + discovery-cap must be <= 20")
    if args.min_gap < 90:
        raise SystemExit("Safety floor exceeded: --min-gap must be >= 90 seconds")
    if args.max_gap < args.min_gap:
        raise SystemExit("--max-gap must be >= --min-gap")

    conn = await db_connect()
    lock_acquired = False
    try:
        refresh, discovery = await build_queues(
            conn,
            refresh_cap=args.refresh_cap,
            discovery_cap=args.discovery_cap,
            stale_hours=args.stale_hours,
        )
        print_queue(refresh, discovery)
        if args.dry_run:
            print("[fr-ua] dry-run: no Telegram call, no write")
            return

        lock_acquired = await try_acquire_collector_lock(conn)
        if not lock_acquired:
            print("[fr-ua] another Telegram collector is already running; exiting")
            return

        await session_preflight(require_live=True)
        from src.ingestor.client import TelegramClient

        if STOP_FILE.exists():
            STOP_FILE.unlink()

        before = await conn.fetchval("SELECT count(*) FROM messages")
        attempted = inserted = 0
        started = time.monotonic()
        async with TelegramClient.from_env() as client:
            for item in [*refresh, *discovery]:
                if STOP_FILE.exists():
                    print("[fr-ua] stop sentinel detected; stopping between channels")
                    break
                attempted += 1
                try:
                    n = await backfill_channel(
                        client, conn, "@" + item.username, limit=args.message_limit
                    )
                    inserted += n
                    print(f"[fr-ua] {attempted:02d} @{item.username} +{n} messages", flush=True)
                except Exception as exc:  # one dead public channel must not abort the run
                    print(
                        f"[fr-ua] {attempted:02d} @{item.username} skipped: "
                        f"{type(exc).__name__}: {str(exc)[:100]}",
                        flush=True,
                    )
                if attempted < len(refresh) + len(discovery):
                    await asyncio.sleep(random.uniform(args.min_gap, args.max_gap))

        after = await conn.fetchval("SELECT count(*) FROM messages")
        elapsed = (time.monotonic() - started) / 60
        print(
            f"[fr-ua] complete attempted={attempted} inserted={inserted} "
            f"db_delta={after - before} elapsed_min={elapsed:.1f}",
            flush=True,
        )
    finally:
        if lock_acquired:
            await release_collector_lock(conn)
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-cap", type=int, default=5)
    parser.add_argument("--discovery-cap", type=int, default=12)
    parser.add_argument("--stale-hours", type=int, default=10)
    parser.add_argument("--message-limit", type=int, default=300)
    parser.add_argument("--min-gap", type=float, default=90.0)
    parser.add_argument("--max-gap", type=float, default=150.0)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
