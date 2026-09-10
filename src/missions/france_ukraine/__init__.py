"""Mission « France dans le conflit ukrainien ».

Cible les narratifs visant l'image / l'intégrité / la souveraineté de la France
DANS le conflit ukrainien (soldats/cercueils/mercenaires français, financement et
livraisons d'armes, positionnement OTAN/escalade) — docs/method/01-problem-and-scope.md +
``data/claims/claims_fr.jsonl``.

Réutilise INTÉGRALEMENT le moteur générique : le ciblage est un ``LexiconProfile``
sur ``targeting.py`` (aucun nouveau code de matching ni de scorer). Comme la
russosphère, le ciblage est LARGEUR-led (la largeur des catégories attaquées
prime sur le volume). Signal de pertinence propre ``france_ukraine_targeting``
(modulateur de sévérité, JAMAIS filtre — MÉTA-CONTRAINTE 1).

Le snowball ancre sur ``france_ukraine_targeting`` ; tant qu'aucun
``tag_france_ukraine.py`` ne le peuple (rétrofit J2), ``build_scores`` calcule la
pertinence à la volée via ``relevance_scorer``.
"""
from __future__ import annotations

from src.missions.france_ukraine.lexicon import (
    FRANCE_UKRAINE_ADVERSARY_DOMAINS,
    FRANCE_UKRAINE_CONTEXTUAL_TERMS,
    FRANCE_UKRAINE_LEXICON,
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

_FU_LEXICON_PROFILE = LexiconProfile(
    name="france_ukraine",
    categories=FRANCE_UKRAINE_LEXICON,
    contextual_terms=FRANCE_UKRAINE_CONTEXTUAL_TERMS,
    adversary_domains=FRANCE_UKRAINE_ADVERSARY_DOMAINS,
    cyrillic_inflection=True,
    accent_fold=True,
)

# Largeur-led (comme la russosphère) : la largeur des catégories attaquées prime.
_FU_WEIGHTS = TargetingProfile(
    breadth_weight=0.55,
    depth_weight=0.30,
    domain_weight=0.15,
    depth_saturation=4.0,
)

# Mots-clés snowball (densité) — frontière dirigée France×Ukraine.
_FU_SNOWBALL_KW = (
    "france", "français", "macron", "ukraine", "zelensky", "donbass",
    "soldats français", "mercenaires français", "livraison d'armes", "otan",
    "франци", "украин", "макрон", "зеленск",
)

MISSION = MissionDefinition(
    name="france_ukraine",
    title="France dans le conflit ukrainien",
    description=(
        "Narratifs visant l'image/intégrité/souveraineté de la France dans le "
        "conflit ukrainien (implication militaire alléguée, financement, OTAN). "
        "Telegram-only, arm-only, T1/T2."
    ),
    source_universe=SourceUniverse(
        # Graines : presse FR + ancres russosphère francophone déjà au catalogue
        # (origination/amplification des narratifs France×Ukraine). À affiner par
        # l'analyste (TODO) à partir des découvertes de crawl_france_ukraine.py.
        default_seeds=(
            "@RFI_fr", "@france24_fr", "@Geopolitika_fr",
        ),
        snowball_keywords=_FU_SNOWBALL_KW,
        anchor_threshold=0.15,
        snowball_anchor_signal="france_ukraine_targeting",
    ),
    lexicon=_FU_LEXICON_PROFILE,
    targeting=_FU_WEIGHTS,
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
        relevance_signal="france_ukraine_targeting",
        suspect_threshold=0.15,
        adversary_domains=ADVERSARY_DOMAINS,
    ),
    dashboard=DashboardProfile(
        porosity_enabled=False,
        coverage_callout_extra=(
            "Périmètre France×Ukraine : narratifs visant la France dans le conflit. "
            "Couverture Telegram uniquement (cf. cécité mono-plateforme)."
        ),
    ),
    export=ExportProfile(
        out_subdir="france_ukraine",
        flat_default=False,
        snapshots=(
            (
                "france_ukraine_snapshot.json",
                "france_ukraine.json",
                "FRANCE_UKRAINE_SNAPSHOT",
            ),
        ),
        coverage_callout=COVERAGE_CALLOUT_FR,
    ),
    relevance_scorer=score_all_channels_targeting(_FU_LEXICON_PROFILE, _FU_WEIGHTS),
    implemented=True,
)
