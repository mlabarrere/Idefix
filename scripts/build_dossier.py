"""
Construit le dossier RÉEL du cluster eurasianiste Dugin/Geopolitika depuis
PostgreSQL et l'écrit au contrat webapp dans webapp/public/data/russosphere/dugin_cluster.json.

- AUCUN appel Telegram/MTProto : lecture seule de PostgreSQL.
- Graphe de forward construit via NetworkX (origine -> relayeur), self-loops exclus.
- Scores RÉELS : familles (b) cascade_role, (c) coordination, (d) recidivism.
  Familles (a) proximité et (e) origine IA = stubs explicites (cf. builder).
- Épisode = cluster contenant Dugin/AGDchan/Geopolitika : canaux eurasianistes
  à fr_score < 0.15 (ou ancres) connectés à l'appareil dans le graphe de forward.

Usage :
    PYTHONUTF8=1 PYTHONPATH=. ./.venv/Scripts/python.exe scripts/build_dossier.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.shared.db import db_connect
import networkx as nx
from dotenv import load_dotenv

from src.dossier.builder import build_episode_dossier
from src.scorer.cascade_role import score_cascade_role
from src.scorer.coordination import score_coordination
from src.scorer.recidivism import score_recidivism

load_dotenv()

OUTPUT_PATH = Path(__file__).parent.parent / "webapp" / "public" / "data" / "russosphere" / "dugin_cluster.json"

# Sous-chaînes d'usernames identifiant l'appareil eurasianiste Dugin/Geopolitika.
EURASIANIST_SUBSTRINGS = (
    "dugin", "agdchan", "geopolitika", "multipolar", "kvmalofeev", "arktos",
    "arsregia", "imperium", "eurosiberia", "metapolitic", "novaresistencia",
    "tsargrad", "katehon", "paideuma", "unitedworld", "newrules",
    "rainaldograziani", "cantieremultipolare", "occvltimperium", "nebesnyegory",
)

# Seuil de pertinence-France : un canal eurasianiste à fr_score < ce seuil
# (donc non centré sur la France) entre dans le cluster d'influence.
FR_SCORE_MAX = 0.15

N_TIMELINE_BUCKETS = 24


async def fetch_data() -> tuple[list, list, list]:
    """Lit canaux + arêtes de forward + timestamps de forward (self-loops exclus)."""
    conn = await db_connect()
    try:
        channels = await conn.fetch(
            "SELECT channel_id, username, title, member_count, extra FROM channels"
        )
        edges = await conn.fetch(
            """
            SELECT forward_from_channel_id AS origin,
                   channel_id              AS reposter,
                   count(*)                AS n,
                   COALESCE(max(forward_delay_seconds), 0) AS max_delay
            FROM messages
            WHERE forward_from_channel_id IS NOT NULL
              AND forward_from_channel_id <> channel_id
            GROUP BY 1, 2
            """
        )
        # Timestamps des messages de forward, pour la timeline d'activité.
        fwd_ts = await conn.fetch(
            """
            SELECT forward_from_channel_id AS origin,
                   channel_id              AS reposter,
                   timestamp
            FROM messages
            WHERE forward_from_channel_id IS NOT NULL
              AND forward_from_channel_id <> channel_id
              AND timestamp IS NOT NULL
            """
        )
    finally:
        await conn.close()
    return channels, edges, fwd_ts


def _fr_score(extra) -> float | None:
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}
    if isinstance(extra, dict):
        return extra.get("fr_score")
    return None


def build_forward_graph(channels: list, edges: list) -> nx.DiGraph:
    """DiGraph origine -> relayeur ; poids = count ; délai max porté sur l'arête."""
    meta = {r["channel_id"]: r for r in channels}
    graph = nx.DiGraph()
    for cid, r in meta.items():
        graph.add_node(cid, username=r["username"] or "", title=r["title"] or "")
    for e in edges:
        for cid in (e["origin"], e["reposter"]):
            if cid not in graph:
                graph.add_node(cid, username="", title="")
        graph.add_edge(
            e["origin"], e["reposter"],
            count=int(e["n"]),
            min_delay_s=int(e["max_delay"] or 0),  # cascade_role lit min_delay_s
        )
    return graph


def select_dugin_cluster(graph: nx.DiGraph, channels: list) -> list[dict]:
    """
    Sélectionne le cluster : ancres eurasianistes + leurs voisins de forward
    (1 hop, toute direction) qui sont eux-mêmes à fr_score < FR_SCORE_MAX.
    Garantit un sous-graphe connexe centré sur l'appareil Dugin/Geopolitika.
    """
    meta = {r["channel_id"]: r for r in channels}

    anchors = {
        cid for cid, r in meta.items()
        if any(s in (r["username"] or "").lower() for s in EURASIANIST_SUBSTRINGS)
        and cid in graph
    }

    undirected = graph.to_undirected()
    near = set(anchors)
    for a in anchors:
        if a in undirected:
            near |= set(undirected.neighbors(a))

    cluster_ids = set()
    for cid in near:
        if cid not in graph:
            continue
        fr = _fr_score(meta.get(cid, {}).get("extra"))
        if cid in anchors or (fr is not None and fr < FR_SCORE_MAX):
            cluster_ids.add(cid)

    return [
        {
            "channel_id": cid,
            "username": meta[cid]["username"],
            "member_count": meta[cid]["member_count"],
            "fr_score": _fr_score(meta[cid]["extra"]),
        }
        for cid in cluster_ids
    ]


