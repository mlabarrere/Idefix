"""Exporteur STATIQUE — matérialise le bundle JSON de la webapp analyste
(``webapp/public/data/<mission>/``), site 100 % statique sans backend.

> Décision 2026-06-08 : pas de backend Python web. Le site lit des JSON
> précalculés ; le voisinage / filtrage / recherche se font côté navigateur.
> Python reste UNIQUEMENT offline pour produire ce bundle (ce fichier).
> 2026-06-10 (Lot 0) : la cible canonique devient ``webapp/public/data/<mission>``
> (le frontend HTML/JS legacy est supprimé) ; les jumeaux ``.js`` (repli
> ``file://`` du vieux frontend) ne sont plus émis par défaut.

Contenu du bundle (les fonctions sources sont celles du pipeline offline) :

    _build_channel_queue_live(conn, top_k=None)
        -> channels.json + channels_index.json + channels/<id>.json
    fetch_*_rows + build_graph + archetypes       -> graph.json
    list_episodes(conn) / build_evidence(conn,id) -> episodes/index.json + episodes/<id>.json
    stub littéral                                 -> tasking.json
    snapshots analyze_*.py (déjà dans le dossier mission) + manifest.json

Lecture seule PostgreSQL. AUCUN appel Telegram. Idempotent (réécriture).

Usage :
    python scripts/export_static.py [--mission gan] [--out DIR] [--public]
                                    [--no-snapshots] [--js-twins]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

load_dotenv()

from src.dossier.evidence import build_evidence, list_episodes, load_episodes  # noqa: E402
from src.graph.loader import (  # noqa: E402
    build_graph,
    fetch_channel_rows,
    fetch_edge_rows,
)
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.missions.registry import DEFAULT_MISSION  # noqa: E402
from src.scorer.channel_suspicion import _build_channel_queue_live  # noqa: E402
from src.shared.db import db_connect  # noqa: E402
from src.shared.scrub import scrub as _scrub  # noqa: E402  (scrubber canonique partagé)

# Enveloppe « tasking » v0 — littéral lifté de src/api/main.py:298-304.
TASKING_STUB: dict = {
    "account": "+33 · série",
    "flood_wait": {"used": 0, "window": 100, "cooldown_s": 0, "next_eta_s": 0},
    "running": 0,
    "depth_max": 1,
    "tasks": [],
}

# Caveat cécité mono-plateforme — chaîne exacte de neighborhood_to_dict (loader.py:434).
COVERAGE_CALLOUT = (
    "Couverture Telegram uniquement : la couche d'amplification de masse "
    "(X / autres plateformes) n'est pas observée (docs/limitations.md L1)."
)

EXPORT_VERSION = "static-bundle/v1"
METHODOLOGY_VERSION = "idefix-methodology/2026-06-15"
SCORER_VERSION = "explainable-channel-suspicion/v1"
DEFAULT_CLASSIFICATION_MARKING = "UNMARKED_INTERNAL_REVIEW"
DEFAULT_HANDLING_INSTRUCTIONS = (
    "Internal sponsor review only until an official classification marking is supplied."
)
DEFAULT_REVIEW_STATUS = "machine_generated_pending_human_review"

# Snapshots déjà statiques produits par analyze_communities.py / analyze_porosity.py.
# Source = le dossier mission canonique (webapp/public/data/<mission>/) ; on ne
# les recopie que vers un AUTRE dossier (ex. --public pour Pages).
_SNAPSHOTS = [
    ("russosphere_snapshot.json", "russosphere.json", "RUSSOSPHERE_SNAPSHOT"),
    ("porosity_snapshot.json", "porosity.json", "POROSITY_SNAPSHOT"),
]

# Racine canonique du bundle de la webapp statique (servie par Vite : public/).
_WEBAPP_DATA = _REPO / "webapp" / "public" / "data"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


def _env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def build_export_metadata(
    *,
    mission: str,
    generated_at: str,
    coverage_callout: str | None,
    public: bool = False,
) -> dict[str, str | bool]:
    """Common sponsor-facing envelope added to exploitable static exports."""

    return {
        "mission": mission,
        "generated_at": generated_at,
        "methodology_version": _env_or_default(
            "IDEFIX_METHODOLOGY_VERSION",
            METHODOLOGY_VERSION,
        ),
        "scorer_version": _env_or_default("IDEFIX_SCORER_VERSION", SCORER_VERSION),
        "export_version": EXPORT_VERSION,
        "coverage_callout": coverage_callout or COVERAGE_CALLOUT,
        "classification_marking": _env_or_default(
            "IDEFIX_CLASSIFICATION_MARKING",
            DEFAULT_CLASSIFICATION_MARKING,
        ),
        "handling_instructions": _env_or_default(
            "IDEFIX_HANDLING_INSTRUCTIONS",
            DEFAULT_HANDLING_INSTRUCTIONS,
        ),
        "produced_by": _env_or_default("IDEFIX_PRODUCED_BY", "idefix-offline-export"),
        "review_status": _env_or_default("IDEFIX_REVIEW_STATUS", DEFAULT_REVIEW_STATUS),
        "public_bundle": public,
    }


def _with_export_metadata(
    obj: dict,
    *,
    mission: str,
    generated_at: str,
    coverage_callout: str | None,
    public: bool = False,
) -> dict:
    metadata = build_export_metadata(
        mission=mission,
        generated_at=generated_at,
        coverage_callout=coverage_callout,
        public=public,
    )
    return {**metadata, **obj, "export_metadata": metadata}


def _write_json(path: Path, obj) -> int:
    # Scrub des secrets au point d'écriture unique (jamais de numéro/session
    # dans le bundle exporté).
    text = json.dumps(_scrub(obj), ensure_ascii=False, default=_json_default)
    path.write_text(text, encoding="utf-8")
    return len(text)


def _write_twin(path_js: Path, varname: str, obj) -> None:
    """Jumeau ``.js`` chargeable via <script> (contourne le CORS file://)."""
    payload = json.dumps(_scrub(obj), ensure_ascii=False, default=_json_default)
    text = f"window.{varname} = {payload};\n"
    path_js.write_text(text, encoding="utf-8")


def _serialize_graph(graph, archetypes: dict) -> tuple[list, list]:
    """Dump du graphe COMPLET avec EXACTEMENT les noms de champs de
    ``neighborhood_to_dict`` (loader.py:376-418) — le rendu Cytoscape ne change pas.
    """
    nodes: list[dict] = []
    for n, data in graph.nodes(data=True):
        if data.get("kind") == "domain":
            nodes.append({"domain": n})
        else:
            nodes.append(
                {
                    "channel_id": n,
                    "username": data.get("username", ""),
                    "title": data.get("title", ""),
                    "archetype": archetypes.get(n),  # précalculé (channel_scores) sinon None
                    "credibility_prior": data.get("credibility_prior", "other"),
                    "engagement": data.get("engagement", 0),
                    "fr_score": data.get("fr_score"),
                    "confidence": {"level": "ok", "reason": "ok"},
                }
            )

    edges: list[dict] = []
    for u, v, data in graph.edges(data=True):
        family = data.get("family")
        etype = data.get("edge_type")
        if family == "coordination":
            edges.append(
                {
                    "family": family,
                    "type": etype,
                    "a": u,
                    "b": v,
                    "dt_seconds": data.get("window_delta_seconds"),
                    "count": data.get("count"),
                }
            )
        else:
            edge = {
                "family": family,
                "type": etype,
                "source": u,
                "target": v,
                "count": data.get("count"),
            }
            if data.get("delay_seconds") is not None:
                edge["delay_seconds"] = data.get("delay_seconds")
            edges.append(edge)
    return nodes, edges


async def _fetch_archetypes(conn, mission_name: str = DEFAULT_MISSION) -> dict:
    """Map channel_id -> archetype depuis channel_scores, SCOPÉ MISSION.
    {} si table absente/vide. (mission défaut = lignes historiques.)"""
    try:
        rows = await conn.fetch(
            "SELECT channel_id, archetype FROM channel_scores "
            "WHERE mission = $1 AND archetype IS NOT NULL",
            mission_name,
        )
    except Exception:  # noqa: BLE001 — table absente -> pas d'archétypes
        return {}
    return {r["channel_id"]: r["archetype"] for r in rows}


async def export(
    out: Path,
    *,
    public: bool = False,
    snapshots: bool = True,
    js_twins: bool = False,
    mission: str | None = None,
) -> None:
    # mission None => mission par défaut (russosphère). La cible nominale est
    # webapp/public/data/<mission>/ (calculée dans main() quand --out est absent).
    mission_def = resolve_mission(mission) if mission else None
    mission_name = mission_def.name if mission_def is not None else DEFAULT_MISSION
    conn = await db_connect()
    gen = _now_iso()
    files: dict[str, str] = {}
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / "episodes").mkdir(exist_ok=True)

        # --- Données opérationnelles (bundle COMPLET, jamais sur Pages public) ---
        if not public:
            queue = await _build_channel_queue_live(
                conn, top_k=None, mission=mission_def
            )  # univers complet
            channels = queue["channels"]
            _write_json(
                out / "channels.json",
                _with_export_metadata(
                    {
                        "generated_at": gen,
                        "coverage_callout": queue.get("coverage_callout"),
                        "symmetric_ratio": queue.get("symmetric_ratio"),
                        "total": len(channels),
                        "channels": channels,  # TOUS, triés suspicion desc
                    },
                    mission=mission_name,
                    generated_at=gen,
                    coverage_callout=queue.get("coverage_callout"),
                    public=public,
                ),
            )
            files["channels"] = "channels.json"

            # --- Forme SHARDÉE (zéro infra, scale sans serveur) -----------------
            # Le « dossier de situation » lit un index LÉGER + un fichier par canal
            # (fetch lazy au drill). Évite de charger ~6 Mo de channels.json d'un coup
            # et tient à 50k+ canaux sans serveur (hébergeable GitHub Pages).
            ch_dir = out / "channels"
            ch_dir.mkdir(exist_ok=True)
            for _old in ch_dir.glob("*.json"):  # purge des per-canal obsolètes
                _old.unlink()
            for c in channels:
                _write_json(ch_dir / f"{c['channel_id']}.json", c)
            index_obj = {
                "generated_at": gen,
                "coverage_callout": queue.get("coverage_callout"),
                "symmetric_ratio": queue.get("symmetric_ratio"),
                "total": len(channels),
                "channels": [
                    {
                        "channel_id": c["channel_id"],
                        "username": c.get("username"),
                        "title": c.get("title"),
                        "suspicion": (c.get("suspicion") or {}).get("v"),
                        "tier": c.get("tier"),
                        "archetype": c.get("archetype"),
                        "credibility_prior": c.get("credibility_prior"),
                        "fr_score": c.get("fr_score"),
                        "france_targeting": c.get("france_targeting"),
                        "gate_met": (c.get("gate") or {}).get("met"),
                    }
                    for c in channels
                ],
            }
            index_obj = _with_export_metadata(
                index_obj,
                mission=mission_name,
                generated_at=gen,
                coverage_callout=queue.get("coverage_callout"),
                public=public,
            )
            _write_json(out / "channels_index.json", index_obj)
            files["channels_index"] = "channels_index.json"
            if js_twins:
                _write_twin(out / "channels_index.js", "CHANNELS_INDEX", index_obj)

            edge_rows = await fetch_edge_rows(conn)
            channel_rows = await fetch_channel_rows(conn)
            graph = build_graph(edge_rows, channel_rows)
            archetypes = await _fetch_archetypes(conn, mission_name)
            nodes, edges = _serialize_graph(graph, archetypes)
            _write_json(
                out / "graph.json",
                _with_export_metadata(
                    {
                        "generated_at": gen,
                        "coverage_callout": COVERAGE_CALLOUT,
                        "nodes": nodes,
                        "edges": edges,
                    },
                    mission=mission_name,
                    generated_at=gen,
                    coverage_callout=COVERAGE_CALLOUT,
                    public=public,
                ),
            )
            files["graph"] = "graph.json"

            _write_json(
                out / "tasking.json",
                _with_export_metadata(
                    TASKING_STUB,
                    mission=mission_name,
                    generated_at=gen,
                    coverage_callout=COVERAGE_CALLOUT,
                    public=public,
                ),
            )
            files["tasking"] = "tasking.json"

            # --- THÈMES : ensembles de canaux par lentille (UNE galaxie, N thèmes) -
            # Permet au frontend d'illuminer « les canaux qui parlent du GAN »,
            # « ceux qui ciblent la France », etc. — et de VOIR leurs liens dans le
            # graphe unique (la demande « faire des liens entre russophilie/RN/GAN »).
            theme_rows = await conn.fetch(
                """
                SELECT ch.channel_id,
                       (ch.extra->>'gan_targeting')::float AS gan,
                       s.france_targeting AS ft,
                       (ch.extra->>'fr_score')::float AS fr
                FROM channels ch
                LEFT JOIN channel_scores s
                  ON s.channel_id = ch.channel_id AND s.mission = $1
                """,
                mission_name,
            )
            themes: dict[str, list[int]] = {
                "gan": [], "france_targeting": [], "francophone": []
            }
            for r in theme_rows:
                if (r["gan"] or 0) >= 0.15:
                    themes["gan"].append(r["channel_id"])
                if (r["ft"] or 0) >= 0.30:
                    themes["france_targeting"].append(r["channel_id"])
                if (r["fr"] or 0) >= 0.15:
                    themes["francophone"].append(r["channel_id"])
            _write_json(
                out / "themes.json",
                _with_export_metadata(
                    {
                        "generated_at": gen,
                        "coverage_callout": COVERAGE_CALLOUT,
                        "themes": [
                            {"id": "gan", "label": "Empreinte GAN",
                             "color": "#38bdf8", "channel_ids": themes["gan"]},
                            {"id": "france_targeting", "label": "Ciblage France",
                             "color": "#f87171", "channel_ids": themes["france_targeting"]},
                            {"id": "francophone", "label": "Francophone",
                             "color": "#4ade80", "channel_ids": themes["francophone"]},
                        ],
                    },
                    mission=mission_name,
                    generated_at=gen,
                    coverage_callout=COVERAGE_CALLOUT,
                    public=public,
                ),
            )
            files["themes"] = "themes.json"

            index = await list_episodes(conn, mission=mission_name)
            _write_json(out / "episodes" / "index.json", index)
            files["episodes_index"] = "episodes/index.json"
            episodes = load_episodes(mission_name)
            for eid in episodes:
                _write_json(out / "episodes" / f"{eid}.json", await build_evidence(conn, eid, mission=mission_name))

        # --- Snapshots déjà statiques (relocalisés ; cœur du bundle PUBLIC) ------
        # Quand on exporte DANS webapp/public/data/<mission>/ (cas nominal), les
        # snapshots y sont déjà (produits par analyze_*.py sous leur nom
        # *_snapshot.json, lu tel quel par la webapp) -> on ne recopie pas. On ne
        # relocalise que vers un AUTRE dossier (ex. --public pour Pages).
        dossiers = _WEBAPP_DATA / mission_name
        if snapshots and dossiers.resolve() != out.resolve():
            for src_name, dst_name, var in _SNAPSHOTS:
                src = dossiers / src_name
                if not src.exists():
                    print(f"  [skip] {src_name} absent ({src})")
                    continue
                obj = json.loads(src.read_text(encoding="utf-8"))
                _write_json(out / dst_name, obj)
                files[dst_name[:-5]] = dst_name
                if js_twins:
                    _write_twin(out / (dst_name[:-5] + ".js"), var, obj)

        # --- Manifest (version + horodatage + stats) ----------------------------
        stats = {
            "n_channels": await conn.fetchval("SELECT count(*) FROM channels"),
            "n_edges": await conn.fetchval("SELECT count(*) FROM edges"),
            "n_messages": await conn.fetchval("SELECT count(*) FROM messages"),
        }
        _write_json(
            out / "manifest.json",
            _with_export_metadata(
                {"version": gen[:10], "public": public, "files": files, "stats": stats},
                mission=mission_name,
                generated_at=gen,
                coverage_callout=COVERAGE_CALLOUT,
                public=public,
            ),
        )
    finally:
        await conn.close()

    tier = "PUBLIC (agrégats)" if public else "COMPLET"
    print(
        f"Bundle {tier} écrit dans {out}/ · {len(files)} fichiers · "
        f"{stats['n_channels']} canaux · {stats['n_edges']} arêtes · "
        f"{stats['n_messages']} messages."
    )
    for k, v in files.items():
        size = (out / v).stat().st_size
        print(f"    {v:<24} {size/1024:7.1f} Ko")


