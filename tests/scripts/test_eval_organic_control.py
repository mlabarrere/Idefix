from __future__ import annotations

import importlib.util
from pathlib import Path

from src.validation_lab.schema import OrganicControlCorpus

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eval_organic_control.py"


def _load():
    spec = importlib.util.spec_from_file_location("eval_organic_control", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load()


def _corpus():
    return OrganicControlCorpus.model_validate(
        {
            "corpus_id": "organic-fixture",
            "provenance": "Fixture analyste",
            "independence_statement": "Corpus non utilise par le scoreur.",
            "groups": [
                {
                    "group_id": "media-1",
                    "label": "Syndication media",
                    "category": "media",
                    "rationale": "Coordination editoriale attendue.",
                    "channels": [
                        {"username": "@Media_A", "source_ref": "fixture", "confidence": 0.9},
                        {"channel_id": 202, "source_ref": "fixture", "confidence": 0.9},
                    ],
                }
            ],
        }
    )


def test_evaluate_corpus_matches_by_username_and_channel_id():
    channels = [
        {"channel_id": 101, "username": "@media_a", "title": "A", "suspicion": {"v": 0.99}},
        {"channel_id": 202, "username": "@media_b", "title": "B", "suspicion": {"v": 0.98}},
        {"channel_id": 303, "username": "@other", "title": "Other", "suspicion": {"v": 0.2}},
    ]

    report = _mod.evaluate_corpus(_corpus(), channels)

    assert report["matched_channels"] == 2
    assert report["organic_channels_in_top50"] == 2
    assert report["false_positive_alarm"] is True
    assert report["groups"][0]["group_flags_false_positive_risk"] is True
    assert report["groups"][0]["top_matches"][0]["username"] == "media_a"


def test_evaluate_corpus_keeps_unmatched_channels_visible():
    channels = [
        {"channel_id": 303, "username": "@other", "title": "Other", "suspicion": {"v": 0.2}},
    ]

    report = _mod.evaluate_corpus(_corpus(), channels)

    assert report["matched_channels"] == 0
    assert report["organic_channels_in_top50"] == 0
    assert report["false_positive_alarm"] is False
    assert report["groups"][0]["unmatched_channels"] == ["media_a", 202]


def test_missing_corpus_report_is_non_probative():
    report = _mod._missing_corpus_report(
        [{"channel_id": 1, "username": "a", "suspicion": {"v": 0.4}}]
    )

    assert report["has_organic_corpus"] is False
    assert report["false_positive_alarm"] is None
    assert "not probative" in report["method_note"]
