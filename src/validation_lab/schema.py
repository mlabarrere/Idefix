"""Validation Lab schemas.

These contracts make the validation inputs explicit and non-circular:
external gold episodes must come from human/external sources, and organic
control corpora must document why they are non-hostile coordination examples.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GoldChannel(BaseModel):
    """One externally identified channel in a documented episode."""

    username: str | None = None
    channel_id: int | None = None
    role: Literal["seed", "relay", "bridge", "monitor", "unknown"] = "unknown"
    source_ref: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    @model_validator(mode="after")
    def _has_identifier(self) -> "GoldChannel":
        if self.username is None and self.channel_id is None:
            raise ValueError("gold channel requires username or channel_id")
        return self

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lstrip("@").lower()
        if not cleaned:
            raise ValueError("username cannot be empty")
        return cleaned

    @field_validator("source_ref")
    @classmethod
    def _source_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("source_ref must be non-empty")
        return value


class ExternalGoldEpisode(BaseModel):
    """Non-circular gold episode used by `eval_episode_recovery.py`."""

    schema_version: Literal["validation-gold-episode/v1"] = "validation-gold-episode/v1"
    episode_id: str
    title: str
    mission: str = "russosphere"
    provenance: str
    independence_statement: str
    claims: list[str] = Field(default_factory=list)
    channels: list[GoldChannel] = Field(min_length=1)
    excluded_from_scorer_inputs: bool = True
    created_by: str | None = None
    created_at: str | None = None

    @field_validator("episode_id", "title", "provenance", "independence_statement")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("required gold episode fields must be non-empty")
        return value

    @model_validator(mode="after")
    def _must_be_independent(self) -> "ExternalGoldEpisode":
        if not self.excluded_from_scorer_inputs:
            raise ValueError("external gold must be excluded from scorer inputs")
        if not any(c.role == "seed" for c in self.channels):
            raise ValueError("external gold episode requires at least one seed channel")
        return self

    def legacy_eval_payload(self) -> dict[str, object]:
        """Payload compatible with the existing eval_episode_recovery.py reader."""

        seeds = [c.username for c in self.channels if c.role == "seed" and c.username]
        relays = [
            c.username
            for c in self.channels
            if c.role in {"relay", "bridge", "monitor", "unknown"} and c.username
        ]
        return {
            "episode": self.title,
            "seeds": seeds,
            "relays": relays,
            "provenance": self.provenance,
        }


class OrganicControlGroup(BaseModel):
    """One non-hostile coordinated group used to test false positives."""

    group_id: str
    label: str
    category: Literal["media", "institution", "activism", "sport", "civil_event", "other"]
    rationale: str
    channels: list[GoldChannel] = Field(min_length=2)
    expected_adversary_linkage: Literal["none", "low"] = "none"

    @field_validator("group_id", "label", "rationale")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("organic group fields must be non-empty")
        return value


class OrganicControlCorpus(BaseModel):
    """Corpus of organic French coordination examples."""

    schema_version: Literal["organic-control-corpus/v1"] = "organic-control-corpus/v1"
    corpus_id: str
    mission: str = "russosphere"
    provenance: str
    independence_statement: str
    groups: list[OrganicControlGroup] = Field(min_length=1)
    created_by: str | None = None
    created_at: str | None = None

    @field_validator("corpus_id", "provenance", "independence_statement")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("organic corpus fields must be non-empty")
        return value


def load_external_gold_episode(path: str | Path) -> ExternalGoldEpisode:
    """Load and validate one external gold episode JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return ExternalGoldEpisode.model_validate(data)


def load_organic_control_corpus(path: str | Path) -> OrganicControlCorpus:
    """Load and validate one organic control corpus JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return OrganicControlCorpus.model_validate(data)
