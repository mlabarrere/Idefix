"""Étiquetage de communautés via Mistral — PISTE PARALLÈLE (Jalon 1).

Lit le snapshot LEXICAL de communautés (baseline taxonomie regex × IDF, produit par
``scripts/analyze_communities.py``) et, pour chaque communauté, agrège ses top-N
canaux représentatifs + leurs classifications par-canal (table ``channel_llm_scores``)
pour demander à Mistral UN label thématique haut-niveau.

Écrit un snapshot PARALLÈLE ``<mission>_llm_snapshot.json`` qui MIROITE la forme du
snapshot lexical (communities/bridges/meta_graph/stats) afin de permettre un diff
champ-à-champ (frontend + éval). Le snapshot lexical n'est JAMAIS modifié.

Les champs ``label``/``rationale`` exportés passent par
``src.labeling.aggregate._redact_providers`` (garde-fou #6 : aucun nom de
fournisseur dans un export).

Usage :
    python scripts/label_communities_llm.py --mission russosphere --top-n 6 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import structlog  # noqa: E402

from src.labeling.aggregate import _redact_providers  # noqa: E402
from src.llm.mistral import MistralClient, resolve_model  # noqa: E402
from src.llm.prompts import (  # noqa: E402
    COMMUNITY_LABEL_SYSTEM,
    COMMUNITY_SCHEMA,
    PROMPT_VERSION,
    community_user_prompt,
)
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.shared.db import db_connect  # noqa: E402

log = structlog.get_logger(__name__)

_DATA = _ROOT / "webapp" / "public" / "data"

_LLM_BY_CHANNEL_Q = (
    "SELECT actor_type, themes FROM channel_llm_scores "
    "WHERE mission=$1 AND channel_id=$2 "
    "ORDER BY computed_at DESC LIMIT 1"
)


def _snapshot_paths(mission: str) -> tuple[Path, Path]:
    base = _DATA / mission
    return base / f"{mission}_snapshot.json", base / f"{mission}_llm_snapshot.json"


def _top_members(community: dict, n: int) -> list[dict]:
    chans = sorted(
        community.get("channels", []),
        key=lambda c: c.get("engagement", 0) or 0,
        reverse=True,
    )
    return chans[:n]


async def _member_payload(conn, mission: str, ch: dict) -> dict:
    row = await conn.fetchrow(_LLM_BY_CHANNEL_Q, mission, ch.get("channel_id"))
    themes, actor = [], None
    if row:
        actor = row["actor_type"]
        raw = row["themes"]
        themes = json.loads(raw) if isinstance(raw, str) else (raw or [])
    return {
        "username": ch.get("username"),
        "title": ch.get("title"),
        "actor_type": actor,
        "themes": themes,
    }


async def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    model = args.model or resolve_model()
    lexical_path, llm_path = _snapshot_paths(mission.name)

    if not lexical_path.exists():
        raise SystemExit(
            f"Snapshot lexical absent : {lexical_path}\n"
            f"Générez-le d'abord : python scripts/analyze_communities.py "
            f"(--mission {mission.name} si câblé)."
        )
    snap = json.loads(lexical_path.read_text(encoding="utf-8"))
    communities = snap.get("communities", [])
    print(
        f"[label] mission={mission.name} model={model} prompt={PROMPT_VERSION} "
        f"· {len(communities)} communautés"
    )

    conn = await db_connect()
    out_comms: list[dict] = []
    try:
        async with MistralClient(model=model) as client:
            for c in communities:
                members = [await _member_payload(conn, mission.name, ch)
                           for ch in _top_members(c, args.top_n)]
                user = community_user_prompt(mission=mission.name, members=members)

                if args.dry_run:
                    approx = (len(COMMUNITY_LABEL_SYSTEM) + len(user)) // 4
                    print(f"  [dry-run] comm#{c.get('id')} ({c.get('size')} canaux) ~{approx} tok")
                    out_comms.append({**_carry(c), "llm": None})
                    continue

                res = await client.complete(
                    system=COMMUNITY_LABEL_SYSTEM, user=user,
                    json_mode=True, schema=COMMUNITY_SCHEMA,
                )
                p = res.parsed or {}
                llm_label = {
                    "label": _redact_providers(str(p.get("label") or "")),
                    "theme": _redact_providers(str(p.get("theme") or "")),
                    "confidence": _as_float(p.get("confidence")),
                    "rationale": _redact_providers(str(p.get("rationale") or "")),
                    "model": res.model,
                    "prompt_version": res.prompt_version,
                }
                out_comms.append({**_carry(c), "llm": llm_label})

                if args.budget_usd and client.totals.est_cost_usd >= args.budget_usd:
                    print(f"  [budget] plafond {args.budget_usd} USD atteint — arrêt.")
                    break

            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mission": mission.name,
                "label_source": "llm-mistral-parallel",
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "baseline_snapshot": lexical_path.name,
                "stats": snap.get("stats", {}),
                "communities": out_comms,
                "bridges": snap.get("bridges", []),
                "meta_graph": snap.get("meta_graph", {}),
                "coverage_callout": snap.get("coverage_callout", ""),
            }
            if not args.dry_run:
                llm_path.parent.mkdir(parents=True, exist_ok=True)
                llm_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    f"[label] écrit : {llm_path} · coût≈{client.totals.est_cost_usd} USD"
                )
            else:
                print("[label] dry-run : aucun snapshot écrit.")
    finally:
        await conn.close()


def _carry(c: dict) -> dict:
    """Conserve les champs lexicaux clés pour le diff (label lexical = comparaison)."""
    return {
        "id": c.get("id"),
        "size": c.get("size"),
        "color": c.get("color"),
        "lexical_label": c.get("label"),
        "lexical_theme_confidence": c.get("theme_confidence"),
        "n_suspects": c.get("n_suspects"),
    }


def _as_float(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Étiquetage Mistral de communautés (piste parallèle).")
    add_mission_arg(ap)
    ap.add_argument("--top-n", type=int, default=6, help="canaux représentatifs/communauté")
    ap.add_argument("--model", default=None, help="surcharge MISTRAL_MODEL")
    ap.add_argument("--dry-run", action="store_true", help="aucun réseau ; imprime les prompts")
    ap.add_argument("--budget-usd", type=float, default=0.0, help="plafond coût estimé (0=illim.)")
    asyncio.run(main(ap.parse_args()))
