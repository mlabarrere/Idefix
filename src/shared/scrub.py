"""Scrubber canonique des secrets — point unique réutilisé par tout export.

Retire les secrets de tout objet AVANT écriture/push (défense en profondeur) :
- par-CLÉ : toute clé dont le nom (insensible à la casse) est dans ``SECRET_KEYS``
- par-VALEUR : toute chaîne contenant un secret résolu (numéro / session / api_hash,
  via ``secret_values()``), même noyé en sous-chaîne.

Extrait de ``scripts/export_static.py`` pour que le push Supabase
(``src/shared/snapshot_store.py``) scrube avec EXACTEMENT la même règle que le
bundle statique — le navigateur lira ces snapshots tels quels.
"""
from __future__ import annotations

from src.ingestor.session import secret_values

# Clés dont le NOM est secret (jamais exportées). Le numéro/la session sont une
# dépendance d'exécution, pas une donnée métier (docs/method/07-tiers-and-governance.md).
SECRET_KEYS = frozenset(
    {
        "phone", "session", "session_string", "session_name", "api_hash", "api_id",
        "tg_phone", "tg_session_string", "tg_api_id", "tg_api_hash",
        "telegram_phone_number", "telegram_session_string", "telegram_session_name",
        "telegram_api_id", "telegram_api_hash",
        # LLM (Mistral parallel track) — clé jamais exportée (par-clé + par-valeur).
        "mistral_api_key", "mistral_key",
    }
)


def scrub(obj):
    """Rédige récursivement secrets par-clé et par-valeur. Voir module docstring."""
    secrets = secret_values()

    def _clean(o):
        if isinstance(o, dict):
            return {
                k: ("[REDACTED]" if str(k).lower() in SECRET_KEYS else _clean(v))
                for k, v in o.items()
            }
        if isinstance(o, (list, tuple)):
            return [_clean(x) for x in o]
        if isinstance(o, str) and secrets:
            s = o
            for sec in secrets:
                if sec and sec in s:
                    s = s.replace(sec, "[REDACTED]")
            return s
        return o

    return _clean(obj)
