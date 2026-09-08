"""channel_scores.gate_families — traçabilité du verrou multi-source

Le verrou multi-source (``≥ N familles distinctes déclenchées``) ne stockait
que le booléen ``gate_met``. Cette révision AJOUTE ``gate_families TEXT[]`` :
la liste des familles qui ont DÉCLENCHÉ (le même ensemble que ``gate_met``
compte), surfacée par noms pour l'audit/traçabilité (EIP). Additif et nullable
— ``gate_met`` est conservé inchangé (compat).

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_STATEMENTS = [
    "ALTER TABLE channel_scores ADD COLUMN IF NOT EXISTS gate_families TEXT[]",
]

DOWNGRADE_STATEMENTS = [
    "ALTER TABLE channel_scores DROP COLUMN IF EXISTS gate_families",
]


def upgrade() -> None:
    """Ajoute la colonne ``gate_families`` (text[], nullable)."""
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Supprime la colonne ``gate_families``."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
