"""Export du bundle statique via l'API REST Supabase (sans wire-protocol PostgreSQL).

AURA bloque le port PG (5432/6543) mais pas REST (HTTPS:443). Le scoring est DÉJÀ
matérialisé dans ``channel_scores`` (1 ligne/canal, ``payload`` = objet canal scoré
exact, contrat queue) par ``build_scores.py``. On reconstruit donc le bundle
directement depuis ``channel_scores`` — PAS de re-scoring, PAS de graphe.

Produit, par mission, dans ``webapp/public/data/<mission>/`` :
  * channels_index.json   (projection scorée : ce que lit la table Canaux + la Synthèse)
  * channels/<id>.json    (payload complet : ce que lit le ChannelDrawer)
  * manifest.json         (stats réelles : n_channels/n_edges/n_messages)

Les snapshots communautés (galaxie) sont déjà gérés par pull-snapshots.mjs au build.
Les épisodes nécessitent mine_episodes (corpus messages) — hors de ce script.

Creds lues depuis l'env (.env) — JAMAIS en dur. Idempotent.

Usage :
    python scripts/export_via_rest_api.py                       # russosphere + gan
    python scripts/export_via_rest_api.py --mission russosphere
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
_H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
_PAGE = 1000  # plafond REST Supabase par requête -> pagination obligatoire

OUT_ROOT = Path("webapp/public/data")


def _get(table: str, select: str, filt: str = "", *, rng: str | None = None) -> tuple[list, str]:
    url = f"{BASE}/{table}?select={urllib.parse.quote(select)}"
    if filt:
        url += f"&{filt}"
    headers = dict(_H)
    if rng is not None:
        headers["Range"] = rng
        headers["Prefer"] = "count=exact"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode()), r.headers.get("Content-Range", "")


def _count(table: str, filt: str = "") -> int:
    _, cr = _get(table, "*", filt, rng="0-0")
    return int(cr.split("/")[-1]) if "/" in cr else 0


def _paginate(table: str, select: str, filt: str) -> list:
    out, off = [], 0
    while True:
        rows, _ = _get(table, select, filt, rng=f"{off}-{off + _PAGE - 1}")
        out.extend(rows)
        if len(rows) < _PAGE:
            return out
        off += _PAGE


def _index_row(p: dict) -> dict:
    """payload (objet canal scoré) -> ligne d'index (contrat ChannelIndexRow)."""
    return {
        "channel_id": p["channel_id"],
        "username": p.get("username"),
        "title": p.get("title"),
        "suspicion": (p.get("suspicion") or {}).get("v"),
        "tier": p.get("tier"),
        "archetype": p.get("archetype"),
        "credibility_prior": p.get("credibility_prior"),
        "fr_score": p.get("fr_score"),
        "france_targeting": p.get("france_targeting"),
        "gate_met": (p.get("gate") or {}).get("met"),
    }


def export_mission(mission: str, n_edges: int, n_messages: int) -> None:
    rows = _paginate("channel_scores", "payload", f"mission=eq.{mission}")
    if not rows:
        print(f"[{mission}] aucun score — sauté.")
        return
    payloads = [r["payload"] for r in rows]

    out = OUT_ROOT / mission
    (out / "channels").mkdir(parents=True, exist_ok=True)

    # envelope (coverage_callout, symmetric_ratio) depuis scores_run_meta
    meta_rows, _ = _get("scores_run_meta", "envelope", f"mission=eq.{mission}&limit=1")
    env = (meta_rows[0]["envelope"] if meta_rows else {}) or {}

    index_obj = {
        "generated_at": "rest-export",
        "total": len(payloads),
        "coverage_callout": env.get("coverage_callout"),
        "symmetric_ratio": env.get("symmetric_ratio"),
        "channels": [_index_row(p) for p in payloads],
    }
    (out / "channels_index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False), encoding="utf-8"
    )

    for p in payloads:
        (out / "channels" / f"{p['channel_id']}.json").write_text(
            json.dumps(p, ensure_ascii=False), encoding="utf-8"
        )

    manifest = {
        "mission": mission,
        "generated_at": "rest-export",
        "source": "supabase-rest-api (channel_scores)",
        "stats": {
            "n_channels": len(payloads),
            "n_edges": n_edges,
            "n_messages": n_messages,
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n_t2 = sum(1 for p in payloads if p.get("tier") == "T2")
    print(f"[{mission}] {len(payloads)} canaux ({n_t2} T2) -> {out}/ (index + channels/ + manifest)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Export bundle via Supabase REST (channel_scores).")
    ap.add_argument("--mission", help="mission unique (défaut : toutes celles ayant des scores)")
    args = ap.parse_args()

    n_edges = _count("edges")
    n_messages = _count("messages")
    print(f"global: {n_edges} arêtes, {n_messages} messages")

    if args.mission:
        missions = [args.mission]
    else:
        # missions ayant des scores matérialisés
        rows = _paginate("channel_scores", "mission", "")
        missions = sorted({r["mission"] for r in rows})
    for m in missions:
        export_mission(m, n_edges, n_messages)


if __name__ == "__main__":
    main()
