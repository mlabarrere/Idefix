"""mission scoping — add `mission` column to channel_scores + scores_run_meta

Idéfix becomes a generic multi-mission platform ("one engine, N missions" —
scope-change-multi-mission-2026-06-09). The materialized score tables, until now
single-mission, gain a ``mission`` column so each mission's scores can coexist in
the shared tables.

ADDITIVE & SAFE on the populated DB: this migration ONLY adds a column with a
``DEFAULT 'russosphere'`` (the default mission) — it does NOT change primary keys
or constraints, so the existing ``build_scores`` write path
(``ON CONFLICT (channel_id)`` / ``TRUNCATE``) keeps working byte-identically for
the default mission. The composite-PK switch + mission-scoped UPSERT/DELETE
(``DELETE WHERE mission=$1``, never TRUNCATE — risk R5) are wired together with
the ``build_scores`` / ``_read_precomputed_queue`` parameterization in a later
revision, so this one stays a no-behaviour-change schema prepositioning.

A composite index ``(mission, suspicion DESC, channel_id)`` is added for the
future mission-scoped read path; the existing ``idx_channel_scores_suspicion``
is kept (default-mission read path unchanged).

Idempotent: ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# One statement per list entry — the asyncpg dialect rejects multi-statement
# strings (extended/prepared-statement protocol). See 0001_baseline.py note.
UPGRADE_STATEMENTS = [
    "ALTER TABLE channel_scores "
    "ADD COLUMN IF NOT EXISTS mission TEXT NOT NULL DEFAULT 'russosphere'",
    "ALTER TABLE scores_run_meta "
    "ADD COLUMN IF NOT EXISTS mission TEXT NOT NULL DEFAULT 'russosphere'",
    # Future mission-scoped read path (build_scores wiring switches reads to this).
    "CREATE INDEX IF NOT EXISTS idx_channel_scores_mission_suspicion "
    "ON channel_scores(mission, suspicion DESC, channel_id)",
]

DOWNGRADE_STATEMENTS = [
    "DROP INDEX IF EXISTS idx_channel_scores_mission_suspicion",
    "ALTER TABLE scores_run_meta DROP COLUMN IF EXISTS mission",
    "ALTER TABLE channel_scores DROP COLUMN IF EXISTS mission",
]


def upgrade() -> None:
    """Add the ``mission`` column (DEFAULT 'russosphere') + mission-scoped index.

    Additive and safe on the populated DB; does not alter PKs/constraints, so the
    current default-mission write path is unchanged.
    """
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Reverse 0005. Drops the mission column + the mission-scoped index."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
