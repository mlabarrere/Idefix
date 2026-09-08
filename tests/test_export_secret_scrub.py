"""Scrub des secrets à l'export — le bundle ne contient JAMAIS numéro/session.

Critère d'acceptation (CLAUDE.md bandeau 2026-06-09) : le numéro/la session sont
une dépendance d'EXÉCUTION, jamais une donnée métier ; ils ne doivent apparaître
dans aucun fichier exporté. On charge scripts/export_static.py via importlib et on
exerce ``_write_json`` / ``_write_twin`` (point d'écriture unique scrubé).
"""
import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_static.py"

_SECRET_ENV = (
    "TELEGRAM_SESSION_STRING", "TELEGRAM_PHONE_NUMBER", "TELEGRAM_API_HASH",
    "TELEGRAM_API_ID", "TELEGRAM_SESSION_NAME",
    "TG_SESSION_STRING", "TG_PHONE", "TG_API_HASH", "TG_API_ID",
    "MISTRAL_API_KEY",
)


def _load():
    spec = importlib.util.spec_from_file_location("export_static_scrub", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_scrub_by_key_and_by_value(monkeypatch, tmp_path):
    for k in _SECRET_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TELEGRAM_SESSION_STRING", "SECRET_SESSION_XYZ")
    monkeypatch.setenv("TELEGRAM_PHONE_NUMBER", "+33611223344")
    m = _load()
    obj = {
        "phone": "+33611223344",                 # clé secrète
        "tg_session_string": "anything",          # clé secrète
        "note": "leak +33611223344 here",         # contient une valeur secrète
        "exact": "SECRET_SESSION_XYZ",            # valeur secrète exacte
        "channels": [{"username": "@ok", "session": "x"}],  # clé secrète imbriquée
        "safe": "hello world",
    }
    p = tmp_path / "out.json"
    m._write_json(p, obj)
    text = p.read_text(encoding="utf-8")
    assert "SECRET_SESSION_XYZ" not in text
    assert "+33611223344" not in text             # rédigé même dans "note"
    assert "[REDACTED]" in text
    assert "hello world" in text                  # contenu anodin préservé
    assert "@ok" in text

    pj = tmp_path / "out.js"
    m._write_twin(pj, "BUNDLE", obj)
    tj = pj.read_text(encoding="utf-8")
    assert "SECRET_SESSION_XYZ" not in tj
    assert "+33611223344" not in tj


def test_scrub_mistral_api_key_by_key_and_value(monkeypatch, tmp_path):
    """La clé Mistral (piste parallèle LLM) ne fuit jamais — par-clé ET par-valeur."""
    for k in _SECRET_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-MISTRAL-SECRET-123")
    m = _load()
    obj = {
        "mistral_api_key": "whatever",                  # clé secrète (par-nom)
        "rationale": "réponse du juge sk-MISTRAL-SECRET-123 ici",  # valeur noyée
        "exact": "sk-MISTRAL-SECRET-123",               # valeur secrète exacte
        "safe": "analyse normale",
    }
    p = tmp_path / "out.json"
    m._write_json(p, obj)
    text = p.read_text(encoding="utf-8")
    assert "sk-MISTRAL-SECRET-123" not in text          # rédigé partout (par-valeur)
    assert "[REDACTED]" in text
    assert "analyse normale" in text                    # contenu anodin préservé


def test_scrub_noop_when_no_secret_keys_or_values(monkeypatch, tmp_path):
    for k in _SECRET_ENV:
        monkeypatch.delenv(k, raising=False)
    m = _load()
    obj = {"username": "@ok", "title": "Hello", "suspicion": {"v": 0.5}}
    p = tmp_path / "out.json"
    m._write_json(p, obj)
    assert json.loads(p.read_text(encoding="utf-8")) == obj


def test_export_metadata_defaults_to_internal_review(monkeypatch):
    for k in (
        "IDEFIX_CLASSIFICATION_MARKING",
        "IDEFIX_HANDLING_INSTRUCTIONS",
        "IDEFIX_PRODUCED_BY",
        "IDEFIX_REVIEW_STATUS",
    ):
        monkeypatch.delenv(k, raising=False)
    m = _load()

    metadata = m.build_export_metadata(
        mission="russosphere",
        generated_at="2026-06-15T12:00:00+00:00",
        coverage_callout="Telegram only",
    )

    assert metadata["mission"] == "russosphere"
    assert metadata["classification_marking"] == "UNMARKED_INTERNAL_REVIEW"
    assert metadata["review_status"] == "machine_generated_pending_human_review"
    assert metadata["coverage_callout"] == "Telegram only"
    assert metadata["export_version"] == "static-bundle/v1"


def test_export_metadata_accepts_sponsor_env_overrides(monkeypatch):
    monkeypatch.setenv("IDEFIX_CLASSIFICATION_MARKING", "SPONSOR_REVIEW")
    monkeypatch.setenv("IDEFIX_HANDLING_INSTRUCTIONS", "Sponsor circuit only")
    monkeypatch.setenv("IDEFIX_PRODUCED_BY", "integration-cell")
    monkeypatch.setenv("IDEFIX_REVIEW_STATUS", "reviewed")
    m = _load()

    metadata = m.build_export_metadata(
        mission="gan",
        generated_at="2026-06-15T12:00:00+00:00",
        coverage_callout=None,
        public=True,
    )

    assert metadata["classification_marking"] == "SPONSOR_REVIEW"
    assert metadata["handling_instructions"] == "Sponsor circuit only"
    assert metadata["produced_by"] == "integration-cell"
    assert metadata["review_status"] == "reviewed"
    assert metadata["public_bundle"] is True


def test_export_metadata_is_scrubbed_at_write_boundary(monkeypatch, tmp_path):
    for k in _SECRET_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TELEGRAM_SESSION_STRING", "SECRET_SESSION_XYZ")
    monkeypatch.setenv("IDEFIX_CLASSIFICATION_MARKING", "SECRET_SESSION_XYZ")
    m = _load()

    obj = m._with_export_metadata(
        {"payload": "ok"},
        mission="russosphere",
        generated_at="2026-06-15T12:00:00+00:00",
        coverage_callout="Telegram only",
    )
    p = tmp_path / "metadata.json"
    m._write_json(p, obj)
    text = p.read_text(encoding="utf-8")

    assert "SECRET_SESSION_XYZ" not in text
    assert "[REDACTED]" in text
    assert json.loads(text)["export_metadata"]["classification_marking"] == "[REDACTED]"
