"""Peuple la table `edges` (graphe multiplex centré-canal) depuis PostgreSQL.

Brique de pipeline : dérive toutes les familles d'arêtes matérialisées à ce stade
(FORWARD / MENTIONS / CITES_DOMAIN / CO_FORWARD / CO_URL / CO_URL_EXACT / CO_HASHTAG /
MEDIA_REUSE) depuis les messages et le texte déjà stockés, puis UPSERT idempotent dans
la table `edges`. Lecture/écriture PostgreSQL uniquement — AUCUN appel Telegram (les
arêtes sont dérivées des données déjà en base). Parallèle de build_graph.py (qui, lui,
recalcule le forward à la volée en NetworkX et n'écrit rien).

Note : MEDIA_REUSE est câblé mais ne produit RIEN tant que `messages.media_hash` est NULL
(pas encore d'étape de téléchargement média — graph-model §4). Il s'activera tout seul une
fois les hashs média peuplés. CO_URL (domaine) et CO_URL_EXACT (URL complète) coexistent :
signaux distincts (host partagé vs deep-link identique).

La logique vit dans src/graph/edges.py (fonctions pures + I/O testées). Ce script n'est
qu'un point d'entrée CLI.

Usage :
    python scripts/build_edges.py                  # fenêtre de coordination par défaut (72h)
    python scripts/build_edges.py --window-hours 48
"""
import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv()  # edges.py (lib) lit DATABASE_URL depuis l'env ; le script charge .env

from src.graph.edges import DEFAULT_WINDOW_SECONDS, derive_and_upsert_edges  # noqa: E402


async def main(window_seconds: int, embed: bool, model: str | None) -> None:
    embedder = None
    if embed:
        # Lazy import: only require the `embed` extra (sentence-transformers) when
        # semantic edges are explicitly requested — the default path stays torch-free.
        from src.embed.encoder import Embedder

        embedder = Embedder(model_name=model)
    summary = await derive_and_upsert_edges(window_seconds=window_seconds, embedder=embedder)
    total = sum(summary.values())
    for edge_type, n in sorted(summary.items()):
        print(f"  {edge_type:14s} {n:6d}")
    hours = window_seconds // 3600
    print(f"\nTerminé : {total} arêtes upsertées (fenêtre coordination {hours} h).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dérive + UPSERT le graphe multiplex `edges`.")
    ap.add_argument("--window-hours", type=float, default=DEFAULT_WINDOW_SECONDS / 3600,
                    help="Fenêtre Δt de coordination (heures) pour CO_FORWARD / CO_URL.")
    ap.add_argument("--embed", action="store_true",
                    help="Dérive aussi les arêtes sémantiques TEXT_SIM/TRANSLATION "
                         "(embeddings locaux ; nécessite l'extra `embed`).")
    ap.add_argument("--model", default=None, help="surcharge le modèle ST (avec --embed)")
    args = ap.parse_args()
    asyncio.run(
        main(window_seconds=int(args.window_hours * 3600), embed=args.embed, model=args.model)
    )
