"""edges — materialize the channel-centric multiplex graph

Creates the ``edges`` table, the persistent projection of the multiplex
channel-centric graph defined in
``_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md`` §2.3
(SOURCE OF TRUTH for the edge model). Until now the FORWARD graph was recomputed
on the fly from ``messages``; this table persists ALL edge families.

Edge families / types supported (graph-model §2.3):
  Propagation   FORWARD       directed  origin -> relayer (channel->channel)
  Influence     MENTIONS      directed  channel -> channel
                CITES_DOMAIN  directed  channel -> domain
  Coordination  CO_FORWARD    undirected, time-windowed (delta t)
  (windowed)    COPYPASTA     undirected, time-windowed (delta t) [a.k.a. TEXT_SIM]
                CO_URL        undirected, time-windowed (delta t), carries a domain
                MEDIA_REUSE   undirected, time-windowed (delta t)

Design decisions (documented inline so a cold reader understands the model):

  * An edge targets EITHER another channel (dst_channel_id) OR a web domain
    (dst_domain), never both, never neither -- enforced by
    ck_edges_exactly_one_dst. CITES_DOMAIN always targets a domain. CO_URL pairs
    two channels (dst_channel_id) and records the shared domain in ``attrs``.

  * UNIQUENESS for aggregated upsert. We want one row per
    (src, dst, edge_type) so the extractor can UPSERT an aggregated edge
    (incrementing ``count`` / refreshing ``weight``). PostgreSQL treats NULLs as
    DISTINCT in a normal UNIQUE constraint, so a plain
    UNIQUE(src_channel_id, dst_channel_id, dst_domain, edge_type) would allow
    duplicate channel->domain edges (dst_channel_id is NULL on every one of them
    and NULL != NULL). We therefore use a UNIQUE INDEX over COALESCE expressions
    that fold the unused target into sentinel values, making the key
    deterministic regardless of which target column is NULL:
        UNIQUE (src_channel_id,
                COALESCE(dst_channel_id, -1),
                COALESCE(dst_domain, ''),
                edge_type)
    (a Telegram channel_id is never -1, '' is never a real domain.)

  * COORDINATION edges are undirected pairs but stored as a single row using the
    extractor's own canonical ordering (e.g. src_channel_id < dst_channel_id).
    That convention lives in the extractor, not the schema; the schema only
    guarantees one row per ordered (src, dst, type) key.

  * delta-t window: stored as BOTH a scalar ``window_delta_seconds`` (the
    tightness of the coordination -- the load-bearing discriminator per
    graph-model §2.3.2) AND optional explicit ``window_start`` / ``window_end``
    for auditability. Extractors may fill either or both.

  * FK to channels(channel_id) on src and dst keeps the graph referentially
    sound with existing data; dst_domain is free text (the domain layer has no
    table yet -- graph-model §2.2 keeps domains as a node TYPE, not a table).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# One statement per list entry — the asyncpg dialect rejects multi-statement
# strings (extended/prepared-statement protocol). See 0001_baseline.py note.
CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS edges (
        id                    BIGSERIAL PRIMARY KEY,

        -- endpoints ----------------------------------------------------------
        src_channel_id        BIGINT NOT NULL REFERENCES channels(channel_id),
        dst_channel_id        BIGINT REFERENCES channels(channel_id),  -- channel target
        dst_domain            TEXT,                                    -- domain target

        -- typing -------------------------------------------------------------
        edge_type             TEXT NOT NULL,   -- FORWARD | MENTIONS | CITES_DOMAIN
                                               -- | CO_FORWARD | COPYPASTA | CO_URL
                                               -- | MEDIA_REUSE

        -- aggregated weight --------------------------------------------------
        count                 INTEGER NOT NULL DEFAULT 1,  -- occurrences aggregated
        weight                REAL,                        -- optional derived weight

        -- per-family attributes ----------------------------------------------
        delay_seconds         INTEGER,   -- FORWARD: forward delay (min/agg)
        text_sim              REAL,      -- COPYPASTA/TEXT_SIM: similarity score

        -- coordination delta-t window (graph-model §2.3.2) -------------------
        window_delta_seconds  INTEGER,        -- tightness of the coordination window
        window_start          TIMESTAMPTZ,    -- optional explicit window bounds
        window_end            TIMESTAMPTZ,

        -- catch-all (shared domain for CO_URL, phash for MEDIA_REUSE, # common
        -- forward origins for CO_FORWARD, etc.) ------------------------------
        attrs                 JSONB,

        created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        -- exactly one target endpoint must be set ----------------------------
        CONSTRAINT ck_edges_exactly_one_dst CHECK (
            (dst_channel_id IS NOT NULL)::int + (dst_domain IS NOT NULL)::int = 1
        )
    )
    """,
    # Aggregated-edge upsert key. COALESCE folds the unused target into a
    # sentinel so NULLs do not defeat uniqueness (see migration docstring).
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_edges_src_dst_type ON edges (
        src_channel_id,
        COALESCE(dst_channel_id, -1),
        COALESCE(dst_domain, ''),
        edge_type
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_edges_src         ON edges(src_channel_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_dst_channel ON edges(dst_channel_id)",
    "CREATE INDEX IF NOT EXISTS idx_edges_type        ON edges(edge_type)",
    "CREATE INDEX IF NOT EXISTS idx_edges_dst_domain  ON edges(dst_domain)",
]


def upgrade() -> None:
    """Create the multiplex graph ``edges`` table + indexes (additive, safe)."""
    for stmt in CREATE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Drop the ``edges`` table (indexes dropped with the table)."""
    op.execute("DROP TABLE IF EXISTS edges")
