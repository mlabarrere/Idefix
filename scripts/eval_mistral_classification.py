"""Évaluation « Mistral seul » vs gold humain + baseline lexical — LE LIVRABLE.

Mesure si la classification Mistral (table ``channel_llm_scores``) identifie
l'empreinte GAN / les narratifs France×Ukraine, comparée :
  1. au GOLD humain indépendant (``data/eval/gold_<target>.json``) → precision/
     recall/F1 (global + @K), matrice de confusion ``actor_type`` ;
  2. au BASELINE lexical (signal de pertinence du bundle / ``channels.extra``) →
     accord Jaccard top-K + Spearman(confiance Mistral, pertinence lexicale).
Plus le COÛT (somme ``est_cost_usd``) — réponse chiffrée à « à quel prix ».

READ-ONLY : lit ``channel_llm_scores`` + ``channels`` (DB) et le gold (fichier).
Écrit le rapport sous ``data/eval/`` via ``_eval_common.write_report``.

Usage :
    python scripts/eval_mistral_classification.py --mission gan
    python scripts/eval_mistral_classification.py --mission france_ukraine --k 10 20 50
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

sys.path.insert(0, str(_ROOT / "scripts"))
from _eval_common import EVAL_OUT, jaccard, spearman, topk_set, write_report  # noqa: E402

# Champ booléen Mistral selon la mission (override via --target).
_TARGET_FIELD = {
    "gan": ("gan_footprint", "is_gan_footprint"),
    "france_ukraine": ("france_ukraine", "is_france_ukraine"),
    "russosphere": ("france_ukraine", "is_france_ukraine"),
}

_PRED_Q = (
    "SELECT l.channel_id, c.username, "
    " l.is_gan_footprint, l.is_france_ukraine, l.actor_type, l.confidence, "
    " l.est_cost_usd, COALESCE((c.extra->>$2)::float, 0.0) AS rel "
    "FROM channel_llm_scores l JOIN channels c USING (channel_id) "
    "WHERE l.mission = $1"
)


def _norm(u: str | None) -> str:
    return (u or "").lstrip("@").lower()


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn}


async def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    signal = mission.scoring.relevance_signal
    target_slug, bool_field = _TARGET_FIELD.get(
        mission.name, ("france_ukraine", "is_france_ukraine")
    )
    if args.target:
        target_slug = args.target
        bool_field = "is_gan_footprint" if "gan" in target_slug else "is_france_ukraine"

    gold_path = EVAL_OUT / f"gold_{target_slug}.json"
    if not gold_path.exists():
        raise SystemExit(
            f"Gold absent : {gold_path}\n"
            f"Copier data/eval/templates/gold_{target_slug}.example.json → {gold_path} "
            f"et remplir les étiquettes humaines."
        )
    gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))
    gold = {_norm(c["username"]): c for c in gold_doc.get("channels", [])}

    query = _PRED_Q
    params: list = [mission.name, signal]
    if args.model:
        query += " AND l.model = $3"
        params.append(args.model)

    conn = await db_connect()
    try:
        rows = await conn.fetch(query, *params)
    finally:
        await conn.close()

    if not rows:
        which = f"model={args.model} " if args.model else ""
        raise SystemExit(
            f"Aucune classification {which}pour mission={mission.name}. "
            f"Lancer d'abord scripts/classify_channels_llm.py (Mistral) ou "
            f"scripts/classify_channels_embed.py (embeddings) --mission {mission.name}."
        )

    # Prédictions indexées par username.
    preds: dict[str, dict] = {}
    for r in rows:
        preds[_norm(r["username"])] = {
            "channel_id": r["channel_id"],
            "pred": bool(r[bool_field]) if r[bool_field] is not None else False,
            "actor_type": r["actor_type"],
            "confidence": float(r["confidence"] or 0.0),
            "rel": float(r["rel"] or 0.0),
            "cost": float(r["est_cost_usd"] or 0.0),
        }

    # ── 1. PRF vs gold (sur les canaux gold ET classés) ──
    tp = fp = fn = 0
    confusion: dict[str, dict[str, int]] = {}
    matched = 0
    for u, g in gold.items():
        if u not in preds:
            continue
        matched += 1
        gt = bool(g.get("is_target"))
        pr = preds[u]["pred"]
        tp += int(gt and pr)
        fp += int(pr and not gt)
        fn += int(gt and not pr)
        # matrice de confusion actor_type (gold vs prédit)
        ga = g.get("actor_type") or "?"
        pa = preds[u]["actor_type"] or "?"
        confusion.setdefault(ga, {}).setdefault(pa, 0)
        confusion[ga][pa] += 1

    prf = _prf(tp, fp, fn)

    # ── precision/recall @K (rang par confiance Mistral sur la classe positive) ──
    ids = list(preds.keys())
    conf = [preds[u]["confidence"] if preds[u]["pred"] else 0.0 for u in ids]
    gold_pos = {u for u, g in gold.items() if g.get("is_target") and u in preds}
    at_k = {}
    for k in args.k:
        topk = topk_set(ids, conf, k)
        hit = len(topk & gold_pos)
        denom_p = len(topk) or 1
        denom_r = len(gold_pos) or 1
        at_k[str(k)] = {
            "precision_at_k": round(hit / denom_p, 4),
            "recall_at_k": round(hit / denom_r, 4),
        }

    # ── 2. Accord vs baseline lexical ──
    rels = [preds[u]["rel"] for u in ids]
    confs_all = [preds[u]["confidence"] for u in ids]
    agreement = {
        "spearman_confidence_vs_lexical_relevance": round(spearman(confs_all, rels), 4),
        "jaccard_topk": {},
    }
    for k in args.k:
        mistral_top = topk_set(ids, confs_all, k)
        lexical_top = topk_set(ids, rels, k)
        agreement["jaccard_topk"][str(k)] = round(jaccard(mistral_top, lexical_top), 4)

    # ── 3. Coût ──
    total_cost = round(sum(p["cost"] for p in preds.values()), 6)
    cost = {
        "channels_classified": len(preds),
        "total_est_cost_usd": total_cost,
        "cost_per_channel_usd": round(total_cost / len(preds), 6) if preds else 0.0,
    }

    report = {
        "mission": mission.name,
        "model_filter": args.model,
        "target": target_slug,
        "bool_field": bool_field,
        "relevance_signal": signal,
        "gold_file": gold_path.name,
        "gold_size": len(gold),
        "matched_gold_and_classified": matched,
        "prf_vs_gold": prf,
        "at_k": at_k,
        "actor_type_confusion": confusion,
        "agreement_vs_lexical_baseline": agreement,
        "cost": cost,
        "verdict_hint": (
            "Mistral seul utile si recall élevé sur le gold ET Jaccard faible vs "
            "baseline lexical (=> il capte ce que le lexique manque), à coût maîtrisé."
        ),
    }
    tag = "embed" if (args.model and "sentence-transformers" in args.model) else "mistral"
    out = write_report(f"{tag}_classification_{mission.name}.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nÉcrit : {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Éval Mistral vs gold + baseline lexical.")
    add_mission_arg(ap)
    ap.add_argument("--target", default=None, help="slug gold (défaut: dérivé de la mission)")
    ap.add_argument("--k", type=int, nargs="+", default=[10, 20, 50], help="valeurs de K")
    ap.add_argument(
        "--model", default=None,
        help="filtre channel_llm_scores.model (ex. un nom sentence-transformers/… "
        "pour évaluer la piste embeddings au lieu de Mistral)",
    )
    asyncio.run(main(ap.parse_args()))
