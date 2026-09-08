"""Mineur d'ÉPISODES — découvre dans le graphe les sujets/médias qui traversent
RU → FR (production russophile reprise côté français), sans liste curée.

> Question Micky (2026-06-10) : « est-il possible de faire remonter des
> sujets/médias dans le graphe — voir comment les russophiles impactent les
> comptes [extrême droite / RN] ? » Ce script répond OUI par les données : il
> généralise `analyze_porosity.py` (qui ne voyait que le média-hash) à
> PLUSIEURS pivots trans-côté, et nomme chaque épisode par ses termes saillants.

Un **épisode** = un PIVOT partagé entre un canal RU (origine) et un canal FR
(reprise), avec horodatage (donc vélocité). Trois types de pivot DURS (preuve
matérielle, zéro NLP) :

  1. **média**  — un même `media_hash` (file_unique_id, stable aux re-upload)
                  vu côté RU puis côté FR.
  2. **url**    — une même URL exacte (colonne `messages.urls`) des deux côtés.
  3. **forward**— un message d'un canal RU republié (forward) par un canal FR.

Enrichissements :
  * **sujet** — label TF-IDF des textes de l'épisode (termes saillants), pour
                lire « de quoi ça parle » (le « sujet » demandé).
  * **corroboration** — nb de TYPES de pivot distincts reliant la même paire
                RU→FR : ≥2 = épisode fort (même logique de verrou multi-source
                que le score canal). Un pivot isolé reste affiché mais signalé.

HONNÊTETÉ (load-bearing) : la porosité observable est RÉELLE mais SPARSE — on
sort une poignée d'épisodes nommés et datés, jamais un volume gonflé. T1/T2
uniquement (diffusion observable / récurrence). Telegram-only.

Le « côté » dérive de `fr_score` (densité lexicale FR ≥ 0.15 ⇒ FR), comme
`analyze_porosity.py` ; `france_targeting` (thème) est orthogonal et reporté
en appoint. Lecture seule PostgreSQL. AUCUN appel Telegram. Idempotent.

Usage :
    python scripts/mine_episodes.py [--mission russosphere] [--min-corroboration 1]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
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

# Seuil de côté : identique à analyze_porosity (graph-model §3.1).
FR_SIDE_MIN = 0.15

# URLs de plateforme : co-partagées par tout le monde ⇒ bruit, pas un épisode.
GENERIC_URL_HOST = re.compile(
    r"(t\.me|telegram\.|youtube\.|youtu\.be|x\.com|twitter\.com|vk\.com|vk\.ru|"
    r"facebook\.|instagram\.|tiktok\.|google\.|rutube\.|dzen\.ru|spotify\.|"
    r"telegra\.ph|archive\.org|bit\.ly|share\.google)",
    re.I,
)

# Stop-words FR+RU+EN minimaux pour le label TF-IDF (library-first : on garde
# le vectoriseur sklearn mais on lui passe une stop-list ciblée multilingue).
_STOP = {
    "the", "and", "for", "que", "qui", "les", "des", "une", "uno", "pour", "dans",
    "sur", "avec", "est", "pas", "plus", "tout", "comme", "leur", "nous", "vous",
    "это", "как", "что", "для", "над", "под", "при", "the", "with", "from", "this",
    "https", "http", "www", "com", "amp", "via", "ont", "ses", "son", "par", "aux",
    "от", "из", "по", "не", "на", "в", "и", "с", "а", "о", "у", "к", "за", "до",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str | None, n: int = 120) -> str:
    return " ".join((text or "").split())[:n]


async def load_sides(conn) -> dict[int, dict]:
    """channel_id -> {username, title, fr_score, france_targeting, side}."""
    rows = await conn.fetch(
        """
        SELECT ch.channel_id, ch.username, ch.title,
               (ch.extra->>'fr_score')::float AS fr_score,
               s.france_targeting AS ft
        FROM channels ch
        LEFT JOIN channel_scores s ON s.channel_id = ch.channel_id
        WHERE (ch.extra->>'fr_score') IS NOT NULL
        """
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


def _appearance(meta, cid, ts, text, first_ts):
    m = meta[cid]
    return {
        "channel_id": cid,
        "username": m["username"],
        "title": m["title"],
        "side": m["side"],
        "france_targeting": m["france_targeting"],
        "ts": ts.isoformat(),
        "delay_hours": round((ts - first_ts).total_seconds() / 3600, 1),
        "text": _snippet(text),
    }


def _assemble(meta, pivot_type, key, label, events):
    """events = [(cid, ts, text)] -> épisode RU→FR ou None si pas trans-côté."""
    rows = [(c, t, x) for (c, t, x) in events if c in meta and t is not None]
    if len({c for c, _, _ in rows}) < 2:
        return None
    sides = {meta[c]["side"] for c, _, _ in rows}
    if not ({"FR", "RU"} <= sides):
        return None
    rows.sort(key=lambda r: r[1])
    first_ts = rows[0][1]
    seen, apps = set(), []
    for c, t, x in rows:
        if c in seen:
            continue
        seen.add(c)
        apps.append(_appearance(meta, c, t, x, first_ts))
    origin = apps[0]["side"]
    if origin != "RU":
        return None  # on cible la production RUSSOPHILE reprise côté FR
    cross = next((a for a in apps[1:] if a["side"] == "FR"), None)
    if cross is None:
        return None
    return {
        "pivot_type": pivot_type,
        "pivot_key": key,
        "label": label,
        "first_ts": first_ts.isoformat(),
        "velocity_hours": cross["delay_hours"],
        "ru_seeders": sorted({a["username"] for a in apps if a["side"] == "RU"}),
        "fr_receivers": sorted({a["username"] for a in apps if a["side"] == "FR"}),
        "n_channels": len(apps),
        "appearances": apps,
        "_texts": [a["text"] for a in apps if a["text"]],
        "_pair_keys": {
            (s, r)
            for s in (a["username"] for a in apps if a["side"] == "RU")
            for r in (a["username"] for a in apps if a["side"] == "FR")
        },
    }


async def media_pivots(conn, meta) -> list[dict]:
    rows = await conn.fetch(
        "SELECT media_hash, channel_id, timestamp, text FROM messages "
        "WHERE media_hash IS NOT NULL AND timestamp IS NOT NULL"
    )
    by = defaultdict(list)
    for r in rows:
        if r["channel_id"] in meta:
            by[r["media_hash"]].append((r["channel_id"], r["timestamp"], r["text"]))
    out = []
    for h, evs in by.items():
        ep = _assemble(meta, "media", h, "média réutilisé (image/vidéo)", evs)
        if ep:
            out.append(ep)
    return out


async def url_pivots(conn, meta) -> list[dict]:
    rows = await conn.fetch(
        "SELECT channel_id, timestamp, text, urls FROM messages "
        "WHERE urls IS NOT NULL AND timestamp IS NOT NULL"
    )
    by = defaultdict(list)
    for r in rows:
        if r["channel_id"] not in meta:
            continue
        urls = r["urls"]
        if isinstance(urls, str):
            try:
                urls = json.loads(urls)
            except Exception:  # noqa: BLE001
                urls = [urls]
        for u in urls or []:
            u = str(u).strip().rstrip("/")
            if not u or GENERIC_URL_HOST.search(u):
                continue
            by[u].append((r["channel_id"], r["timestamp"], r["text"]))
    out = []
    for u, evs in by.items():
        ep = _assemble(meta, "url", u, f"lien partagé : {u[:60]}", evs)
        if ep:
            out.append(ep)
    return out


async def forward_pivots(conn, meta) -> list[dict]:
    """Un message d'un canal RU republié par >=1 canal FR (+ l'origine RU)."""
    rows = await conn.fetch(
        """
        SELECT m.forward_from_channel_id AS src, m.forward_from_message_id AS mid,
               m.channel_id AS relay, m.timestamp AS ts, m.text AS text
        FROM messages m
        WHERE m.forward_from_channel_id IS NOT NULL
          AND m.forward_from_message_id IS NOT NULL
          AND m.timestamp IS NOT NULL
        """
    )
    by = defaultdict(list)
    for r in rows:
        src, relay = r["src"], r["relay"]
        if src not in meta or relay not in meta:
            continue
        key = (src, r["mid"])
        by[key].append((relay, r["ts"], r["text"]))
        by[key].append((src, r["ts"], r["text"]))  # ancre l'origine côté RU
    # texte original de la source (pour label) si dispo
    out = []
    for (src, mid), evs in by.items():
        orig = await conn.fetchrow(
            "SELECT timestamp, text FROM messages WHERE channel_id=$1 AND message_id=$2",
            src, mid,
        )
        if orig and orig["timestamp"]:
            evs = evs + [(src, orig["timestamp"], orig["text"])]
        label = "message republié : " + (_snippet(orig["text"], 60) if orig else f"#{mid}")
        ep = _assemble(meta, "forward", f"{src}:{mid}", label, evs)
        if ep:
            out.append(ep)
    return out


def label_topics(episodes: list[dict]) -> None:
    """Ajoute episode['subject'] = top termes TF-IDF des textes de l'épisode.

    Library-first : TfidfVectorizer (scikit-learn, déjà une dépendance). Le
    corpus = un document par épisode (concat de ses snippets) ; les termes les
    plus distinctifs nomment le sujet. Silencieux si trop peu de texte.
    """
    docs = [" ".join(e["_texts"]) for e in episodes]
    if sum(len(d) for d in docs) < 200:
        for e in episodes:
            e["subject"] = []
        return
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except Exception:  # noqa: BLE001
        for e in episodes:
            e["subject"] = []
        return
    vec = TfidfVectorizer(
        lowercase=True, ngram_range=(1, 2), min_df=1, max_df=0.6,
        token_pattern=r"(?u)\b[\wà-ÿА-я]{4,}\b",
        stop_words=list(_STOP),
    )
    try:
        X = vec.fit_transform(docs)
    except ValueError:
        for e in episodes:
            e["subject"] = []
        return
    terms = vec.get_feature_names_out()
    for i, e in enumerate(episodes):
        row = X[i].toarray()[0]
        top = sorted(range(len(row)), key=lambda j: -row[j])[:5]
        e["subject"] = [terms[j] for j in top if row[j] > 0]


def group_by_pair(raw: list[dict], meta: dict) -> list[dict]:
    """Regroupe les pivots BRUTS par RELATION RU→FR (origine RU → récepteur FR).

    Un épisode lisible = une relation entre deux canaux, PAS un pivot isolé :
    @serviam→@francenatio republié 8× = UN épisode (8 pivots), pas 8. On agrège
    tous les pivots de la paire, on garde la meilleure vélocité, on unit canaux/
    sujets/preuves, et la **corroboration = nb de TYPES de pivot distincts** entre
    la paire (média+forward ⇒ 2 ⇒ verrou multi-signal ⇒ T2).
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in raw:
        ru = e["ru_seeders"][0] if e["ru_seeders"] else "?"
        fr = e["fr_receivers"][0] if e["fr_receivers"] else "?"
        groups[(ru, fr)].append(e)

    merged: list[dict] = []
    for (ru, fr), members in groups.items():
        members.sort(key=lambda m: m["first_ts"])
        types = sorted({m["pivot_type"] for m in members})
        # apparences uniques par canal (la plus précoce)
        seen, apps = set(), []
        for m in sorted(members, key=lambda m: m["first_ts"]):
            for a in m["appearances"]:
                if a["channel_id"] not in seen:
                    seen.add(a["channel_id"])
                    apps.append(a)
        ru_users = sorted({u for m in members for u in m["ru_seeders"]})
        fr_users = sorted({u for m in members for u in m["fr_receivers"]})
        merged.append({
            "pivot_type": max(types, key=lambda t: sum(1 for m in members if m["pivot_type"] == t)),
            "pivot_types": types,
            "n_pivots": len(members),
            "label": f"@{ru} → @{fr} : {len(members)} reprise(s)",
            "first_ts": members[0]["first_ts"],
            "velocity_hours": min(m["velocity_hours"] for m in members),
            "ru_seeders": ru_users,
            "fr_receivers": fr_users,
            "n_channels": len(apps),
            "appearances": apps,
            "corroboration": len(types),
            "corroborating_signals": types,
            "_texts": [a["text"] for a in apps if a["text"]],
        })
    return merged


