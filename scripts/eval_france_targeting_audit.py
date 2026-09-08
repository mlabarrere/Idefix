"""Exp 4 — Audit de précision du périmètre « France » (Q7) : classification robuste
ou heuristique lexicale fragile ?

france_targeting est un LEXIQUE (pas un classifieur). Cette expérience échantillonne
des canaux par bande de score, re-score leurs messages les plus France-ciblants via
``score_france_targeting`` et fait REMONTER les TERMES qui ont matché + le texte —
pour qu'un humain juge : ciblage SUBSTANTIEL de la France vs mention INCIDENTE.

Nécessite la DB (texte des messages ; cf. docs/ops-runbook.md §1). READ-ONLY DB.
Écrit data/eval/france_targeting_audit.json (matériel à labelliser).
Usage : python scripts/eval_france_targeting_audit.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

import _eval_common as ev  # noqa: E402
from src.normalizer.france_targeting import score_france_targeting  # noqa: E402

BANDS = [("high", 0.5, 1.01), ("mid", 0.25, 0.5), ("low", 0.0001, 0.25)]
PER_BAND = 10
MSG_PER_CHANNEL = 60   # messages tirés en DB par canal
TOP_MSG = 4            # meilleurs messages France gardés comme preuve


def _sample(channels: list[dict], lo: float, hi: float, n: int) -> list[dict]:
    band = sorted(
        [c for c in channels if lo <= (c.get("france_targeting") or 0.0) < hi],
        key=lambda c: c.get("france_targeting") or 0.0, reverse=True,
    )
    if len(band) <= n:
        return band
    step = len(band) / n  # échantillon réparti sur la bande (déterministe)
    return [band[int(i * step)] for i in range(n)]


async def main() -> None:
    ch = ev.load_channels()["channels"]
    conn = await db_connect()
    out_bands = {}
    try:
        for label, lo, hi in BANDS:
            sample = _sample(ch, lo, hi, PER_BAND)
            audited = []
            for c in sample:
                rows = await conn.fetch(
                    "SELECT text, language FROM messages "
                    "WHERE channel_id=$1 AND text IS NOT NULL AND length(text)>20 "
                    "ORDER BY length(text) DESC LIMIT $2",
                    c["channel_id"], MSG_PER_CHANNEL,
                )
                scored = []
                for r in rows:
                    res = score_france_targeting(r["text"], r["language"])
                    if res.score > 0:
                        scored.append((res.score, res.evidence.get("matched_terms", {}), r["text"]))
                scored.sort(key=lambda x: x[0], reverse=True)
                audited.append({
                    "username": c.get("username"),
                    "title": (c.get("title") or "")[:70],
                    "channel_ft_score": round(c.get("france_targeting") or 0.0, 3),
                    "n_messages_scanned": len(rows),
                    "n_messages_france_hit": len(scored),
                    "top_messages": [
                        {"msg_ft": round(s, 3), "matched_terms": mt,
                         "text": " ".join(t.split())[:240]}
                        for s, mt, t in scored[:TOP_MSG]
                    ],
                    "verdict_humain": "?? (substantiel / incident / mixte)",
                })
            out_bands[label] = audited
    finally:
        await conn.close()

    report = {
        "experiment": "france_targeting_precision_audit",
        "method": "Échantillon par bande de france_targeting ; re-score des messages via "
                  "score_france_targeting ; les TERMES matchés + le texte sont à juger : "
                  "ciblage substantiel de la France vs mention incidente.",
        "falsify_rule": "FALSIFIÉ (lexique fragile) si précision bande HAUTE (ft≥0.5) < 0.70, "
                        "i.e. ≥3/10 canaux haut-score portés par des mentions incidentes.",
        "human_step_required": True,
        "bands": out_bands,
    }
    p = ev.write_report("france_targeting_audit.json", report)
    print(f"[Exp4 audit France] matériel écrit -> {p}")
    for label, _, _ in BANDS:
        aud = out_bands.get(label, [])
        print(f"  bande {label:4}: {len(aud)} canaux échantillonnés")
        for a in aud[:3]:
            terms = sorted({t for mt in a["top_messages"] for cat in mt["matched_terms"].values() for t in cat})
            print(f"    @{a['username']:22} ft={a['channel_ft_score']:.2f} | termes: {', '.join(terms[:8])}")


if __name__ == "__main__":
    asyncio.run(main())
