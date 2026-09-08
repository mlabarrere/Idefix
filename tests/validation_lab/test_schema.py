import json

import pytest
from pydantic import ValidationError

from src.validation_lab.schema import (
    ExternalGoldEpisode,
    GoldChannel,
    OrganicControlCorpus,
    load_external_gold_episode,
    load_organic_control_corpus,
)


def _gold_payload():
    return {
        "episode_id": "gold-test",
        "title": "Episode externe test",
        "provenance": "Source externe fixture",
        "independence_statement": "Fixture indépendante des inputs scorer.",
        "channels": [
            {
                "username": "@Seed_Channel",
                "role": "seed",
                "source_ref": "rapport externe",
                "confidence": 0.9,
            },
            {
                "username": "relay_channel",
                "role": "relay",
                "source_ref": "rapport externe",
                "confidence": 0.8,
            },
        ],
    }


def _organic_payload():
    return {
        "corpus_id": "organic-test",
        "provenance": "Fixture analyste",
        "independence_statement": "Groupes non utilisés pour scorer.",
        "groups": [
            {
                "group_id": "media-1",
                "label": "Syndication média",
                "category": "media",
                "rationale": "Co-posting attendu entre médias affiliés.",
                "channels": [
                    {"username": "media_a", "source_ref": "fixture", "confidence": 0.9},
                    {"username": "media_b", "source_ref": "fixture", "confidence": 0.9},
                ],
            }
        ],
    }


def test_gold_channel_requires_username_or_channel_id():
    with pytest.raises(ValidationError):
        GoldChannel(source_ref="rapport externe", confidence=0.8)


def test_gold_episode_requires_seed_channel():
    payload = _gold_payload()
    payload["channels"][0]["role"] = "relay"

    with pytest.raises(ValidationError):
        ExternalGoldEpisode.model_validate(payload)


def test_gold_episode_requires_independence_from_scorer_inputs():
    payload = _gold_payload()
    payload["excluded_from_scorer_inputs"] = False

    with pytest.raises(ValidationError):
        ExternalGoldEpisode.model_validate(payload)


def test_gold_episode_normalizes_usernames_and_legacy_payload():
    gold = ExternalGoldEpisode.model_validate(_gold_payload())

    assert gold.channels[0].username == "seed_channel"
    assert gold.legacy_eval_payload()["seeds"] == ["seed_channel"]
    assert gold.legacy_eval_payload()["relays"] == ["relay_channel"]


def test_organic_corpus_requires_groups_with_multiple_channels():
    corpus = OrganicControlCorpus.model_validate(_organic_payload())

    assert corpus.groups[0].category == "media"
    assert len(corpus.groups[0].channels) == 2


def test_loaders_accept_utf8_sig_json(tmp_path):
    gold_path = tmp_path / "gold.json"
    organic_path = tmp_path / "organic.json"
    gold_path.write_text("\ufeff" + json.dumps(_gold_payload()), encoding="utf-8")
    organic_path.write_text("\ufeff" + json.dumps(_organic_payload()), encoding="utf-8")

    assert load_external_gold_episode(gold_path).episode_id == "gold-test"
    assert load_organic_control_corpus(organic_path).corpus_id == "organic-test"
