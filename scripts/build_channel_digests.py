"""Construit un digest par canal actif pour la labellisation NIVEAU CANAL (nouvelle
méthode : on classe le canal — propagateur / légitime / mixte — pas le message).

Pour chaque canal actif (>= --min-msgs messages), produit :
  - stats : volume, fenêtre temporelle, % messages anti-France, crédibilité a priori
  - comportement de forward : DE QUI il re-forwarde (signal clé de propagation),
    QUI le re-forwarde
  - échantillons : messages anti-France représentatifs (le contenu qui décide du label)

Sorties (data/annotations/) :
  channel_digests.jsonl  — structuré (un objet par canal) pour le juge LLM
  channel_digests.md     — lisible par Micky

Lecture seule PostgreSQL. Aucun appel Telegram/réseau. Library-first.

Usage : python scripts/build_channel_digests.py [--min-msgs 50] [--samples 5]
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.shared.db import db_connect
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.labeling import io  # noqa: E402

from src.missions.russosphere import FR_KEYWORDS_ELECTORAL as FR_KW  # noqa: E402
_FRP = re.compile("|".join(re.escape(k) for k in FR_KW), re.IGNORECASE)
LEGIT = {"france24_fr", "rfi_fr", "actu17", "mediavenir", "euronewsfr", "alertefr", "neodia"}


def credibility(username: str | None, fr: float | None) -> str:
    if (username or "").lower() in LEGIT:
        return "legit"
    if fr is not None and fr < 0.15:
        return "suspect"
    return "other"


def _name(meta: dict, cid: int) -> str:
    m = meta.get(cid, {})
    return ("@" + m["username"]) if m.get("username") else (m.get("title") or f"id={cid}")


async def build(min_msgs: int, n_samples: int) -> list[dict]:
    conn = await db_connect()
    chans = await conn.fetch(
        "SELECT channel_id, username, title, member_count, "
        "(extra->>'fr_score')::float fr FROM channels"
    )
    msgs = await conn.fetch(
        """SELECT channel_id, message_id, text, timestamp, forward_from_channel_id fwd
           FROM messages WHERE is_deleted=false ORDER BY timestamp"""
    )
    await conn.close()

    meta = {
        r["channel_id"]: {
            "username": r["username"],
            "title": r["title"],
            "fr": r["fr"],
            "members": r["member_count"],
        }
        for r in chans
    }
    by_chan: dict[int, list] = defaultdict(list)
    for m in msgs:
        by_chan[m["channel_id"]].append(m)

    # forward edges
    fwd_from = defaultdict(lambda: defaultdict(int))  # chan -> {origin: n}
    fwd_by = defaultdict(lambda: defaultdict(int))  # chan -> {reposter: n}
    for m in msgs:
        o = m["fwd"]
        if o and o != m["channel_id"]:
            fwd_from[m["channel_id"]][o] += 1
            fwd_by[o][m["channel_id"]] += 1

    digests = []
    for cid, ms in by_chan.items():
        if len(ms) < min_msgs:
            continue
        texts = [m for m in ms if m["text"]]
        france = [m for m in texts if _FRP.search(m["text"])]
        ts = [m["timestamp"] for m in ms if m["timestamp"]]
        u = meta[cid].get("username")
        fr = meta[cid].get("fr")
        # who it forwards FROM (top origins) with their credibility
        froms = sorted(fwd_from[cid].items(), key=lambda kv: -kv[1])[:5]
        forwards_from = [
            {
                "channel": _name(meta, o),
                "n": n,
                "credibility": credibility(
                    meta.get(o, {}).get("username"), meta.get(o, {}).get("fr")
                ),
            }
            for o, n in froms
        ]
        bys = sorted(fwd_by[cid].items(), key=lambda kv: -kv[1])[:5]
        forwarded_by = [{"channel": _name(meta, r), "n": n} for r, n in bys]
        # representative anti-France samples (longest = most substantive)
        samples = [
            re.sub(r"\s+", " ", m["text"]).strip()[:280]
            for m in sorted(france, key=lambda m: -len(m["text"]))[:n_samples]
        ]
        digests.append(
            {
                "channel_id": cid,
                "channel": _name(meta, cid),
                "members": meta[cid].get("members"),
                "fr_score": round(fr, 3) if fr is not None else None,
                "credibility_prior": credibility(u, fr),
                "n_messages": len(ms),
                "window": (f"{min(ts).date()} → {max(ts).date()}" if ts else None),
                "n_france_targeting": len(france),
                "pct_france": round(100 * len(france) / max(len(texts), 1), 1),
                "forwards_from": forwards_from,
                "forwarded_by": forwarded_by,
                "samples_france": samples,
                # to be filled by the judge:
                "label": None,  # propagateur | legitime | mixte
                "confidence": None,
                "rationale": None,
                "sources": [],
            }
        )
    digests.sort(key=lambda d: (d["credibility_prior"] != "suspect", -d["n_france_targeting"]))
    return digests


def to_markdown(digests: list[dict]) -> str:
    out = [
        "# Digests canaux — labellisation niveau canal\n",
        f"_{len(digests)} canaux actifs · généré le {date.today().isoformat()}_\n",
        "Label attendu par canal : **propagateur** / **legitime** / **mixte** "
        "(sourcé fact-check, pas position graphe).\n",
    ]
    for d in digests:
        out.append(f"\n## {d['channel']}  ·  a priori: {d['credibility_prior']}\n")
        out.append(
            f"- fr_score={d['fr_score']} · membres={d['members']} · messages={d['n_messages']} "
            f"· fenêtre={d['window']}\n"
        )
        out.append(f"- anti-France: {d['n_france_targeting']} msgs ({d['pct_france']}%)\n")
        if d["forwards_from"]:
            ff = "; ".join(
                f"{x['channel']}({x['n']},{x['credibility']})" for x in d["forwards_from"]
            )
            out.append(f"- **re-forwarde DE** : {ff}\n")
        if d["forwarded_by"]:
            fb = "; ".join(f"{x['channel']}({x['n']})" for x in d["forwarded_by"])
            out.append(f"- re-forwardé PAR : {fb}\n")
        out.append("- échantillons anti-France :\n")
        for s in d["samples_france"]:
            out.append(f"  - {s!r}\n")
    return "".join(out)


async def main(min_msgs: int, n_samples: int) -> None:
    load_dotenv()
    digests = await build(min_msgs, n_samples)
    io.ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    io.write_jsonl(io.ANNOTATIONS_DIR / "channel_digests.jsonl", digests)
    (io.ANNOTATIONS_DIR / "channel_digests.md").write_text(to_markdown(digests), encoding="utf-8")
    print(f"{len(digests)} digests canaux écrits :")
    print(f"  {io.ANNOTATIONS_DIR / 'channel_digests.jsonl'}")
    print(f"  {io.ANNOTATIONS_DIR / 'channel_digests.md'}")
    cred = defaultdict(int)
    for d in digests:
        cred[d["credibility_prior"]] += 1
    print(f"a priori crédibilité : {dict(cred)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Digests canaux pour labellisation niveau canal.")
    ap.add_argument("--min-msgs", type=int, default=50, help="Seuil de messages pour 'canal actif'")
    ap.add_argument(
        "--samples", type=int, default=5, help="Nb d'échantillons anti-France par canal"
    )
    args = ap.parse_args()
    asyncio.run(main(args.min_msgs, args.samples))
