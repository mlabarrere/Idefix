"""Pure embedding-based channel classification (local mirror of the Mistral track).

Produces the SAME fields as the Mistral ``CHANNEL_SCHEMA`` (is_gan_footprint /
is_france_ukraine / actor_type / themes / confidence / rationale) but from a
local embedding + zero-shot nearest-centroid, so it is free, fast and
deterministic. This module is PURE (numpy only): the script wires DB I/O around
it, and tests exercise it offline with synthetic vectors.

Thresholds (``theme_threshold`` / ``flag_threshold``) are model-specific and
**must be calibrated** against the shared gold (see ``scripts/calibrate_text_sim``
/ ``eval_*``); the defaults here are conservative seeds, not validated cutoffs.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from src.embed.centroids import classify

# Mission name -> the boolean target field it populates (parity with Mistral).
TARGET_FLAG: dict[str, str] = {
    "gan": "is_gan_footprint",
    "france_ukraine": "is_france_ukraine",
}

# Small multilingual (FR/RU/EN) anchor sets for zero-shot actor typing. Coarse by
# design — a seed for the calibration loop, not a validated taxonomy.
ACTOR_TYPE_ANCHORS: dict[str, list[str]] = {
    "press": ["média d'information", "rédaction journal", "agence de presse",
              "newsroom press agency", "СМИ редакция новости"],
    "osint": ["osint analyse open source", "renseignement open source",
              "open source intelligence tracking", "разведка по открытым источникам"],
    "milblogger": ["blogueur militaire", "war correspondent front",
                   "военкор военный блогер фронт"],
    "state_aligned": ["média d'état propagande", "state media ministry",
                      "государственное сми пропаганда"],
    "activist": ["militant collectif mobilisation", "activist protest movement",
                 "активисты мобилизация протест"],
    "aggregator": ["agrégateur revue de presse fil d'actualité",
                   "news aggregator feed", "новостной агрегатор лента"],
}


def classify_channel(
    vec: np.ndarray,
    mission_centroids: Mapping[str, np.ndarray],
    actor_centroids: Mapping[str, np.ndarray] | None,
    *,
    mission_name: str,
    theme_threshold: float = 0.20,
    flag_threshold: float = 0.30,
    max_themes: int = 5,
) -> dict:
    """Classify one L2-normalized channel vector into the Mistral output schema."""
    best_cat, mission_score, cat_scores = classify(vec, mission_centroids)

    themes = [
        cat for cat, _ in sorted(cat_scores.items(), key=lambda kv: kv[1], reverse=True)
        if cat_scores[cat] >= theme_threshold
    ][:max_themes]

    actor_type: str | None = None
    actor_score = 0.0
    if actor_centroids:
        actor_type, actor_score, _ = classify(vec, actor_centroids)

    flags: dict[str, bool | None] = {"is_gan_footprint": None, "is_france_ukraine": None}
    flag_field = TARGET_FLAG.get(mission_name)
    if flag_field is not None:
        flags[flag_field] = bool(mission_score >= flag_threshold)

    confidence = round(max(0.0, min(1.0, mission_score)), 4)
    rationale = (
        f"embedding local (coût 0) : cosinus {mission_score:.3f} vers « {best_cat} » ; "
        f"thèmes={themes} ; type d'acteur≈{actor_type} ({actor_score:.2f})"
    )
    return {
        **flags,
        "actor_type": actor_type,
        "themes": themes,
        "confidence": confidence,
        "rationale": rationale,
        "mission_score": float(mission_score),
    }
