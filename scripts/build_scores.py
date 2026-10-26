"""Matérialise les scores de suspicion PAR CANAL dans PostgreSQL.

Brique de pipeline (à lancer APRÈS un crawl + ``build_edges.py``, AVANT que
l'API ne serve) :

    crawl -> build_edges.py -> build_scores.py -> analyze_communities.py
                                     ^ ICI

Calcule UNE fois, hors du chemin de requête, ce que l'API recomputait à la volée
(france_targeting sur tous les messages + projection forward + eigenvector +
coordination + récidivisme), et l'écrit dans :
  * ``channel_scores`` : 1 ligne / (mission, canal) (``suspicion`` indexée pour le top_k,
    ``archetype`` pour le voisinage, ``payload`` = objet canal exact du contrat) ;
  * ``scores_run_meta`` : 1 ligne / mission (enveloppe : coverage_callout, symmetric_ratio).

L'API (``build_channel_queue``) lit ensuite ce précalculé (quasi instantané) et
ne recalcule en LIVE que si la table est vide. Réutilise ``compute_channel_queue``
via ``_build_channel_queue_live(top_k=None)`` (= univers complet, sans troncature).

Lecture/écriture PostgreSQL uniquement — AUCUN appel Telegram. Idempotent par
mission (``DELETE … WHERE mission = $1`` + réécriture, dans une transaction).

Usage :
    python scripts/build_scores.py
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.scorer.channel_suspicion import _build_channel_queue_live  # noqa: E402

# Scopé par mission (alembic 0005/0006 : colonne ``mission`` + PK composite).
_UPSERT = """
INSERT INTO channel_scores (
    mission, channel_id, suspicion, suspicion_lo, suspicion_hi, archetype, tier,
    gate_met, gate_families, france_targeting, credibility_prior, payload, computed_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW())
ON CONFLICT (mission, channel_id) DO UPDATE SET
    suspicion         = EXCLUDED.suspicion,
    suspicion_lo      = EXCLUDED.suspicion_lo,
    suspicion_hi      = EXCLUDED.suspicion_hi,
    archetype         = EXCLUDED.archetype,
    tier              = EXCLUDED.tier,
    gate_met          = EXCLUDED.gate_met,
    gate_families     = EXCLUDED.gate_families,
    france_targeting  = EXCLUDED.france_targeting,
    credibility_prior = EXCLUDED.credibility_prior,
    payload           = EXCLUDED.payload,
    computed_at       = NOW()
"""


def _record(mission_name: str, c: dict) -> tuple:
    """Objet canal (contrat queue) -> tuple de colonnes channel_scores (mission-scopé)."""
    susp = c["suspicion"]
    ft = c.get("france_targeting")
    return (
        mission_name,
        c["channel_id"],
        float(susp["v"]),
        float(susp.get("lo", 0.0)),
        float(susp.get("hi", 0.0)),
        c.get("archetype"),
        c.get("tier"),
        bool((c.get("gate") or {}).get("met")),
        (c.get("gate") or {}).get("gate_families"),  # text[] : asyncpg accepte une list[str]
        float(ft) if isinstance(ft, (int, float)) else None,
        c.get("credibility_prior"),
        json.dumps(c),
    )


async def main(mission_name: str | None = None, compute_embeddings: bool = False) -> None:
    mission = resolve_mission(mission_name)  # None -> russosphère (défaut)
    conn = await db_connect()
    try:
        t = time.perf_counter()
        # Univers complet, scoré selon le profil de la mission.
        # compute_embeddings=True => famille (f) sémantique activée (Phase 1).
        queue = await _build_channel_queue_live(
            conn, top_k=None, mission=mission, compute_embeddings=compute_embeddings
        )
        channels = queue["channels"]
        records = [_record(mission.name, c) for c in channels]
        envelope = json.dumps(
            {
                "coverage_callout": queue["coverage_callout"],
                "symmetric_ratio": queue["symmetric_ratio"],
            }
        )
        async with conn.transaction():
            # DELETE WHERE mission (JAMAIS TRUNCATE — n'efface pas les autres
            # missions ; risque R5).
            await conn.execute(
                "DELETE FROM channel_scores WHERE mission = $1", mission.name
            )
            if records:
                await conn.executemany(_UPSERT, records)
            await conn.execute(
                "DELETE FROM scores_run_meta WHERE mission = $1", mission.name
            )
            await conn.execute(
                "INSERT INTO scores_run_meta (mission, envelope, computed_at) "
                "VALUES ($1, $2::jsonb, NOW())",
                mission.name,
                envelope,
            )
        dt = time.perf_counter() - t
        susp_max = max((float(c["suspicion"]["v"]) for c in channels), default=0.0)
        print(
            f"[{mission.name}] Matérialisé {len(channels)} canaux en {dt:.1f}s · "
            f"suspicion max {susp_max:.3f} · ratio_adv "
            f"{queue['symmetric_ratio']['adversary_infra']}"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(
        description="Matérialise channel_scores + scores_run_meta (post build_edges), "
        "scopé par mission."
    )
    add_mission_arg(_ap)
    _ap.add_argument(
        "--embeddings",
        action="store_true",
        help="Calcule famille (f) sémantique via embeddings (Phase 1). Coût : ~30s/1000 canaux.",
    )
    _args = _ap.parse_args()
    asyncio.run(main(_args.mission, compute_embeddings=_args.embeddings))
