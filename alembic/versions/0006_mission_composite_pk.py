"""mission scoping (suite) — composite primary keys for multi-mission materialization

Suite de 0005 (qui a AJOUTÉ la colonne ``mission``). Cette révision bascule les
clés primaires pour que PLUSIEURS missions coexistent réellement dans les tables
de scores partagées :

  * ``channel_scores`` : PK ``(channel_id)`` -> ``(mission, channel_id)``
    (un même canal peut porter un score dans plusieurs missions).
  * ``scores_run_meta`` : PK ``(id)`` -> ``(mission)`` (une enveloppe par mission).

Couplé au câblage ``scripts/build_scores.py`` (``--mission``, ``DELETE WHERE
mission=$1`` au lieu de ``TRUNCATE`` — risque R5) et à ``channel_suspicion.
_read_precomputed_queue`` (``WHERE mission=$1``). La mission par défaut reste
``russosphere`` (lignes historiques portées par le DEFAULT de 0005), donc le
chemin par défaut lit/écrit exactement les mêmes lignes qu'avant.

Révision gérée par alembic (pas de re-application) : ``DROP CONSTRAINT IF EXISTS``
puis ``ADD CONSTRAINT`` sur un seul passage.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_STATEMENTS = [
    "ALTER TABLE channel_scores DROP CONSTRAINT IF EXISTS channel_scores_pkey",
    "ALTER TABLE channel_scores "
    "ADD CONSTRAINT channel_scores_pkey PRIMARY KEY (mission, channel_id)",
    "ALTER TABLE scores_run_meta DROP CONSTRAINT IF EXISTS scores_run_meta_pkey",
    "ALTER TABLE scores_run_meta "
    "ADD CONSTRAINT scores_run_meta_pkey PRIMARY KEY (mission)",
]

DOWNGRADE_STATEMENTS = [
    "ALTER TABLE scores_run_meta DROP CONSTRAINT IF EXISTS scores_run_meta_pkey",
    "ALTER TABLE scores_run_meta ADD CONSTRAINT scores_run_meta_pkey PRIMARY KEY (id)",
    "ALTER TABLE channel_scores DROP CONSTRAINT IF EXISTS channel_scores_pkey",
    "ALTER TABLE channel_scores ADD CONSTRAINT channel_scores_pkey PRIMARY KEY (channel_id)",
]


def upgrade() -> None:
    """Bascule les PK vers ``(mission, channel_id)`` et ``(mission)``."""
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Revient aux PK mono-mission ``(channel_id)`` / ``(id)``."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
