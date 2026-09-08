"""Build one EvidenceDossierV1 example from a static webapp bundle.

This closes the pre-production sponsor path: an already exported static mission
bundle can produce an auditable dossier object without touching PostgreSQL or
Telegram.

Usage:
    python scripts/build_dossier_v1_example.py --mission russosphere
    python scripts/build_dossier_v1_example.py --mission gan
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.dossier.v1 import EvidenceDossierV1, build_evidence_dossier_v1  # noqa: E402
from src.pockets.scoring import PocketInput, PocketMetrics, build_pocket_record  # noqa: E402
from src.shared.analytical_contract import (  # noqa: E402
    ChannelRoleEvidence,
    CoordinationEdgeEvidence,
    CoverageLimit,
    EpisodeRecord,
    MethodVersion,
    ScoreRunRecord,
)

_WEBAPP_DATA = _REPO / "webapp" / "public" / "data"
_DEFAULT_OUT = _REPO / "data" / "dossiers"

_MISSION_EXAMPLES = {
    "russosphere": {
        "episode_id": "example:russosphere:france-ukraine",
        "title": "Exemple dossier — infosphère France / Ukraine",
        "claim_ids": ["example:france-ukraine"],
        "thematic_category": "france_ukraine",
        "target_entity": "FR_integrity",
        "source_refs": ["webapp/public/data/russosphere/channels.json"],
        "note": (
            "Dossier exemple généré depuis le bundle statique russosphere ; "
            "il illustre la structure de preuve, pas un verdict analyste final."
        ),
    },
    "gan": {
        "episode_id": "example:gan:telegram-footprint",
        "title": "Exemple dossier — empreinte informationnelle Telegram du GAN",
        "claim_ids": ["example:gan-footprint"],
        "thematic_category": "gan_telegram_footprint",
        "target_entity": "FR_defense_asset",
        "source_refs": ["webapp/public/data/gan/channels.json"],
        "note": (
            "Dossier exemple généré depuis le bundle statique GAN ; il mesure "
            "l'observable Telegram, pas l'empreinte informationnelle totale."
        ),
    },
}

_VALID_COORDINATION_TYPES = {
    "CO_FORWARD",
    "CO_URL",
    "CO_URL_EXACT",
    "CO_HASHTAG",
    "COPYPASTA",
    "TEXT_SIM",
    "TRANSLATION",
    "MEDIA_REUSE",
}
_VALID_ROLES = {
    "seeding-source",
    "forward-hub",
    "cross-channel-bridge",
    "reactivator",
    "unclassified",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mission_example(mission: str) -> dict[str, Any]:
    return _MISSION_EXAMPLES.get(
        mission,
        {
            "episode_id": f"example:{mission}:static-dossier",
            "title": f"Exemple dossier — mission {mission}",
            "claim_ids": [f"example:{mission}"],
            "thematic_category": "static_bundle_example",
            "target_entity": "FR_integrity",
            "source_refs": [f"webapp/public/data/{mission}/channels.json"],
            "note": "Dossier exemple généré depuis le bundle statique.",
        },
    )


def _score(channel: dict[str, Any]) -> float:
    return float(((channel.get("suspicion") or {}).get("v")) or 0.0)


def _confidence(channel: dict[str, Any], key: str, default: float) -> float:
    return float(((channel.get("suspicion") or {}).get(key)) or default)


def _component(channel: dict[str, Any], family: str) -> float:
    score = (channel.get("scores") or {}).get(family) or {}
    if score.get("na"):
        return 0.0
    return max(0.0, min(1.0, float(score.get("v") or 0.0)))


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _role(channel: dict[str, Any]) -> str:
    archetype = channel.get("archetype") or "unclassified"
    return archetype if archetype in _VALID_ROLES else "unclassified"


def _coverage_limits() -> list[CoverageLimit]:
    return [
        CoverageLimit(
            limit_id="telegram-only",
            label="Couverture Telegram public uniquement",
            description=(
                "Le dossier observe le bundle Telegram statique. Il ne couvre pas "
                "l'amplification sur X, médias, plateformes privées ou signaux hors Telegram."
            ),
            severity="degraded",
        )
    ]


def _method_versions(channels_payload: dict[str, Any]) -> MethodVersion:
    metadata = channels_payload.get("export_metadata") or {}
    return MethodVersion(
        methodology_version_hash=metadata.get("methodology_version", "idefix-methodology/unknown"),
        scorer_version=metadata.get("scorer_version", "explainable-channel-suspicion/unknown"),
        edge_builder_version=metadata.get("edge_builder_version", "static-graph-export/unknown"),
        claim_matcher_version=metadata.get("claim_matcher_version"),
        export_version=metadata.get("export_version", "static-bundle/unknown"),
    )


def _channel_roles(mission: str, channels: list[dict[str, Any]]) -> list[ChannelRoleEvidence]:
    roles = []
    for channel in channels:
        roles.append(
            ChannelRoleEvidence(
                channel_id=int(channel["channel_id"]),
                mission=mission,
                attribution_tier="T2" if _component(channel, "c") >= 0.5 else "T1",
                cascade_role=_role(channel),  # type: ignore[arg-type]
                score=_score(channel),
                confidence_low=_confidence(channel, "lo", 0.0),
                confidence_high=_confidence(channel, "hi", 1.0),
                evidence_refs=[f"channels/{channel['channel_id']}.json"],
            )
        )
    return roles


def _pocket(
    *,
    mission: str,
    example: dict[str, Any],
    channels: list[dict[str, Any]],
    generated_at: str,
) -> Any:
    channel_ids = [int(channel["channel_id"]) for channel in channels]
    metrics = PocketMetrics(
        claim_exposure=_avg([_component(channel, "a") for channel in channels]),
        coordination_density=_avg([_component(channel, "c") for channel in channels]),
        bridge_presence=_avg([1.0 if _role(channel) == "cross-channel-bridge" else 0.0
                              for channel in channels]),
        recidivism=_avg([_component(channel, "d") for channel in channels]),
        stability=0.0,
        volume=min(1.0, len(channels) / 10),
        coverage=1.0,
    )
    return build_pocket_record(
        PocketInput(
            pocket_id=f"example:{mission}:top-static-pocket",
            mission=mission,
            window_start=generated_at,
            window_end=generated_at,
            member_channel_ids=channel_ids,
            metrics=metrics,
            claim_ids=list(example["claim_ids"]),
            coverage_limits=_coverage_limits(),
        )
    )


def _coordination_edges(
    *,
    mission: str,
    graph_payload: dict[str, Any],
    selected_channel_ids: set[int],
    generated_at: str,
) -> list[CoordinationEdgeEvidence]:
    out: list[CoordinationEdgeEvidence] = []
    for edge in graph_payload.get("edges", []):
        if edge.get("family") != "coordination":
            continue
        edge_type = edge.get("type")
        if edge_type not in _VALID_COORDINATION_TYPES:
            continue
        source = edge.get("a", edge.get("source"))
        target = edge.get("b", edge.get("target"))
        if source not in selected_channel_ids or target not in selected_channel_ids:
            continue
        count = int(edge.get("count") or 1)
        out.append(
            CoordinationEdgeEvidence(
                edge_type=edge_type,
                source_channel_id=int(source),
                target_channel_id=int(target),
                mission=mission,
                window_start=generated_at,
                window_end=generated_at,
                score=min(1.0, count / 5),
                method=f"static_bundle:{edge_type.lower()}",
                evidence_refs=[f"graph:{edge_type}:{source}:{target}"],
            )
        )
        if len(out) >= 25:
            break
    return out


def build_dossier_from_static_bundle(
    *,
    mission: str,
    bundle_dir: Path,
    top_n: int = 8,
) -> EvidenceDossierV1:
    channels_payload = _load_json(bundle_dir / "channels.json")
    graph_path = bundle_dir / "graph.json"
    graph_payload = _load_json(graph_path) if graph_path.exists() else {"edges": []}
    generated_at = channels_payload.get("generated_at") or "unknown"
    channels = sorted(
        channels_payload.get("channels", []),
        key=lambda channel: (_score(channel), str(channel.get("username") or "")),
        reverse=True,
    )[:top_n]
    if not channels:
        raise ValueError(f"No channels found in {bundle_dir / 'channels.json'}")

    example = _mission_example(mission)
    method_versions = _method_versions(channels_payload)
    channel_roles = _channel_roles(mission, channels)
    selected_channel_ids = {role.channel_id for role in channel_roles}
    episode = EpisodeRecord(
        episode_id=example["episode_id"],
        title=example["title"],
        mission=mission,
        claim_ids=list(example["claim_ids"]),
        canonical_claim_id=example["claim_ids"][0],
        thematic_category=example["thematic_category"],
        target_entity=example["target_entity"],
        window_start=generated_at,
        window_end=generated_at,
        source_refs=list(example["source_refs"]),
    )
    score_run = ScoreRunRecord(
        run_id=f"static-export:{mission}:{generated_at}",
        mission=mission,
        created_at=generated_at,
        method_versions=method_versions,
        channel_count=int(
            channels_payload.get("total") or len(channels_payload.get("channels", []))
        ),
        top_k=len(channels),
        coverage_limits=_coverage_limits(),
        symmetric_ratio=channels_payload.get("symmetric_ratio") or {},
    )
    pocket = _pocket(
        mission=mission,
        example=example,
        channels=channels,
        generated_at=generated_at,
    )
    edges = _coordination_edges(
        mission=mission,
        graph_payload=graph_payload,
        selected_channel_ids=selected_channel_ids,
        generated_at=generated_at,
    )
    tier = "T2" if edges or any(role.attribution_tier == "T2" for role in channel_roles) else "T1"
    return build_evidence_dossier_v1(
        dossier_id=f"example:{mission}:evidence-dossier-v1",
        episode=episode,
        attribution_tier=tier,  # type: ignore[arg-type]
        method_versions=method_versions,
        score_run=score_run,
        channel_roles=channel_roles,
        pockets=[pocket],
        coordination_edges=edges,
        coverage_limits=_coverage_limits(),
        analyst_notes=[example["note"]],
    )


def write_dossier(path: Path, dossier: EvidenceDossierV1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dossier.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an EvidenceDossierV1 example.")
    parser.add_argument("--mission", default="russosphere")
    parser.add_argument("--data-root", type=Path, default=_WEBAPP_DATA)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--top-n", type=int, default=8)
    args = parser.parse_args()

    bundle_dir = args.data_root / args.mission
    out = args.out or _DEFAULT_OUT / f"evidence_dossier_v1_{args.mission}_example.json"
    dossier = build_dossier_from_static_bundle(
        mission=args.mission,
        bundle_dir=bundle_dir,
        top_n=args.top_n,
    )
    write_dossier(out, dossier)
    print(f"[dossier v1 example] écrit -> {out}")


if __name__ == "__main__":
    main()
