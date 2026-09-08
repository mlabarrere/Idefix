"""Registre des missions — découverte par convention, sélection par nom.

Une mission vit dans ``src/missions/<name>/__init__.py`` et y exporte une
constante module ``MISSION: MissionDefinition``. Le registre découvre ces
packages par convention (aucun enregistrement explicite à maintenir → « ajouter
une mission sans fork de code »).

``DEFAULT_MISSION = "russosphere"`` : le pipeline sans ``--mission`` reproduit le
comportement actuel (bundle byte-identique — golden test).
"""
from __future__ import annotations

import importlib
import pkgutil

from src.missions.spec import MissionDefinition

DEFAULT_MISSION = "russosphere"

# Sous-modules de package qui ne sont pas des missions.
_NON_MISSION = frozenset({"spec", "registry", "loader"})


def _load(name: str) -> MissionDefinition:
    """Importe ``src.missions.<name>`` et renvoie son ``MISSION``."""
    module = importlib.import_module(f"src.missions.{name}")
    mission = getattr(module, "MISSION", None)
    if not isinstance(mission, MissionDefinition):
        raise ValueError(
            f"mission '{name}': src/missions/{name}/__init__.py doit exporter "
            f"une constante MISSION: MissionDefinition"
        )
    return mission


def available() -> list[str]:
    """Liste les missions découvertes (packages ``src/missions/<name>/``), triées.

    Inclut les missions planifiées (``implemented=False``) afin qu'elles
    apparaissent au switcher du frontend.
    """
    import src.missions as pkg

    names: list[str] = []
    for info in pkgutil.iter_modules(pkg.__path__):
        if not info.ispkg or info.name in _NON_MISSION:
            continue
        names.append(info.name)
    return sorted(names)


def get(name: str) -> MissionDefinition:
    """Renvoie la ``MissionDefinition`` nommée.

    Lève ``KeyError`` si la mission est inconnue (avec la liste disponible), et
    ``ValueError`` si elle est planifiée mais non implémentée (sélection refusée).
    """
    try:
        mission = _load(name)
    except ModuleNotFoundError:
        raise KeyError(
            f"mission inconnue '{name}'. Disponibles : {', '.join(available())}"
        ) from None
    if not mission.implemented:
        raise ValueError(
            f"mission '{name}' planifiée mais non implémentée (status=planned)"
        )
    return mission
