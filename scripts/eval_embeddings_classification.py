"""Éval de la piste EMBEDDINGS — alias d'eval_mistral_classification --model <ST>.

Mêmes métriques (precision/recall/F1 vs gold, @K, Spearman, Jaccard@K vs la piste
Mistral, coût) ; on présélectionne simplement le filtre ``--model`` sur le modèle
sentence-transformers afin de n'évaluer que les lignes ``channel_llm_scores``
produites par ``scripts/classify_channels_embed.py``. Le gold humain est PARTAGÉ
avec la piste Mistral ⇒ comparaison directe « qualité ≥, coût 0 ».

Usage :
    python scripts/eval_embeddings_classification.py --mission gan
    python scripts/eval_embeddings_classification.py --mission gan --model sentence-transformers/…
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.embed.encoder import Embedder  # noqa: E402
from src.missions.loader import add_mission_arg  # noqa: E402

# `scripts/` n'est pas un package : on charge l'éval Mistral par chemin (convention).
_SPEC = importlib.util.spec_from_file_location(
    "eval_mistral_classification", ROOT / "scripts" / "eval_mistral_classification.py"
)
_EVAL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EVAL)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Éval piste embeddings vs gold + baseline.")
    add_mission_arg(ap)
    ap.add_argument("--target", default=None, help="slug gold (défaut: dérivé de la mission)")
    ap.add_argument("--k", type=int, nargs="+", default=[10, 20, 50], help="valeurs de K")
    ap.add_argument("--model", default=None, help="surcharge le modèle ST filtré")
    args = ap.parse_args()
    if not args.model:
        args.model = Embedder().model_name  # respecte IDEFIX_EMBED_MODEL
    asyncio.run(_EVAL.main(args))