def finalize(episodes: list[dict], meta: dict) -> list[dict]:
    """Nettoie les champs privés, ajoute l'id, le tier et le ciblage France."""
    ft_by_user = {m["username"]: m["france_targeting"] for m in meta.values()}
    out = []
    for i, e in enumerate(sorted(
        episodes,
        key=lambda e: (-e["corroboration"], e["velocity_hours"], -e["n_channels"]),
    )):
        recv_ft = [ft_by_user.get(u) for u in e["fr_receivers"]]
        recv_ft = [x for x in recv_ft if x is not None]
        e2 = {k: v for k, v in e.items() if not k.startswith("_")}
        e2["id"] = f"ep_{e['pivot_type']}_{i:03d}"
        # T2 si corroboré par >=2 signaux (récurrence comportementale), sinon T1.
        e2["tier"] = "T2" if e["corroboration"] >= 2 else "T1"
        e2["fr_targeting_max"] = round(max(recv_ft), 3) if recv_ft else None
        # channel_ids (pour l'illumination directe sur la galaxie côté frontend)
        e2["channel_ids"] = sorted({a["channel_id"] for a in e["appearances"]})
        out.append(e2)
    return out


async def mine(conn, meta) -> list[dict]:
    raw = []
    raw += await media_pivots(conn, meta)
    raw += await url_pivots(conn, meta)
    raw += await forward_pivots(conn, meta)
    grouped = group_by_pair(raw, meta)  # 1 épisode = 1 relation RU→FR (dédupliqué)
    label_topics(grouped)
    return finalize(grouped, meta)


