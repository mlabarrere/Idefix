"""Telegram account/session dependency — explicit, fail-fast, secret-safe.

LOAD-BEARING (docs/method/07-tiers-and-governance.md, scope-change-multi-mission §3) :
l'ingestion repose TOUJOURS sur le compte/numéro de l'utilisateur via une session
MTProto. Le numéro/la session sont une **dépendance d'exécution, pas une donnée
métier** : jamais hardcodés, jamais journalisés, **jamais exportés** dans le
bundle (cf. ``export_static`` scrub par-valeur, qui consomme ``secret_values()``).

Noms d'environnement canoniques ``TELEGRAM_*`` avec **alias rétro-compatibles**
vers les ``TG_*`` historiques (préférence au nouveau nom) :

    TELEGRAM_API_ID         (alias TG_API_ID)
    TELEGRAM_API_HASH       (alias TG_API_HASH)
    TELEGRAM_SESSION_STRING / TELEGRAM_SESSION_NAME  (alias TG_SESSION_STRING)
    TELEGRAM_PHONE_NUMBER   (alias TG_PHONE)

``session_preflight`` est appelé EN TÊTE de tout script touchant Telegram :
il transforme l'échec d'auth Hydrogram tardif et cryptique (en plein crawl) en
une **erreur amont explicite** avec remédiation. ``--dry-run`` ⇒
``require_live=False`` (aucune session ouverte).
"""
from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)

# clé interne -> noms d'env acceptés, dans l'ordre de préférence (nouveau d'abord).
_ALIASES: dict[str, tuple[str, ...]] = {
    "api_id": ("TELEGRAM_API_ID", "TG_API_ID"),
    "api_hash": ("TELEGRAM_API_HASH", "TG_API_HASH"),
    "session": ("TELEGRAM_SESSION_STRING", "TELEGRAM_SESSION_NAME", "TG_SESSION_STRING"),
    "phone": ("TELEGRAM_PHONE_NUMBER", "TG_PHONE"),
}

# Clés dont la VALEUR est secrète (à rédiger des exports, jamais à journaliser).
_SECRET_KEYS = frozenset({"api_hash", "session", "phone"})


class SessionError(RuntimeError):
    """Configuration de session Telegram absente ou invalide (erreur amont claire)."""


def resolve_session_env() -> dict[str, str | None]:
    """Résout les secrets de session depuis l'environnement (alias rétro-compat).

    Renvoie ``{api_id, api_hash, session, phone}`` ; chaque valeur = la première
    variable d'environnement non vide de la liste d'alias, sinon ``None``.
    """
    out: dict[str, str | None] = {}
    for key, names in _ALIASES.items():
        value: str | None = None
        for name in names:
            v = os.environ.get(name)
            if v:
                value = v
                break
        out[key] = value
    return out


def llm_secret_values() -> set[str]:
    """VALEUR secrète de la clé LLM (Mistral) — pour le scrub par-valeur d'export.

    Distincte de la session Telegram (scope/preflight différents) : on ne pollue
    pas ``_ALIASES``/``_SECRET_KEYS``. La clé n'est résolue que pour le scrub ;
    NE JAMAIS la journaliser ni la stocker.
    """
    key = os.environ.get("MISTRAL_API_KEY")
    return {key} if key else set()


def secret_values() -> set[str]:
    """VALEURS secrètes résolues (api_hash, session, phone, clé LLM) — scrub d'export.

    Défense en profondeur : ``export_static`` rédige par-CLÉ *et* par-VALEUR toute
    chaîne égale à un secret connu. NE JAMAIS journaliser ce retour.
    """
    env = resolve_session_env()
    out = {v for k, v in env.items() if v and k in _SECRET_KEYS}
    out |= llm_secret_values()  # MISTRAL_API_KEY rédigé par-VALEUR dans les exports
    return out


async def session_preflight(*, require_live: bool = False) -> None:
    """Vérifie la session Telegram AVANT tout backfill. Lève ``SessionError`` sinon.

    - credentials manquants -> erreur explicite (où les obtenir).
    - ni session string ni numéro -> erreur explicite (comment s'authentifier).
    - ``require_live=True`` : un appel léger (``get_chat("me")``) confirme que la
      session est vivante ; une session expirée -> ``SessionError`` (ré-auth).

    Ne journalise JAMAIS le numéro ni la session (seulement des booléens de
    présence).
    """
    env = resolve_session_env()
    if not env["api_id"] or not env["api_hash"]:
        raise SessionError(
            "Identifiants API Telegram manquants. Définir TELEGRAM_API_ID et "
            "TELEGRAM_API_HASH (alias TG_API_ID / TG_API_HASH) — à obtenir sur "
            "https://my.telegram.org. Le collecteur utilise VOTRE compte/session."
        )
    if not env["session"] and not env["phone"]:
        raise SessionError(
            "Aucune session Telegram configurée. Définir TELEGRAM_SESSION_STRING "
            "(alias TG_SESSION_STRING) ou TELEGRAM_PHONE_NUMBER pour la première "
            "authentification — lancer : streamlit run scripts/session_web.py"
        )
    log.info(
        "session_preflight_ok",
        has_session=bool(env["session"]),
        has_phone=bool(env["phone"]),
        require_live=require_live,
    )
    if not require_live:
        return

    # Vérification vivante : import paresseux (Hydrogram requis seulement ici).
    from hydrogram.errors import AuthKeyUnregistered, UserDeactivated

    from src.ingestor.client import TelegramClient

    client = TelegramClient.from_env()
    try:
        async with client:
            await client.get_channel_info("me")  # le plus léger : résout self
    except (AuthKeyUnregistered, UserDeactivated) as e:
        raise SessionError(
            "Session Telegram expirée/invalide — ré-authentifier via "
            "scripts/session_web.py (rotation de session-string)."
        ) from e
    log.info("session_preflight_live_ok")
