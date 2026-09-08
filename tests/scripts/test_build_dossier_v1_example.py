from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_dossier_v1_example.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_dossier_v1_example", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()


def _write_bundle(root: Path) -> Path:
    bundle = root / "russosphere"
    bundle.mkdir(parents=True)
    channels = [
        {
            "channel_id": 1,
            "username": "@source",
            "title": "Source",
            "suspicion": {"v": 0.9, "lo": 0.7, "hi": 0.95},
            "archetype": "cross-channel-bridge",
            "scores": {"a": {"v": 0.8}, "c": {"v": 0.7}, "d": {"v": 0.6}},
        },
        {
            "channel_id": 2,
            "username": "@relay",
            "title": "Relay",
            "suspicion": {"v": 0.7, "lo": 0.5, "hi": 0.8},
            "archetype": "forward-hub",
            "scores": {"a": {"v": 0.5}, "c": {"v": 0.9}, "d": {"v": 0.1}},
        },
    ]
    (bundle / "channels.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-15T12:00:00+00:00",
                "coverage_callout": "Telegram only",
                "symmetric_ratio": {"ratio": 0.4},
                "total": 2,
                "channels": channels,
                "export_metadata": {
                    "methodology_version": "method/v-test",
                    "scorer_version": "scorer/v-test",
                    "export_version": "export/v-test",
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle / "graph.json").write_text(
        json.dumps(
            {
                "edges": [
                    {
                        "family": "coordination",
                        "type": "CO_FORWARD",
                        "a": 1,
                        "b": 2,
                        "count": 4,
                        "dt_seconds": 120,
                    },
                    {"family": "propagation", "type": "FORWARD", "source": 1, "target": 2},
                ]
            }
        ),
        encoding="utf-8",
    )
    return bundle


def test_build_dossier_from_static_bundle_contains_roles_pocket_and_edge(tmp_path):
    bundle = _write_bundle(tmp_path)

    dossier = _mod.build_dossier_from_static_bundle(
        mission="russosphere",
        bundle_dir=bundle,
        top_n=2,
    )

    assert dossier.schema_version == "evidence-dossier/v1"
    assert dossier.episode.episode_id == "example:russosphere:france-ukraine"
    assert dossier.attribution_tier == "T2"
    assert dossier.score_run.channel_count == 2
    assert len(dossier.channel_roles) == 2
    assert dossier.channel_roles[0].cascade_role == "cross-channel-bridge"
    assert len(dossier.pockets) == 1
    assert dossier.pockets[0].member_channel_ids == [1, 2]
    assert len(dossier.coordination_edges) == 1
    assert dossier.method_versions.scorer_version == "scorer/v-test"


def test_write_dossier_outputs_valid_json(tmp_path):
    bundle = _write_bundle(tmp_path)
    dossier = _mod.build_dossier_from_static_bundle(
        mission="russosphere",
        bundle_dir=bundle,
        top_n=1,
    )
    out = tmp_path / "dossier.json"

    _mod.write_dossier(out, dossier)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "evidence-dossier/v1"
    assert data["coverage_limits"][0]["limit_id"] == "telegram-only"
