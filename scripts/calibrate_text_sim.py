"""Calibration des seuils TEXT_SIM / TRANSLATION pour le modèle d'embeddings local.

Les seuils par défaut (rewording 0.715 / translation 0.85) ont été seedés pour
D3lta/BGE-M3 : ils sont MODÈLE-SPÉCIFIQUES et n'ont pas de sens tels quels pour un
autre sentence-transformers. Ce script échantillonne des messages, calcule la
distribution des similarités cosinus entre paires de canaux distincts, et affiche
des percentiles + des exemples de paires autour de seuils candidats — pour que
l'analyste (Micky) fixe les coupures sur des données réelles plutôt qu'en aveugle.

Lecture DB + inférence locale uniquement (coût 0). Nécessite l'extra `embed`.

Usage :
    python scripts/calibrate_text_sim.py --limit 800
    python scripts/calibrate_text_sim.py --limit 800 --thresholds 0.6 0.7 0.8 0.9
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv()

import numpy as np  # noqa: E402

from src.embed.encoder import Embedder  # noqa: E402
from src.normalizer.handlers import clean_text  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

_Q = (
    "SELECT channel_id, language, text FROM messages "
    "WHERE text IS NOT NULL AND length(text) > 40 "
    "ORDER BY length(text) DESC LIMIT $1"
)


async def main(args: argparse.Namespace) -> None:
    conn = await db_connect()
    try:
        rows = await conn.fetch(_Q, args.limit)
    finally:
        await conn.close()

    items = [(r["channel_id"], r["language"], clean_text(r["text"])) for r in rows]
    items = [it for it in items if it[2]]
    if len(items) < 2:
        raise SystemExit("Pas assez de messages avec texte pour calibrer.")

    emb = Embedder(model_name=args.model)
    vecs = emb.encode_texts([it[2] for it in items])
    sim = vecs @ vecs.T

    iu, ju = np.triu_indices(len(items), k=1)
    # garder uniquement les paires inter-canaux (la coordination est inter-canal)
    cross_chan = np.array([items[i][0] != items[j][0] for i, j in zip(iu, ju)])
    s = sim[iu, ju][cross_chan]
    same_lang = np.array(
        [bool(items[i][1] and items[j][1] and items[i][1] == items[j][1])
         for i, j in zip(iu[cross_chan], ju[cross_chan])]
    )

    print(f"[calibrate] {len(items)} messages · {s.size} paires inter-canaux")
    for p in (50, 75, 90, 95, 99):
        print(f"  p{p:<2} sim = {np.percentile(s, p):.3f}")
    print(f"  même langue : {int(same_lang.sum())} paires · langue ≠ : {int((~same_lang).sum())}")

    for thr in args.thresholds:
        n = int((s >= thr).sum())
        n_cross = int((s[~same_lang] >= thr).sum())
        print(f"  seuil {thr:.2f} -> {n} paires (dont {n_cross} cross-langue ⇒ TRANSLATION)")

    # quelques exemples autour du seuil médian candidat
    mid = args.thresholds[len(args.thresholds) // 2]
    print(f"\nExemples de paires sim≈{mid:.2f} :")
    shown = 0
    order = np.argsort(-s)
    pair_idx = list(zip(iu[cross_chan].tolist(), ju[cross_chan].tolist()))
    for k in order:
        if shown >= 5:
            break
        if s[k] < mid:
            break
        i, j = pair_idx[k]
        print(f"  sim={s[k]:.3f} [{items[i][1]}|{items[j][1]}] "
              f"{items[i][2][:70]!r} ⇄ {items[j][2][:70]!r}")
        shown += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Calibration des seuils TEXT_SIM/TRANSLATION.")
    ap.add_argument("--limit", type=int, default=800, help="nb de messages échantillonnés")
    ap.add_argument("--model", default=None, help="surcharge le modèle ST")
    ap.add_argument("--thresholds", type=float, nargs="+", default=[0.6, 0.7, 0.8, 0.85, 0.9],
                    help="seuils candidats à inspecter")
    asyncio.run(main(ap.parse_args()))
