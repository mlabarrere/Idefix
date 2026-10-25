"""Extrait les traces de POROSITÉ russo-sphère -> extrême droite FR (1re étape).

> Objectif (cadrage Micky) : montrer comment un contenu venu de la russo-sphère
> est REPRIS/transformé côté souverainiste-identitaire français. Le lien n'est
> jamais un repost direct de message ; les meilleurs signaux sont, dans l'ordre :
>   1. RÉUTILISATION MÉDIA — un hash média (file_unique_id) qui apparaît d'abord
>      côté russo-sphère puis réapparaît côté FR (langue-indépendant : une image
>      n'a pas besoin de traduction). + VÉLOCITÉ = délai 1re apparition -> reprise.
>   2. THÈME france_targeting — l'apparat russe attaque la France (institutions /
>      armée / élections) en russe/anglais (fr_score≈0) ; l'extrême droite FR
>      porte le même thème en français. Pont thématique TRANS-LANGUE.
>   3. DOMAINE ADVERSE co-cité des deux côtés (ex. arktos.com, l'éditeur de
>      Douguine) — porosité d'infrastructure (signal ténu, donné en appoint).

Le « côté » d'un canal est dérivé de ``fr_score`` (densité lexicale FR) :
``fr_score >= FR_SIDE_MIN`` => côté FR (le véhicule, qui « a l'air français ») ;
sinon côté russo-sphère (apparat, souvent fr_score≈0). ``france_targeting`` (lu
de ``channel_scores``) est le signal THÉMATIQUE, orthogonal à ``fr_score`` — c'est
toute la démonstration (cf. memory france-targeting-vs-fr-score).

HONNÊTETÉ (load-bearing) : la porosité observable est RÉELLE mais SPARSE. On
publie une poignée de traces NOMMÉES et vérifiables, jamais un volume gonflé.
Aucun lien de message direct n'est revendiqué ; T1/T2 uniquement.

Lecture seule PostgreSQL — AUCUN appel Telegram. Écrit un JSON consommé par la
webapp statique (webapp/public/data/russosphere/).

Usage :
    python scripts/analyze_porosity.py
"""
import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.shared.db import db_connect  # noqa: E402

OUT_PATH = ROOT / "webapp" / "public" / "data" / "russosphere" / "porosity_snapshot.json"
# Mission dont on lit le thème france_targeting (channel_scores est scopé mission).
MISSION = "russosphere"

# Seuil de côté : fr_score >= 0.15 => « a l'air français » (véhicule FR).
# Identique au seuil suspect/France-relevant du graph-model (§3.1).
FR_SIDE_MIN = 0.15

# Domaines génériques (plateformes) : co-cités par tout le monde -> bruit, pas de
# la porosité. On les EXCLUT des ponts-domaines pour ne garder que l'idéologique.
GENERIC_DOMAINS = frozenset({
    "instagram.com", "vk.com", "vk.ru", "vkvideo.ru", "facebook.com", "t.me",
    "telegra.ph", "youtube.com", "m.youtube.com", "youtu.be", "rutube.ru",
    "tiktok.com", "vm.tiktok.com", "twitter.com", "x.com", "google.com",
    "share.google", "drive.google.com", "forms.gle", "form.jotform.com",
    "archive.org", "rumble.com", "odysee.com", "substack.com", "telegram.org",
    "lnk.bio", "linktr.ee", "amazon.com", "max.ru", "dzen.ru", "helloasso.com",
    "apple.com", "spotify.com", "soundcloud.com", "bit.ly",
})


def _jload(x):
    return json.loads(x) if isinstance(x, str) else (x or {})


def _snippet(text: str, n: int = 90) -> str:
    s = " ".join((text or "").split())
    return s[:n]


async def load_channel_meta(conn, mission: str = MISSION) -> dict:
    """channel_id -> {username, title, fr_score, france_targeting, side}.

    Seuls les canaux TAGGÉS (avec fr_score, donc avec du texte observable) ont un
    côté ; les coquilles vides du catalogue sont ignorées pour la porosité.

    ``channel_scores`` est scopé mission (alembic 0005/0006 : PK (mission,
    channel_id)) : la jointure filtre sur ``mission``, sinon un canal scoré par
    plusieurs missions sort en N lignes et ``france_targeting`` dépend de l'ordre.
    """
    rows = await conn.fetch(
        """
        SELECT ch.channel_id, ch.username, ch.title,
               (ch.extra->>'fr_score')::float AS fr_score,
               s.france_targeting AS ft
        FROM channels ch
        LEFT JOIN channel_scores s
          ON s.channel_id = ch.channel_id AND s.mission = $1
        WHERE (ch.extra->>'fr_score') IS NOT NULL
        """,
        mission,
    )
    meta = {}
    for r in rows:
        fr = r["fr_score"] or 0.0
        meta[r["channel_id"]] = {
            "username": r["username"],
            "title": r["title"] or "",
            "fr_score": round(fr, 3),
            "france_targeting": round(r["ft"], 3) if r["ft"] is not None else None,
            "side": "FR" if fr >= FR_SIDE_MIN else "RU",
        }
    return meta


