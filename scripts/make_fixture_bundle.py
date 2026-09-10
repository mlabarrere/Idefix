#!/usr/bin/env python
"""Generate a small SYNTHETIC analyst bundle, deterministically.

Why this exists
---------------
Real analyst bundles are corpus- and run-specific, so they are not tracked in
this repository (`docs/limitations.md` Part III). That is the right call for
published numbers, but it leaves two holes:

1. a fresh clone has nothing for the webapp to display, so the end-to-end
   browser tests cannot run in CI;
2. a reader cannot see the interface at all without first standing up a
   database and a Telegram account.

This script fills both with a bundle that is **obviously synthetic**: invented
channels, a planted coordination cluster, and a fixed seed. It exercises the
loaders and the galaxy without asserting anything about the world.

It is NOT an evaluation fixture. No number it produces means anything about
Telegram, and nothing here may be cited. Real results, when a corpus exists,
belong in `docs/experiments/results/`.

Usage:
    python scripts/make_fixture_bundle.py [--out webapp/public/data/russosphere]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "webapp" / "public" / "data" / "russosphere"

SEED = 1312
N_COMMUNITIES = 5
N_PER_COMMUNITY = 8

COVERAGE_CALLOUT = (
    "Ce dossier observe uniquement la couche d'ensemencement Telegram. Une "
    "opération atteignant la France principalement via d'autres plateformes "
    "sans étape Telegram ne sera PAS détectée."
)
SYNTHETIC_NOTE = (
    "DONNÉES SYNTHÉTIQUES — générées par scripts/make_fixture_bundle.py. "
    "Aucun canal réel, aucun résultat citable."
)

THEMES = [
    ("Communauté synthétique A", "#C9880A"),
    ("Communauté synthétique B", "#3B82F6"),
    ("Communauté synthétique C", "#10B981"),
    ("Communauté synthétique D", "#EF4444"),
    ("Communauté synthétique E", "#8B5CF6"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build(rng: random.Random) -> dict:
    """Build every bundle file in memory. Pure apart from ``rng``."""
    channels: list[dict] = []
    communities: list[dict] = []
    cid = -1000000000

    for c_idx in range(N_COMMUNITIES):
        label, color = THEMES[c_idx]
        members = []
        # Communities are laid out on a circle; members on a smaller circle
        # around their community centre. Deterministic, no layout engine.
        cx = 900 * math.cos(2 * math.pi * c_idx / N_COMMUNITIES)
        cy = 900 * math.sin(2 * math.pi * c_idx / N_COMMUNITIES)

        for m_idx in range(N_PER_COMMUNITY):
            cid -= 1
            angle = 2 * math.pi * m_idx / N_PER_COMMUNITY
            # The first community is the planted "coordinated" one: it is the
            # only place where suspicion is high and the gate is met.
            planted = c_idx == 0
            suspicion = round(rng.uniform(0.55, 0.85) if planted else rng.uniform(0.0, 0.30), 4)
            prior = "suspect" if planted and m_idx < 5 else "other"
            username = f"synthetic_{c_idx}_{m_idx}"
            node = {
                "channel_id": cid,
                "username": f"@{username}",
                "title": f"Canal synthétique {c_idx}.{m_idx}",
                "suspicion": suspicion,
                "tier": "T2" if suspicion >= 0.5 else "T1",
                "archetype": (
                    "seeding-source" if m_idx == 0
                    else "cross-channel-bridge" if m_idx == 1
                    else "forward-hub"
                ),
                "credibility_prior": prior,
            }
            channels.append(node)
            members.append({
                "channel_id": cid,
                "username": username,
                "title": node["title"],
                "is_seed": m_idx == 0,
                "fr_score": round(rng.uniform(0.0, 1.0), 3),
                "engagement": rng.randint(0, 5000),
                "betweenness": round(rng.uniform(0.0, 0.2), 4),
                "member_count": rng.randint(100, 50000),
                "credibility_prior": prior,
                "x": round(cx + 260 * math.cos(angle), 2),
                "y": round(cy + 260 * math.sin(angle), 2),
            })

        communities.append({
            "id": c_idx,
            "size": len(members),
            "color": color,
            "label": label,
            "domains": [],
            "channels": members,
        })

    channels.sort(key=lambda c: c["suspicion"], reverse=True)
    ids = [c["channel_id"] for c in channels]

    # --- graph.json : forward edges inside communities, a few bridges across --
    nodes = [
        {"id": c["channel_id"], "username": c["username"].lstrip("@"), "title": c["title"]}
        for c in channels
    ]
    edges = []
    for comm in communities:
        member_ids = [m["channel_id"] for m in comm["channels"]]
        seed = member_ids[0]
        for other in member_ids[1:]:
            edges.append({
                "family": "forward", "source": seed, "target": other,
                "count": rng.randint(1, 20),
            })
        # coordination inside the planted community only
        if comm["id"] == 0:
            for a, b in zip(member_ids[1:], member_ids[2:]):
                edges.append({"family": "coordination", "source": a, "target": b, "count": 3})
    for c_idx in range(N_COMMUNITIES - 1):
        edges.append({
            "family": "forward",
            "source": communities[c_idx]["channels"][1]["channel_id"],
            "target": communities[c_idx + 1]["channels"][0]["channel_id"],
            "count": 2,
        })

    n_suspect = sum(1 for c in channels if c["credibility_prior"] == "suspect")
    ratio = round(n_suspect / len(channels), 4)

    return {
        "manifest.json": {
            "mission": "russosphere",
            "generated_at": _now(),
            "source": "synthetic fixture (scripts/make_fixture_bundle.py)",
            "synthetic": True,
            "note": SYNTHETIC_NOTE,
            "stats": {
                "n_channels": len(channels),
                "n_edges": len(edges),
                "n_messages": 0,
            },
        },
        "channels_index.json": {
            "generated_at": _now(),
            "total": len(channels),
            "synthetic": True,
            "note": SYNTHETIC_NOTE,
            "coverage_callout": COVERAGE_CALLOUT,
            "symmetric_ratio": {
                "note": SYNTHETIC_NOTE,
                "organic_fr": round(1.0 - ratio, 4),
                "adversary_infra": ratio,
            },
            "channels": channels,
        },
        "graph.json": {
            "generated_at": _now(),
            "synthetic": True,
            "nodes": nodes,
            "edges": edges,
        },
        "russosphere_snapshot.json": {
            "seed": "@synthetic_0_0",
            "generated_at": _now(),
            "synthetic": True,
            "note": SYNTHETIC_NOTE,
            "coverage_callout": COVERAGE_CALLOUT,
            "stats": {
                "n_channels": len(channels),
                "n_communities": len(communities),
                "density": round(len(edges) / max(1, len(nodes) ** 2), 6),
            },
            "bridges": [
                {
                    "channel_id": communities[i]["channels"][1]["channel_id"],
                    "username": communities[i]["channels"][1]["username"],
                    "betweenness": round(0.2 - 0.02 * i, 4),
                }
                for i in range(min(3, len(communities)))
            ],
            "meta_graph": {
                "nodes": [
                    {"id": c["id"], "label": c["label"], "size": c["size"], "color": c["color"]}
                    for c in communities
                ],
                "edges": [
                    {"source": i, "target": i + 1, "weight": 1}
                    for i in range(len(communities) - 1)
                ],
            },
            "communities": communities,
        },
        "stories.json": {
            "generated_at": _now(),
            "synthetic": True,
            "stories": [],
        },
        "themes.json": {"generated_at": _now(), "synthetic": True, "themes": []},
    }, channels, ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="bundle directory")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "channels").mkdir(exist_ok=True)

    rng = random.Random(SEED)
    files, channels, _ids = build(rng)

    for name, payload in files.items():
        (out / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # Per-channel detail, fetched lazily on drill-down.
    for c in channels:
        detail = {
            **c,
            "synthetic": True,
            "coverage_callout": COVERAGE_CALLOUT,
            "gate": {
                "met": c["tier"] == "T2",
                "families": 2 if c["tier"] == "T2" else 1,
                "gate_families": ["b", "c"] if c["tier"] == "T2" else ["b"],
            },
            "_components": {
                "b": {"weight": 0.30, "value": c["suspicion"], "triggered": True},
                "c": {"weight": 0.25, "value": 0.5, "triggered": c["tier"] == "T2"},
            },
        }
        (out / "channels" / f"{c['channel_id']}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"synthetic bundle written -> {out}")
    print(f"  {len(channels)} channels, {len(files)} bundle files")
    print("  NOT real data. Nothing here may be cited.")


if __name__ == "__main__":
    main()
