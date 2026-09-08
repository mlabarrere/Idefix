"""Snapshot communautés « LLM Embedding » — détection regroupée par embeddings.

Pendant local/gratuit de ``scripts/analyze_communities.py`` : même schéma de
sortie (``RussosphereSnapshot`` : communities + bridges + meta_graph + stats),
MAIS la détection Leiden tourne sur un graphe enrichi d'arêtes de similarité
d'embeddings (les canaux sémantiquement proches sont tirés ensemble) ⇒ groupes
plus cohérents. On ajoute un bloc ``stats.comparison`` chiffré (cohésion intra,
modularité, nb communautés) qui alimente le callout factuel du switch galaxie.

Écrit ``webapp/public/data/<mission>/<mission>_embed_snapshot.json``. Le snapshot
« Analytics » par défaut (``analyze_communities.py``) n'est jamais touché.

Lecture seule PostgreSQL + inférence locale (coût 0). Nécessite l'extra `embed`.

Usage :
    python scripts/analyze_communities_embed.py --mission russosphere
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import asyncpg  # noqa: E402
import numpy as np  # noqa: E402

from src.embed.community import add_embedding_edges, comparison_block  # noqa: E402
from src.embed.encoder import Embedder  # noqa: E402
from src.graph.loader import build_graph, fetch_channel_rows, fetch_edge_rows  # noqa: E402
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.normalizer.handlers import clean_text  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

# Reuse the analytics pipeline we mirror (Leiden + snapshot builder). `scripts/`
# is not a package, so load the sibling module by path (repo convention).
_AC_SPEC = importlib.util.spec_from_file_location(
    "analyze_communities", ROOT / "scripts" / "analyze_communities.py"
)
_AC = importlib.util.module_from_spec(_AC_SPEC)
_AC_SPEC.loader.exec_module(_AC)
build_snapshot = _AC.build_snapshot
detect_communities = _AC.detect_communities


async def _load_graph_and_messages():
    conn = await db_connect()
    try:
        edges = await fetch_edge_rows(conn)
        chans = await fetch_channel_rows(conn)
        msgs = await conn.fetch(
            "SELECT channel_id, text FROM messages "
            "WHERE text IS NOT NULL AND length(text) > 20"
        )
    finally:
        await conn.close()
    return build_graph(edges, chans), msgs


def _fetch_messages_rest(sample_per_channel: int) -> list[dict]:
    """Corpus messages via l'API REST Supabase (HTTPS:443).

    AURA bloque le wire-protocol PostgreSQL (5432/6543) mais pas REST. On pagine
    toute la table ``messages`` en ne gardant que les ``sample_per_channel`` plus
    longs textes par canal (mémoire bornée) — c'est ce que l'embedding échantillonne.
    Identifiants lus depuis l'env (``SUPABASE_URL`` + ``SUPABASE_KEY``), jamais en dur.
    """
    import heapq
    import urllib.request

    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    best: dict[int, list] = defaultdict(list)  # channel_id -> min-heap (len, text)
    offset, page = 0, 1000
    while True:
        u = (f"{base}/rest/v1/messages?select=channel_id,text&text=not.is.null"
             f"&order=channel_id&limit={page}&offset={offset}")
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as r:
            rows = json.loads(r.read().decode())
        if not rows:
            break
        for row in rows:
            cid, t = row["channel_id"], row["text"] or ""
            h = best[cid]
            if len(h) < sample_per_channel:
                heapq.heappush(h, (len(t), t))
            elif len(t) > h[0][0]:
                heapq.heapreplace(h, (len(t), t))
        offset += len(rows)
        if len(rows) < page:
            break
    return [{"channel_id": cid, "text": t} for cid, h in best.items() for _, t in h]


def _load_graph_and_messages_from_bundle(out_subdir: str):
    """Repli sans wire-protocol PG. Graphe = bundle statique (même base que le
    snapshot Analytics ⇒ comparaison équitable). Texte = corpus messages via REST
    si ``SUPABASE_*`` présents, sinon métadonnées canal (titre + description)."""
    g = _AC.load_graph_from_bundle()  # ponytail: lit le bundle russosphere
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        return g, _fetch_messages_rest(15)
    data_dir = ROOT / "webapp" / "public" / "data" / out_subdir
    chans = json.loads((data_dir / "channels.json").read_text("utf-8"))
    msgs = [
        {"channel_id": c["channel_id"],
         "text": " ".join(filter(None, [c.get("title"), c.get("description")]))}
        for c in chans
    ]
    return g, [m for m in msgs if m["text"].strip()]


def _channel_embeddings(embedder: Embedder, msgs, sample_size: int) -> dict[int, np.ndarray]:
    """Mean embedding per channel from its longest ``sample_size`` messages."""
    by_chan: dict[int, list[str]] = defaultdict(list)
    for r in msgs:
        t = clean_text(r["text"])
        if t:
            by_chan[r["channel_id"]].append(t)

    flat: list[str] = []
    spans: dict[int, tuple[int, int]] = {}
    for cid, texts in by_chan.items():
        texts.sort(key=len, reverse=True)
        chosen = texts[:sample_size]
        spans[cid] = (len(flat), len(flat) + len(chosen))
        flat.extend(chosen)

    if not flat:
        return {}
    vecs = embedder.encode_texts(flat)
    out: dict[int, np.ndarray] = {}
    for cid, (lo, hi) in spans.items():
        if hi > lo:
            mean = vecs[lo:hi].mean(axis=0)
            norm = float(np.linalg.norm(mean))
            out[cid] = (mean / norm).astype(np.float32) if norm else mean.astype(np.float32)
    return out


async def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    out_subdir = mission.export.out_subdir
    out_path = (
        ROOT / "webapp" / "public" / "data" / out_subdir / f"{out_subdir}_embed_snapshot.json"
    )

    try:
        g, msgs = await _load_graph_and_messages()
    except (OSError, asyncpg.PostgresError):
        print("Wire-protocol PG injoignable → repli bundle + corpus messages REST")
        g, msgs = _load_graph_and_messages_from_bundle(out_subdir)
    print(f"Graphe : {g.number_of_nodes()} nœuds / {g.number_of_edges()} arêtes · "
          f"{len(msgs)} messages texte")

    embedder = Embedder(model_name=args.model)
    chan_emb = _channel_embeddings(embedder, msgs, args.sample_size)
    print(f"Embeddings canaux : {len(chan_emb)}")

    g_emb = add_embedding_edges(
        g, chan_emb, k=args.k, threshold=args.threshold, weight_scale=args.weight_scale
    )

    comm_a, mod_a = detect_communities(g)
    comm_e, mod_e = detect_communities(g_emb)
    snapshot = build_snapshot(g_emb, comm_e, mod_e)

    snapshot["label_source"] = "embedding"
    snapshot["model"] = embedder.model_name
    snapshot["stats"]["comparison"] = comparison_block(
        chan_emb, comm_a, comm_e, mod_a, mod_e, n_bridges=len(snapshot["bridges"])
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.push:
        from src.shared.snapshot_store import push_snapshot
        push_snapshot(out_subdir, "embedding", snapshot)
        print(f"Push Supabase : community_snapshots[{out_subdir}, embedding]")

    comp = snapshot["stats"]["comparison"]
    print(
        f"{snapshot['stats']['n_communities']} communautés · "
        f"cohésion intra {comp['intra_cohesion']['analytics']} → "
        f"{comp['intra_cohesion']['embedding']} "
        f"(gain {comp['intra_cohesion']['gain_pct']}%) · "
        f"modularité {comp['modularity']['analytics']} → {comp['modularity']['embedding']}"
    )
    print(f"Écrit : {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Snapshot communautés regroupées par embeddings.")
    add_mission_arg(ap)
    ap.add_argument("--sample-size", type=int, default=15, help="messages/canal pour l'embedding")
    ap.add_argument("--model", default=None, help="surcharge le modèle ST")
    ap.add_argument("--k", type=int, default=5, help="voisins sémantiques par canal")
    ap.add_argument("--threshold", type=float, default=0.5, help="cosinus min d'une arête EMB_SIM")
    ap.add_argument("--weight-scale", type=float, default=3.0, help="poids des arêtes d'embedding")
    ap.add_argument("--push", action="store_true",
                    help="pousse le snapshot (scrubbé) vers Supabase community_snapshots")
    asyncio.run(main(ap.parse_args()))
