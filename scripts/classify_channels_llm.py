"""Classification par canal via Mistral — PISTE PARALLÈLE (Jalon 1).

Échantillonne les messages texte d'un canal, demande à Mistral une classification
haut-niveau (``is_gan_footprint`` / ``is_france_ukraine`` / ``actor_type`` /
``themes`` / ``confidence`` / ``rationale``) et UPSERT le résultat dans la table
dédiée ``channel_llm_scores`` (idempotent ; cache offline ⇒ re-runs gratuits).

N'écrit JAMAIS dans ``channels``/``channel_scores`` : le score explicable et le
bundle ``russosphere`` par défaut restent intacts. AUCUN appel Telegram (lecture DB
seule + appels Mistral) ⇒ pas de ``run_lock``.

Usage :
    python scripts/classify_channels_llm.py --mission gan --limit 50 --dry-run
    python scripts/classify_channels_llm.py --mission gan --limit 50 --budget-usd 2.0
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

import structlog  # noqa: E402

from src.llm.mistral import MistralClient, resolve_model  # noqa: E402
from src.llm.prompts import (  # noqa: E402
    CHANNEL_CLASSIFY_SYSTEM,
    CHANNEL_SCHEMA,
    PROMPT_VERSION,
    channel_user_prompt,
)
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

log = structlog.get_logger(__name__)

# Échantillon : messages les plus substantiels (pattern eval_france_targeting_audit).
_SAMPLE_Q = (
    "SELECT text FROM messages "
    "WHERE channel_id = $1 AND text IS NOT NULL AND length(text) > 20 "
    "ORDER BY length(text) DESC LIMIT $2"
)

# Sélection des canaux à classer, classés par pertinence de mission (extra->signal).
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


async def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    signal = mission.scoring.relevance_signal
    model = args.model or resolve_model()

    conn = await db_connect()
    classified = skipped = 0
    try:
        rows = await conn.fetch(_CHANNELS_Q, signal, args.min_relevance, args.limit)
        print(
            f"[classify] mission={mission.name} model={model} "
            f"prompt={PROMPT_VERSION} · {len(rows)} canaux (signal={signal} "
            f">= {args.min_relevance})"
        )
        if not rows:
            return

        async with MistralClient(model=model) as client:
            for r in rows:
                cid, uname, title = r["channel_id"], r["username"], r["title"]
                samples = await _sample(conn, cid, args.sample_size)
                if not samples:
                    skipped += 1
                    continue
                user = channel_user_prompt(
                    username=uname or "", title=title or "",
                    mission=mission.name, samples=samples,
                )

                if args.dry_run:
                    approx_tok = (len(CHANNEL_CLASSIFY_SYSTEM) + len(user)) // 4
                    print(
                        f"  [dry-run] @{uname or cid} · {len(samples)} msgs "
                        f"· ~{approx_tok} tok in"
                    )
                    classified += 1
                    continue

                res = await client.complete(
                    system=CHANNEL_CLASSIFY_SYSTEM, user=user,
                    json_mode=True, schema=CHANNEL_SCHEMA,
                )
                p = res.parsed or {}
                await conn.execute(
                    _UPSERT_Q,
                    mission.name, cid, res.model, res.prompt_version,
                    _as_bool(p.get("is_gan_footprint")),
                    _as_bool(p.get("is_france_ukraine")),
                    _as_str(p.get("actor_type")),
                    json.dumps(p.get("themes") or []),
                    _as_float(p.get("confidence")),
                    _as_str(p.get("rationale")),
                    res.request_hash,
                    res.usage.prompt_tokens, res.usage.completion_tokens,
                    res.usage.est_cost_usd,
                )
                classified += 1

                if args.budget_usd and client.totals.est_cost_usd >= args.budget_usd:
                    print(
                        f"  [budget] plafond {args.budget_usd} USD atteint "
                        f"(coût≈{client.totals.est_cost_usd}) — arrêt."
                    )
                    break

            print(
                f"[classify] terminé : {classified} classés, {skipped} sans texte "
                f"· coût≈{client.totals.est_cost_usd} USD "
                f"({client.totals.total_tokens} tokens)"
            )
    finally:
        await conn.close()


def _as_bool(v):
    return bool(v) if isinstance(v, bool) else None


def _as_float(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


def _as_str(v):
    return str(v) if v is not None else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Classification Mistral par canal (piste parallèle).")
    add_mission_arg(ap)
    ap.add_argument("--limit", type=int, default=50, help="nb de canaux (défaut 50)")
    ap.add_argument("--sample-size", type=int, default=40, help="messages/canal (défaut 40)")
    ap.add_argument(
        "--min-relevance", type=float, default=0.0,
        help="filtre coût : ne classer que les canaux dont extra->signal >= seuil",
    )
    ap.add_argument("--model", default=None, help="surcharge MISTRAL_MODEL")
    ap.add_argument("--dry-run", action="store_true", help="aucun réseau ; imprime les prompts")
    ap.add_argument("--budget-usd", type=float, default=0.0, help="plafond coût estimé (0=illim.)")
    asyncio.run(main(ap.parse_args()))
