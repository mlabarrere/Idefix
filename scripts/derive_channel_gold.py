"""Dérive le GOLD niveau-canal (suspect/bénin) depuis les golds externes.

READ-ONLY sur les golds ; écrit UNIQUEMENT ``data/eval/channel_gold.json``.
Non-circulaire : ne lit ni ``channels.json`` ni les sorties du scorer.

Usage :
    python scripts/derive_channel_gold.py --mission russosphere
    python scripts/derive_channel_gold.py --episodes data/eval/gold_episode_*.json \
        --organic data/eval/organic_control_*.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402
from src.validation_lab.channel_gold import derive_channel_gold  # noqa: E402

_EVAL = _ROOT / "data" / "eval"


def main(args: argparse.Namespace) -> None:
    mission = resolve_mission(args.mission)
    episodes = [Path(p) for p in (args.episodes or sorted(_EVAL.glob("gold_episode_*.json")))]
    organic = [Path(p) for p in (args.organic or sorted(_EVAL.glob("organic_control_*.json")))]
    if not episodes:
        raise SystemExit(
            f"Aucun épisode gold dans {_EVAL} (gold_episode_*.json). "
            f"Voir data/eval/templates/gold_episode.example.json."
        )
    gold = derive_channel_gold(episodes, organic, mission=mission.name)
    _EVAL.mkdir(parents=True, exist_ok=True)
    out = _EVAL / "channel_gold.json"
    out.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[gold] {out} · {len(gold['positives'])} positifs, "
        f"{len(gold['negatives'])} négatifs (mission={mission.name})"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dérive le gold niveau-canal (non-circulaire).")
    add_mission_arg(ap)
    ap.add_argument("--episodes", nargs="*", help="chemins des épisodes gold (défaut: glob)")
    ap.add_argument("--organic", nargs="*", help="chemins des corpus organiques (défaut: glob)")
    main(ap.parse_args())
