"""Moteur générique de ciblage thématique multilingue (piloté par lexique).

GÉNÉRALISE l'ancien scorer spécifique-France (``src/normalizer/france_targeting.py``,
désormais un mince *shim*) en un moteur RÉUTILISABLE paramétré par un
``LexiconProfile`` + ``TargetingProfile`` (``src/missions/spec.py``). La logique de
matching / scoring / agrégation est **inchangée** — seules les DONNÉES (lexique,
domaines adverses) et les POIDS sont injectés — afin que le shim France reproduise
un comportement **byte-identique** (golden gate : ``tests/normalizer/
test_france_targeting.py`` reste vert). Le scorer GAN (``gan_targeting``) n'est
alors qu'un autre ``LexiconProfile`` — aucun nouveau code de matching.

LOAD-BEARING — MÉTA-CONTRAINTE 1 : MODULATEUR DE SÉVÉRITÉ, JAMAIS UN GATE. Chaque
fonction renvoie un score + évidence explicable ; rien ici ne filtre/exclut. Cœur
PUR (aucune DB) ; fine enveloppe I/O lecture-seule en bas (asyncpg).

Cross-langue par conception : le matching ne conditionne PAS sur ``language`` —
un texte purement russe attaquant la cible score HAUT malgré une densité FR nulle.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from src.missions.spec import LexiconProfile, TargetingProfile


@dataclass
class TargetingResult:
    """Signal de ciblage explicable (NFR-8). ``score`` ∈ [0,1] — modulateur, jamais gate."""

    score: float
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"score": self.score, "evidence": self.evidence}


def _strip_accents(s: str) -> str:
    """Minuscule + suppression des diacritiques (repli NFKD). ``élysée`` -> ``elysee``."""
    nkfd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nkfd if not unicodedata.combining(c)).lower()


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
# Jusqu'à 3 lettres cyrilliques tolérées en suffixe flexionnel (russe très fléchi :
# Макрон -> Макрона/Макроном). Borné pour ne pas déborder sur le mot suivant.
_RU_SUFFIX = r"[Ѐ-ӿ]{0,3}"


def _build_term_pattern(term: str, *, cyrillic_inflection: bool = True) -> re.Pattern[str]:
    """Compile un matcher à frontières de mot, replié-accents, pour un terme.

    INFLEXION (load-bearing RU) : si le terme finit par une lettre cyrillique et
    ``cyrillic_inflection`` est vrai, on autorise un suffixe cyrillique borné avant
    la frontière finale (pour capter les déclinaisons). Termes latins/mixtes :
    frontière finale stricte (pas de sur-matching de ``france`` dans ``frances``).
    """
    folded = _strip_accents(term)
    parts = [re.escape(p) for p in folded.split()]
    body = r"\s+".join(parts)
    word = r"[^\W]"  # avec re.UNICODE = toute lettre/chiffre/_
    suffix = _RU_SUFFIX if (cyrillic_inflection and _CYRILLIC_RE.search(folded[-1:])) else ""
    return re.compile(rf"(?<!{word})(?:{body}){suffix}(?!{word})", re.UNICODE)


@dataclass
class _CompiledLexicon:
    compiled: dict[str, list[tuple[str, re.Pattern[str]]]]
    contextual_folded: frozenset[str]
    prescreen: re.Pattern[str]
    n_categories: int


# Cache des lexiques compilés, par ``LexiconProfile.name`` (les profils sont des
# singletons de module : france, gan…). Évite de recompiler ~150 patterns à chaque
# message. (LexiconProfile contient un dict -> non hashable -> pas de lru_cache.)
_CACHE: dict[str, _CompiledLexicon] = {}


def _get_compiled(lexicon: LexiconProfile) -> _CompiledLexicon:
    cached = _CACHE.get(lexicon.name)
    if cached is not None:
        return cached
    compiled = {
        cat: [
            (term, _build_term_pattern(term, cyrillic_inflection=lexicon.cyrillic_inflection))
            for term in terms
        ]
        for cat, terms in lexicon.categories.items()
    }
    contextual_folded = frozenset(_strip_accents(t) for t in lexicon.contextual_terms)
    # Pré-filtre PERF : alternation des CORPS de termes (sans lookarounds ni suffixe),
    # sur-ensemble des patterns détaillés -> n'altère AUCUN résultat, court-circuite
    # seulement les messages sans aucun terme cible (la grande majorité).
    prescreen = re.compile(
        "|".join(
            r"\s+".join(re.escape(p) for p in _strip_accents(term).split())
            for terms in lexicon.categories.values()
            for term in terms
        ),
        re.UNICODE,
    )
    out = _CompiledLexicon(compiled, contextual_folded, prescreen, len(lexicon.categories))
    _CACHE[lexicon.name] = out
    return out


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def score_targeting(
    text: str | None,
    language: str | None = None,
    cited_domains: Iterable[str] | None = None,
    *,
    lexicon: LexiconProfile,
    weights: TargetingProfile,
    claim_proximity: float | None = None,
) -> TargetingResult:
    """Score le ciblage thématique d'un texte selon ``lexicon`` + ``weights``.

    Logique IDENTIQUE à l'ancien ``score_france_targeting`` ; le lexique, les
    domaines adverses et les poids sont injectés. Cross-langue (ne conditionne pas
    sur ``language``). Ne lève jamais sur entrée vide/None.
    """
    comp = _get_compiled(lexicon)
    adversary_domains = {d.lower() for d in lexicon.adversary_domains}

    matched_terms: dict[str, list[str]] = {}
    contextual_deferred: dict[str, list[tuple[str, int]]] = {}
    total_hits = 0
    has_anchor = False

    folded = _strip_accents(text) if text else ""
    if folded and comp.prescreen.search(folded):
        for category, compiled in comp.compiled.items():
            cat_anchor: list[str] = []
            cat_context: list[tuple[str, int]] = []
            for term, pattern in compiled:
                n = len(pattern.findall(folded))
                if not n:
                    continue
                term_folded = _strip_accents(term)
                if term_folded in comp.contextual_folded:
                    cat_context.append((term, n))  # provisoire — nécessite une ancre
                else:
                    has_anchor = True
                    total_hits += n
                    cat_anchor.append(term)
            if cat_anchor:
                matched_terms.setdefault(category, []).extend(cat_anchor)
            if cat_context:
                contextual_deferred[category] = cat_context

        # Les termes contextuels ne comptent que si une ancre a matché quelque part.
        if has_anchor:
            for category, items in contextual_deferred.items():
                for term, n in items:
                    total_hits += n
                    matched_terms.setdefault(category, []).append(term)

        for category in list(matched_terms):
            matched_terms[category] = list(dict.fromkeys(matched_terms[category]))

    distinct_categories = len(matched_terms)

    # --- co-signal domaine -------------------------------------------------- #
    domain_hits: list[str] = []
    if cited_domains:
        seen: set[str] = set()
        for d in cited_domains:
            if not d:
                continue
            dl = d.lower()
            if dl in adversary_domains and dl not in seen:
                seen.add(dl)
                domain_hits.append(dl)

    # --- composantes du score ---------------------------------------------- #
    breadth = distinct_categories / comp.n_categories if comp.n_categories else 0.0
    depth = (
        total_hits / (total_hits + weights.depth_saturation) if total_hits else 0.0
    )
    domain_signal = 1.0 if domain_hits else 0.0

    score = (
        weights.breadth_weight * breadth
        + weights.depth_weight * depth
        + weights.domain_weight * domain_signal
    )

    # --- seam proximité-revendication (BGE-M3 / registre épisodes vide v0) -- #
    if claim_proximity is not None:
        cp = _clamp01(float(claim_proximity))
        claim_note: float | str = cp
        score = score + (1.0 - score) * cp  # OR doux : ne fait que MONTER
    else:
        claim_note = "N/A — episodes registry empty (v0)"

    score = _clamp01(score)

    evidence = {
        "matched_terms": matched_terms,
        "distinct_categories": distinct_categories,
        "total_hits": total_hits,
        "has_anchor": has_anchor,
        "domain_hits": domain_hits,
        "claim_proximity": claim_note,
        "language_hint": language,
        "components": {
            "breadth": round(breadth, 4),
            "depth": round(depth, 4),
            "domain_signal": domain_signal,
            "weights": {
                "breadth": weights.breadth_weight,
                "depth": weights.depth_weight,
                "domain": weights.domain_weight,
            },
        },
    }
    return TargetingResult(score=round(score, 4), evidence=evidence)


def aggregate_channel(channel_id: int, per_message: list[TargetingResult]) -> TargetingResult:
    """Agrégation PURE des résultats par message en un résultat canal.

    Score canal = max par-message ; évidence porte couverture + moyenne + union des
    catégories (un one-off vs. une campagne soutenue restent distinguables).
    """
    n = len(per_message)
    if n == 0:
        return TargetingResult(
            score=0.0,
            evidence={
                "channel_id": channel_id,
                "messages_sampled": 0,
                "coverage": 0.0,
                "mean_score": 0.0,
                "matched_categories": [],
                "note": "no messages sampled",
            },
        )

    scores = [r.score for r in per_message]
    hits = sum(1 for r in per_message if r.evidence.get("total_hits", 0) > 0)
    matched_categories: set[str] = set()
    for r in per_message:
        matched_categories.update(r.evidence.get("matched_terms", {}).keys())

    max_score = max(scores)
    return TargetingResult(
        score=round(max_score, 4),
        evidence={
            "channel_id": channel_id,
            "messages_sampled": n,
            "coverage": round(hits / n, 4),
            "mean_score": round(sum(scores) / n, 4),
            "max_score": round(max_score, 4),
            "matched_categories": sorted(matched_categories),
        },
    )


# --------------------------------------------------------------------------- #
# Enveloppe I/O (fine) — seul accès PostgreSQL (asyncpg, lecture seule).        #
# --------------------------------------------------------------------------- #
def score_all_channels_targeting(lexicon: LexiconProfile, weights: TargetingProfile):
    """Fabrique un ``ChannelRelevanceScorer`` ``async conn -> {channel_id: float}``.

    Conforme au Protocol ``src.missions.spec.ChannelRelevanceScorer`` : c'est ce
    que chaque mission expose comme ``relevance_scorer``. Une seule requête (pas de
    N+1) + cap recency par canal en Python (≤ sample_limit messages récents/canal).
    """

    async def _scorer(conn) -> dict[int, float]:
        sample_limit = 500
        rows = await conn.fetch(
            """
            SELECT channel_id, text, language
            FROM messages
            WHERE text IS NOT NULL
            ORDER BY channel_id, timestamp DESC NULLS LAST
            """
        )
        by_channel: dict[int, list] = {}
        for r in rows:
            bucket = by_channel.setdefault(r["channel_id"], [])
            if len(bucket) < sample_limit:
                bucket.append(r)

        out: dict[int, float] = {}
        for cid, msgs in by_channel.items():
            per_message = [
                score_targeting(m["text"], m["language"], lexicon=lexicon, weights=weights)
                for m in msgs
            ]
            out[cid] = aggregate_channel(cid, per_message).score
        return out

    return _scorer
