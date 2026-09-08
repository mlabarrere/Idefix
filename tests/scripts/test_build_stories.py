"""Tests de ``scripts/build_stories.py`` — dérivation + résolution éditoriale.

Épingle le CONTRAT du sélecteur narratif (UX rév. 2, couche 2) : phases nommées
AVEC dates, channel_ids résolus, marquage honnête ``partial`` quand des handles
manquent au bundle. Fonctions pures — aucune base, aucun réseau.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_stories.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_stories", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()


_SNAPSHOT = {
    "stats": {"fr_side": 3, "ru_side": 10, "ru_targeting_france": 7,
              "media_traces_ru_to_fr": 3},
    "timeline": {
        "crossings": [
            # volontairement non triés — la dérivation doit trier par date
            {"first_ts": "2026-04-20T10:00:00+00:00", "velocity_hours": 0.0,
             "ru_user": "arktos", "fr_user": "iliade", "media_hash": "h2"},
            {"first_ts": "2025-12-14T16:00:00+00:00", "velocity_hours": 0.3,
             "ru_user": "kadosh", "fr_user": "subver", "media_hash": "h1"},
            {"first_ts": "2026-05-21T06:00:00+00:00", "velocity_hours": 2.5,
             "ru_user": "arktos", "fr_user": "iliade", "media_hash": "h3"},
        ]
    },
}

_UID = {"arktos": -100, "iliade": -200, "kadosh": -300}  # "subver" absent


def test_fr_date_deterministic():
    assert _mod._fr_date("2026-03-04T14:20:21+00:00") == "4 mars 2026"
    assert _mod._fr_date("2025-12-14T16:28:56+00:00") == "14 déc 2025"


def test_derive_three_phases_sorted_and_dated():
    story = _mod.derive_porosity_story(_SNAPSHOT, _UID)
    assert story["data_status"] == "derived"
    ids = [p["id"] for p in story["phases"]]
    assert ids == ["premier-croisement", "axe-installe", "etat-observe"]
    # phase 1 = croisement le plus ANCIEN malgré l'ordre d'entrée
    p1 = story["phases"][0]
    assert p1["date_label"] == "14 déc 2025"
    assert p1["evidence"][0]["from"] == "kadosh"
    # chaque phase porte un label de date et un chiffre clé (contrat StoryBar)
    for p in story["phases"]:
        assert p["date_label"] and p["headline_stat"]


def test_derive_axis_is_most_frequent_pair():
    story = _mod.derive_porosity_story(_SNAPSHOT, _UID)
    axe = story["phases"][1]
    assert "arktos" in axe["name"] and "iliade" in axe["name"]
    assert len(axe["evidence"]) == 2  # les 2 croisements de la paire dominante
    assert set(axe["channel_ids"]) == {-100, -200}


def test_derive_resolves_known_ids_keeps_all_usernames():
    story = _mod.derive_porosity_story(_SNAPSHOT, _UID)
    last = story["phases"][-1]
    # "subver" absent du bundle -> pas d'id, mais le handle reste listé
    assert set(last["channel_ids"]) == {-100, -200, -300}
    assert "subver" in last["usernames"]


def test_derive_empty_crossings_returns_none():
    assert _mod.derive_porosity_story({"timeline": {"crossings": []}}, {}) is None


def test_finalize_editorial_marks_partial_on_missing():
    story = {
        "id": "s", "data_status": "editorial",
        "phases": [{"id": "p", "usernames": ["known", "Ghost"]}],
    }
    out = _mod._finalize_editorial(story, {"known": -1})
    assert out["phases"][0]["channel_ids"] == [-1]
    assert out["phases"][0]["missing_usernames"] == ["Ghost"]
    assert out["data_status"] == "partial"


def test_finalize_editorial_no_missing_keeps_status():
    story = {
        "id": "s", "data_status": "editorial",
        "phases": [{"id": "p", "usernames": ["@Known"]}],  # @ + casse tolérés
    }
    out = _mod._finalize_editorial(story, {"known": -1})
    assert out["phases"][0]["channel_ids"] == [-1]
    assert out["data_status"] == "editorial"
