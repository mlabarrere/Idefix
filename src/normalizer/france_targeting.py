"""France-targeting thematic signal — SHIM over the generic ``targeting`` engine.

Depuis 2026-06-09 (scope-change-multi-mission), le moteur de matching a été
EXTRAIT dans ``src/normalizer/targeting.py`` (piloté par ``LexiconProfile`` +
``TargetingProfile``). Ce module n'est plus qu'un **shim** : il porte les DONNÉES
du lexique France (``FRANCE_LEXICON`` / ``FRANCE_CONTEXTUAL_TERMS`` /
``FRANCE_ADVERSARY_DOMAINS``) et délègue tout le calcul au moteur générique, de
sorte qu'il n'existe qu'UNE seule implémentation du matching (pas de dérive). Le
comportement est byte-identique (golden gate : ``tests/normalizer/
test_france_targeting.py``). ``FranceTargetingResult`` est un alias de
``TargetingResult`` ; ``score_france_targeting`` / ``_aggregate_channel`` /
``score_all_channels_france_targeting`` restent disponibles (compat).

Rappels load-bearing (inchangés) :
  * ``fr_score`` = densité de mots français ≠ ciblage thématique France. Ce signal
    détecte le ciblage CROSS-LANGUE (l'adversaire RU/EN attaque la France ;
    fr_score bas, ciblage HAUT).
  * SEVERITY MODULATOR, NEVER A GATE (MÉTA-CONTRAINTE 1).
"""
from __future__ import annotations

from typing import Iterable

from src.missions.spec import LexiconProfile, TargetingProfile
from src.normalizer.targeting import (
    TargetingResult,
    aggregate_channel,
    score_all_channels_targeting,
    score_targeting,
)

# --------------------------------------------------------------------------- #
# Lexique France multilingue — organisé par catégories CLAUDE.md §2.1.
# DONNÉES (le moteur vit dans targeting.py). Deux tiers par catégorie : ANCRES
# (toujours comptées) + CONTEXTUELS (comptés seulement avec une ancre présente).
# TODO(analyst): graine PoC à curer/étendre (VIGINUM/Arcom) — termes FR/EN/RU +
#   translittérations/racines cyrilliques. Minuscules ; le matching replie casse+accents.
# --------------------------------------------------------------------------- #
FRANCE_LEXICON: dict[str, list[str]] = {
    "national_cohesion": [
        "france", "français", "française", "la république française",
        "république française", "nation française", "peuple français", "laïcité",
        "cohésion nationale", "identité nationale", "hexagone",
        "french republic", "french nation", "the french people", "french sovereignty",
        "франци", "французск", "frantsiya", "francii",
        "souveraineté", "national cohesion", "суверенитет",
    ],
    "republican_institutions": [
        "l'élysée", "elysée", "palais de l'élysée", "matignon",
        "gouvernement français", "conseil constitutionnel", "conseil d'état",
        "quai d'orsay", "ministère des armées", "ministère de l'intérieur",
        "viginum", "arcom", "cnil", "sgdsn", "5e république", "cinquième république",
        "the elysee", "elysee palace", "french government", "french state",
        "fifth republic", "french ministry",
        "елисейский дворец", "елисейский", "французское правительство",
        "правительство франции", "пятая республика", "eliseyskiy",
        "préfecture", "constitutional council",
    ],
    "armed_forces": [
        "armée française", "armées françaises", "légion étrangère",
        "gendarmerie nationale", "marine nationale", "armée de terre",
        "armée de l'air", "barkhane", "opération barkhane",
        "militaire français", "soldats français", "otan",
        "french army", "french armed forces", "french military", "french troops",
        "foreign legion", "french soldiers", "nato",
        "французск", "французские военные", "французские войска",
        "иностранный легион", "французские солдаты", "нато", "frantsuzskaya armiya",
        "forces armées", "gendarmerie", "sahel", "арми",
    ],
    "elected_officials": [
        "macron", "emmanuel macron", "président macron", "président de la république",
        "le pen", "marine le pen", "mélenchon", "jean-luc mélenchon", "attal",
        "gabriel attal", "élu français",
        "president macron", "french president", "french mp", "french senator",
        "prime minister of france",
        "макрон", "эмманюэль макрон", "ле пен", "марин ле пен", "меланшон",
        "makron", "le pen", "melanshon",
        "premier ministre", "député", "sénateur", "prime minister", "président",
        "президент",
    ],
    "electoral_process": [
        "élection présidentielle", "présidentielle 2027", "élections françaises",
        "campagne électorale", "fraude électorale", "vote français", "législatives",
        "french election", "french elections", "2027 election", "french vote",
        "vybory vo frantsii",
        "scrutin", "bureau de vote", "abstention", "presidential election",
        "electoral fraud", "ballot", "выбор", "избирательная кампания",
        "фальсификация", "vybory",
    ],
}

