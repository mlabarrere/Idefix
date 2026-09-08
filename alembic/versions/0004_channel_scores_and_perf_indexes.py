"""perf — channel_scores materialization + hot-path indexes

Performance: the API used to recompute everything on the fly per request
(france_targeting over ALL messages + full graph build + eigenvector centrality).
This migration adds the storage + indexes that let a post-crawl pipeline
(`scripts/build_scores.py`) MATERIALIZE per-channel scores once, so the API only
READS precomputed data:

  1. ``idx_messages_text_notnull`` — partial index targeting the france_targeting
     query (``... FROM messages WHERE text IS NOT NULL``). Turns a full table
     scan into an index scan over the (much smaller) set of text-bearing rows.
  2. ``idx_messages_channel_ts_desc`` — composite for the recency windowing
     (``ORDER BY channel_id, timestamp DESC``, keep N most recent per channel).
  3. ``channel_scores`` — per-channel materialized suspicion score. ``suspicion``
     is a real column indexed DESC so ``GET /api/channels`` reads a pre-sorted
     top_k cheaply. ``archetype`` is exposed as a column so
     ``GET /api/channels/{id}/neighborhood`` annotates nodes without recomputing
     cascade_role over the whole graph. ``payload`` holds the EXACT ``channel``
     object of the queue contract (so the API does not reassemble per-channel).
  4. ``scores_run_meta`` — single-row table holding the queue ENVELOPE
     (coverage_callout, symmetric_ratio, nominal top_k) for one run.

Materialization invalidation is by TRUNCATE+rewrite per run (build_scores) and by
the API's in-memory TTL cache — no mutable endpoint (the API stays read-only).
The score freshness is therefore "as of the last build_scores run after a crawl"
(pipeline order: crawl -> build_edges -> build_scores -> analyze_communities).

Idempotent: every statement uses IF NOT EXISTS — additive and safe on the
populated DB. Transition: ``alembic upgrade head`` (or ``alembic stamp 0004`` if
hand-applied).

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# One statement per list entry — the asyncpg dialect rejects multi-statement
# strings (extended/prepared-statement protocol). See 0001_baseline.py note.
UPGRADE_STATEMENTS = [
    # 1. Partial index for the france_targeting query (WHERE text IS NOT NULL).
    "CREATE INDEX IF NOT EXISTS idx_messages_text_notnull "
    "ON messages(channel_id) WHERE text IS NOT NULL",
    # 2. Composite for per-channel recency windowing.
    "CREATE INDEX IF NOT EXISTS idx_messages_channel_ts_desc "
    "ON messages(channel_id, timestamp DESC)",
    # 3. Materialized per-channel score (read by /api/channels and /neighborhood).
    """
    CREATE TABLE IF NOT EXISTS channel_scores (
        channel_id        BIGINT PRIMARY KEY REFERENCES channels(channel_id),
        suspicion         REAL NOT NULL,
        suspicion_lo      REAL,
        suspicion_hi      REAL,
        archetype         TEXT,
        tier              TEXT,
        gate_met          BOOLEAN,
        france_targeting  REAL,
        credibility_prior TEXT,
        payload           JSONB NOT NULL,
        computed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_channel_scores_suspicion "
    "ON channel_scores(suspicion DESC, channel_id)",
    # 4. Queue envelope (single row) — coverage_callout, symmetric_ratio, top_k.
    """
    CREATE TABLE IF NOT EXISTS scores_run_meta (
        id          INT PRIMARY KEY DEFAULT 1,
        envelope    JSONB NOT NULL,
        computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]

DOWNGRADE_STATEMENTS = [
    "DROP TABLE IF EXISTS scores_run_meta",
    "DROP TABLE IF EXISTS channel_scores",
    "DROP INDEX IF EXISTS idx_messages_channel_ts_desc",
    "DROP INDEX IF EXISTS idx_messages_text_notnull",
]


def upgrade() -> None:
    """Add hot-path indexes + the channel_scores / scores_run_meta tables.

    All statements are IF NOT EXISTS — additive and safe on the populated DB.
    """
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Reverse 0004. Drops the materialized score tables + the added indexes."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
