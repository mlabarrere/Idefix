"""Smoke test famille (f) — score_embedding_coherence (synthétique, SANS modèle ni DB).

Vecteurs L2-normalisés en base canonique 3D : orthogonaux => cosine 0, identiques => 1.
"""
import numpy as np

from src.scorer.embedding_signals import score_embedding_coherence

# Base orthonormale : cosine(e0,e1)=0, cosine(e0,e0)=1.
BASELINE = np.array([1.0, 0.0, 0.0], dtype=np.float32)   # organique
ADVERSARY = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # adverse
adversary_emb = {99: ADVERSARY}


async def test_close_to_baseline_is_low():
    # Canal == baseline : dist 0, prox adversaire 0 => score bas.
    scores = await score_embedding_coherence(None, {1: BASELINE}, BASELINE, adversary_emb)
    assert scores[1].value < 0.3
    assert scores[1].evidence["baseline_distance"] == 0.0


async def test_close_to_adversary_is_high():
    # Canal == adversaire : loin baseline (dist 1) + collé adversaire (prox 1) => score haut.
    scores = await score_embedding_coherence(None, {2: ADVERSARY}, BASELINE, adversary_emb)
    assert scores[2].value > 0.7
    assert scores[2].evidence["adversary_proximity"] == 1.0
    assert scores[2].evidence["closest_adversary_id"] == 99


async def test_score_clamped_and_evidence_keys():
    scores = await score_embedding_coherence(
        None, {1: BASELINE, 2: ADVERSARY}, BASELINE, adversary_emb
    )
    for res in scores.values():
        assert 0.0 <= res.value <= 1.0
        expected = {"baseline_distance", "adversary_proximity", "closest_adversary_id"}
        assert expected <= res.evidence.keys()
