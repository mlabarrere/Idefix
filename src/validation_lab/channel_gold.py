"""Dérivation d'un GOLD niveau-CANAL (suspect / bénin) — vérité de validation.

Le scoring rigoureux se VALIDE contre une vérité INDÉPENDANTE et NON-CIRCULAIRE :
- positifs (suspect) = seeds + relays des épisodes gold externes
  (``ExternalGoldEpisode``, ``excluded_from_scorer_inputs=True``) ;
- négatifs (bénin)   = canaux des corpus de contrôle organique
  (``OrganicControlCorpus``, ``expected_adversary_linkage`` ∈ {none, low}).

Contrat de NON-CIRCULARITÉ (load-bearing) : on ne lit QUE le gold externe + le
corpus organique — JAMAIS ``channels.json`` ni une sortie du scorer ni l'allowlist.
La dérivation REFUSE toute source dont ``excluded_from_scorer_inputs`` n'est pas
vrai. L'``independence_statement`` est reporté verbatim.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.validation_lab.schema import (
    load_external_gold_episode,
    load_organic_control_corpus,
)


def _norm(u: str | None) -> str | None:
    return u.lstrip("@").lower() if u else None


def derive_channel_gold(
    episode_paths: list[Path], organic_paths: list[Path], *, mission: str
) -> dict:
    """Compose le gold niveau-canal à partir des épisodes + corpus organiques."""
    positives: dict[str, dict] = {}
    negatives: dict[str, dict] = {}
    derived_from: list[str] = []
    independence: list[str] = []

    for p in episode_paths:
        ep = load_external_gold_episode(p)
        if not ep.excluded_from_scorer_inputs:
            raise ValueError(
                f"épisode {p} non exclu des entrées du scorer : circularité refusée."
            )
        derived_from.append(str(p.name))
        stmt = getattr(ep, "independence_statement", "") or ""
        if stmt:
            independence.append(stmt)
        for ch in ep.channels:
            key = _norm(ch.username) or (f"#{ch.channel_id}" if ch.channel_id else None)
            if not key:
                continue
            positives.setdefault(
                key,
                {"username": ch.username, "channel_id": ch.channel_id,
                 "role": ch.role, "source_ref": ep.episode_id},
            )

    for p in organic_paths:
        corpus = load_organic_control_corpus(p)
        derived_from.append(str(p.name))
        if corpus.independence_statement:
            independence.append(corpus.independence_statement)
        for grp in corpus.groups:
            for ch in grp.channels:
                key = _norm(ch.username) or (f"#{ch.channel_id}" if ch.channel_id else None)
                if not key or key in positives:
                    continue  # un positif documenté prime (ne pas le marquer bénin)
                negatives.setdefault(
                    key,
                    {"username": ch.username, "channel_id": ch.channel_id,
                     "group_id": grp.group_id, "category": grp.category},
                )

    return {
        "schema_version": "channel-gold/v1",
        "mission": mission,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "derived_from": derived_from,
        "excluded_from_scorer_inputs": True,
        "independence_statement": " | ".join(dict.fromkeys(independence))
        or "Dérivé exclusivement de golds externes non-circulaires.",
        "positives": list(positives.values()),
        "negatives": list(negatives.values()),
    }
