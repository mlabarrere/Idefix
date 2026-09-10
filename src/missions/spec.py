"""Abstraction « mission » d'Idéfix — types des profils (PUR, stdlib only).

Idéfix est repositionné en **moteur Telegram, N missions analytiques** (docs/README.md
bandeau 2026-06-09 ; architecture-multi-mission-2026-06-09.md). Une **mission est
une CONFIGURATION**, jamais une fourche de code : elle compose six profils
+ un scorer de pertinence que le moteur (pipeline + scoring + export) consomme.

Ce module ne contient QUE des dataclasses gelées et un Protocol — aucun import
lourd (pas de networkx, pas de DB, pas de Telegram). Il peut donc être importé
par ``channel_suspicion`` (pour typer le ``ScoringProfile``) sans cycle ni coût.

LOAD-BEARING (MÉTA-CONTRAINTE 1, déjà gravé dans ``channel_suspicion``) : la
pertinence thématique (``relevance_signal`` / ``relevance_scorer``) MODULE la
sévérité (bornée, multiplicative, montante) ; elle ne FILTRE jamais l'inclusion.
Cet axiome est générique et vaut pour toute mission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ChannelRelevanceScorer(Protocol):
    """Calcule ``{channel_id: pertinence∈[0,1]}`` pour la mission (lecture seule).

    Implémentations : ``score_all_channels_france_targeting`` (russosphère) ;
    ``score_all_channels_targeting(gan_lexicon, gan_weights)`` (GAN, via le
    ``targeting`` généralisé). Le résultat est injecté comme **modulateur de
    sévérité** dans ``compute_channel_queue`` — jamais comme filtre.
    """

    async def __call__(self, conn) -> dict[int, float]: ...  # noqa: D401


@dataclass(frozen=True)
class SourceUniverse:
    """Univers de sources de la mission (graines + frontière snowball).

    Généralise ``scripts/backfill_seeds.py`` (``_DEFAULT_SEEDS``) et
    ``scripts/snowball_crawl.py`` (``FR_KW`` / ``ANCHOR_THRESHOLD``). Le
    ``snowball_anchor_signal`` nomme la clé JSON de ``channels.extra`` sur
    laquelle ancrer l'expansion dirigée (``fr_score`` pour russosphère,
    ``gan_targeting`` pour le GAN).
    """

    default_seeds: tuple[str, ...] = ()
    snowball_keywords: tuple[str, ...] = ()
    anchor_threshold: float = 0.15
    snowball_anchor_signal: str = "fr_score"
    seed_channel_id: int | None = None
    seed_username: str | None = None


@dataclass(frozen=True)
class LexiconProfile:
    """Lexique multilingue de ciblage thématique (généralise ``FRANCE_LEXICON``).

    ``categories`` = ``{catégorie: [termes…]}`` (ancres) ; ``contextual_terms`` =
    termes génériques comptés UNIQUEMENT en présence d'une ancre (gate
    contextuel) ; ``adversary_domains`` = domaines dont la citation est un
    co-signal de sévérité. ``cyrillic_inflection`` / ``accent_fold`` gèrent les
    règles de matching (la règle de suffixe cyrillique et le repli d'accents).
    """

    name: str
    categories: Mapping[str, Sequence[str]]
    contextual_terms: frozenset[str] = frozenset()
    adversary_domains: frozenset[str] = frozenset()
    cyrillic_inflection: bool = True
    accent_fold: bool = True


@dataclass(frozen=True)
class TargetingProfile:
    """Pondérations du scorer de ciblage (généralise ``france_targeting`` §weights)."""

    breadth_weight: float = 0.55
    depth_weight: float = 0.30
    domain_weight: float = 0.15
    depth_saturation: float = 4.0


@dataclass(frozen=True)
class ScoringProfile:
    """Paramètres de ``compute_channel_queue`` pour la mission.

    Le défaut reproduit EXACTEMENT les constantes actuelles de
    ``channel_suspicion`` (russosphère) → chemin identique drapeau ``--mission``
    absent. Les missions GAN ajoutent des familles via ``family_weights`` +
    ``extra_family_scorers`` (clés ``telegram_*``).

    ``family_weights`` DOIT être un mapping ORDONNÉ a/b/c/d/e (puis telegram_*)
    pour la stabilité du bundle golden (cf. risque R3).
    """

    family_weights: Mapping[str, float]
    active_families: frozenset[str]
    gate_threshold: float = 0.3
    min_families_for_gate: int = 2
    max_reforward_boost: float = 0.20
    max_adversary_domain_boost: float = 0.15
    adversary_domain_saturation: int = 5
    max_targeting_boost: float = 0.20
    stale_days: int = 14
    window_delta_seconds: int = 72 * 3600
    # Nom du scalaire de pertinence par canal (affichage + clé d'ancrage).
    relevance_signal: str = "france_targeting"
    # Politique de credibility_prior (résout R1) : seuil sous lequel un canal est
    # a priori « suspect » sur le ``relevance_signal``. None => prior neutre
    # (« other ») pour toute la mission (cas GAN : pas de présomption de suspicion
    # sur les canaux discutant d'un actif ami).
    suspect_threshold: float | None = 0.15
    # Domaines adverses pour le boost de citation (mission-spécifique).
    adversary_domains: frozenset[str] = frozenset()
    # Familles supplémentaires précalculées (ex. familles GAN telegram_*).
    extra_family_scorers: tuple[str, ...] = ()
    # --- Scoring rigoureux (modèle nul + significativité + bootstrap) ---------
    # ``alpha`` = seuil de significativité (nouvelle sémantique du gate : une
    # famille DÉCLENCHE si p < alpha ; remplace le cutoff de valeur historique
    # ``gate_threshold``, conservé pour compat). ``n_null`` graphes nuls (endpoints
    # randomisés), ``n_bootstrap`` ré-échantillonnages pour les IC. ``rng_seed`` fixe
    # ⇒ bundle byte-reproductible (EIP). ``fdr_method`` = correction multi-tests
    # Benjamini-Hochberg appliquée à l'ENSEMBLE des canaux (définit ``flagged``).
    alpha: float = 0.05
    n_null: int = 200
    n_bootstrap: int = 100
    rng_seed: int = 1312
    fdr_method: str = "fdr_bh"
    # Rubrique de précision-de-divulgation EEFI injectée (text, lang) -> [0,1],
    # pour la famille ``telegram_disclosure_precision`` (mission GAN). None =>
    # famille N/A. Sévérités = décision métier (calibration MinArm).
    disclosure_rubric: Callable[[str | None, str | None], float] | None = None
    # Famille (f) embedding semantic coherence (Phase 1). Handles de canaux baseline
    # (médias FR légitimes) + adversaires (RT, Sputnik...). None => famille (f) N/A.
    # ponytail: baseline=100 canaux, étendre à 500 si recall < 0.5 (Phase 3).
    embedding_baseline_channels: tuple[str, ...] | None = None
    embedding_adversary_channels: tuple[str, ...] | None = None


@dataclass(frozen=True)
class DashboardProfile:
    """Configuration des vues/snapshots (communautés, porosité, encodages UI)."""

    community_theme_rules: tuple[tuple[str, tuple[str, ...]], ...] = ()
    palette: tuple[str, ...] = ()
    porosity_enabled: bool = False
    porosity_side_signal: str = "fr_score"
    porosity_side_min: float = 0.15
    coverage_callout_extra: str = ""


@dataclass(frozen=True)
class ExportProfile:
    """Configuration de l'export du bundle JSON (``scripts/export_static.py``).

    ``out_subdir`` = sous-dossier ``webapp/public/data/<out_subdir>/`` (cible
    canonique de la webapp statique depuis 2026-06-10 — le frontend HTML/JS
    legacy est supprimé). ``flat_default`` est conservé pour compat (plus de
    bundle plat : chaque mission a son sous-dossier).
    ``snapshots`` = liste de triplets ``(fichier_json, fichier_court, var_js)``.
    ``extra_scrub_keys`` complète le scrub global des secrets.
    """

    out_subdir: str
    flat_default: bool = False
    snapshots: tuple[tuple[str, str, str], ...] = ()
    coverage_callout: str = ""
    public_aggregates_only: bool = True
    extra_scrub_keys: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MissionDefinition:
    """Une mission = la composition des six profils + un scorer de pertinence.

    ``implemented=False`` => mission planifiée (apparaît au registre/switcher mais
    ``registry.get`` refuse de la sélectionner). ``relevance_scorer`` peut être
    ``None`` pour une mission planifiée.
    """

    name: str
    title: str
    source_universe: SourceUniverse
    lexicon: LexiconProfile
    targeting: TargetingProfile
    scoring: ScoringProfile
    dashboard: DashboardProfile
    export: ExportProfile
    relevance_scorer: ChannelRelevanceScorer | None = None
    implemented: bool = True
    description: str = ""
