"""Exp f — Embedding discrimination (organic-FR baseline vs scored channels).

Tests whether the embedding space separates organic FR channels from the scored
population. Measures ROC-AUC (baseline=0, scored=1), silhouette, and a t-SNE
projection.

>>> Non-circular: baseline channels are EXTERNAL to scorer inputs.
>>> Target ROC-AUC > 0.7.

DEFECT D11 (fixed 2026-09)
--------------------------
This script used to build its corpus as ``[f"@{u}" for u in usernames]`` — it
embedded **channel handles**, nothing else. The deployed family (f) embeds the
mean of a channel's longest MESSAGES. The experiment therefore did not test the
family it claimed to test, and its near-chance ROC-AUC measured only that
handle strings are arbitrary tokens.

It now calls ``src.scorer.embedding_signals.compute_channel_embeddings`` — the
exact function the scorer uses — so experiment and deployment share one code
path. This requires a database connection, since message text lives there.

It also refuses to report when the mission's anchors did not resolve: on that
failure the deployed family silently substitutes a zero vector, which inflates
every baseline distance to 1.0 (defect D10).

READ-ONLY on the database. Writes docs/experiments/results/.
Usage: python scripts/eval_embedding_discrimination.py [--mission russosphere]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _eval_common as ev  # noqa: E402

import numpy as np
from sklearn.manifold import TSNE
from sklearn.metrics import roc_auc_score, silhouette_score

from src.embed.encoder import Embedder  # noqa: E402
from src.scorer.embedding_signals import compute_channel_embeddings  # noqa: E402
from src.shared.db import close_pool, db_connection  # noqa: E402

BASELINE_PATH = _REPO / "data" / "eval" / "baseline_organic_fr.json"

# Sous ce nombre de canaux dans une classe, ni ROC-AUC ni silhouette ne sont
# interprétables. On refuse de produire un verdict plutôt que d'en inventer un.
MIN_PER_CLASS = 10


def _norm(u: str) -> str:
    return (u or "").lstrip("@").lower()


async def _run(mission: str) -> None:
    # Load baseline
    if not BASELINE_PATH.exists():
        print(f"[ERROR] Baseline not found: {BASELINE_PATH}")
        print("Run: python scripts/bootstrap_baseline.py")
        sys.exit(1)

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_usernames = {_norm(c["username"]) for c in baseline["channels"]}
    print(f"[baseline] {len(baseline_usernames)} canaux organiques FR chargés")

    # Load scored channels
    ch = ev.load_channels()["channels"]
    scored_usernames = {_norm(c.get("username")) for c in ch if c.get("username")}
    print(f"[scored] {len(scored_usernames)} canaux scorés chargés")

    # Remove overlap (sanity check — should be zero)
    overlap = baseline_usernames & scored_usernames
    if overlap:
        print(f"[WARNING] {len(overlap)} canaux en commun baseline/scored: {overlap}")
        baseline_usernames -= overlap

    # --- D11 fix: embed MESSAGE CONTENT, via the deployed code path ---------
    # ``compute_channel_embeddings`` is the same function family (f) uses at
    # scoring time: mean of a channel's longest messages, L2-renormalized.
    emb = Embedder()
    async with db_connection() as conn:
        chan_emb = await compute_channel_embeddings(conn, emb)
        id_by_username = {
            _norm(r["username"]): r["channel_id"]
            for r in await conn.fetch(
                "SELECT channel_id, username FROM channels WHERE username IS NOT NULL"
            )
        }
    print(f"[embed] {len(chan_emb)} canaux encodés depuis le CONTENU des messages")

    # Keep only channels we could actually represent. A channel with no message
    # text has no embedding; counting it as a miss would confound coverage with
    # separability.
    usable, labels_list = [], []
    missing_baseline = missing_scored = 0
    for u in sorted(baseline_usernames | scored_usernames):
        cid = id_by_username.get(u)
        if cid is None or cid not in chan_emb:
            if u in scored_usernames:
                missing_scored += 1
            else:
                missing_baseline += 1
            continue
        usable.append(cid)
        labels_list.append(1 if u in scored_usernames else 0)

    labels = np.array(labels_list, dtype=int)
    n_base, n_scored = int(np.sum(labels == 0)), int(np.sum(labels == 1))
    print(
        f"[corpus] {len(usable)} canaux exploitables "
        f"(baseline={n_base}, scored={n_scored}; "
        f"sans contenu: baseline={missing_baseline}, scored={missing_scored})"
    )

    if n_base < MIN_PER_CLASS or n_scored < MIN_PER_CLASS:
        report = {
            "experiment": "embedding_discrimination",
            "mission": mission,
            "status": "NON CONCLUANT",
            "reason": (
                f"classes trop petites après filtrage sur le contenu "
                f"(baseline={n_base}, scored={n_scored}, minimum {MIN_PER_CLASS}). "
                f"Ni ROC-AUC ni silhouette ne sont interprétables."
            ),
            "baseline_count": n_base,
            "scored_count": n_scored,
            "channels_without_text": {
                "baseline": missing_baseline, "scored": missing_scored
            },
        }
        out = ev.write_report(f"embedding_discrimination_{mission}.json", report)
        print(f"[Exp f] NON CONCLUANT -> {out}")
        return

    vecs = np.vstack([chan_emb[cid] for cid in usable]).astype(np.float32)
    print(f"[embed] done — shape {vecs.shape}")

    # Distance stats
    baseline_vecs = vecs[labels == 0]
    scored_vecs = vecs[labels == 1]
    baseline_centroid = np.mean(baseline_vecs, axis=0) if len(baseline_vecs) > 0 else np.zeros(vecs.shape[1])
    scored_centroid = np.mean(scored_vecs, axis=0) if len(scored_vecs) > 0 else np.zeros(vecs.shape[1])

    baseline_dists = np.linalg.norm(baseline_vecs - baseline_centroid, axis=1) if len(baseline_vecs) > 0 else []
    scored_dists = np.linalg.norm(scored_vecs - scored_centroid, axis=1) if len(scored_vecs) > 0 else []

    baseline_mean_dist = float(np.mean(baseline_dists)) if len(baseline_dists) > 0 else 0.0
    scored_mean_dist = float(np.mean(scored_dists)) if len(scored_dists) > 0 else 0.0
    centroid_separation = float(np.linalg.norm(baseline_centroid - scored_centroid))

    # Separability metrics
    # ROC-AUC: distance to scored centroid as discriminant score (closer to scored = higher score)
    dist_to_scored = np.linalg.norm(vecs - scored_centroid, axis=1)
    roc_auc = float(roc_auc_score(labels, -dist_to_scored))  # negate: closer = higher score
    sil = float(silhouette_score(vecs, labels)) if len(np.unique(labels)) > 1 else 0.0

    # t-SNE visualization
    print("[tsne] projecting to 2D...")
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, max(2, len(usable) // 2)))
    vecs_2d = tsne.fit_transform(vecs)

    # Save plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 8))
        for label, color, name in [(0, "blue", "baseline"), (1, "red", "scored")]:
            mask = labels == label
            plt.scatter(vecs_2d[mask, 0], vecs_2d[mask, 1], c=color, alpha=0.6, s=30, label=name)
        plt.xlabel("t-SNE dim 1")
        plt.ylabel("t-SNE dim 2")
        plt.title(f"Embedding Discrimination: {mission} (baseline={np.sum(labels == 0)}, scored={np.sum(labels == 1)})")
        plt.legend()
        plt.grid(alpha=0.3)
        out_png = ev.EVAL_OUT / f"embedding_discrimination_{mission}.png"
        plt.savefig(out_png, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[tsne] plot saved -> {out_png}")
    except ImportError:
        print("[WARNING] matplotlib not available, skipping plot")
        out_png = None

    # Report
    report = {
        "experiment": "embedding_discrimination",
        "mission": mission,
        "baseline_count": int(np.sum(labels == 0)),
        "scored_count": int(np.sum(labels == 1)),
        "total": len(usable),
        "representation": "mean of longest messages (deployed family (f) path)",
        "channels_without_text": {
            "baseline": missing_baseline, "scored": missing_scored
        },
        "roc_auc": round(roc_auc, 4),
        "silhouette": round(sil, 4),
        "baseline_mean_distance": round(baseline_mean_dist, 4),
        "scored_mean_distance": round(scored_mean_dist, 4),
        "centroid_separation": round(centroid_separation, 4),
        "tsne_plot": str(out_png) if out_png else None,
        "verdict": (
            "FAIBLE (ROC-AUC < 0.7 ou silhouette < 0.3 — embedding ne sépare pas baseline/scored)"
            if roc_auc < 0.7 or sil < 0.3
            else "DISCRIMINANT (ROC-AUC ≥ 0.7, silhouette ≥ 0.3)"
        ),
        "note": (
            "Baseline organique FR (externe) vs scored channels, encodés sur le "
            "CONTENU des messages via le chemin de code de la famille (f) "
            "déployée. ROC-AUC cible > 0.7."
        ),
    }

    p = ev.write_report(f"embedding_discrimination_{mission}.json", report)
    print(f"[Exp3 discrimination] écrit -> {p}")
    print(f"  ROC-AUC: {report['roc_auc']} | Silhouette: {report['silhouette']} | {report['verdict']}")
    print(f"  Baseline mean dist: {report['baseline_mean_distance']} | Scored mean dist: {report['scored_mean_distance']}")
    print(f"  Centroid separation: {report['centroid_separation']}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mission", default="russosphere", help="Mission ID (default: russosphere)"
    )
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.mission))
    finally:
        asyncio.run(close_pool())


if __name__ == "__main__":
    main()
