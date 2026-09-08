"""Diff temporel snapshots communautés — détection reconfigurations réseau.

Tire deux snapshots via REST (analytics + embedding si dispos), compare structure
canaux/communautés/embeddings, écrit ``data/<mission>/snapshot_diff.json``.

Usage:
    python scripts/compare_snapshots.py --mission russosphere
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shared.snapshot_store import pull_snapshot  # noqa: E402

# ponytail: évite les dépendances lourdes (networkx etc.), mission → out_subdir direct
_MISSION_SUBDIRS = {"russosphere": "russosphere", "gan": "gan", "france_ukraine": "dircom"}


def _jaccard(a: set, b: set) -> float:
    i = len(a & b)
    return i / len(a | b) if a | b else 1.0


def _extract_channels(snapshot: dict) -> list[dict]:
    """Flatten channels from communities structure."""
    channels = []
    for comm in snapshot.get("communities", []):
        for chan in comm.get("channels", []):
            channels.append({"channel_id": chan["channel_id"],
                           "username": chan.get("username"),
                           "community": comm["id"]})
    return channels


def _compare_channels(old: dict, new: dict) -> dict:
    old_chans = _extract_channels(old)
    new_chans = _extract_channels(new)
    old_ids = {c["channel_id"] for c in old_chans}
    new_ids = {c["channel_id"] for c in new_chans}
    return {
        "appeared": sorted(new_ids - old_ids),
        "disappeared": sorted(old_ids - new_ids),
        "old_channels": old_chans,
        "new_channels": new_chans,
    }


def _compare_communities(old_chans: list, new_chans: list) -> dict:
    """Canaux ayant changé de communauté (Jaccard < 0.5)."""
    old_comm = {c["channel_id"]: c["community"] for c in old_chans}
    new_comm = {c["channel_id"]: c["community"] for c in new_chans}
    common = set(old_comm) & set(new_comm)
    old_by_comm = defaultdict(set)
    new_by_comm = defaultdict(set)
    for cid in common:
        old_by_comm[old_comm[cid]].add(cid)
        new_by_comm[new_comm[cid]].add(cid)

    drifted = []
    for cid in common:
        if old_comm[cid] != new_comm[cid]:
            old_members = old_by_comm[old_comm[cid]]
            new_members = new_by_comm[new_comm[cid]]
            if _jaccard(old_members, new_members) < 0.5:
                drifted.append({
                    "channel_id": cid,
                    "old_community": old_comm[cid],
                    "new_community": new_comm[cid],
                })
    return {"channels_drifted": drifted}


def _compare_structure(old_chans: list, new_chans: list) -> dict:
    """Détection merge/split communautés (heuristique Jaccard)."""
    old_comm = defaultdict(set)
    new_comm = defaultdict(set)
    for c in old_chans:
        old_comm[c["community"]].add(c["channel_id"])
    for c in new_chans:
        new_comm[c["community"]].add(c["channel_id"])

    merged, split = [], []
    seen_old, seen_new = set(), set()

    # Merge: plusieurs old → une new
    for nid, nmembers in new_comm.items():
        matched = [oid for oid, omembers in old_comm.items()
                   if _jaccard(omembers, nmembers) > 0.3]
        if len(matched) > 1:
            merged.append(matched)
            seen_old.update(matched)
            seen_new.add(nid)

    # Split: une old → plusieurs new
    for oid, omembers in old_comm.items():
        if oid in seen_old:
            continue
        matched = [nid for nid, nmembers in new_comm.items()
                   if nid not in seen_new and _jaccard(omembers, nmembers) > 0.3]
        if len(matched) > 1:
            split.append([oid, matched])

    return {"communities_merged": merged, "communities_split": split}


def main(args: argparse.Namespace) -> None:
    out_subdir = _MISSION_SUBDIRS.get(args.mission, args.mission)
    out_path = ROOT / "data" / out_subdir / "snapshot_diff.json"

    # Pull 2 snapshots (analytics prioritaire, embedding si dispo)
    old = pull_snapshot(out_subdir, "analytics")
    new = pull_snapshot(out_subdir, "embedding") or pull_snapshot(out_subdir, "analytics")

    if not old or not new:
        print("Pas assez de snapshots (besoin 2) — sortie vide")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"note": "Pas de comparaison (snapshots manquants)"}),
                           encoding="utf-8")
        return

    chan_diff = _compare_channels(old, new)
    comm_diff = _compare_communities(chan_diff["old_channels"], chan_diff["new_channels"])
    struct_diff = _compare_structure(chan_diff["old_channels"], chan_diff["new_channels"])

    result = {
        "mission": out_subdir,
        "compared_snapshots": [old.get("label_source") or "analytics",
                              new.get("label_source") or "analytics"],
        "channels_appeared": len(chan_diff["appeared"]),
        "channels_disappeared": len(chan_diff["disappeared"]),
        "channels_drifted": comm_diff["channels_drifted"],
        "communities_merged": struct_diff["communities_merged"],
        "communities_split": struct_diff["communities_split"],
        "note": "Snapshot temporal diff — detect network reconfigurations",
    }

    # Flags reconfigurations significatives
    n_total = len(chan_diff["old_channels"])
    if n_total > 0:
        drift_pct = len(comm_diff["channels_drifted"]) / n_total
        if drift_pct > 0.2:
            result["flag_high_drift"] = f"{drift_pct:.1%} canaux ont changé de communauté"
    if len(struct_diff["communities_merged"]) + len(struct_diff["communities_split"]) > 5:
        result["flag_structural_change"] = "Plus de 5 merge/split détectés"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Diff : {result['channels_appeared']} apparus, "
          f"{result['channels_disappeared']} disparus, "
          f"{len(result['channels_drifted'])} driftés, "
          f"{len(result['communities_merged'])} merges, "
          f"{len(result['communities_split'])} splits")
    if "flag_high_drift" in result or "flag_structural_change" in result:
        print("⚠️  Reconfiguration significative détectée")
    print(f"Écrit : {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compare deux snapshots communautés (temporal diff).")
    ap.add_argument("--mission", default="russosphere",
                    help=f"Mission à analyser (défaut: russosphere). "
                         f"Disponibles: {', '.join(_MISSION_SUBDIRS.keys())}")
    main(ap.parse_args())