def calculate_embeddings(episodes: list[dict]) -> None:
    """Calcule l'embedding de chaque cluster + métriques de cohésion/outliers.

    Graceful degradation: si l'extra embed n'est pas installé, passe silencieux.

    Ajoute à chaque épisode:
        pourquoi_embedding = {
            "intra_cohesion": float,           # avg similarity intra-cluster
            "distance_to_baseline": float,      # vs baseline organique FR
            "top_outliers": [{"channel": str, "distance": float}, ...]  # top-3 farthest
        }
    """
    try:
        from src.embed.encoder import Embedder, cosine
    except ImportError:
        for e in episodes:
            e["pourquoi_embedding"] = None
        return

    embedder = Embedder()

    # ponytail: baseline = mean de tous les textes FR (organique). Simplification:
    # on prend les textes FR de tous les épisodes comme baseline proxy.
    all_fr_texts = [
        t for e in episodes for a in e.get("appearances", [])
        if a.get("side") == "FR" and (t := a.get("text"))
    ]
    if len(all_fr_texts) < 5:
        for e in episodes:
            e["pourquoi_embedding"] = None
        return

    baseline_vecs = embedder.encode_texts(all_fr_texts[:100])  # cap à 100 pour perfs
    baseline_centroid = baseline_vecs.mean(axis=0)

    for e in episodes:
        texts = e.get("_texts", [])
        if len(texts) < 2:
            e["pourquoi_embedding"] = None
            continue

        vecs = embedder.encode_texts(texts)
        centroid = vecs.mean(axis=0)

        # ponytail: cohésion = variance intra-cluster (std dev des distances au centroïde).
        # Silhouette needs 2+ clusters labels; variance est plus direct pour 1 cluster.
        if len(vecs) >= 2:
            dists_centroid = [1.0 - cosine(v, centroid) for v in vecs]
            cohesion = 1.0 - (sum(dists_centroid) / len(dists_centroid))  # avg similarity
        else:
            cohesion = None

        # Distance au baseline
        dist_baseline = 1.0 - cosine(centroid, baseline_centroid)

        # Top-3 outliers du cluster (farthest from centroid)
        dists = [(1.0 - cosine(v, centroid)) for v in vecs]
        indexed = sorted(enumerate(dists), key=lambda x: -x[1])[:3]
        outliers = [
            {"channel": e["appearances"][i]["username"], "distance": round(d, 3)}
            for i, d in indexed if i < len(e.get("appearances", []))
        ]

        e["pourquoi_embedding"] = {
            "intra_cohesion": round(cohesion, 3) if cohesion is not None else None,
            "distance_to_baseline": round(dist_baseline, 3),
            "top_outliers": outliers,
        }