def main() -> None:
    ap = argparse.ArgumentParser(description="Exporte le bundle JSON statique de la webapp.")
    ap.add_argument(
        "--out",
        default=None,
        help=(
            "Dossier de sortie (défaut: webapp/public/data/<mission>/ — servi par "
            "la webapp statique)"
        ),
    )
    ap.add_argument(
        "--public",
        action="store_true",
        help="Bundle réduit (agrégats only) pour GitHub Pages",
    )
    ap.add_argument(
        "--no-snapshots",
        dest="snapshots",
        action="store_false",
        help="Ne pas relocaliser russosphere/porosity",
    )
    ap.add_argument(
        "--js-twins",
        dest="js_twins",
        action="store_true",
        default=False,
        help="Émettre les jumeaux .js window-global (repli file:// legacy, off par défaut)",
    )
    add_mission_arg(ap)
    args = ap.parse_args()
    mission_name = args.mission or DEFAULT_MISSION
    out = Path(args.out) if args.out else _WEBAPP_DATA / mission_name
    if not out.is_absolute():
        out = _REPO / out
    asyncio.run(
        export(
            out,
            public=args.public,
            snapshots=args.snapshots,
            js_twins=args.js_twins,
            mission=args.mission,
        )
    )


if __name__ == "__main__":
    main()