# Termes génériques comptés UNIQUEMENT en présence d'une ancre (gate contextuel).
FRANCE_CONTEXTUAL_TERMS: frozenset[str] = frozenset(
    {
        "souveraineté", "national cohesion", "суверенитет",
        "préfecture", "constitutional council",
        "forces armées", "gendarmerie", "sahel", "арми",
        "premier ministre", "député", "sénateur", "prime minister",
        "président", "президент",
        "scrutin", "bureau de vote", "abstention", "presidential election",
        "electoral fraud", "ballot", "выбор", "избирательная кампания",
        "фальсификация", "vybory",
    }
)

# Domaines adverses documentés ciblant la France (Pravda / Doppelganger /
# Geopolitika / RRN). Citer l'un d'eux est un co-signal de sévérité.
FRANCE_ADVERSARY_DOMAINS: frozenset[str] = frozenset(
    {
        "pravda-fr.com",
        "pravdafr.com",
        "news-pravda.com",
        "geopolitika.ru",
        "katehon.com",
        "rrn.world",
        "rrn.media",
        "reliable-recent-news.com",
        "multipolarpress.com",
        "multipolarista.com",
    }
)

# --------------------------------------------------------------------------- #
# Profil France = lexique + poids historiques. Source de vérité du shim ; le GAN
# (gan_targeting) est simplement un autre LexiconProfile sur le même moteur.
# --------------------------------------------------------------------------- #
_FRANCE_PROFILE = LexiconProfile(
    name="france",
    categories=FRANCE_LEXICON,
    contextual_terms=FRANCE_CONTEXTUAL_TERMS,
    adversary_domains=FRANCE_ADVERSARY_DOMAINS,
    cyrillic_inflection=True,
    accent_fold=True,
)
# Poids historiques (ex-_BREADTH_WEIGHT/_DEPTH_WEIGHT/_DOMAIN_WEIGHT/_DEPTH_SATURATION).
_FRANCE_WEIGHTS = TargetingProfile(
    breadth_weight=0.55,
    depth_weight=0.30,
    domain_weight=0.15,
    depth_saturation=4.0,
)

# Alias de compatibilité : l'ancien type de résultat == le type générique.
FranceTargetingResult = TargetingResult


def score_france_targeting(
    text: str | None,
    language: str | None = None,
    cited_domains: Iterable[str] | None = None,
    *,
    claim_proximity: float | None = None,
) -> TargetingResult:
    """Score le ciblage thématique France (délègue au moteur générique).

    Signature et comportement INCHANGÉS (cross-langue, modulateur de sévérité).
    """
    return score_targeting(
        text,
        language,
        cited_domains,
        lexicon=_FRANCE_PROFILE,
        weights=_FRANCE_WEIGHTS,
        claim_proximity=claim_proximity,
    )


# Ré-export de l'agrégation pure (tests + I/O wrappers historiques l'importent).
_aggregate_channel = aggregate_channel


# --------------------------------------------------------------------------- #
# Enveloppes I/O (fines) — compat ; délèguent au moteur générique. Lecture seule.
# --------------------------------------------------------------------------- #
async def score_all_channels_france_targeting(conn) -> dict[int, float]:
    """Map ``channel_id -> france_targeting`` sur tous les canaux (lecture seule).

    Délègue au scorer générique paramétré par le profil France (= le
    ``relevance_scorer`` de la mission russosphère).
    """
    return await score_all_channels_targeting(_FRANCE_PROFILE, _FRANCE_WEIGHTS)(conn)
