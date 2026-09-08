"""Les rationales Mistral exportées ne nomment jamais le fournisseur (garde-fou #6).

``label_communities_llm.py`` redige ``label``/``rationale`` via
``src.labeling.aggregate._redact_providers`` AVANT écriture. On vérifie ici que ce
helper neutralise bien « Mistral » (déjà listé dans ``_PROVIDER_TOKENS``).
"""
from src.labeling.aggregate import _redact_providers


def test_mistral_provider_name_redacted():
    txt = "D'après Mistral Large, cette communauté relaie des contenus pro-Kremlin."
    out = _redact_providers(txt)
    assert "mistral" not in out.lower()
    assert "[juge]" in out
    # le contenu analytique substantiel survit.
    assert "pro-Kremlin" in out


def test_accentuated_and_plain_variants_redacted():
    assert "mistral" not in _redact_providers("analyse Mistral").lower()
    assert "mistral" not in _redact_providers("MISTRAL dit que").lower()
