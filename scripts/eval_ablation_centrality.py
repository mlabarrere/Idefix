"""Exp 1 — Ablation null-baseline : le score de suspicion est-il PLUS que de la
centralité / activité de graphe ? (le falsificateur le moins cher : 0 label).

FALSIFIÉ si, pour la centralité brute (in-degree OU eigenvector) :
    Spearman(suspicion, centralité) > 0.90   OU   Jaccard(top-50) > 0.80
=> le score serait « de la centralité maquillée ».

READ-ONLY. Lit l'instantané data/channels.json + data/graph.json (le graphe sur
lequel les scores ont été matérialisés — pas la DB live). Écrit
data/eval/ablation_centrality.json et imprime un verdict PASS / FALSIFIED.

Usage : python scripts/eval_ablation_centrality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import networkx as nx  # noqa: E402

import _eval_common as ev  # noqa: E402
from src.scorer.cascade_role import compute_bridge_scores  # noqa: E402

FALSIFY_SPEARMAN = 0.90
FALSIFY_JACCARD = 0.80


def _forward_digraph_from_graph_json(g: dict) -> nx.DiGraph:
    """Rebuild le DiGraph de forward (origin -> relayer, weight=count) depuis
    les arêtes FORWARD de data/graph.json — même orientation que
    src.scorer.channel_suspicion.forward_digraph."""
    d = nx.DiGraph()
    for e in g["edges"]:
        if e.get("type") != "FORWARD":
            continue
        u, v = e.get("source"), e.get("target")
        if u is None or v is None or u == v:
            continue
        c = int(e.get("count") or 0)
        if d.has_edge(u, v):
            d.edges[u, v]["count"] += c
        else:
            d.add_edge(u, v, count=c)
    return d


def main() -> None:
    ch = ev.load_channels()["channels"]
    g = ev.load_graph()

    engagement = {
        n["channel_id"]: (n.get("engagement") or 0)
        for n in g["nodes"]
        if "channel_id" in n
    }
    fwd = _forward_digraph_from_graph_json(g)
    bridge = compute_bridge_scores(fwd)  # {cid: {in_centrality, eigenvector, out_weight, ...}}

    ids = [c["channel_id"] for c in ch]
    suspicion = [(c.get("suspicion") or {}).get("v") or 0.0 for c in ch]

    baselines = {
        "in_degree_centrality": [bridge.get(c, {}).get("in_centrality", 0.0) for c in ids],
        "eigenvector_centrality": [bridge.get(c, {}).get("eigenvector", 0.0) for c in ids],
        "forward_influence_out_weight": [bridge.get(c, {}).get("out_weight", 0.0) for c in ids],
        "activity_engagement": [engagement.get(c, 0) for c in ids],
        "cascade_family_value_composite": [
            ((c.get("_components") or {}).get("b") or {}).get("value") or 0.0 for c in ch
        ],
    }

    susp_top = {k: ev.topk_set(ids, suspicion, k) for k in (20, 50)}
    order = sorted(range(len(ids)), key=lambda i: suspicion[i], reverse=True)
    top50_idx = order[:50]

    report = {
        "experiment": "centrality_activity_null_baseline_ablation",
        "snapshot": ev.load_channels().get("generated_at"),
        "n_channels": len(ids),
        "nonzero_suspicion": sum(1 for s in suspicion if s > 0),
        "forward_graph": {"nodes": fwd.number_of_nodes(), "edges": fwd.number_of_edges()},
        "falsify_thresholds": {"spearman": FALSIFY_SPEARMAN, "jaccard_top50": FALSIFY_JACCARD},
        "spearman": {},
        "topk_jaccard": {"20": {}, "50": {}},
        "head_spearman_top50": {},
    }

    for name, vals in baselines.items():
        report["spearman"][name] = round(ev.spearman(suspicion, vals), 4)
        for k in (20, 50):
            report["topk_jaccard"][str(k)][name] = round(
                ev.jaccard(susp_top[k], ev.topk_set(ids, vals, k)), 4
            )
        report["head_spearman_top50"][name] = round(
            ev.spearman([suspicion[i] for i in top50_idx], [vals[i] for i in top50_idx]), 4
        )

    cent_keys = ["in_degree_centrality", "eigenvector_centrality"]
    falsified = any(
        report["spearman"][k] > FALSIFY_SPEARMAN
        or report["topk_jaccard"]["50"][k] > FALSIFY_JACCARD
        for k in cent_keys
    )
    report["falsified"] = falsified
    report["verdict"] = "FALSIFIED" if falsified else "PASS"

    p = ev.write_report("ablation_centrality.json", report)

    print(f"[Exp1 ablation] VERDICT = {report['verdict']}  ->  {p}")
    print(f"  graphe forward: {fwd.number_of_nodes()} noeuds / {fwd.number_of_edges()} aretes ; "
          f"{report['nonzero_suspicion']}/{len(ids)} canaux a suspicion > 0")
    for name in baselines:
        print(f"  Spearman(suspicion, {name:32}) = {report['spearman'][name]:+.3f} | "
              f"Jaccard@50 = {report['topk_jaccard']['50'][name]:.3f} | "
              f"head@50 = {report['head_spearman_top50'][name]:+.3f}")
    print(f"  Falsifie si (centralite) Spearman>{FALSIFY_SPEARMAN} OU Jaccard@50>{FALSIFY_JACCARD}")


if __name__ == "__main__":
    main()