def compute_forward_influence_norm(graph: nx.DiGraph) -> dict[int, float]:
    """forward-influence normalisée (somme des poids sortants / max global)."""
    infl = {n: 0.0 for n in graph.nodes}
    for origin, _r, data in graph.edges(data=True):
        infl[origin] += float(data.get("count", 1))
    mx = max(infl.values(), default=0.0)
    return {n: (v / mx if mx > 0 else 0.0) for n, v in infl.items()}


def build_timeline(fwd_ts: list, cluster_ids: set[int]) -> tuple[list[int], int]:
    """
    24 buckets d'activité de forward réelle pour le cluster (forwards émis OU
    reçus par un canal du cluster), répartis uniformément sur la fenêtre
    observée [min_ts, max_ts]. Retourne (buckets, hours_span).
    """
    times = [
        r["timestamp"] for r in fwd_ts
        if r["origin"] in cluster_ids or r["reposter"] in cluster_ids
    ]
    if not times:
        return [0] * N_TIMELINE_BUCKETS, 0

    t_min, t_max = min(times), max(times)
    span = (t_max - t_min).total_seconds()
    hours = int(span // 3600)
    buckets = [0] * N_TIMELINE_BUCKETS
    if span <= 0:
        buckets[-1] = len(times)
        return buckets, hours

    width = span / N_TIMELINE_BUCKETS
    for t in times:
        idx = int((t - t_min).total_seconds() // width)
        if idx >= N_TIMELINE_BUCKETS:
            idx = N_TIMELINE_BUCKETS - 1
        buckets[idx] += 1
    return buckets, hours


async def main() -> None:
    channels, edges, fwd_ts = await fetch_data()
    graph = build_forward_graph(channels, edges)

    # Scores réels sur le graphe entier (puis projetés sur le cluster).
    cascade = score_cascade_role(graph)
    coordination = score_coordination(graph)
    recidivism = score_recidivism(graph)
    fi_norm = compute_forward_influence_norm(graph)

    cluster = select_dugin_cluster(graph, channels)
    cluster_ids = {c["channel_id"] for c in cluster}
    print(f"Cluster Dugin/Geopolitika : {len(cluster)} canaux")

    timeline, hours = build_timeline(fwd_ts, cluster_ids)

    # Sévérité du cluster = max des scores réels b/c/d mappé sur T1..T5.
    def fam_max(scores: dict) -> float:
        vals = [scores[c].value for c in cluster_ids if c in scores]
        return max(vals, default=0.0)

    peak = max(fam_max(cascade), fam_max(coordination), fam_max(recidivism))
    severity = (
        "T5" if peak >= 0.9 else
        "T4" if peak >= 0.7 else
        "T3" if peak >= 0.5 else
        "T2" if peak >= 0.3 else "T1"
    )

    dossier = build_episode_dossier(
        episode_id="dugin_cluster",
        title="Réseau eurasianiste coordonné (Dugin/Geopolitika) — amplification multilingue",
        theme="Écosystème d'influence",
        severity_tier=severity,
        cluster_channels=cluster,
        cascade_scores=cascade,
        coordination_scores=coordination,
        recidivism_scores=recidivism,
        forward_influence_norm=fi_norm,
        timeline=timeline,
        hours=hours,
        attribution_tier="T2",   # récurrence comportementale
        next_tier="T4",
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Récapitulatif console ------------------------------------------- #
    print(f"\nÉcrit : {OUTPUT_PATH}")
    print(f"Sévérité : {severity} | gateMet={dossier['gateMet']} ({dossier['gateDetail']})")
    print("Scores réels du cluster (leads) :")
    print(f"  b cascade      v={dossier['scores']['b']['v']} (archétype={dossier['scores']['b']['label']})")
    print(f"  c coordination v={dossier['scores']['c']['v']}")
    print(f"  d récidivisme  v={dossier['scores']['d']['v']}")
    print(f"  timeline (24 buckets) : {dossier['timeline']}  | heures observées={hours}")
    print("\nchannels_detail :")
    for cd in sorted(dossier["channels_detail"], key=lambda x: -x["fi"]):
        print(f"  {cd['id']:26s} arch={cd['arch']:11s} subs={cd['subs']:>8d} fi={cd['fi']}")


if __name__ == "__main__":
    asyncio.run(main())
