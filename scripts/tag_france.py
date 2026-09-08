"""Tag every backfilled channel with a crude France-relevance score (parameterized, safe).
Axiom #1: tag, don't filter. Stored in channels.extra.fr_score."""
import asyncio
import json
import re

from src.shared.db import db_connect
from dotenv import load_dotenv

load_dotenv()

from src.missions.russosphere import FR_KEYWORDS_ELECTORAL as FR_KW  # noqa: E402

async def main():
    conn = await db_connect()
    pattern = "|".join(re.escape(k) for k in FR_KW)
    # Un seul passage : total messages + hits mots-clés FR par canal, agrégés
    # côté SQL (remplace ~1600 requêtes séquentielles). Sémantique identique à
    # l'ancienne version : total = TOUS les messages du canal, hits = ceux dont
    # le texte matche un mot-clé FR (text NULL ne matche pas ~*). fr = hits/total.
    rows = await conn.fetch(
        """
        SELECT m.channel_id,
               COALESCE(c.username, c.title) AS name,
               COUNT(*)                              AS total,
               COUNT(*) FILTER (WHERE m.text ~* $1)  AS hits
        FROM messages m
        JOIN channels c ON c.channel_id = m.channel_id
        GROUP BY m.channel_id, c.username, c.title
        """,
        pattern,
    )
    tagged = []
    for r in rows:
        total = r["total"]
        if not total:
            continue
        fr = round(r["hits"] / total, 3)
        # MERGE (||) : ne touche que fr_score/msg_sampled, préserve les autres
        # clés éventuelles d'``extra`` (ne PAS écraser tout l'objet).
        await conn.execute(
            "UPDATE channels "
            "SET extra = COALESCE(extra, '{}'::jsonb) || $2::jsonb "
            "WHERE channel_id = $1",
            r["channel_id"], json.dumps({"fr_score": fr, "msg_sampled": total}),
        )
        tagged.append((r["name"], fr, total))
    await conn.close()
    print(f"{len(tagged)} canaux taggés\n")
    for name, fr, total in sorted(tagged, key=lambda x: -x[1]):
        flag = "  <== FRANCE-PERTINENT" if fr >= 0.15 else ""
        print(f"  fr={fr:<5} ({total:3d} msgs) {str(name)[:32]}{flag}")

asyncio.run(main())
