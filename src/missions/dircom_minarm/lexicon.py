"""Lexique « DIRCOM MinArm » — détection de la reprise/déformation des messages
officiels sur Telegram. Multilingue, pilote le moteur générique
``src/normalizer/targeting.py`` (DONNÉES uniquement, aucun code de matching).

Trois axes (catégories) :
  * ``official_comms`` — l'émetteur officiel et ses porte-voix (MinArm, DIRCOM,
    Armées, État-major, Sénat des armées, porte-parole).
  * ``distortion`` — marqueurs de transformation/déformation du message officiel
    (détourné, manipulé, fake, propagande, mensonge).
  * ``institutions`` — institutions citées en co-occurrence (ministère, gouvernement).

Domaines adverses : on réutilise l'appareil OSINT/propagande russophone du projet
(RT / Sputnik) plutôt que d'en inventer de spécifiques.
"""
from __future__ import annotations

from src.missions.spec import LexiconProfile, TargetingProfile

DIRCOM_LEXICON: dict[str, list[str]] = {
    # L'émetteur officiel et ses porte-voix (ancres).
    "official_comms": [
        "minarm", "ministère des armées", "ministere des armees",
        "dircom", "délégation à l'information et à la communication",
        "armées", "armee", "armées françaises", "état-major", "etat-major",
        "état-major des armées", "sénat des armées", "senat des armees",
        "porte-parole", "porte-parole du ministère des armées",
        "министерство вооружённых сил франции", "французская армия",
    ],
    # Marqueurs de transformation / déformation du message officiel (ancres).
    "distortion": [
        "détourné", "detourne", "manipulé", "manipule", "fake", "fake news",
        "propagande", "mensonge", "désinformation", "desinformation",
        "intox", "trucage", "пропаганда", "фейк", "дезинформация",
    ],
    # Institutions citées en co-occurrence (ancres).
    "institutions": [
        "ministère", "ministere", "gouvernement", "government",
        "министерство", "правительство",
    ],
}

# Pas de gate contextuel pour cette graine v0 (toutes les catégories sont des
# ancres). Laissé vide — à enrichir si des termes génériques ambigus apparaissent.
DIRCOM_CONTEXTUAL_TERMS: frozenset[str] = frozenset()

# Réutilise l'infrastructure adverse RU documentée du projet (cf. gan/lexicon).
DIRCOM_ADVERSARY_DOMAINS: frozenset[str] = frozenset({"rt.com", "sputniknews.com"})

DIRCOM_LEXICON_PROFILE = LexiconProfile(
    name="dircom_minarm",
    categories=DIRCOM_LEXICON,
    contextual_terms=DIRCOM_CONTEXTUAL_TERMS,
    adversary_domains=DIRCOM_ADVERSARY_DOMAINS,
    cyrillic_inflection=True,
    accent_fold=True,
)

# Ciblage : message officiel reconnu d'abord par la LARGEUR des catégories
# attaquées (émetteur + déformation), façon russosphère.
DIRCOM_WEIGHTS = TargetingProfile(
    breadth_weight=0.50,
    depth_weight=0.35,
    domain_weight=0.15,
    depth_saturation=4.0,
)
