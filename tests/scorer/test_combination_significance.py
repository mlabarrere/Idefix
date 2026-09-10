"""Combinaison rigoureuse de bout en bout : détecte la coordination RÉELLE, pas
la simple position dans le graphe (modèle nul + Stouffer + FDR).

Cœur de la revendication scientifique : un cluster coordonné PLANTÉ est significatif
(p < alpha, verrou franchi, voire flagged FDR), tandis qu'un nœud isolé / un fond
aléatoire ne l'est pas — la suspicion ne récompense pas la centralité seule.
"""
from __future__ import annotations

import dataclasses

from src.graph.loader import build_graph
from src.scorer.channel_suspicion import _DEFAULT_PROFILE, compute_channel_queue
from tests.scorer.test_channel_suspicion import _signal_network, channel_row

_FAST = dataclasses.replace(_DEFAULT_PROFILE, n_null=150, n_bootstrap=60)


def test_planted_multisignal_channel_passes_gate_and_isolated_does_not():
    multi = _signal_network()
    q = compute_channel_queue(multi, top_k=50, profile=_FAST)
    by_id = {c["channel_id"]: c for c in q["channels"]}

    # 201 porte DEUX signaux (forward-influence significative + coordination ≥2
    # types) -> verrou multi-source franchi (T2).
    assert by_id[201]["gate"]["met"] is True
    assert by_id[201]["gate"]["families"] >= 2
    assert by_id[201]["tier"] == "T2"

    # Un nœud de fond à faible intensité (903, queue d'une mini-chaîne) ne franchit
    # pas le verrou.
    assert by_id[903]["gate"]["met"] is False


def test_isolated_channel_is_not_significant():
    """Un canal sans arête : aucune famille structurelle applicable -> suspicion 0,
    p_combined = 1, non flaggé (pas de significativité fabriquée)."""
    multi = build_graph([], [channel_row(5000, username="iso", fr_score=0.9)])
    q = compute_channel_queue(multi, top_k=10, profile=_FAST)
    c = q["channels"][0]
    assert c["suspicion"]["v"] == 0.0
    assert c["p_combined"] == 1.0
    assert c["flagged"] is False


def test_determinism_same_seed_same_bundle():
    """Même rng_seed -> sortie identique (bundle byte-reproductible, EIP)."""
    multi = _signal_network()
    q1 = compute_channel_queue(multi, top_k=50, profile=_FAST)
    q2 = compute_channel_queue(multi, top_k=50, profile=_FAST)
    v1 = {c["channel_id"]: c["suspicion"]["v"] for c in q1["channels"]}
    v2 = {c["channel_id"]: c["suspicion"]["v"] for c in q2["channels"]}
    assert v1 == v2


def test_flagged_implies_low_qvalue():
    """Cohérence FDR : un canal flaggé a une q-value <= alpha du profil."""
    multi = _signal_network()
    q = compute_channel_queue(multi, top_k=50, profile=_FAST)
    for c in q["channels"]:
        if c["flagged"]:
            assert c["q_value"] <= _FAST.alpha + 1e-9


# --------------------------------------------------------------------------- #
# DÉFAUT D4 — continuité de la combinaison au voisinage de « pas de signal ».  #
# --------------------------------------------------------------------------- #
def _p_combined_for_coordination_value(value: float) -> float:
    """Combine une famille (c) synthétique de valeur donnée, seule.

    Reproduit le chemin de ``_combine`` sans dépendre d'un graphe : la famille
    (c) n'a pas de modèle nul, donc sa pseudo-p vaut ``1 - value``.
    """
    import src.scorer.significance as sig
    from src.scorer.channel_suspicion import NO_SIGNAL_PVALUE

    pv = max(1e-12, min(1.0, 1.0 - value))
    if pv >= NO_SIGNAL_PVALUE:
        return 1.0  # exclue de la combinaison -> aucun signal
    _, p = sig.stouffer_combine([pv], [0.25])
    return p


def test_combination_is_continuous_near_zero_signal():
    """Non-régression D4.

    La pseudo-p de la famille (c) vaut ``1 - value``. Avec l'ancien test
    ``pv >= 1.0`` (égalité exacte), ``value == 0.0`` était exclu de Stouffer
    tandis que ``value == 1e-4`` donnait p = 0.9999, soit z ≈ -3.7, ce qui
    écrasait le score combiné. Une variation infinitésimale de l'entrée
    produisait un saut de rang.

    La bande ``NO_SIGNAL_PVALUE`` rend la frontière continue : les valeurs
    indiscernables de zéro sont traitées comme zéro.
    """
    at_zero = _p_combined_for_coordination_value(0.0)
    just_above = _p_combined_for_coordination_value(1e-4)
    assert at_zero == 1.0
    assert just_above == at_zero, (
        "un signal infinitésimal ne doit pas basculer la combinaison"
    )


def test_a_real_signal_still_enters_the_combination():
    """La bande ne doit pas avaler un signal authentique."""
    strong = _p_combined_for_coordination_value(0.5)
    assert strong < 1.0


def test_combined_p_is_monotone_in_the_family_value():
    """Plus la famille porte de signal, plus la p combinée est basse."""
    values = [0.0, 0.05, 0.2, 0.5, 0.9]
    ps = [_p_combined_for_coordination_value(v) for v in values]
    assert ps == sorted(ps, reverse=True)
