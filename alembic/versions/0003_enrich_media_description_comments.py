"""enrich — exact media id, channel bio, and public-group commenters

Additive enrichment of the ingestion layer so the re-crawl pass captures three
new data points WITHOUT any schema rewrite:

  1. messages.media_hash now carries the Telegram ``file_unique_id`` of the
     attached media (photo / video / document / animation / audio / voice). This
     is a STABLE, cross-message identifier obtained WITHOUT downloading the file
     — Telegram guarantees the same file_unique_id for the same underlying media
     across forwards and re-uploads. We REUSE the existing ``media_hash`` column
     (rather than adding ``media_unique_id``) to keep the schema minimal: the
     column was always meant to hold "the thing that identifies the media", and
     file_unique_id is exactly that for the no-download PoC. A real perceptual
     hash (pHash/dHash) is deferred (media_reuse edges are deferred too — see
     graph-model §2.3). An index on media_hash is added so the future
     MEDIA_REUSE extractor can group identical media in one indexed scan.

  2. channels.description holds the channel bio (``chat.description``). Useful for
     the France thematic filter and for catalogue review. Added only IF the
     column is absent (a previous hand-patch may already have created it); if it
     somehow exists this migration is a no-op for that column.

  3. comments — a NEW table logging individual commenters of PUBLIC discussion
     groups linked to monitored channels.

     RGPD SCOPE DECISION (validated by Micky, 2026-06-05) — load-bearing:
       We deliberately collect INDIVIDUAL commenters (commenter_id +
       commenter_username) of PUBLIC linked discussion groups. This is a
       collection of personal data of natural persons, NOT only channel-admin
       publishers. Legal basis: public-interest mission (docs/method/07-tiers-and-governance.md §7.3, RGPD
       Art. 6.1.e, loi 2024-850). It is justified by the downstream need to
       derive co-commenter coordination edges (the same accounts commenting in
       lockstep across channels is a coordination signal). Constraints that
       still apply and MUST be honoured by any consumer of this table:
         * public groups only (no private content, no DM, no member scraping);
         * retention bounds and access journal per docs/method/07-tiers-and-governance.md §7.3 (13/36 months);
         * minimization — store id + username + comment text + timestamp, NOTHING
           that links the account to a real person without a separate legal basis;
         * deletion propagation (a deleted comment must be deletable here too).
       This table is the ONLY place in Idéfix that logs non-admin individuals;
       treat it as the sensitive surface and review it in the RGPD NFR audit.

Idempotent: every statement uses IF NOT EXISTS (table / index / column add via a
guarded DO block), so on the existing populated DB this migration is safe to run
or to stamp.

Transition procedure for the already-populated local DB:
    alembic upgrade head    # applies 0003 additively (IF NOT EXISTS guards)
  (or, if you prefer to record without running because you hand-applied it:)
    alembic stamp 0003

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# One statement per list entry — the asyncpg dialect rejects multi-statement
# strings (extended/prepared-statement protocol). See 0001_baseline.py note.
UPGRADE_STATEMENTS = [
    # 1. media_hash now stores file_unique_id; index it for the MEDIA_REUSE scan.
    "CREATE INDEX IF NOT EXISTS idx_messages_media_hash ON messages(media_hash)",
    # 2. channel bio. ADD COLUMN IF NOT EXISTS is supported by PostgreSQL 9.6+.
    "ALTER TABLE channels ADD COLUMN IF NOT EXISTS description TEXT",
    # 3. commenters of public linked discussion groups (see RGPD note above).
    """
    CREATE TABLE IF NOT EXISTS comments (
        id                  BIGSERIAL PRIMARY KEY,
        channel_id          BIGINT NOT NULL,
        message_id          BIGINT NOT NULL,
        commenter_id        BIGINT,
        commenter_username  TEXT,
        text                TEXT,
        timestamp           TIMESTAMPTZ,
        created_at          TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(channel_id, message_id, commenter_id, timestamp)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_comments_channel_id ON comments(channel_id)",
    "CREATE INDEX IF NOT EXISTS idx_comments_commenter  ON comments(commenter_id)",
]

# Drop order is independent here (comments has no FK; index/column drops are safe).
DOWNGRADE_STATEMENTS = [
    "DROP TABLE IF EXISTS comments",
    "ALTER TABLE channels DROP COLUMN IF EXISTS description",
    "DROP INDEX IF EXISTS idx_messages_media_hash",
]


def upgrade() -> None:
    """Add media_hash index, channels.description, and the comments table.

    All statements are IF NOT EXISTS — additive and safe on the populated DB.
    """
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Reverse 0003. Dropping comments DELETES collected commenter data."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