async def media_traces(conn, meta: dict) -> list[dict]:
    """Traces de réutilisation média qui traversent RU<->FR, avec vélocité.

    Un même ``media_hash`` (file_unique_id Telegram, stable aux forwards/re-upload)
    vu dans >=2 canaux dont au moins un FR et un RU. On ordonne par horodatage,
    on calcule le délai depuis la 1re apparition (vélocité), et on retient en
    priorité les traces d'ORIGINE russo-sphère reprises côté FR.
    """
    rows = await conn.fetch(
        """
        SELECT media_hash, channel_id, timestamp, LEFT(COALESCE(text,''), 160) AS text
        FROM messages
        WHERE media_hash IS NOT NULL AND timestamp IS NOT NULL
        """
    )
    by_hash: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["channel_id"] in meta:
            by_hash[r["media_hash"]].append(r)

    traces = []
    for h, evs in by_hash.items():
        sides = {meta[r["channel_id"]]["side"] for r in evs}
        if not ({"FR", "RU"} <= sides):
            continue
        if len({r["channel_id"] for r in evs}) < 2:
            continue
        evs = sorted(evs, key=lambda r: r["timestamp"])
        first_ts = evs[0]["timestamp"]
        # 1 apparition par canal (la plus précoce) pour la timeline.
        seen, appearances = set(), []
        for r in evs:
            cid = r["channel_id"]
            if cid in seen:
                continue
            seen.add(cid)
            m = meta[cid]
            appearances.append({
                "channel_id": cid,
                "username": m["username"],
                "title": m["title"],
                "side": m["side"],
                "fr_score": m["fr_score"],
                "france_targeting": m["france_targeting"],
                "ts": r["timestamp"].isoformat(),  # horodatage absolu (chronologie)
                "delay_hours": round((r["timestamp"] - first_ts).total_seconds() / 3600, 1),
                "text": _snippet(r["text"]),
            })
        origin_side = appearances[0]["side"]
        # Vélocité = délai jusqu'à la 1re reprise de l'AUTRE côté que l'origine.
        cross = next(
            (a for a in appearances[1:] if a["side"] != origin_side), None
        )
        traces.append({
            "media_hash": h,
            "origin_side": origin_side,
            "ru_to_fr": origin_side == "RU"
            and any(a["side"] == "FR" for a in appearances),
            "first_ts": first_ts.isoformat(),  # ancrage temporel absolu (chronologie)
            "velocity_hours": cross["delay_hours"] if cross else None,
            "n_channels": len(appearances),
            "appearances": appearances,
        })

    # Tri : RU->FR d'abord, puis vélocité la plus rapide, puis plus de canaux.
    traces.sort(key=lambda t: (
        not t["ru_to_fr"],
        t["velocity_hours"] if t["velocity_hours"] is not None else 9e9,
        -t["n_channels"],
    ))
    return traces


async def domain_bridges(conn, meta: dict) -> list[dict]:
    """Domaines adverses cités PAR LES DEUX côtés (hors plateformes génériques)."""
    fr_dom, ru_dom = defaultdict(set), defaultdict(set)
    rows = await conn.fetch(
        "SELECT src_channel_id, dst_domain FROM edges WHERE edge_type = 'CITES_DOMAIN'"
    )
    for r in rows:
        m = meta.get(r["src_channel_id"])
        if not m or not r["dst_domain"]:
            continue
        d = r["dst_domain"].lower()
        if d in GENERIC_DOMAINS:
            continue
        (fr_dom if m["side"] == "FR" else ru_dom)[d].add(r["src_channel_id"])

    bridges = []
    for d in set(fr_dom) & set(ru_dom):
        bridges.append({
            "domain": d,
            "fr_channels": sorted(meta[c]["username"] for c in fr_dom[d]),
            "ru_channels": sorted(meta[c]["username"] for c in ru_dom[d]),
            "n_fr": len(fr_dom[d]),
            "n_ru": len(ru_dom[d]),
        })
    bridges.sort(key=lambda b: -(b["n_fr"] + b["n_ru"]))
    return bridges


def theme_spine(meta: dict) -> dict:
    """L'asymétrie qui PORTE la démonstration : combien de canaux russo-sphère
    ciblent la France (france_targeting) tout en étant lexicalement non-français
    (fr_score bas) — l'infusion thématique cachée."""
    ru = [m for m in meta.values() if m["side"] == "RU"]
    fr = [m for m in meta.values() if m["side"] == "FR"]

    def targeting(group):
        return [m for m in group if (m["france_targeting"] or 0) > 0.05]

    ru_targeting = targeting(ru)
    return {
        "fr_side_total": len(fr),
        "ru_side_total": len(ru),
        "ru_targeting_france": len(ru_targeting),
        # Les plus frappants : ciblent fort la France, fr_score ~ 0.
        "hidden_attackers": sorted(
            (
                {
                    "username": m["username"],
                    "france_targeting": m["france_targeting"],
                    "fr_score": m["fr_score"],
                }
                for m in ru_targeting
            ),
            key=lambda x: -(x["france_targeting"] or 0),
        )[:15],
    }


