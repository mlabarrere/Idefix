"""Construit ``stories.json`` — le bundle « histoires » du sélecteur narratif.

> UX spec rév. 2 (2026-06-10), couche 2 : un dropdown d'histoires ; chaque
> histoire = des PHASES NOMMÉES AVEC DATES (pas d'animation) ; sélectionner une
> phase filtre la galaxie sur les canaux pertinents. Les histoires sont
> DÉCOUVERTES DANS LES DONNÉES puis ÉDITORIALISÉES — jamais construites à la
> volée par l'utilisateur.

Deux sources, fusionnées :

1. **Dérivée des données** (mission russosphère) : l'histoire de porosité
   russo-sphère → extrême droite FR est reconstruite depuis
   ``porosity_snapshot.json`` (croisements média RU→FR datés, vélocités).
   Déterministe : mêmes données => mêmes phases.
2. **Éditoriale** (``src/missions/<mission>/stories.py`` exportant
   ``EDITORIAL_STORIES``) : épisodes documentés hors-base (ex. fuite Strava du
   GAN) ; les handles sont résolus contre ``channels_index.json`` du bundle ;
   les canaux absents restent affichés mais l'histoire est marquée
   ``data_status: "partial"`` (honnêteté : on ne prétend pas avoir les données).

OFFLINE PUR : lit et écrit le bundle ``webapp/public/data/<mission>/``.
Aucune base, AUCUN appel Telegram. Idempotent.

Usage :
    python scripts/build_stories.py [--mission gan] [--out DIR]
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.missions.loader import add_mission_arg  # noqa: E402
from src.missions.registry import DEFAULT_MISSION  # noqa: E402

_WEBAPP_DATA = _REPO / "webapp" / "public" / "data"

# Mois abrégés FR — formatage déterministe sans dépendre de la locale système.
_MOIS = ["jan", "fév", "mars", "avr", "mai", "juin",
         "juil", "août", "sept", "oct", "nov", "déc"]


def _fr_date(iso_ts: str) -> str:
    """'2026-03-04T14:20:21+00:00' -> '4 mars 2026' (label lisible des phases)."""
    d = datetime.fromisoformat(iso_ts)
    return f"{d.day} {_MOIS[d.month - 1]} {d.year}"


def _username_map(channels_index: dict | None) -> dict[str, int]:
    """username (lowercase) -> channel_id, depuis channels_index.json."""
    out: dict[str, int] = {}
    for c in (channels_index or {}).get("channels", []):
        u = (c.get("username") or "").lstrip("@").lower()
        if u:
            out[u] = c["channel_id"]
    return out


def _resolve(usernames: list[str], uid: dict[str, int]) -> tuple[list[int], list[str]]:
    """Résout des handles en channel_ids ; renvoie (ids_trouvés, handles_manquants)."""
    ids: list[int] = []
    missing: list[str] = []
    for u in usernames:
        key = u.lstrip("@").lower()
        if key in uid:
            ids.append(uid[key])
        else:
            missing.append(u)
    return ids, missing


# --------------------------------------------------------------------------- #
# Histoire DÉRIVÉE — porosité russo-sphère -> extrême droite FR.
# Algorithme délibérément simple et auditable (3 phases) :
#   1. « Premier croisement »   = le croisement RU->FR le plus ancien.
#   2. « L'axe s'installe »     = la paire (ru_user, fr_user) la plus fréquente.
#   3. « Dernier état observé » = le croisement le plus récent + stats globales.
# --------------------------------------------------------------------------- #

def derive_porosity_story(snapshot: dict, uid: dict[str, int]) -> dict | None:
    crossings = sorted(
        (snapshot.get("timeline") or {}).get("crossings") or [],
        key=lambda c: c["first_ts"],
    )
    if not crossings:
        return None
    stats = snapshot.get("stats") or {}

    def phase_channels(cs: list[dict]) -> tuple[list[int], list[str]]:
        users = sorted({u for c in cs for u in (c.get("ru_user"), c.get("fr_user")) if u})
        ids, missing = _resolve(users, uid)
        return ids, users

    first = crossings[0]
    pair_counts = Counter((c["ru_user"], c["fr_user"]) for c in crossings)
    (axis_ru, axis_fr), axis_n = pair_counts.most_common(1)[0]
    axis_cs = [c for c in crossings if (c["ru_user"], c["fr_user"]) == (axis_ru, axis_fr)]
    last = crossings[-1]

    phases = []
    ids, users = phase_channels([first])
    phases.append({
        "id": "premier-croisement",
        "name": "Premier croisement",
        "date_label": _fr_date(first["first_ts"]),
        "date_range": [first["first_ts"], first["first_ts"]],
        "headline_stat": f"reprise en {first['velocity_hours']} h",
        "narrative": (
            f"Premier croisement média observé : un contenu publié côté russo-sphère "
            f"(@{first['ru_user']}) réapparaît côté extrême droite FR "
            f"(@{first['fr_user']}) {first['velocity_hours']} h plus tard. "
            f"Trace média (hash identique), pas un repost déclaré."
        ),
        "channel_ids": ids,
        "usernames": users,
        "evidence": [{"kind": "media_trace", "media_hash": first.get("media_hash"),
                      "from": first["ru_user"], "to": first["fr_user"],
                      "velocity_hours": first["velocity_hours"]}],
    })
    if axis_n >= 2:
        ids, users = phase_channels(axis_cs)
        phases.append({
            "id": "axe-installe",
            "name": f"L'axe @{axis_ru} → @{axis_fr} s'installe",
            "date_label": f"{_fr_date(axis_cs[0]['first_ts'])} → {_fr_date(axis_cs[-1]['first_ts'])}",
            "date_range": [axis_cs[0]["first_ts"], axis_cs[-1]["first_ts"]],
            "headline_stat": f"{axis_n} reprises, jusqu'à {min(c['velocity_hours'] for c in axis_cs)} h",
            "narrative": (
                f"La même paire revient {axis_n} fois : @{axis_ru} publie, "
                f"@{axis_fr} reprend. La récurrence — pas un croisement isolé — "
                f"est le signal de porosité (T2 : récurrence comportementale)."
            ),
            "channel_ids": ids,
            "usernames": users,
            "evidence": [{"kind": "media_trace", "media_hash": c.get("media_hash"),
                          "from": c["ru_user"], "to": c["fr_user"],
                          "velocity_hours": c["velocity_hours"]} for c in axis_cs],
        })
    ids, users = phase_channels(crossings)
    phases.append({
        "id": "etat-observe",
        "name": "Dernier état observé",
        "date_label": _fr_date(last["first_ts"]),
        "date_range": [first["first_ts"], last["first_ts"]],
        "headline_stat": (
            f"{stats.get('media_traces_ru_to_fr', len(crossings))} croisements RU→FR · "
            f"{stats.get('ru_targeting_france', '—')} canaux RU ciblant la France"
        ),
        "narrative": (
            "L'ensemble des croisements observés, replacé dans le périmètre : "
            f"{stats.get('ru_side', '—')} canaux côté russo-sphère, "
            f"{stats.get('fr_side', '—')} côté FR. La porosité est réelle mais "
            "SPARSE — quelques traces nommées et datées, jamais un volume gonflé."
        ),
        "channel_ids": ids,
        "usernames": users,
        "evidence": [{"kind": "media_trace", "media_hash": c.get("media_hash"),
                      "from": c["ru_user"], "to": c["fr_user"],
                      "velocity_hours": c["velocity_hours"]} for c in crossings],
    })

    return {
        "id": "porosite-russosphere-fr",
        "title": "Influences russes → extrême droite FR",
        "subtitle": "La porosité observée, trace par trace",
        "data_status": "derived",
        "tier": "T2",
        "phases": phases,
    }


# --------------------------------------------------------------------------- #
# Fusion + écriture
# --------------------------------------------------------------------------- #

def _load_editorial(mission: str) -> list[dict]:
    """Histoires éditoriales de la mission (src/missions/<mission>/stories.py)."""
    try:
        mod = importlib.import_module(f"src.missions.{mission}.stories")
    except ModuleNotFoundError:
        return []
    return [json.loads(json.dumps(s)) for s in getattr(mod, "EDITORIAL_STORIES", [])]


def _finalize_editorial(story: dict, uid: dict[str, int]) -> dict:
    """Résout les handles d'une histoire éditoriale ; marque partial si manques."""
    any_missing = False
    for ph in story.get("phases", []):
        ids, missing = _resolve(ph.get("usernames", []), uid)
        ph["channel_ids"] = ids
        if missing:
            any_missing = True
            ph["missing_usernames"] = missing
    if any_missing and story.get("data_status") != "partial":
        story["data_status"] = "partial"
    return story


