"""channel_llm_scores — persistance de la PISTE PARALLÈLE Mistral

Table dédiée (PAS une sous-clé de ``channels.extra`` ni ``channel_scores``) pour
garder la classification LLM physiquement SÉPARÉE du score de suspicion explicable :
- permet plusieurs lignes (model, prompt_version) par canal → trace d'audit / EIP ;
- évite tout MERGE ``||`` qui collisionnerait avec les scores de mission dans ``extra``.

La clé API n'est JAMAIS une colonne. Provenance conservée : ``model``,
``prompt_version``, ``request_hash`` (clé de cache déterministe), tokens + coût.

PK composite ``(mission, channel_id, model, prompt_version)`` — cohérent avec le
scoping multi-mission introduit en 0005/0006.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS channel_llm_scores (
        mission            TEXT        NOT NULL,
        channel_id         BIGINT      NOT NULL REFERENCES channels(channel_id),
        model              TEXT        NOT NULL,
        prompt_version     TEXT        NOT NULL,
        is_gan_footprint   BOOLEAN,
        is_france_ukraine  BOOLEAN,
        actor_type         TEXT,
        themes             JSONB       NOT NULL DEFAULT '[]'::jsonb,
        confidence         DOUBLE PRECISION,
        rationale          TEXT,
        request_hash       TEXT,
        prompt_tokens      INTEGER     NOT NULL DEFAULT 0,
        completion_tokens  INTEGER     NOT NULL DEFAULT 0,
        est_cost_usd       DOUBLE PRECISION NOT NULL DEFAULT 0,
        computed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT channel_llm_scores_pkey
            PRIMARY KEY (mission, channel_id, model, prompt_version)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_channel_llm_scores_mission "
    "ON channel_llm_scores(mission, channel_id)",
]

DOWNGRADE_STATEMENTS = [
    "DROP INDEX IF EXISTS idx_channel_llm_scores_mission",
    "DROP TABLE IF EXISTS channel_llm_scores",
]


def upgrade() -> None:
    """Crée la table parallèle ``channel_llm_scores`` + son index."""
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Supprime la table parallèle (aucune dépendance du score explicable)."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
