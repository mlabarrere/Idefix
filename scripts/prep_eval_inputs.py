"""Prépare les entrées des scripts eval_*.py depuis Supabase REST (sans wire PG).

Les évals (_eval_common.py) lisent l'INSTANTANÉ statique :
  * data/channels.json  -> {"generated_at", "channels": [payload scoré, ...]}
  * data/graph.json     -> {"nodes": [{channel_id, engagement, ...}],
                            "edges": [{type, source, target, count}, ...]}

Le scoring est déjà matérialisé dans `channel_scores` (payload = objet canal scoré,
avec _components/suspicion/gate) et le graphe dans `edges`. On reconstruit donc ces
deux fichiers par REST (HTTPS:443) — AURA bloque le wire PG.

Creds depuis l'env (.env) — jamais en dur. Idempotent.

Usage :
    python scripts/prep_eval_inputs.py --mission russosphere
"""
import argparse
import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_REPO = Path(__file__).resolve().parents[1]
DATA = _REPO / "data"
BASE = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
_H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
_PAGE = 1000


def _paginate(table: str, select: str, filt: str = "") -> list:
    out, off = [], 0
    while True:
        url = f"{BASE}/{table}?select={select}" + (f"&{filt}" if filt else "")
        req = urllib.request.Request(url, headers={**_H, "Range": f"{off}-{off + _PAGE - 1}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            rows = json.loads(r.read().decode())
        out.extend(rows)
        if len(rows) < _PAGE:
            return out
        off += _PAGE


def main(mission: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    # 1. channels.json = payloads scorés (contrat queue : _components/suspicion/gate)
    scores = _paginate("channel_scores", "payload", f"mission=eq.{mission}")
    payloads = [r["payload"] for r in scores]
    (DATA / "channels.json").write_text(
        json.dumps({"generated_at": f"rest-eval:{mission}", "channels": payloads},
                   ensure_ascii=False),
        encoding="utf-8",
    )

    # 2. graph.json = noeuds (engagement proxy = member_count) + arêtes FORWARD
    chans = _paginate("channels", "channel_id,username,member_count")
    nodes = [
        {"channel_id": c["channel_id"], "username": c.get("username"),
         "engagement": c.get("member_count") or 0}
        for c in chans
    ]
    edges_rows = _paginate("edges", "src_channel_id,dst_channel_id,edge_type,count")
    edges = [
        {"type": e["edge_type"], "source": e["src_channel_id"],
         "target": e["dst_channel_id"], "count": e.get("count") or 0}
        for e in edges_rows
        if e.get("src_channel_id") is not None and e.get("dst_channel_id") is not None
    ]
    n_fwd = sum(1 for e in edges if e["type"] == "FORWARD")
    (DATA / "graph.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[{mission}] data/channels.json : {len(payloads)} canaux scorés")
    print(f"[{mission}] data/graph.json    : {len(nodes)} noeuds, {len(edges)} arêtes "
          f"({n_fwd} FORWARD)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prépare data/channels.json + data/graph.json (REST).")
    ap.add_argument("--mission", default="russosphere")
    main(ap.parse_args().mission)
