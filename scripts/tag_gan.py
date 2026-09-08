"""Tag channels with the GAN thematic-targeting score (channels.extra.gan_targeting).

Pipeline (mission GAN, après crawl + build_edges) :
    crawl --mission gan -> build_edges -> tag_gan -> build_scores --mission gan

Calcule ``gan_targeting`` par canal via le ``relevance_scorer`` de la mission GAN
(le moteur ``targeting`` générique sur le lexique GAN) et le **fusionne** dans
``channels.extra`` (MERGE ``||`` — préserve ``fr_score`` et les autres clés ;
cf. mémoire ``loader-clobbers-fr-score``). Lecture/écriture PostgreSQL uniquement,
AUCUN appel Telegram.

Usage :
    python scripts/tag_gan.py
"""
import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

from src.missions.loader import resolve_mission  # noqa: E402


async def main() -> None:
    mission = resolve_mission("gan")
    key = mission.source_universe.snowball_anchor_signal  # "gan_targeting"
    threshold = mission.source_universe.anchor_threshold
    if mission.relevance_scorer is None:  # pragma: no cover - safety
        raise SystemExit("mission GAN sans relevance_scorer")

    conn = await db_connect()
    try:
        scores = await mission.relevance_scorer(conn)  # {channel_id: float}
        n = 0
        for cid, val in scores.items():
            # MERGE (||) — ne clobbe pas fr_score ni les autres clés de extra.
            await conn.execute(
                "UPDATE channels "
                "SET extra = COALESCE(extra, '{}'::jsonb) || $2::jsonb "
                "WHERE channel_id = $1",
                cid,
                json.dumps({key: round(float(val), 4)}),
            )
            n += 1
        flagged = sum(1 for v in scores.values() if v >= threshold)
        print(
            f"Taggé {n} canaux avec '{key}' · {flagged} pertinents GAN "
            f"({key} >= {threshold})"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
