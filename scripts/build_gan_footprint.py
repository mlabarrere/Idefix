"""Lecteur d'EMPREINTE GAN — auto-évaluation OPSEC (mission GAN).

> Mission GAN (doctrine L2I / OPSEC) : mesurer l'empreinte informationnelle
> OBSERVABLE SUR TELEGRAM du Groupe Aéronaval (*Charles de Gaulle*) pour la
> MINIMISER, et repérer sa captation/amplification par la russosphère.

Ce script ne crawle rien : il lit la base (canaux taggés ``gan_targeting`` par
``tag_gan.py``) et produit un READOUT d'empreinte pour la webapp :

  * **origination** — canaux NON adverses (presse défense / OSINT naval occidental)
    qui parlent du GAN : c'est la source de l'empreinte (à minimiser).
  * **amplification adverse** — canaux russosphère (credibility ``suspect``) qui
    reprennent : la captation à surveiller.
  * **circulation interne** — liens (forward/média/co-forward) ENTRE canaux GAN.
  * **mentions du porte-avions** — volume + échantillons datés + frise mensuelle.

Le côté adverse vient de ``credibility_prior`` (snapshot russosphère, déjà calculé
par le loader). Telegram-only, T1/T2, arm-only. Lecture seule PostgreSQL.

Usage : python scripts/build_gan_footprint.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

_OUT = _REPO / "webapp" / "public" / "data" / "russosphere" / "gan_footprint.json"
_SNAPSHOT = _REPO / "webapp" / "public" / "data" / "russosphere" / "russosphere_snapshot.json"

GAN_MIN = 0.15  # seuil de pertinence GAN (cohérent avec themes.json)
CARRIER_RX = "(charles de gaulle|porte-avions français|porte-avion français|r91|шарль де голль|авианосец|groupe aéronaval)"


def _snip(t: str | None, n: int = 110) -> str:
    return " ".join((t or "").split())[:n]


def _credibility_map() -> dict[int, str]:
    """channel_id -> credibility_prior, depuis le snapshot déjà calculé."""
    if not _SNAPSHOT.exists():
        return {}
    snap = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for c in snap.get("communities", []):
        for ch in c.get("channels", []):
            out[ch["channel_id"]] = ch.get("credibility_prior", "other")
    return out


async def main() -> None:
    conn = await db_connect()
    try:
        cred = _credibility_map()
        rows = await conn.fetch(
            """
            SELECT channel_id, username, title,
                   (extra->>'gan_targeting')::float AS gan,
                   (extra->>'fr_score')::float AS fr
            FROM channels
            WHERE (extra->>'gan_targeting')::float >= $1
            ORDER BY (extra->>'gan_targeting')::float DESC
            """,
            GAN_MIN,
        )
        gan_ids = [r["channel_id"] for r in rows]

        msgcount = {
            r["channel_id"]: r["n"]
            for r in await conn.fetch(
                "SELECT channel_id, count(*) n FROM messages WHERE channel_id = ANY($1) GROUP BY 1",
                gan_ids,
            )
        }

        origination, adverse = [], []
        for r in rows:
            entry = {
                "channel_id": r["channel_id"],
                "username": r["username"],
                "title": r["title"] or "",
                "gan_targeting": round(r["gan"], 3),
                "credibility": cred.get(r["channel_id"], "other"),
                "messages": msgcount.get(r["channel_id"], 0),
            }
            (adverse if entry["credibility"] == "suspect" else origination).append(entry)

        # circulation interne (l'info GAN passe de canal en canal)
        internal = {}
        for et in ("FORWARD", "MEDIA_REUSE", "CO_FORWARD"):
            internal[et.lower()] = await conn.fetchval(
                "SELECT count(*) FROM edges WHERE edge_type=$1 "
                "AND src_channel_id=ANY($2) AND dst_channel_id=ANY($2)",
                et, gan_ids,
            )

        # mentions explicites du porte-avions (toute la base, pas que les GAN-taggés)
        n_mentions = await conn.fetchval(
            f"SELECT count(*) FROM messages WHERE text ~* '{CARRIER_RX}'"
        )
        samples = await conn.fetch(
            f"""
            SELECT ch.username, ch.channel_id, m.timestamp,
                   LEFT(m.text, 160) AS text
            FROM messages m JOIN channels ch ON ch.channel_id = m.channel_id
            WHERE m.text ~* '{CARRIER_RX}' AND m.timestamp IS NOT NULL
            ORDER BY m.timestamp DESC LIMIT 10
            """
        )
        recent = [
            {
                "username": s["username"],
                "credibility": cred.get(s["channel_id"], "other"),
                "ts": s["timestamp"].isoformat(),
                "text": _snip(s["text"]),
            }
            for s in samples
        ]

        # frise mensuelle des mentions
        tl = await conn.fetch(
            f"SELECT date_trunc('month', timestamp) m, count(*) n FROM messages "
            f"WHERE text ~* '{CARRIER_RX}' AND timestamp IS NOT NULL GROUP BY 1 ORDER BY 1"
        )
        timeline = [{"month": r["m"].date().isoformat()[:7], "n": r["n"]} for r in tl]

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_channels": len(rows),
            "n_origination": len(origination),
            "n_adverse": len(adverse),
            "internal_circulation": internal,
            "carrier_mentions": n_mentions,
            "origination": origination[:15],
            "adverse": adverse[:15],
            "recent_mentions": recent,
            "timeline": timeline,
            "coverage_callout": (
                "Empreinte OBSERVABLE SUR TELEGRAM uniquement — non l'empreinte "
                "totale. AIS / Strava / X / presse / satellite peuvent alimenter "
                "Telegram mais ne sont pas collectés ici (cf. cas Strava). "
                "Objectif OPSEC : minimiser cette empreinte. Arm-only, T1/T2."
            ),
        }
        _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        await conn.close()

    print(f"Ecrit : {_OUT}")
    print(f"  empreinte GAN : {payload['n_channels']} canaux "
          f"({payload['n_origination']} origination / {payload['n_adverse']} adverse)")
    print(f"  circulation interne : {internal}")
    print(f"  mentions porte-avions : {n_mentions}")


if __name__ == "__main__":
    asyncio.run(main())