async def main() -> None:
    ap = argparse.ArgumentParser(description="Découvre les épisodes RU→FR dans le graphe.")
    ap.add_argument("--mission", default=None)
    ap.add_argument("--min-corroboration", type=int, default=1,
                    help="Ne garder que les épisodes corroborés par >=N signaux (défaut 1 = tous)")
    args = ap.parse_args()
    mission = args.mission or DEFAULT_MISSION
    out_dir = _WEBAPP_DATA / mission
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = await db_connect()
    try:
        meta = await load_sides(conn)
        episodes = await mine(conn, meta)
        calculate_embeddings(episodes)  # post-labeling enrichment
    finally:
        await conn.close()

    kept = [e for e in episodes if e["corroboration"] >= args.min_corroboration]

    # ponytail: nettoie _texts avant export final
    for e in kept:
        e.pop("_texts", None)

    payload = {
        "generated_at": _now_iso(),
        "mission": mission,
        "n_episodes": len(kept),
        "by_pivot": {
            t: sum(1 for e in kept if e["pivot_type"] == t)
            for t in ("media", "url", "forward")
        },
        "coverage_callout": (
            "Épisodes RU→FR OBSERVABLES sur Telegram (porosité réelle mais sparse). "
            "Une campagne passant surtout hors Telegram n'apparaît pas. T1/T2 uniquement."
        ),
        "episodes": kept,
    }
    path = out_dir / "episodes_discovered.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Écrit : {path} · {len(kept)} épisodes RU→FR "
          f"(media={payload['by_pivot']['media']} url={payload['by_pivot']['url']} "
          f"forward={payload['by_pivot']['forward']})")
    print("\nTop épisodes (corroboration · vélocité · sujet) :")
    for e in kept[:15]:
        subj = ", ".join(e.get("subject") or []) or "—"
        ru = ", ".join("@" + u for u in e["ru_seeders"][:2])
        fr = ", ".join("@" + u for u in e["fr_receivers"][:2])
        print(f"  [{e['tier']}] x{e['corroboration']} {e['pivot_type']:7} "
              f"+{e['velocity_hours']:>6}h  {ru} → {fr}  | {subj[:50]}")


if __name__ == "__main__":
    asyncio.run(main())
