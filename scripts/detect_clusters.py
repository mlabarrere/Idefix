"""Détection automatique de grappes coordonnées sur le graphe de forward réel.

Idée (Micky 2026-06-03) : partir d'un point X, étendre à K hops, repérer les motifs.
1) charge le graphe de forward depuis PostgreSQL (origine -> relayeur, pondéré),
2) optionnel : restreint au voisinage à K hops d'un canal seed X,
3) détection de communautés (igraph, multilevel/Louvain pondéré),
4) score chaque communauté sur des motifs de coordination,
5) sort les grappes classées + le « pourquoi ».

Aucun appel Telegram. Lecture seule PostgreSQL. NetworkX/igraph (pas de Neo4j/Kùzu).

Usage:
    python scripts/detect_clusters.py                 # tout le graphe
    python scripts/detect_clusters.py --seed @Dugin_Aleksandr --hops 5
"""
import argparse, asyncio
from collections import defaultdict
from src.shared.db import db_connect
import igraph as ig
from dotenv import load_dotenv
load_dotenv()


async def load_graph():
    conn = await db_connect()
    chans = await conn.fetch(
        "SELECT channel_id, username, title, (extra->>'fr_score')::float AS fr FROM channels")
    edges = await conn.fetch("""
        SELECT forward_from_channel_id AS origin, channel_id AS reposter, count(*) AS n
        FROM messages
        WHERE forward_from_channel_id IS NOT NULL
          AND forward_from_channel_id <> channel_id
        GROUP BY 1, 2
    """)
    await conn.close()
    meta = {r["channel_id"]: {"username": r["username"], "title": r["title"],
                              "fr": r["fr"] if r["fr"] is not None else None} for r in chans}
    return meta, [(e["origin"], e["reposter"], e["n"]) for e in edges]


def build_igraph(meta, edges):
    nodes = sorted({n for e in edges for n in (e[0], e[1])})
    idx = {n: i for i, n in enumerate(nodes)}
    # directed edges kept for co-forwarding; undirected weighted for communities
    g = ig.Graph(n=len(nodes), directed=False)
    g.vs["cid"] = nodes
    w = defaultdict(int)
    for o, r, n in edges:
        a, b = sorted((idx[o], idx[r]))
        w[(a, b)] += n
    g.add_edges(list(w.keys()))
    g.es["weight"] = list(w.values())
    # per-reposter set of origins (for co-forwarding within a community)
    origins_of = defaultdict(set)
    for o, r, n in edges:
        origins_of[r].add(o)
    return g, idx, nodes, origins_of


def ego_subgraph(g, idx, seed_cid, hops):
    if seed_cid not in idx:
        raise SystemExit(f"Seed {seed_cid} absent du graphe.")
    vs = g.neighborhood(vertices=idx[seed_cid], order=hops)
    return g.induced_subgraph(vs)


def name_of(meta, cid):
    m = meta.get(cid, {})
    return ("@" + m["username"]) if m.get("username") else (m.get("title") or f"id={cid}")


def analyse(g, meta, origins_of):
    if g.vcount() == 0 or g.ecount() == 0:
        print("Graphe vide."); return
    comms = g.community_multilevel(weights="weight")
    clusters = []
    for ci, members in enumerate(comms):
        if len(members) < 3:
            continue
        cids = [g.vs[m]["cid"] for m in members]
        sub = g.induced_subgraph(members)
        n = len(members)
        internal_fwd = sum(sub.es["weight"]) if sub.ecount() else 0
        density = sub.density()
        # co-forwarding : origines forwardées par >=2 membres de la grappe
        cnt = defaultdict(int)
        for cid in cids:
            for o in origins_of.get(cid, ()):
                cnt[o] += 1
        shared_origins = sum(1 for v in cnt.values() if v >= 2)
        frs = [meta[c]["fr"] for c in cids if meta.get(c, {}).get("fr") is not None]
        fr_mean = round(sum(frs) / len(frs), 3) if frs else None
        # canal le plus central (degré pondéré) = "tête" de la grappe
        deg = sub.strength(weights="weight")
        lead = cids[max(range(n), key=lambda i: deg[i])]
        score = round(0.45 * min(internal_fwd / 100, 1) + 0.35 * min(shared_origins / 10, 1)
                      + 0.20 * density, 3)
        clusters.append({"n": n, "internal_fwd": internal_fwd, "density": round(density, 3),
                         "shared_origins": shared_origins, "fr_mean": fr_mean,
                         "lead": lead, "cids": cids, "score": score})
    clusters.sort(key=lambda c: -c["score"])

    print(f"\n{g.vcount()} canaux, {g.ecount()} liens → {len(clusters)} grappe(s) ≥3 détectée(s)\n")
    for rank, c in enumerate(clusters, 1):
        fr = "n/a" if c["fr_mean"] is None else c["fr_mean"]
        print(f"#{rank}  score={c['score']}  | {c['n']} canaux · forwards internes={c['internal_fwd']} "
              f"· sources partagées={c['shared_origins']} · densité={c['density']} · fr_moyen={fr}")
        print(f"     tête : {name_of(meta, c['lead'])}")
        membres = ", ".join(name_of(meta, x) for x in sorted(c["cids"], key=lambda x:-(meta.get(x,{}).get('fr') or 0))[:10])
        print(f"     membres : {membres}{' …' if c['n']>10 else ''}")
        # pourquoi
        flags = []
        if c["shared_origins"] >= 3: flags.append(f"co-forwarding fort ({c['shared_origins']} sources communes)")
        if c["internal_fwd"] >= 50: flags.append(f"forwarding interne intense ({c['internal_fwd']})")
        if c["fr_mean"] is not None and c["fr_mean"] < 0.15: flags.append("hors-France (réseau étranger)")
        if c["fr_mean"] is not None and c["fr_mean"] >= 0.15: flags.append("orienté France")
        print(f"     pourquoi : {'; '.join(flags) or 'signal faible'}\n")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", help="canal de départ X (@handle)", default=None)
    ap.add_argument("--hops", type=int, default=5)
    args = ap.parse_args()

    meta, edges = await load_graph()
    g, idx, nodes, origins_of = build_igraph(meta, edges)

    if args.seed:
        seed_cid = next((c for c, m in meta.items()
                         if m.get("username") and m["username"].lower() == args.seed.lstrip("@").lower()), None)
        if seed_cid is None:
            raise SystemExit(f"Seed {args.seed} introuvable dans les canaux.")
        print(f"Voisinage à {args.hops} hops depuis {args.seed} …")
        g = ego_subgraph(g, idx, seed_cid, args.hops)
    else:
        print("Détection sur l'ensemble du graphe de forward …")

    analyse(g, meta, origins_of)

asyncio.run(main())
