"""Tests de l'abstraction mission : registre, résolution, profils (pur, SANS DB)."""
import pytest

from src.missions import registry
from src.missions.loader import resolve_mission
from src.missions.spec import MissionDefinition


def test_available_lists_missions():
    avail = registry.available()
    assert "russosphere" in avail
    assert "gan" in avail
    assert "france_ukraine" in avail


def test_france_ukraine_mission_resolves():
    m = registry.get("france_ukraine")
    assert m.name == "france_ukraine"
    assert m.implemented is True
    assert m.scoring.relevance_signal == "france_ukraine_targeting"
    assert m.source_universe.snowball_anchor_signal == "france_ukraine_targeting"
    assert m.export.out_subdir == "france_ukraine"
    assert m.relevance_scorer is not None
    # largeur-led comme la russosphère (la largeur prime sur le volume).
    assert m.targeting.breadth_weight > m.targeting.depth_weight


def test_default_mission_is_russosphere():
    m = resolve_mission()  # None -> défaut
    assert m.name == "russosphere"
    assert isinstance(m, MissionDefinition)
    # Profils de la mission par défaut = constantes historiques (ordonné a..e).
    assert list(m.scoring.family_weights.keys())[:5] == ["a", "b", "c", "d", "e"]
    assert m.scoring.relevance_signal == "france_targeting"
    assert m.scoring.credibility_prior_enabled is True
    assert m.export.flat_default is True
    assert m.relevance_scorer is not None


def test_gan_mission_resolves_and_is_telegram_scoped():
    m = registry.get("gan")
    assert m.name == "gan"
    assert m.implemented is True
    # R1 : prior neutre pour le GAN.
    assert m.scoring.credibility_prior_enabled is False
    assert m.scoring.relevance_signal == "gan_targeting"
    # Tous les scores propres au GAN sont nommés telegram_*.
    extra = m.scoring.extra_family_scorers
    assert extra and all(k.startswith("telegram_") for k in extra)
    assert "telegram_disclosure_precision" in extra
    # Empreinte ≠ porosité.
    assert m.dashboard.porosity_enabled is False
    assert m.relevance_scorer is not None


def test_unknown_mission_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get("does_not_exist")


def test_active_families_are_declared_in_weights():
    # Invariant consommé par le combineur : toute famille active doit avoir un
    # poids déclaré (le combineur renormalise par les poids présents — la somme
    # n'a PAS à valoir 1.0 ; russosphère somme à 1.15 par conception historique).
    for name in ("russosphere", "gan", "france_ukraine"):
        m = registry.get(name)
        weight_keys = set(m.scoring.family_weights)
        assert m.scoring.active_families <= weight_keys, (
            f"{name}: familles actives sans poids "
            f"{m.scoring.active_families - weight_keys}"
        )
