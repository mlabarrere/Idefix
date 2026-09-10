"""Mission « russosphère → extrême droite FR » — MISSION PAR DÉFAUT.

C'est le comportement HISTORIQUE d'Idéfix, exprimé comme une configuration de la
plateforme générique. Ses profils RÉFÉRENCENT les constantes actuelles (lexique
France, pondérations de scoring, domaines adverses) → drapeau ``--mission`` absent
⇒ ``DEFAULT_MISSION`` ⇒ bundle byte-identique (garantie zéro-régression,
golden test).

Source unique de vérité : le lexique et les pondérations sont IMPORTÉS de
``france_targeting`` / ``channel_suspicion`` (pas dupliqués) pour éliminer toute
dérive. Les valeurs d'univers de sources / export (graines, mots-clés snowball,
snapshots) sont reportées ici depuis ``backfill_seeds`` / ``snowball_crawl`` /
``export_static`` : la mission DEVIENT leur source de vérité quand les scripts
seront câblés ``--mission`` (rétrofit ultérieur).
"""
from __future__ import annotations

from src.missions.spec import (
    DashboardProfile,
    ExportProfile,
    LexiconProfile,
    MissionDefinition,
    ScoringProfile,
    SourceUniverse,
    TargetingProfile,
)
from src.normalizer.france_targeting import (
    FRANCE_ADVERSARY_DOMAINS,
    FRANCE_CONTEXTUAL_TERMS,
    FRANCE_LEXICON,
    score_all_channels_france_targeting,
)
from src.scorer.channel_suspicion import (
    ADVERSARY_DOMAIN_SATURATION,
    ADVERSARY_DOMAINS,
    BASE_FAMILY_WEIGHTS,
    GATE_THRESHOLD,
    MAX_ADVERSARY_DOMAIN_BOOST,
    MAX_FRANCE_TARGETING_BOOST,
    MAX_REFORWARD_BOOST,
    MIN_FAMILIES_FOR_GATE,
    STALE_DAYS,
)
from src.shared.dossier import COVERAGE_CALLOUT_FR

# Reporté de scripts/backfill_seeds.py::_DEFAULT_SEEDS (la mission devient la
# source de vérité au câblage --mission de backfill_seeds).
_DEFAULT_SEEDS = (
    "@RFI_fr", "@euronewsfr", "@france24_fr", "@actu17", "@Mediavenir", "@CerfiaFR",
    "@Geopolitika_fr",
)
# Source unique des mots-clés « France » (importée par les scripts de tag/crawl —
# tag_france, snowball_crawl, build_channel_digests, build_label_batch — pour
# éviter la dérive entre copies).
FR_KEYWORDS = (
    "france", "français", "francais", "française", "macron", "paris", "élys",
    "otan", "arcom", "viginum", "répub", "repub", "gendarm", "assemblée",
    "hexagone", "quai d'orsay", "barkhane", "sahel",
)
# Variante « électorale » : ajoute les figures politiques clivantes, pour le
# tag au niveau MESSAGE (tag_france / build_label_batch / build_channel_digests).
FR_KEYWORDS_ELECTORAL = (*FR_KEYWORDS, "le pen", "mélenchon")

MISSION = MissionDefinition(
    name="russosphere",
    title="Russosphère → extrême droite FR",
    description=(
        "Désinformation coordonnée visant l'image / l'intégrité / la souveraineté "
        "de la France (docs/method/01-problem-and-scope.md). Mission historique, par défaut."
    ),
    source_universe=SourceUniverse(
        default_seeds=_DEFAULT_SEEDS,
        snowball_keywords=FR_KEYWORDS,
        anchor_threshold=0.15,  # snowball_crawl.ANCHOR_THRESHOLD
        snowball_anchor_signal="fr_score",
        seed_channel_id=-1001508539275,  # analyze_communities.SEED_CHANNEL_ID
        seed_username="France24_fr",
    ),
    lexicon=LexiconProfile(
        name="france",
        categories=FRANCE_LEXICON,
        contextual_terms=FRANCE_CONTEXTUAL_TERMS,
        adversary_domains=FRANCE_ADVERSARY_DOMAINS,
        cyrillic_inflection=True,
        accent_fold=True,
    ),
    # Pondérations actuelles de france_targeting (breadth/depth/domain/saturation).
    targeting=TargetingProfile(
        breadth_weight=0.55,
        depth_weight=0.30,
        domain_weight=0.15,
        depth_saturation=4.0,
    ),
    scoring=ScoringProfile(
        family_weights=BASE_FAMILY_WEIGHTS,          # ordonné a/b/c/d/e
        active_families=frozenset({"b", "c", "d"}),  # a/e = N/A en v0
        gate_threshold=GATE_THRESHOLD,
        min_families_for_gate=MIN_FAMILIES_FOR_GATE,
        max_reforward_boost=MAX_REFORWARD_BOOST,
        max_adversary_domain_boost=MAX_ADVERSARY_DOMAIN_BOOST,
        adversary_domain_saturation=ADVERSARY_DOMAIN_SATURATION,
        max_targeting_boost=MAX_FRANCE_TARGETING_BOOST,
        stale_days=STALE_DAYS,
        relevance_signal="france_targeting",
        credibility_prior_enabled=True,  # prior adossé à adversary_domains
        adversary_domains=ADVERSARY_DOMAINS,
        # Famille (f) embedding (Phase 1) : baseline FR légit + adversaires RU.
        # ponytail: handles hardcodés, migrer vers data/eval/baseline_organic_fr.json (Phase 3).
        embedding_baseline_channels=(
            "@RFI_fr", "@France24_fr", "@lemondefr", "@libe", "@lcp",
        ),
        embedding_adversary_channels=(
            "@rt_fr", "@sputnik_fr", "@Geopolitika_fr",
        ),
    ),
    dashboard=DashboardProfile(
        porosity_enabled=True,
        porosity_side_signal="fr_score",
        porosity_side_min=0.15,
        # TODO(câblage analyze_communities) : reporter THEME_RULES + PALETTE ici
        # (la mission deviendra leur source de vérité). Laissé vide tant que
        # analyze_communities n'est pas câblé --mission (rien ne le consomme ici).
    ),
    export=ExportProfile(
        out_subdir="russosphere",
        flat_default=True,  # compat historique (la cible est webapp/public/data/russosphere/)
        snapshots=(
            ("russosphere_snapshot.json", "russosphere.json", "RUSSOSPHERE_SNAPSHOT"),
            ("porosity_snapshot.json", "porosity.json", "POROSITY_SNAPSHOT"),
        ),
        coverage_callout=COVERAGE_CALLOUT_FR,
    ),
    relevance_scorer=score_all_channels_france_targeting,
    implemented=True,
)