async def timeline_block(conn, meta: dict) -> dict:
    """Le PASSÉ, en données réelles : empan temporel + volume de publication
    mensuel par côté (RU/FR). HONNÊTETÉ : c'est du volume de PUBLICATION, pas une
    portée/audience (les vues sont un instantané écrasé à chaque crawl). Les
    croisements RU->FR sont ajoutés dans main() depuis les traces média.
    """
    span = await conn.fetchrow(
        "SELECT MIN(timestamp) AS mn, MAX(timestamp) AS mx "
        "FROM messages WHERE timestamp IS NOT NULL"
    )
    rows = await conn.fetch(
        "SELECT channel_id, date_trunc('month', timestamp) AS m, count(*) AS n "
        "FROM messages WHERE timestamp IS NOT NULL GROUP BY channel_id, m"
    )
    monthly: dict[str, dict] = defaultdict(lambda: {"ru": 0, "fr": 0})
    for r in rows:
        m = meta.get(r["channel_id"])
        if not m:  # canal non taggé (pas de côté) -> hors timeline
            continue
        key = r["m"].strftime("%Y-%m")
        monthly[key]["ru" if m["side"] == "RU" else "fr"] += r["n"]
    return {
        "span": {
            "min_ts": span["mn"].isoformat() if span and span["mn"] else None,
            "max_ts": span["mx"].isoformat() if span and span["mx"] else None,
        },
        "monthly": [
            {"month": k, "ru": v["ru"], "fr": v["fr"]} for k, v in sorted(monthly.items())
        ],
    }


async def main() -> None:
    # Console Windows en cp1252 : un emoji dans un extrait de message faisait
    # planter le print final (exit 1) ALORS QUE le JSON était déjà écrit. On
    # rend stdout tolérant pour que le rapport ne masque pas un succès.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort
        pass
    conn = await db_connect()
    try:
        meta = await load_channel_meta(conn)
        traces = await media_traces(conn, meta)
        bridges = await domain_bridges(conn, meta)
        spine = theme_spine(meta)
        timeline = await timeline_block(conn, meta)
    finally:
        await conn.close()

    ru_to_fr = [t for t in traces if t["ru_to_fr"]]
    # Croisements RU->FR datés, à poser sur l'axe de la chronologie.
    crossings = []
    for t in ru_to_fr:
        ru0 = next((a for a in t["appearances"] if a["side"] == "RU"), None)
        fr0 = next((a for a in t["appearances"] if a["side"] == "FR"), None)
        if ru0 and fr0:
            crossings.append({
                "first_ts": t["first_ts"],
                "velocity_hours": t["velocity_hours"],
                "ru_user": ru0["username"],
                "fr_user": fr0["username"],
                "media_hash": t["media_hash"],
            })
    crossings.sort(key=lambda c: c["first_ts"])
    timeline["crossings"] = crossings
    snapshot = {
        "coverage_callout": (
            "Liens DIRECTS et observables russo-sphère <-> véhicule extrême "
            "droite / souverainiste-identitaire (reprise de contenu). HORS "
            "PÉRIMÈTRE ASSUMÉ : la diffusion en aval vers la politique française "
            "grand public / les élus — chaîne trop indirecte et non instrumentable "
            "avec ces données (un relais peut être formaté par un tiers européen, "
            "etc.). On ne revendique QUE le lien direct. Telegram seul ; signaux "
            "sparse par nature — traces nommées et vérifiables, jamais un volume "
            "gonflé. Attribution T1/T2 ; jamais de commanditaire (T3) ni de lien "
            "de message direct revendiqué."
        ),
        "stats": {
            "fr_side": spine["fr_side_total"],
            "ru_side": spine["ru_side_total"],
            "ru_targeting_france": spine["ru_targeting_france"],
            "media_traces_cross": len(traces),
            "media_traces_ru_to_fr": len(ru_to_fr),
            "domain_bridges": len(bridges),
        },
        "theme_spine": spine,
        "timeline": timeline,
        "media_traces": traces,
        "domain_bridges": bridges,
    }
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(payload, encoding="utf-8")

    print(f"Écrit : {OUT_PATH}")
    print(
        f"  côtés : FR={spine['fr_side_total']} · RU={spine['ru_side_total']} "
        f"(dont {spine['ru_targeting_france']} ciblent la France, fr_score souvent ~0)"
    )
    print(
        f"  traces média transfrontières : {len(traces)} "
        f"(dont {len(ru_to_fr)} RU->FR) · ponts-domaines : {len(bridges)}"
    )
    print("\nTop traces RU->FR (vélocité) :")
    for t in ru_to_fr[:6]:
        a0 = t["appearances"][0]
        fr_app = next(a for a in t["appearances"] if a["side"] == "FR")
        v = t["velocity_hours"]
        print(
            f"  +{v:>5}h  @{a0['username']} [RU] -> @{fr_app['username']} [FR]"
            f"  | {a0['text'][:54]}"
        )


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="Extrait les traces de porosité russo-sphère -> extrême droite FR."
    ).parse_args()
    asyncio.run(main())
