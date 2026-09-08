"""Offline tests for pure embedding-based channel classification."""
from __future__ import annotations

import numpy as np

from src.embed.classify import classify_channel

_MISSION = {
    "carrier": np.array([1.0, 0.0, 0.0], np.float32),
    "escort": np.array([0.0, 1.0, 0.0], np.float32),
}
_ACTORS = {
    "press": np.array([1.0, 0.0, 0.0], np.float32),
    "osint": np.array([0.0, 0.0, 1.0], np.float32),
}


def test_gan_flag_set_when_above_threshold():
    vec = np.array([1.0, 0.0, 0.0], np.float32)  # == carrier centroid
    out = classify_channel(vec, _MISSION, _ACTORS, mission_name="gan", flag_threshold=0.3)
    assert out["is_gan_footprint"] is True
    assert out["is_france_ukraine"] is None
    assert out["themes"] == ["carrier"]  # escort cosine 0 < theme_threshold
    assert out["actor_type"] == "press"
    assert out["confidence"] == 1.0
    assert "coût 0" in out["rationale"]


def test_flag_false_when_below_threshold():
    vec = np.array([0.2, 0.0, 0.0], np.float32)  # cosine to carrier = 0.2 (normalized -> 1.0? no)
    # normalize so cosine is genuinely small: blend carrier + orthogonal
    vec = np.array([0.25, 0.0, 0.97], np.float32)
    vec = vec / np.linalg.norm(vec)
    out = classify_channel(vec, _MISSION, _ACTORS, mission_name="gan", flag_threshold=0.5)
    assert out["is_gan_footprint"] is False


def test_france_ukraine_maps_to_its_flag():
    vec = np.array([1.0, 0.0, 0.0], np.float32)
    out = classify_channel(
        vec, _MISSION, _ACTORS, mission_name="france_ukraine", flag_threshold=0.3
    )
    assert out["is_france_ukraine"] is True
    assert out["is_gan_footprint"] is None


def test_unknown_mission_sets_no_flag():
    vec = np.array([1.0, 0.0, 0.0], np.float32)
    out = classify_channel(vec, _MISSION, _ACTORS, mission_name="russosphere")
    assert out["is_gan_footprint"] is None
    assert out["is_france_ukraine"] is None
    # themes/actor still produced
    assert out["themes"] == ["carrier"]
