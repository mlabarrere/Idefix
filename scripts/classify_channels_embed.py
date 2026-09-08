"""Classification par canal via EMBEDDINGS LOCAUX — piste parallèle, gratuite.

Miroir local de ``scripts/classify_channels_llm.py`` : même sélection de canaux,
même échantillonnage, même table de sortie ``channel_llm_scores`` (schéma 0007
inchangé) — mais la classification vient d'un **embedding sentence-transformers
local** (coût 0, déterministe) au lieu de Mistral. On écrit avec un ``model``
distinct (le nom du modèle ST) ⇒ comparaison A/B directe avec la piste Mistral,
sans migration.

N'écrit JAMAIS dans ``channels``/``channel_scores``. Aucun appel réseau Telegram
ni API payante (lecture DB + inférence locale) ⇒ pas de ``run_lock``.

Usage :
    python scripts/classify_channels_embed.py --mission gan --limit 50 --dry-run
    python scripts/classify_channels_embed.py --mission gan --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import numpy as np  # noqa: E402
import structlog  # noqa: E402

from src.embed.centroids import build_centroids  # noqa: E402
from src.embed.classify import ACTOR_TYPE_ANCHORS, classify_channel  # noqa: E402
from src.embed.encoder import Embedder  # noqa: E402
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

log = structlog.get_logger(__name__)

EMBED_VERSION = "embed-v1"

# Mêmes requêtes que la piste Mistral (parité de sélection/échantillon/sortie).
_SAMPLE_Q = (
    "SELECT text FROM messages "
    "WHERE channel_id = $1 AND text IS NOT NULL AND length(text) > 20 "
    "ORDER BY length(text) DESC LIMIT $2"
)
_CHANNELS_Q = (
    "SELECT channel_id, username, title, "
    "       COALESCE((extra->>$1)::float, 0.0) AS rel "
    "FROM channels c "
    "WHERE EXISTS (SELECT 1 FROM messages m WHERE m.channel_id = c.channel_id "
    "             AND m.text IS NOT NULL AND length(m.text) > 20) "
    "  AND COALESCE((extra->>$1)::float, 0.0) >= $2 "
    "ORDER BY rel DESC, channel_id "
    "LIMIT $3"
)
_UPSERT_Q = (
    "INSERT INTO channel_llm_scores "
    "(mission, channel_id, model, prompt_version, is_gan_footprint, "
    " is_france_ukraine, actor_type, themes, confidence, rationale, "
    " request_hash, prompt_tokens, completion_tokens, est_cost_usd) "
    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10,$11,$12,$13,$14) "
    "ON CONFLICT (mission, channel_id, model, prompt_version) DO UPDATE SET "
    " is_gan_footprint=EXCLUDED.is_gan_footprint, "
    " is_france_ukraine=EXCLUDED.is_france_ukraine, "
    " actor_type=EXCLUDED.actor_type, themes=EXCLUDED.themes, "
    " confidence=EXCLUDED.confidence, rationale=EXCLUDED.rationale, "
    " request_hash=EXCLUDED.request_hash, prompt_tokens=EXCLUDED.prompt_tokens, "
    " completion_tokens=EXCLUDED.completion_tokens, est_cost_usd=EXCLUDED.est_cost_usd, "
    " computed_at=now()"
)


async def _sample(conn, channel_id: int, n: int) -> list[str]:
    rows = await conn.fetch(_SAMPLE_Q, channel_id, n)
    return [r["text"] for r in rows]


def _channel_vector(embedder: Embedder, samples: list[str]) -> np.ndarray:
    """Mean of message embeddings, L2-normalized -> one channel vector."""
    vecs = embedder.encode_texts(samples)
    mean = vecs.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return (mean / norm).astype(np.float32) if norm else mean.astype(np.float32)


def _request_hash(model: str, mission: str, channel_id: int, samples: list[str]) -> str:
    payload = json.dumps(
        {"model": model, "version": EMBED_VERSION, "mission": mission,
         "channel_id": channel_id, "samples": samples},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    signal = mission.scoring.relevance_signal

    embedder = Embedder(model_name=args.model)
    mission_centroids = build_centroids(
        embedder, mission.lexicon.categories, mission.lexicon.contextual_terms
    )
    actor_centroids = build_centroids(embedder, ACTOR_TYPE_ANCHORS, frozenset())

    conn = await db_connect()
    classified = skipped = 0
    try:
        rows = await conn.fetch(_CHANNELS_Q, signal, args.min_relevance, args.limit)
        print(
            f"[classify-embed] mission={mission.name} model={embedder.model_name} "
            f"version={EMBED_VERSION} · {len(rows)} canaux (signal={signal} "
            f">= {args.min_relevance}) · {len(mission_centroids)} centroïdes"
        )
        for r in rows:
            cid, uname = r["channel_id"], r["username"]
            samples = await _sample(conn, cid, args.sample_size)
            if not samples:
                skipped += 1
                continue

            vec = _channel_vector(embedder, samples)
            out = classify_channel(
                vec, mission_centroids, actor_centroids,
                mission_name=mission.name,
                theme_threshold=args.theme_threshold,
                flag_threshold=args.flag_threshold,
            )

            if args.dry_run:
                print(
                    f"  [dry-run] @{uname or cid} · {len(samples)} msgs · "
                    f"conf={out['confidence']} themes={out['themes']}"
                )
                classified += 1
                continue

            await conn.execute(
                _UPSERT_Q,
                mission.name, cid, embedder.model_name, EMBED_VERSION,
                out["is_gan_footprint"], out["is_france_ukraine"],
                out["actor_type"], json.dumps(out["themes"]),
                out["confidence"], out["rationale"],
                _request_hash(embedder.model_name, mission.name, cid, samples),
                0, 0, 0.0,  # tokens + cost = 0 (inférence locale)
            )
            classified += 1

        print(f"[classify-embed] terminé : {classified} classés, {skipped} sans texte · coût 0 USD")
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Classification par embeddings locaux (piste parallèle, gratuite)."
    )
    add_mission_arg(ap)
    ap.add_argument("--limit", type=int, default=50, help="nb de canaux (défaut 50)")
    ap.add_argument("--sample-size", type=int, default=40, help="messages/canal (défaut 40)")
    ap.add_argument(
        "--min-relevance", type=float, default=0.0,
        help="ne classer que les canaux dont extra->signal >= seuil",
    )
    ap.add_argument("--model", default=None, help="surcharge le modèle ST (IDEFIX_EMBED_MODEL)")
    ap.add_argument(
        "--theme-threshold", type=float, default=0.20,
        help="cosinus min pour retenir un thème (à calibrer)",
    )
    ap.add_argument(
        "--flag-threshold", type=float, default=0.30,
        help="cosinus min pour le drapeau cible is_<mission> (à calibrer)",
    )
    ap.add_argument("--dry-run", action="store_true", help="aucune écriture DB ; imprime")
    asyncio.run(main(ap.parse_args()))
