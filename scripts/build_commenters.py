"""Surface les COMMENTATEURS des groupes de discussion liés (table ``comments``).

> Décision Micky 2026-06-10 : le graphe est canal-centrique et ignore les
> *utilisateurs* (membres/commentateurs). On a déjà 9241 commentaires captés par
> ``enrich_recrawl.py`` (groupes de discussion publics liés aux canaux) mais ils
> n'apparaissent nulle part. Étape intermédiaire (sans nouveau crawl, sans
> modéliser des nœuds-utilisateurs) : on agrège par canal et on expose
> l'engagement de discussion + les commentateurs récurrents dans le drawer.

OFFLINE PUR : lit ``comments`` (PostgreSQL), écrit
``webapp/public/data/<mission>/commenters.json``. Aucun appel Telegram.

⚠ RGPD : ces commentateurs sont des identifiants publics Telegram. Exposition
assumée (décision MinArm 2026-06-10, déploiement public). Le texte des
commentaires N'EST PAS exporté ici — seulement l'agrégat (compte + handle/id).

Usage : python scripts/build_commenters.py [--mission russosphere]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

from src.missions.registry import DEFAULT_MISSION  # noqa: E402

_WEBAPP_DATA = _REPO / "webapp" / "public" / "data"


async def main() -> None:
    ap = argparse.ArgumentParser(description="Agrège les commentateurs par canal.")
    ap.add_argument("--mission", default=None)
    args = ap.parse_args()
    mission = args.mission or DEFAULT_MISSION
    out_dir = _WEBAPP_DATA / mission
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = await db_connect()
    try:
        rows = await conn.fetch(
            "SELECT channel_id, commenter_id, commenter_username FROM comments"
        )
    finally:
        await conn.close()

    # par canal : compte total, commentateurs distincts, top commentateurs récurrents
    per_chan: dict[int, dict] = defaultdict(lambda: {"n": 0, "by_user": defaultdict(int), "names": {}})
    for r in rows:
        cid = r["channel_id"]
        uid = r["commenter_id"]
        d = per_chan[cid]
        d["n"] += 1
        d["by_user"][uid] += 1
        if r["commenter_username"]:
            d["names"][uid] = r["commenter_username"]

    channels: dict[str, dict] = {}
    for cid, d in per_chan.items():
        top = sorted(d["by_user"].items(), key=lambda kv: -kv[1])[:12]
        channels[str(cid)] = {
            "n_comments": d["n"],
            "n_commenters": len(d["by_user"]),
            "top": [
                {"id": uid, "username": d["names"].get(uid), "count": cnt}
                for uid, cnt in top
            ],
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": mission,
        "n_channels": len(channels),
        "note": (
            "Commentateurs des groupes de discussion liés (engagement observable). "
            "Le graphe reste canal-centrique : ceci est une couche d'engagement, "
            "pas une modélisation des utilisateurs. Texte des commentaires non exporté."
        ),
        "channels": channels,
    }
    path = out_dir / "commenters.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(c["n_comments"] for c in channels.values())
    print(f"Écrit : {path} · {len(channels)} canaux · {total} commentaires agrégés")


if __name__ == "__main__":
    asyncio.run(main())
