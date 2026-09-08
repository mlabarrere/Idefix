"""Prompts versionnés + schémas JSON pour la classification Mistral.

``PROMPT_VERSION`` est persisté (table ``channel_llm_scores``, clé de cache) pour
la provenance/repro/EIP : tout changement de prompt DOIT incrémenter cette version
(sinon le cache servirait d'anciennes réponses pour un nouveau prompt).

Mission-aware : le prompt système est paramétré par la mission (``gan`` mesure
l'empreinte informationnelle du *Charles de Gaulle* ; ``france_ukraine`` cible les
narratifs sur la France dans le conflit ukrainien). Les deux drapeaux
``is_gan_footprint`` / ``is_france_ukraine`` sont toujours demandés afin de pouvoir
évaluer une mission depuis l'autre corpus (contrôle croisé).
"""
from __future__ import annotations

# Incrémenter à CHAQUE modification d'un prompt ou d'un schéma ci-dessous.
PROMPT_VERSION = "v1"

# ── Classification par canal ────────────────────────────────────────────────
# Le LLM ne voit qu'un ÉCHANTILLON de messages (texte brut) + métadonnées légères.
# Sortie STRICTEMENT JSON conforme à CHANNEL_SCHEMA (json_mode + validation post-hoc).

CHANNEL_CLASSIFY_SYSTEM = (
    "Tu es un analyste OSINT spécialisé dans les manipulations de l'information "
    "(doctrine VIGINUM). On te donne un ÉCHANTILLON de messages d'une chaîne Telegram "
    "publique. Tu produis une classification HAUT-NIVEAU, factuelle et prudente.\n\n"
    "Périmètre :\n"
    "- GAN : empreinte informationnelle OBSERVABLE du Groupe Aéronaval français "
    "(porte-avions Charles de Gaulle, frégates d'escorte, Rafale Marine, Marine "
    "nationale, déploiements/exercices, incidents Strava/Zhigulevsk).\n"
    "- France-Ukraine : narratifs visant l'image/intégrité de la France dans le "
    "conflit ukrainien (soldats/cercueils français, financement de la guerre, "
    "mercenaires, positionnement international).\n\n"
    "Règles :\n"
    "- N'invente rien : si l'échantillon est insuffisant, baisse la confiance.\n"
    "- Pas d'attribution réelle à une personne/un État (tier T3 interdit).\n"
    "- 'actor_type' ∈ {press, osint, milblogger, state_aligned, activist, "
    "aggregator, other}.\n"
    "- 'themes' = 1 à 5 étiquettes thématiques courtes (FR), p.ex. "
    "'marine nationale', 'porte-avions', 'guerre Ukraine', 'OTAN'.\n"
    "- Réponds UNIQUEMENT par un objet JSON conforme au schéma, sans texte autour."
)

CHANNEL_SCHEMA = {
    "type": "object",
    "properties": {
        "is_gan_footprint": {"type": "boolean"},
        "is_france_ukraine": {"type": "boolean"},
        "actor_type": {
            "type": "string",
            "enum": [
                "press", "osint", "milblogger", "state_aligned",
                "activist", "aggregator", "other",
            ],
        },
        "themes": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string"},
    },
    "required": [
        "is_gan_footprint", "is_france_ukraine", "actor_type",
        "themes", "confidence", "rationale",
    ],
}


def channel_user_prompt(
    *, username: str, title: str, mission: str, samples: list[str]
) -> str:
    """Construit le message utilisateur : métadonnées + échantillon de messages."""
    joined = "\n---\n".join(s.strip() for s in samples if s and s.strip())
    if not joined:
        joined = "(aucun message texte exploitable dans l'échantillon)"
    return (
        f"Mission analytique prioritaire : {mission}\n"
        f"Chaîne : @{username or '?'} — {title or '(sans titre)'}\n"
        f"Nombre de messages échantillonnés : {len(samples)}\n\n"
        f"Échantillon de messages (texte brut) :\n{joined}\n\n"
        "Classe cette chaîne selon le schéma."
    )


# ── Étiquetage de communauté ────────────────────────────────────────────────
# Agrège les top-N canaux d'une communauté (déjà détectée par Leiden) + leurs
# classifications par-canal, et demande UN label thématique haut-niveau.

COMMUNITY_LABEL_SYSTEM = (
    "Tu es un analyste OSINT. On te donne les canaux représentatifs d'une "
    "communauté Telegram (détectée par graphe de forwards) avec leurs "
    "classifications. Tu produis UN label thématique court et discriminant pour "
    "cette communauté, et un niveau de confiance.\n"
    "- 'label' = groupe nominal court en français (max ~6 mots).\n"
    "- 'theme' = catégorie mère (p.ex. 'OSINT naval', 'milblogosphère russe', "
    "'presse défense FR', 'relais francophones').\n"
    "- N'invente pas d'acteur réel ; reste descriptif.\n"
    "- Réponds UNIQUEMENT par un objet JSON conforme au schéma."
)

COMMUNITY_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "theme": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string"},
    },
    "required": ["label", "theme", "confidence", "rationale"],
}


def community_user_prompt(*, mission: str, members: list[dict]) -> str:
    """``members`` = [{username, title, actor_type, themes}] des canaux top-N."""
    lines = []
    for m in members:
        themes = ", ".join(m.get("themes") or []) or "—"
        lines.append(
            f"- @{m.get('username') or '?'} ({m.get('title') or 'sans titre'}) "
            f"· acteur={m.get('actor_type') or '?'} · thèmes={themes}"
        )
    body = "\n".join(lines) or "(aucun membre exploitable)"
    return (
        f"Mission analytique : {mission}\n"
        f"Canaux représentatifs de la communauté ({len(members)}) :\n{body}\n\n"
        "Donne un label thématique pour cette communauté."
    )
