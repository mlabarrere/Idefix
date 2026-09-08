"""Exp 3b — organic control false-positive check.

Reads external organic control corpora from ``data/eval/organic_control_*.json``
and checks whether documented non-hostile coordination groups are surfaced as
high-suspicion pockets. Templates under ``data/eval/templates/`` are ignored.

READ-ONLY on inputs. Writes ``data/eval/organic_control.json``.
Usage: python scripts/eval_organic_control.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _eval_common as ev  # noqa: E402

from src.validation_lab.schema import (  # noqa: E402
    OrganicControlCorpus,
    load_organic_control_corpus,
)

GOLD_DIR = _REPO / "data" / "eval"
WEBAPP_CHANNELS = _REPO / "webapp" / "public" / "data" / "russosphere" / "channels.json"
ChannelIndexes = dict[str, dict[Any, dict[str, Any]]]


def _norm_username(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lstrip("@").lower()
    return cleaned or None


def _score(channel: dict[str, Any]) -> float:
    suspicion = channel.get("suspicion") or {}
    value = suspicion.get("v", 0.0)
    return float(value or 0.0)


def _load_static_channels() -> list[dict[str, Any]]:
    try:
        return ev.load_channels()["channels"]
    except FileNotFoundError:
        return json.loads(WEBAPP_CHANNELS.read_text(encoding="utf-8"))["channels"]


def _rank_channels(channels: list[dict[str, Any]]) -> dict[str, dict[Any, dict[str, Any]]]:
    ordered = sorted(
        channels,
        key=lambda c: (_score(c), str(c.get("username") or "")),
        reverse=True,
    )
    by_username: dict[str, dict[str, Any]] = {}
    by_channel_id: dict[int, dict[str, Any]] = {}

    for rank, channel in enumerate(ordered, start=1):
        enriched = dict(channel)
        enriched["rank"] = rank
        enriched["score"] = _score(channel)
        username = _norm_username(channel.get("username"))
        if username:
            by_username[username] = enriched
        channel_id = channel.get("channel_id")
        if isinstance(channel_id, int):
            by_channel_id[channel_id] = enriched

    return {"by_username": by_username, "by_channel_id": by_channel_id}


def _match_channel(gold_channel: Any, indexes: ChannelIndexes) -> dict[str, Any] | None:
    if gold_channel.channel_id is not None:
        by_id = indexes["by_channel_id"].get(gold_channel.channel_id)
        if by_id is not None:
            return by_id
    if gold_channel.username:
        return indexes["by_username"].get(gold_channel.username)
    return None


def _evaluate_group(group: Any, indexes: dict[str, dict[Any, dict[str, Any]]]) -> dict[str, Any]:
    matched = []
    unmatched = []
    for gold_channel in group.channels:
        channel = _match_channel(gold_channel, indexes)
        if channel is None:
            unmatched.append(gold_channel.username or gold_channel.channel_id)
            continue
        matched.append(
            {
                "username": _norm_username(channel.get("username")),
                "channel_id": channel.get("channel_id"),
                "title": channel.get("title"),
                "rank": channel["rank"],
                "suspicion": round(channel["score"], 4),
            }
        )

    matched.sort(key=lambda item: item["rank"])
    ranks = [int(item["rank"]) for item in matched]
    scores = [float(item["suspicion"]) for item in matched]
    top50 = sum(1 for rank in ranks if rank <= 50)
    top100 = sum(1 for rank in ranks if rank <= 100)

    return {
        "group_id": group.group_id,
        "label": group.label,
        "category": group.category,
        "expected_adversary_linkage": group.expected_adversary_linkage,
        "gold_channels": len(group.channels),
        "matched_channels": len(matched),
        "unmatched_channels": unmatched,
        "top50_count": top50,
        "top100_count": top100,
        "rank_median": statistics.median(ranks) if ranks else None,
        "rank_min": min(ranks) if ranks else None,
        "max_suspicion": round(max(scores), 4) if scores else None,
        "top_matches": matched[:10],
        "group_flags_false_positive_risk": top50 >= 2,
    }


def evaluate_corpus(corpus: OrganicControlCorpus, channels: list[dict[str, Any]]) -> dict[str, Any]:
    indexes = _rank_channels(channels)
    groups = [_evaluate_group(group, indexes) for group in corpus.groups]
    total_matched = sum(int(group["matched_channels"]) for group in groups)
    total_top50 = sum(int(group["top50_count"]) for group in groups)
    total_top100 = sum(int(group["top100_count"]) for group in groups)
    group_flags = [group for group in groups if group["group_flags_false_positive_risk"]]

    return {
        "corpus_id": corpus.corpus_id,
        "mission": corpus.mission,
        "provenance": corpus.provenance,
        "groups_count": len(groups),
        "matched_channels": total_matched,
        "organic_channels_in_top50": total_top50,
        "organic_channels_in_top100": total_top100,
        "false_positive_alarm": total_top50 >= 3 or bool(group_flags),
        "alarm_rule": "alarm if >=3 organic channels in top50, or >=2 in top50 within one group",
        "groups": groups,
    }


def evaluate_all(
    corpora: list[OrganicControlCorpus],
    channels: list[dict[str, Any]],
) -> dict[str, Any]:
    reports = [evaluate_corpus(corpus, channels) for corpus in corpora]
    return {
        "experiment": "organic_control_false_positive_check",
        "has_organic_corpus": bool(corpora),
        "n_channels": len(channels),
        "corpora": reports,
        "false_positive_alarm": any(report["false_positive_alarm"] for report in reports),
        "method_note": (
            "This is a falsification control: documented organic coordination should not dominate "
            "the suspicion top ranks without additional adversarial evidence."
        ),
    }


def _missing_corpus_report(channels: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "experiment": "organic_control_false_positive_check",
        "has_organic_corpus": False,
        "n_channels": len(channels),
        "corpora": [],
        "false_positive_alarm": None,
        "method_note": (
            "No data/eval/organic_control_*.json corpus was found. The false-positive control "
            "is therefore not probative yet."
        ),
        "next_action": (
            "Create at least one organic control corpus from the template in "
            "data/eval/templates/organic_control_corpus.example.json."
        ),
    }


def main() -> None:
    channels = _load_static_channels()
    corpus_files = sorted(GOLD_DIR.glob("organic_control_*.json")) if GOLD_DIR.exists() else []
    if not corpus_files:
        report = _missing_corpus_report(channels)
    else:
        corpora = [load_organic_control_corpus(path) for path in corpus_files]
        report = evaluate_all(corpora, channels)

    path = ev.write_report("organic_control.json", report)
    print(f"[Exp3b organic-control] écrit -> {path} | corpus organique: {bool(corpus_files)}")
    if not corpus_files:
        print("  aucun corpus data/eval/organic_control_*.json trouvé")
        return
    print(f"  alarme faux positifs: {report['false_positive_alarm']}")
    for corpus_report in report["corpora"]:
        print(
            f"  {corpus_report['corpus_id']}: "
            f"{corpus_report['matched_channels']} canaux matches | "
            f"top50={corpus_report['organic_channels_in_top50']} | "
            f"top100={corpus_report['organic_channels_in_top100']}"
        )


if __name__ == "__main__":
    main()
