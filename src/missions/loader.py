"""Résolution de la mission active — point d'entrée unique des scripts CLI.

Chaque script du pipeline appelle ``resolve_mission(args.mission)`` : ``None`` ou
absent ⇒ ``DEFAULT_MISSION`` (russosphère) ⇒ comportement actuel. Centralise la
sémantique du drapeau ``--mission`` pour que tous les scripts se comportent
identiquement.
"""
from __future__ import annotations

import argparse

from src.missions import registry
from src.missions.spec import MissionDefinition


def resolve_mission(name: str | None = None) -> MissionDefinition:
    """Résout la mission par nom ; ``None`` ⇒ mission par défaut (russosphère)."""
    return registry.get(name or registry.DEFAULT_MISSION)


def add_mission_arg(parser: argparse.ArgumentParser) -> None:
    """Ajoute l'option ``--mission`` standard à un parseur de script.

    Défaut ``None`` ⇒ ``resolve_mission`` retombe sur ``DEFAULT_MISSION``.
    """
    parser.add_argument(
        "--mission",
        type=str,
        default=None,
        help=(
            "Mission analytique à exécuter (défaut : "
            f"{registry.DEFAULT_MISSION}). Disponibles : "
            f"{', '.join(registry.available())}."
        ),
    )