def build_stories(mission: str, out_dir: Path) -> dict:
    idx_path = out_dir / "channels_index.json"
    channels_index = (
        json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else None
    )
    uid = _username_map(channels_index)

    stories: list[dict] = []
    if mission == "russosphere":
        snap_path = out_dir / "porosity_snapshot.json"
        if snap_path.exists():
            snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
            derived = derive_porosity_story(snapshot, uid)
            if derived:
                stories.append(derived)
    for s in _load_editorial(mission):
        stories.append(_finalize_editorial(s, uid))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": mission,
        "stories": stories,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Construit stories.json (sélecteur narratif).")
    ap.add_argument("--out", default=None,
                    help="Dossier du bundle (défaut: webapp/public/data/<mission>/)")
    add_mission_arg(ap)
    args = ap.parse_args()
    mission = args.mission or DEFAULT_MISSION
    out_dir = Path(args.out) if args.out else _WEBAPP_DATA / mission
    if not out_dir.is_absolute():
        out_dir = _REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    obj = build_stories(mission, out_dir)
    path = out_dir / "stories.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit : {path} · {len(obj['stories'])} histoire(s)")
    for s in obj["stories"]:
        print(f"  [{s['data_status']:>8}] {s['id']} — {len(s['phases'])} phases")


if __name__ == "__main__":
    main()
