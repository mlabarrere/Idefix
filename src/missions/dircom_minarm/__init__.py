"""Mission « DIRCOM MinArm » (planifiée — non implémentée).

Reprise / transformation / déformation des messages officiels DIRCOM MinArm sur
Telegram : détecter quand la communication institutionnelle des Armées est
détournée, manipulée ou retournée (notamment par l'appareil OSINT/propagande
russophone — RT / Sputnik réutilisés).

Mission = CONFIGURATION (pas de fork de code) : composition des six profils +
``relevance_scorer`` générique ``score_all_channels_targeting`` sur le lexique
DIRCOM (aucun nouveau code de matching), comme la mission GAN.

STATUT : ``implemented=False`` ⇒ apparaît au switcher du frontend mais
``registry.get`` refuse la sélection live (pas de cul-de-sac : aucun bundle de
données n'est encore déployé). Passer à ``implemented=True`` ACTIVE la sélection
live une fois la collecte/le scoring DIRCOM disponibles.
"""
from __future__ import annotations

from src.missions.dircom_minarm.lexicon import (
    DIRCOM_ADVERSARY_DOMAINS,
    DIRCOM_LEXICON_PROFILE,
    DIRCOM_WEIGHTS,
)
from src.missions.spec import (
    DashboardProfile,
    ExportProfile,
    MissionDefinition,
    ScoringProfile,
    SourceUniverse,
)
from src.normalizer.targeting import score_all_channels_targeting

MISSION = MissionDefinition(
    name="dircom_minarm",
    title="DIRCOM MinArm — reprise / déformation des messages officiels",
    description=(
        "Reprise / transformation / déformation des messages officiels DIRCOM "
        "MinArm sur Telegram. Mission planifiée — non implémentée (pas encore de "
        "bundle de données)."
    ),
    source_universe=SourceUniverse(
        default_seeds=("@Armees_Gouv", "@Ministere_Armees"),
        snowball_keywords=(
            "minarm", "ministère des armées", "dircom", "état-major",
            "marine nationale", "armée française", "porte-parole", "communiqué",
            "défense", "naval",
        ),
        anchor_threshold=0.15,
        snowball_anchor_signal="dircom_targeting",
    ),
    lexicon=DIRCOM_LEXICON_PROFILE,
    targeting=DIRCOM_WEIGHTS,
    scoring=ScoringProfile(
        # Familles structurelles b/c/d actives (comme russosphère) ; a/e N/A.
        family_weights={"a": 0.0, "b": 0.40, "c": 0.30, "d": 0.30, "e": 0.0},
        active_families=frozenset({"b", "c", "d"}),
        relevance_signal="dircom_targeting",
        suspect_threshold=0.15,  # présomption de suspicion sous le seuil de ciblage
        adversary_domains=DIRCOM_ADVERSARY_DOMAINS,
        # Famille (f) embedding : baseline = comms défense FR officielles ;
        # adversaires = OSINT/propagande russophone.
        # ponytail: handles graine, à curer une fois la collecte DIRCOM câblée.
        embedding_baseline_channels=(
            "@Armees_Gouv", "@Ministere_Armees", "@Mer_et_Marine",
        ),
        embedding_adversary_channels=(
            "@rt_fr", "@sputnik_fr",
        ),
    ),
    dashboard=DashboardProfile(
        porosity_enabled=False,
        coverage_callout_extra=(
            "Mission PLANIFIÉE — non implémentée. Couverture Telegram uniquement "
            "(reprise/déformation des communiqués officiels) ; aucun bundle de "
            "données n'est encore déployé."
        ),
    ),
    export=ExportProfile(out_subdir="dircom_minarm"),
    relevance_scorer=score_all_channels_targeting(DIRCOM_LEXICON_PROFILE, DIRCOM_WEIGHTS),
    # ponytail: passer à True active la sélection live (registry.get) une fois les
    # données DIRCOM disponibles.
    implemented=False,
)
