"""baseline — faithful copy of the schema created by scripts/init_db.py

Recreates the four existing tables (channels, messages, episodes,
evidence_dossiers) and their indexes EXACTLY as they exist today, so that
Alembic becomes the single source of truth for the schema on a fresh database.

The DDL below is copied verbatim from scripts/init_db.py (the historical
authority). It uses ``CREATE TABLE IF NOT EXISTS`` / ``CREATE INDEX IF NOT
EXISTS`` so that:

  * on a FRESH database, ``alembic upgrade head`` creates everything;
  * on the EXISTING, already-populated database, the recommended path is
    ``alembic stamp 0001`` (mark as applied WITHOUT running) — but should this
    migration ever run there, the IF NOT EXISTS guards make it a safe no-op.

Transition procedure for the already-populated production/local DB:
    alembic stamp 0001      # record baseline as applied, do NOT recreate tables
    alembic upgrade head    # apply 0002_edges (and any later migration)

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Verbatim from scripts/init_db.py — keep in sync if that file is ever the
# authority again. After this baseline lands, Alembic is the authority.
#
# NOTE: each statement is a SEPARATE list entry. The SQLAlchemy asyncpg dialect
# uses PostgreSQL's extended (prepared-statement) protocol, which rejects
# multiple commands in one execute ("cannot insert multiple commands into a
# prepared statement"). init_db.py got away with a single multi-statement string
# only because it used raw asyncpg (simple query protocol). Under Alembic we must
# emit one statement per op.execute call.
BASELINE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS channels (
        channel_id      BIGINT PRIMARY KEY,
        username        TEXT,
        title           TEXT,
        member_count    INTEGER,
        tier            TEXT NOT NULL DEFAULT 'cold',
        is_in_catalogue BOOLEAN NOT NULL DEFAULT false,
        catalogue_source TEXT,
        first_seen_at   TIMESTAMPTZ,
        last_polled_at  TIMESTAMPTZ,
        extra           JSONB,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_channels_username ON channels(username)",
    "CREATE INDEX IF NOT EXISTS idx_channels_tier     ON channels(tier)",
    """
    CREATE TABLE IF NOT EXISTS messages (
        id                          BIGSERIAL PRIMARY KEY,
        message_id                  BIGINT NOT NULL,
        channel_id                  BIGINT NOT NULL REFERENCES channels(channel_id),
        timestamp                   TIMESTAMPTZ NOT NULL,
        text                        TEXT,
        language                    TEXT,
        forward_from_channel_id     BIGINT,
        forward_from_message_id     BIGINT,
        forward_delay_seconds       INTEGER,
        views                       INTEGER,
        forwards                    INTEGER,
        media_type                  TEXT,
        media_hash                  TEXT,
        urls                        JSONB,
        raw_content                 JSONB,
        is_deleted                  BOOLEAN NOT NULL DEFAULT false,
        deleted_at                  TIMESTAMPTZ,
        created_at                  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(channel_id, message_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_channel_id   ON messages(channel_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_timestamp    ON messages(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_messages_forward_from ON messages(forward_from_channel_id)",
    """
    CREATE TABLE IF NOT EXISTS episodes (
        episode_id          TEXT PRIMARY KEY,
        title               TEXT NOT NULL,
        description         TEXT,
        thematic_category   TEXT NOT NULL,
        target_entity       TEXT NOT NULL DEFAULT 'FR_integrity',
        claim_text          TEXT NOT NULL,
        claim_variants      JSONB,
        source_factchecker  TEXT,
        source_url          TEXT,
        source_date         DATE,
        bge_m3_embedding    JSONB,
        status              TEXT NOT NULL DEFAULT 'active',
        created_at          TIMESTAMPTZ DEFAULT NOW(),
        updated_at          TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_dossiers (
        dossier_id               TEXT PRIMARY KEY,
        episode_id               TEXT NOT NULL REFERENCES episodes(episode_id),
        attribution_tier         TEXT NOT NULL,
        severity_tier            TEXT NOT NULL,
        methodology_version_hash TEXT NOT NULL,
        multi_source_rule_met    BOOLEAN NOT NULL DEFAULT false,
        scores                   JSONB NOT NULL,
        evidence_channels        JSONB,
        coverage_callout         TEXT NOT NULL,
        created_at               TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]

# Drop order respects FK dependencies (dossiers→episodes, messages→channels).
DOWNGRADE_STATEMENTS = [
    "DROP TABLE IF EXISTS evidence_dossiers",
    "DROP TABLE IF EXISTS episodes",
    "DROP TABLE IF EXISTS messages",
    "DROP TABLE IF EXISTS channels",
]


def upgrade() -> None:
    """Create the four baseline tables + indexes (IF NOT EXISTS — idempotent)."""
    for stmt in BASELINE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Drop the four baseline tables. DESTRUCTIVE — never run on populated DB."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
