"""Mission « GAN — empreinte informationnelle » (pilote).

Mesure l'empreinte informationnelle OBSERVABLE SUR TELEGRAM du Groupe Aéronaval
(*Charles de Gaulle*) — objectif OPSEC de minimisation (MinArm) — et détecte sa
captation/amplification par la russosphère. Tous les scores sont nommés
``telegram_*`` (mesure de l'observable Telegram, JAMAIS l'empreinte totale).
Périmètre Telegram-only verrouillé ; tiers T1/T2 ; arm-only.

Réutilise le moteur générique : le ciblage GAN est un ``LexiconProfile`` sur
``targeting.py`` (aucun nouveau code de matching). Les familles ``telegram_*``
sont déclarées dans le ``ScoringProfile`` et seront calculées par
``src/scorer/telegram_footprint.py`` (câblage Phase 3) ; d'ici là la mission sert
le tagging (``scripts/tag_gan.py``) et la pertinence (``gan_targeting``).

R1 (credibility_prior France-spécifique) : ``suspect_threshold=None`` ⇒ prior
neutre « other » pour le GAN (pas de présomption de suspicion sur les canaux
discutant d'un actif ami).
"""
from __future__ import annotations

from src.missions.gan.lexicon import (
    GAN_ADVERSARY_DOMAINS,
    GAN_CONTEXTUAL_TERMS,
    GAN_LEXICON,
)
from src.missions.spec import (
    DashboardProfile,
    ExportProfile,
    LexiconProfile,
    MissionDefinition,
    ScoringProfile,
    SourceUniverse,
    TargetingProfile,
)
from src.normalizer.targeting import score_all_channels_targeting
from src.scorer.eefi_rubric import eefi_disclosure_precision

_GAN_LEXICON_PROFILE = LexiconProfile(
    name="gan",
    categories=GAN_LEXICON,
    contextual_terms=GAN_CONTEXTUAL_TERMS,
    adversary_domains=GAN_ADVERSARY_DOMAINS,
    cyrillic_inflection=True,
    accent_fold=True,
)

# Empreinte = volume-led : la profondeur (volume de mentions) pèse plus que la
# largeur, à l'inverse du ciblage France (axé largeur de catégories attaquées).
_GAN_WEIGHTS = TargetingProfile(
    breadth_weight=0.40,
    depth_weight=0.45,
    domain_weight=0.15,
    depth_saturation=4.0,
)

# Mots-clés snowball (style densité, ex-FR_KW) — pour la frontière dirigée GAN.
_GAN_SNOWBALL_KW = (
    "charles de gaulle", "porte-avions", "groupe aéronaval", "marine nationale",
    "rafale marine", "toulon", "clemenceau", "frégate", "авианосец", "шарль де голль",
    # distinctifs épisodes/exercices (recherche 2026-06-10)
    "r91", "zhigulevsk", "varuna", "pacific steller",
)

MISSION = MissionDefinition(
    name="gan",
    title="GAN — empreinte informationnelle",
    description=(
        "Empreinte informationnelle observable sur Telegram du Groupe Aéronaval "
        "(Charles de Gaulle) — objectif OPSEC de minimisation + détection de "
        "l'attention adverse (russosphère). Telegram-only, arm-only, T1/T2."
    ),
    source_universe=SourceUniverse(
        # Graines en 3 tiers (recherche 2026-06-10) :
        #   1A OSINT naval neutre (origination)   : @itamilradar (tracking Méditerranée)
        #   1B presse défense FR (amplification)  : @Mer_et_Marine @OpexNews @naval_news
        #   2  milbloggers russosphère (attention adverse, DÉJÀ au catalogue) :
        #      @rybar @wargonzo @SolovievLive
        # TODO(analyst): vérifier les handles Telegram d'Opex360 / Zone Militaire /
        # NavyLookout (présence non confirmée) avant ajout.
        default_seeds=(
            "@Mer_et_Marine", "@OpexNews", "@naval_news",
            "@itamilradar",
            "@rybar", "@wargonzo", "@SolovievLive",
        ),
        snowball_keywords=_GAN_SNOWBALL_KW,
        anchor_threshold=0.15,
        snowball_anchor_signal="gan_targeting",  # ancre sur le score thématique GAN
    ),
    lexicon=_GAN_LEXICON_PROFILE,
    targeting=_GAN_WEIGHTS,
    scoring=ScoringProfile(
        # Ordonné : a/e en N/A (0.0) ; structurelles b/c/d ; familles telegram_*.
        family_weights={
            "a": 0.0,
            "b": 0.20,
            "c": 0.15,
            "d": 0.15,
            "e": 0.0,
            "telegram_visibility": 0.10,
            "telegram_velocity": 0.10,
            "telegram_source_diversity": 0.10,
            "telegram_disclosure_precision": 0.10,
            "telegram_propagation": 0.05,
            "telegram_adverse_attention": 0.05,
        },
        active_families=frozenset(
            {
                "b", "c", "d",
                "telegram_visibility", "telegram_velocity",
                "telegram_source_diversity", "telegram_disclosure_precision",
                "telegram_propagation", "telegram_adverse_attention",
            }
        ),
        relevance_signal="gan_targeting",
        suspect_threshold=None,  # R1 : prior neutre (pas de présomption de suspicion)
        adversary_domains=GAN_ADVERSARY_DOMAINS,
        extra_family_scorers=(
            "telegram_visibility", "telegram_velocity", "telegram_source_diversity",
            "telegram_disclosure_precision", "telegram_propagation",
            "telegram_adverse_attention",
        ),
        # Rubrique EEFI v0 (graine, calibration MinArm) pour la précision de divulgation.
        disclosure_rubric=eefi_disclosure_precision,
        # Famille (f) embedding (Phase 1) : baseline presse navale/défense FR + adversaires.
        # ponytail: GAN nécessite baseline DIFFÉRENTE (pas médias généralistes, mais spécialisés).
        embedding_baseline_channels=(
            "@Mer_et_Marine", "@Zone_Militaire", "@lcp",  # presse défense FR légitime
        ),
        embedding_adversary_channels=(
            "@rybar", "@grey_zone", "@itamilradar",  # OSINT adversaires
        ),
    ),
    dashboard=DashboardProfile(
        porosity_enabled=False,  # empreinte ≠ porosité RU→FR
        coverage_callout_extra=(
            "Empreinte OBSERVABLE SUR TELEGRAM uniquement — non l'empreinte totale. "
            "AIS / Strava / X / presse / satellite / ship-spotting peuvent alimenter "
            "Telegram mais ne sont pas collectés exhaustivement (cf. cas Strava)."
        ),
    ),
    export=ExportProfile(
        out_subdir="gan",
        flat_default=False,
        coverage_callout=(
            "Empreinte informationnelle du GAN — couverture Telegram uniquement "
            "(non totale). Sorties arm-only (cellule OPSEC MinArm/EMA + VIGINUM). "
            "Tiers T1 (empreinte observable + primo-divulgateur) / T2 (moniteur "
            "récurrent) ; T3 hors périmètre."
        ),
    ),
    relevance_scorer=score_all_channels_targeting(_GAN_LEXICON_PROFILE, _GAN_WEIGHTS),
    implemented=True,
)
