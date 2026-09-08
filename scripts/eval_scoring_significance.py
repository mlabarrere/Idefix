"""Validation du scoring RIGOUREUX vs gold niveau-canal + baseline de centralité.

Le livrable de rigueur : mesure si la suspicion rigoureuse (1 - p combinée, modulée)
sépare suspects/bénins MIEUX qu'une simple centralité — avec intervalles de Wilson,
ROC-AUC, significativité du classement par permutation, et courbe de calibration.

READ-ONLY : lit l'instantané statique (``data/channels.json`` + ``data/graph.json``,
convention ``_eval_common``) et ``data/eval/channel_gold.json``. Écrit le rapport
sous ``data/eval/``.

Usage :
    python scripts/build_scores.py --mission russosphere   # matérialise le bundle
    python scripts/derive_channel_gold.py --mission russosphere
    python scripts/eval_scoring_significance.py --k 20 50 100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

from _eval_common import EVAL_OUT, load_channels, load_graph, topk_set, write_report  # noqa: E402


def _norm(u: str | None) -> str | None:
    return u.lstrip("@").lower() if u else None


def _wilson(k: int, n: int) -> list[float]:
    if n <= 0:
        return [0.0, 0.0]
    from statsmodels.stats.proportion import proportion_confint

    lo, hi = proportion_confint(k, n, method="wilson")
    return [round(float(lo), 4), round(float(hi), 4)]


def _prf_at_k(ranked_keys: list[str], gold_pos: set[str], gold_all: set[str], k: int) -> dict:
    topk = [g for g in ranked_keys if g in gold_all][:k]
    hit = sum(1 for g in topk if g in gold_pos)
    prec = hit / len(topk) if topk else 0.0
    rec = hit / len(gold_pos) if gold_pos else 0.0
    return {
        "k": k, "tp": hit, "n_top": len(topk),
        "precision": round(prec, 4), "precision_wilson": _wilson(hit, len(topk)),
        "recall": round(rec, 4), "recall_wilson": _wilson(hit, len(gold_pos)),
    }


def main(args: argparse.Namespace) -> None:
    gold_path = EVAL_OUT / "channel_gold.json"
    if not gold_path.exists():
        raise SystemExit(
            f"Gold absent : {gold_path}. Lancer scripts/derive_channel_gold.py."
        )
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    pos = {_norm(c.get("username")) for c in gold["positives"] if c.get("username")}
    neg = {_norm(c.get("username")) for c in gold["negatives"] if c.get("username")}
    pos.discard(None)
    neg.discard(None)
    gold_all = pos | neg
    if not pos or not gold_all:
        raise SystemExit("Gold sans positifs exploitables (usernames manquants).")

    bundle = load_channels()
    chans = bundle.get("channels", bundle) if isinstance(bundle, dict) else bundle
    susp: dict[str, float] = {}
    flagged: set[str] = set()
    for c in chans:
        u = _norm(c.get("username"))
        if not u:
            continue
        susp[u] = float(c.get("suspicion", {}).get("v", 0.0))
        if c.get("flagged"):
            flagged.add(u)

    # Baseline de centralité (eigenvector) depuis graph.json (pattern ablation).
    base_score: dict[str, float] = {}
    try:
        g = load_graph()
        for n in g.get("nodes", []):
            u = _norm(n.get("username"))
            if u:
                base_score[u] = float(n.get("eigenvector", n.get("in_degree", 0)) or 0)
    except Exception:
        base_score = {}

    keys = [u for u in gold_all if u in susp]
    ranked_new = sorted(keys, key=lambda u: (-susp.get(u, 0.0), u))
    y = {u: (1 if u in pos else 0) for u in keys}

    at_k = {str(k): _prf_at_k(ranked_new, pos, gold_all, k) for k in args.k}

    # ROC-AUC nouveau vs baseline (si deux classes présentes).
    auc_new = auc_base = None
    if 0 < sum(y.values()) < len(y):
        try:
            from sklearn.metrics import roc_auc_score

            yt = [y[u] for u in keys]
            auc_new = round(float(roc_auc_score(yt, [susp.get(u, 0.0) for u in keys])), 4)
            if base_score:
                auc_base = round(
                    float(roc_auc_score(yt, [base_score.get(u, 0.0) for u in keys])), 4
                )
        except Exception:
            pass

    # Significativité du classement par permutation (recall@K_max vs aléatoire).
    import numpy as np

    rng = np.random.default_rng(1312)
    kmax = max(args.k)
    obs_top = topk_set(keys, [susp.get(u, 0.0) for u in keys], kmax)
    obs_hit = len(obs_top & pos)
    perm_hits = []
    labels = np.array([1 if u in pos else 0 for u in keys])
    for _ in range(args.permutations):
        rng.shuffle(labels)
        permpos = {keys[i] for i in range(len(keys)) if labels[i] == 1}
        perm_hits.append(len(obs_top & permpos))
    perm_p = (1 + int(np.count_nonzero(np.array(perm_hits) >= obs_hit))) / (args.permutations + 1)

    # Courbe de calibration : taux positif empirique par tranche de suspicion.
    bins = [(i / 5, (i + 1) / 5) for i in range(5)]
    calib = []
    for lo, hi in bins:
        members = [
            u for u in keys
            if lo <= susp.get(u, 0.0) < hi or (hi == 1.0 and susp.get(u, 0.0) == 1.0)
        ]
        if members:
            rate = sum(y[u] for u in members) / len(members)
            calib.append(
                {"bin": [round(lo, 2), round(hi, 2)], "n": len(members),
                 "positive_rate": round(rate, 4)}
            )

    flagged_pos = len(flagged & pos)
    base_better = auc_new is not None and auc_base is not None and auc_new > auc_base
    report = {
        "mission": args.mission,
        "gold_file": gold_path.name,
        "n_gold_positives": len(pos),
        "n_gold_negatives": len(neg),
        "n_matched_in_bundle": len(keys),
        "at_k": at_k,
        "roc_auc": {"rigorous": auc_new, "centrality_baseline": auc_base,
                    "baseline_outperformed": base_better},
        "ranking_permutation": {
            "observed_hits_at_kmax": obs_hit, "kmax": kmax, "p_value": round(perm_p, 4)},
        "calibration_curve": calib,
        "fdr_flagged": {"n_flagged": len(flagged), "flagged_positives": flagged_pos,
                        "precision": round(flagged_pos / len(flagged), 4) if flagged else None},
        "independence_statement": gold.get("independence_statement", ""),
    }
    out = write_report("scoring_significance.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nÉcrit : {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Validation du scoring rigoureux vs gold + baseline.")
    ap.add_argument("--mission", default="russosphere")
    ap.add_argument("--k", type=int, nargs="+", default=[20, 50, 100])
    ap.add_argument("--permutations", type=int, default=2000)
    main(ap.parse_args())
