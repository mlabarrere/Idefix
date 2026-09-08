"""Socle statistique du scoring rigoureux — modèle nul, p-values, Stouffer, FDR."""
from __future__ import annotations

import numpy as np

from src.scorer.significance import (
    benjamini_hochberg,
    make_rng,
    null_significance,
    stouffer_combine,
)


def test_null_significance_add_one_p_never_zero():
    null = np.zeros(100)
    out = null_significance(observed=10.0, null_samples=null)
    # observé bien au-dessus du null → p minimale mais JAMAIS 0 (add-one).
    assert out["p_one_sided"] == round(1 / 101, 6)
    assert out["p_one_sided"] > 0
    assert out["z"] == 0.0  # std nul → z=0, pas de NaN


def test_null_significance_observed_within_null():
    rng = make_rng(7)
    null = rng.normal(0.0, 1.0, size=2000)
    out = null_significance(observed=0.0, null_samples=null)
    # une valeur au centre du null n'est pas significative (p ~ 0.5).
    assert 0.4 < out["p_one_sided"] < 0.6
    assert abs(out["z"]) < 0.2


def test_null_significance_empty():
    out = null_significance(observed=1.0, null_samples=np.array([]))
    assert out["p_one_sided"] == 1.0 and out["z"] == 0.0


def test_stouffer_combine_known_values():
    # deux p=0.5 (z=0) avec poids égaux → Z=0 → p=0.5
    z, p = stouffer_combine([0.5, 0.5], [1.0, 1.0])
    assert abs(z) < 1e-6 and abs(p - 0.5) < 1e-6
    # une p très petite tire la combinaison vers la significativité.
    z2, p2 = stouffer_combine([0.001, 0.5], [1.0, 1.0])
    assert z2 > 0 and p2 < 0.5


def test_stouffer_empty_is_nonsignificant():
    assert stouffer_combine([], []) == (0.0, 1.0)


def test_benjamini_hochberg_flags_small_pvalues():
    pvals = [0.001, 0.002, 0.5, 0.9, 0.8]
    rejected, q = benjamini_hochberg(pvals, alpha=0.05)
    assert rejected[0] and rejected[1]          # les deux petites sont retenues
    assert not rejected[2] and not rejected[4]  # les grandes non
    assert all(0.0 <= x <= 1.0 for x in q)


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([], 0.05) == ([], [])
