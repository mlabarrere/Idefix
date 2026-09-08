"""
evidence.py -- Construction « preuve-d'abord » d'un dossier d'épisode, À LA VOLÉE
depuis PostgreSQL. Logique extraite de scripts/build_evidence.py, rendue
consommable par l'exporteur OFFLINE (scripts/export_static.py, qui écrit
episodes/<id>.json dans le bundle statique data/). L'API FastAPI est LEGACY.

Lecture seule PostgreSQL. AUCUN appel Telegram. Langue : français.

Fonctions publiques :
    async def list_episodes(conn) -> list[dict]
    async def build_evidence(conn, episode_id: str) -> dict

`build_evidence` renvoie EXACTEMENT le schéma épisode consommé par la webapp :
    { "episode": {...}, "messages_origine": [...], "canaux_relais": [...],
      "reseau": {"noeuds": [...], "aretes": [...]}, "pourquoi": [...],
      "limite_couverture": "...", "que_faire": "..." }

Les valeurs de scores (familles b/c/d) sont réutilisées depuis le dossier de
scoring déjà calculé (webapp/public/data/russosphere/dugin_cluster.json) pour cohérence —
elles définissent aussi le cluster de canaux (critère de sélection de l'épisode).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOSSIERS = ROOT / "webapp" / "public" / "data" / "russosphere"

LIMITE_COUVERTURE = (
    "Seul Telegram est observé. Une campagne passant surtout par d'autres "
    "plateformes, sans étape Telegram, n'apparaît pas ici."
)
QUE_FAIRE = (
    "Un analyste relit le dossier et confirme la cohérence des signaux. "
    "Le dossier est ensuite transmis à VIGINUM et à l'Arcom, seules "
    "habilitées à décider des suites."
)


# ---------------------------------------------------------------------------
# Registre d'épisodes
# ---------------------------------------------------------------------------
# Un épisode = un critère de sélection de canaux + métadonnées éditoriales +
# la référence vers le dossier de scoring qui fournit les valeurs b/c/d et la
# définition canonique du cluster. Un seul épisode réel pour l'instant ; la
# structure permet d'en ajouter sans toucher au reste du code.
EPISODES_REGISTRY: dict[str, dict[str, dict]] = {
    "russosphere": {
        "dugin_cluster": {
            "scoring_file": "dugin_cluster.json",
            "origin_channel_id": -1001453453123,
            "origin_username": "Dugin_Aleksandr",
            "origin_title": "Alexander Dugin",
            "titre": (
                "Réseau eurasianiste coordonné (Douguine / Geopolitika) — "
                "amplification multilingue"
            ),
            "resume": (
                "Un réseau de canaux Telegram republie en masse, et en une "
                "quinzaine de langues, le contenu d'Alexandre Douguine — idéologue "
                "eurasianiste russe proche du Kremlin — et de ses relais "
                "(Geopolitika, AGDchan, Multipolar). Ce qui le rend suspect n'est "
                "pas le contenu pris isolément, mais le dispositif : une source "
                "unique amorce, des dizaines de canaux la rediffusent de façon "
                "coordonnée et répétée, et ces mêmes canaux récidivent d'un sujet "
                "à l'autre."
            ),
            "pourquoi_phrases": {
                "b": (
                    "Alexandre Douguine est la source qui amorce le contenu ; "
                    "ses messages rayonnent vers tout le réseau, qui les republie."
                ),
                "c": (
                    "Plusieurs canaux republient les mêmes sources de façon "
                    "répétée et quasi simultanée, en une quinzaine de langues — "
                    "bien au-delà du hasard."
                ),
                "d": (
                    "Ces mêmes canaux relais réapparaissent d'un sujet à l'autre : "
                    "c'est une infrastructure de diffusion permanente, pas un "
                    "emballement ponctuel."
                ),
            },
        }
    }
}


def load_episodes(mission: str = "russosphere") -> dict[str, dict]:
    """Fusionne épisodes hardcodés + découverts depuis episodes_discovered.json.

    Returns:
        dict[episode_id, episode_dict] — hardcoded + discovered merged.
    """
    hardcoded = EPISODES_REGISTRY.get(mission, {})
    discovered_path = DOSSIERS.parent / mission / "episodes_discovered.json"
    if discovered_path.exists():
        try:
            payload = json.loads(discovered_path.read_text(encoding="utf-8"))
            discovered = {ep["id"]: ep for ep in payload.get("episodes", [])}
            return {**hardcoded, **discovered}
        except (OSError, json.JSONDecodeError):
            pass
    return hardcoded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_scoring(episode: dict) -> dict:
    """Charge le dossier de scoring (scores b/c/d + définition du cluster)."""
    path = DOSSIERS / episode["scoring_file"]
    return json.loads(path.read_text(encoding="utf-8"))


def _cluster_from_scoring(scoring: dict) -> tuple[list[str], dict[str, str]]:
    """Liste des handles du cluster + map handle -> archétype."""
    handles: list[str] = []
    arch: dict[str, str] = {}
    for ch in scoring["channels_detail"]:
        h = ch["id"].lstrip("@")
        handles.append(h)
        arch[h] = ch.get("arch", "source")
    return handles, arch


def _tg_link(username: str, message_id: int | None = None) -> str:
    if message_id is not None:
        return f"https://t.me/{username}/{message_id}"
    return f"https://t.me/{username}"


def _clip(text: str | None, n: int = 220) -> str:
    if not text:
        return ""
    t = " ".join(text.split())  # normalise retours-ligne / espaces
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
async def list_episodes(conn, mission: str = "russosphere") -> list[dict]:
    """Liste résumée des épisodes calculée à la volée.

    Renvoie : [{id, titre, resume, nb_canaux, scores_resume}]
    où scores_resume = {b, c, d, attr} (valeurs réelles du scoring).
    """
    out: list[dict] = []
    episodes = load_episodes(mission)
    for episode_id, ep in episodes.items():
        # ponytail: discovered episodes have no scoring_file -> skip scoring load
        if "scoring_file" not in ep:
            out.append({
                "id": episode_id,
                "titre": ep.get("label", episode_id),
                "resume": ep.get("label", ""),
                "nb_canaux": ep.get("n_channels", 0),
                "scores_resume": None,
            })
            continue

        scoring = _load_scoring(ep)
        cluster, _ = _cluster_from_scoring(scoring)
        scores = scoring.get("scores", {})
        out.append(
            {
                "id": episode_id,
                "titre": ep["titre"],
                "resume": ep["resume"],
                "nb_canaux": scoring.get("channels", len(cluster)),
                "scores_resume": {
                    "b": scores.get("b", {}).get("v"),
                    "c": scores.get("c", {}).get("v"),
                    "d": scores.get("d", {}).get("v"),
                    "attr": scoring.get("attr"),
                },
            }
        )
    return out


async def build_evidence(conn, episode_id: str, mission: str = "russosphere") -> dict:
    """Construit le dossier « preuve-d'abord » d'un épisode depuis PostgreSQL.

    Lève KeyError si `episode_id` est inconnu (l'API la traduit en 404).
    """
    episodes = load_episodes(mission)
    if episode_id not in episodes:
        raise KeyError(episode_id)

    ep = episodes[episode_id]
    scoring = _load_scoring(ep)
    scores = scoring["scores"]
    cluster, arch = _cluster_from_scoring(scoring)

    origin_id = ep["origin_channel_id"]
    origin_user = ep["origin_username"]

    # --- mapping handle <-> métadonnées canal (titre, fr_score) ------------
    rows = await conn.fetch(
        "SELECT channel_id, username, title, (extra->>'fr_score')::float AS fr "
        "FROM channels WHERE username = ANY($1)",
        cluster,
    )
    meta: dict[str, dict] = {}
    for r in rows:
        meta[r["username"]] = {
            "channel_id": r["channel_id"],
            "title": r["title"] or r["username"],
            "fr": r["fr"],
        }

    # --- fenêtre temporelle observée de l'épisode -------------------------
    tf = await conn.fetchrow(
        "SELECT MIN(timestamp) mn, MAX(timestamp) mx FROM messages "
        "WHERE forward_from_channel_id = $1 OR channel_id = $1",
        origin_id,
    )
    if tf and tf["mn"] and tf["mx"]:
        fenetre = f"{tf['mn'].date().isoformat()} → {tf['mx'].date().isoformat()}"
    else:
        fenetre = ""

    # --- messages d'origine : messages-source les plus republiés ----------
    origin_counts = await conn.fetch(
        """
        SELECT m.forward_from_message_id AS mid, COUNT(*) AS reposts
        FROM messages m
        JOIN channels c ON c.channel_id = m.channel_id
        WHERE m.forward_from_channel_id = $1
          AND c.username = ANY($2)
          AND m.forward_from_message_id IS NOT NULL
        GROUP BY m.forward_from_message_id
        ORDER BY reposts DESC
        LIMIT 12
        """,
        origin_id,
        cluster,
    )

    messages_origine: list[dict] = []
    for row in origin_counts:
        mid = row["mid"]
        reposts = row["reposts"]
        # texte du message original chez la source
        orig = await conn.fetchrow(
            "SELECT timestamp, text FROM messages "
            "WHERE channel_id = $1 AND message_id = $2",
            origin_id,
            mid,
        )
        text = orig["text"] if orig else None
        date = orig["timestamp"] if orig else None
        if not text:
            # repli : texte d'une copie republiée (contenu identique republié)
            copy = await conn.fetchrow(
                "SELECT timestamp, text FROM messages "
                "WHERE forward_from_channel_id = $1 AND forward_from_message_id = $2 "
                "AND text IS NOT NULL AND length(text) > 20 "
                "ORDER BY timestamp ASC LIMIT 1",
                origin_id,
                mid,
            )
            if copy:
                text = copy["text"]
                if date is None:
                    date = copy["timestamp"]
        if not text:
            continue
        messages_origine.append(
            {
                "canal": f"@{origin_user}",
                "titre": meta.get(origin_user, {}).get(
                    "title", ep["origin_title"]
                ),
                "texte": _clip(text, 220),
                "lien": _tg_link(origin_user, mid),
                "date": date.isoformat() if date else None,
                "reposts": reposts,
            }
        )
        if len(messages_origine) >= 5:
            break

    # --- canaux relais : nb de messages-source du cluster republiés par canal
    relay_rows = await conn.fetch(
        """
        SELECT c.username AS relay, COUNT(*) AS reposts
        FROM messages m
        JOIN channels c ON c.channel_id = m.channel_id
        JOIN channels src ON src.channel_id = m.forward_from_channel_id
        WHERE c.username = ANY($1)
          AND src.username = ANY($1)
          AND c.username <> src.username
        GROUP BY c.username
        ORDER BY reposts DESC
        """,
        cluster,
    )
    canaux_relais: list[dict] = []
    for r in relay_rows:
        u = r["relay"]
        m = meta.get(u, {})
        canaux_relais.append(
            {
                "canal": f"@{u}",
                "titre": m.get("title", u),
                "reposts": r["reposts"],
                "fr_score": m.get("fr"),
                "lien": _tg_link(u),
            }
        )

    # --- réseau : top ~8 nœuds / top ~12 arêtes par poids -----------------
    edge_rows = await conn.fetch(
        """
        SELECT src.username AS s, c.username AS t, COUNT(*) AS w
        FROM messages m
        JOIN channels c ON c.channel_id = m.channel_id
        JOIN channels src ON src.channel_id = m.forward_from_channel_id
        WHERE c.username = ANY($1)
          AND src.username = ANY($1)
          AND src.username <> c.username
        GROUP BY s, t
        ORDER BY w DESC
        LIMIT 12
        """,
        cluster,
    )
    aretes = [
        {"source": f"@{r['s']}", "target": f"@{r['t']}", "poids": r["w"]}
        for r in edge_rows
    ]
    node_handles: list[str] = []
    for r in edge_rows:
        for h in (r["s"], r["t"]):
            if h not in node_handles:
                node_handles.append(h)
    node_handles = node_handles[:8]
    noeuds = [
        {"id": f"@{h}", "arch": arch.get(h, "source")} for h in node_handles
    ]

    # --- pourquoi : réutilise les scores réels déjà calculés --------------
    phrases = ep["pourquoi_phrases"]
    pourquoi = [
        {
            "famille": "Rôle en cascade",
            "valeur": scores["b"]["v"],
            "phrase": phrases["b"],
        },
        {
            "famille": "Coordination",
            "valeur": scores["c"]["v"],
            "phrase": phrases["c"],
        },
        {
            "famille": "Récidivisme inter-épisodes",
            "valeur": scores["d"]["v"],
            "phrase": phrases["d"],
        },
    ]

    episode = {
        "id": scoring.get("id", episode_id),
        "titre": ep["titre"],
        "resume": ep["resume"],
        "fenetre": fenetre,
        "nb_canaux": scoring.get("channels", len(cluster)),
    }

    return {
        "episode": episode,
        "messages_origine": messages_origine,
        "canaux_relais": canaux_relais,
        "reseau": {"noeuds": noeuds, "aretes": aretes},
        "pourquoi": pourquoi,
        "limite_couverture": LIMITE_COUVERTURE,
        "que_faire": QUE_FAIRE,
    }
