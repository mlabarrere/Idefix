"""Missions d'Idéfix — plateforme générique « un moteur Telegram, N missions ».

Chaque sous-package ``src/missions/<name>/`` exporte ``MISSION: MissionDefinition``
(cf. ``spec``). Le moteur (pipeline, scoring, export) est theme-agnostique ; une
mission est une CONFIGURATION (six profils + scorer de pertinence), jamais une
fourche de code. Voir ``architecture-multi-mission-2026-06-09.md``.

N.B. : ce ``__init__`` reste volontairement minimal (pas d'import de sous-modules)
pour que ``registry.available()`` puisse énumérer les packages sans coût ni cycle.
"""
