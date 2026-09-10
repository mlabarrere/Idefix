"""Score de suspicion PAR CANAL — cœur du livrable Idéfix (explicable).

Ce module assemble les familles de scores (a–e, cf.
docs/method/03-suspicion-score.md §3.1) en UN score de
suspicion par canal, **transparent et justifiable** (NFR-8), et produit le bloc
``queue`` consommé par scripts/export_static.py (matérialisé dans
``data/channels.json``) puis par la console opérateur (contrat :
``frontend/dossiers/_channel_queue_sample.json`` -> ``queue``). L'API FastAPI
est LEGACY.

PIVOT 2026-06-05 (memory : supervision-pivot-channel-and-explainable-score) :
on classe des CANAUX, pas des messages ; et tant que les données ne passent pas
à l'échelle, on livre un SCORE explicable (pas un GNN). Ce module EST ce score.

──────────────────────────────────────────────────────────────────────────────
LOAD-BEARING — MÉTA-CONTRAINTE 1 (docs/method/03-suspicion-score.md §3.8) :
    Le score ne FILTRE JAMAIS, et ne se GATE JAMAIS, par ``fr_score``.
    ``fr_score`` = densité de mots-clés français ≠ ciblage thématique France.
    L'adversaire RU/EN a un ``fr_score`` BAS : un canal adverse à fr_score bas
    DOIT pouvoir remonter en tête. La liaison à l'infrastructure adverse module
    la SÉVÉRITÉ (vers le haut, bornée), jamais l'INCLUSION.

    CIBLAGE THÉMATIQUE FRANCE (``france_targeting``, src/normalizer/
    france_targeting.py) est désormais CÂBLÉ comme modulateur de SÉVÉRITÉ
    multiplicatif, montant uniquement et borné (``MAX_FRANCE_TARGETING_BOOST``).
    Il REMPLACE ``fr_score`` comme levier de pertinence-France (cross-langue :
    l'adversaire RU/EN qui attaque la France score HAUT, contrairement à
    fr_score). Conséquence multiplicative voulue : un canal à suspicion de base
    0 (aucun rôle cascade/coordination/récidive) reste à 0 même avec un
    france_targeting élevé — la presse française légitime qui parle de la France
    n'est PAS promue ; seul un canal DÉJÀ suspect est amplifié. ``fr_score``
    reste un champ d'AFFICHAGE seulement, jamais un filtre/gate.
──────────────────────────────────────────────────────────────────────────────

Orientation FORWARD (confirmée depuis ``src/graph/edges.py`` ::
``derive_forward_edges`` : ``src_channel_id=origin``, ``dst_channel_id=reposter``)
    => l'arête FORWARD va de l'ORIGINE (canal dont le message est relayé)
       vers le RELAYEUR (canal qui republie).  ORIGIN -> RELAYER.
    Les scorers (b)/(d) consomment ce même sens (out = fan-out / influence,
    in = origines relayées). Dans le multiplex, l'arête FORWARD porte
    ``delay_seconds`` ; les scorers attendent ``min_delay_s`` -> on MAPPE
    ``delay_seconds`` -> ``min_delay_s`` à la projection.

Conception (miroir de ``src/graph/loader.py`` : I/O DB séparée du pur) :
  * Cœur PUR testable sans base : ``forward_digraph``, ``compute_channel_queue``,
    ``channel_archetypes`` opèrent sur un ``MultiDiGraph`` NetworkX en mémoire.
  * Fines enveloppes I/O : ``build_channel_queue(conn, ...)`` lit PostgreSQL via
    le loader (lecture seule) puis appelle le cœur pur.
  * AUCUN appel Telegram/MTProto. Library-first : networkx uniquement.
"""

from __future__ import annotations

from typing import Any, Mapping

import networkx as nx
import structlog

from src.graph.loader import (
    COORDINATION_EDGE_TYPES,
    build_graph,
    fetch_channel_rows,
    fetch_edge_rows,
)

# ScoringProfile paramètre ce combineur PAR MISSION (2026-06-09). Import léger
# (spec = dataclasses stdlib, aucun cycle : spec n'importe rien de src).
from src.missions.spec import ScoringProfile
from src.scorer import rigor as _rigor
from src.scorer import significance as _sig
from src.scorer.cascade_role import score_cascade_role
from src.scorer.coordination import score_coordination_edges
from src.scorer.recidivism import score_recidivism
from src.shared.dossier import COVERAGE_CALLOUT_FR, ScoreResult

log = structlog.get_logger(__name__)

# --------------------------------------------------------------------------- #
# Constantes de contrat (couleurs + libellés repris de l'échantillon JSON).   #
# --------------------------------------------------------------------------- #
# Couleurs hex EXACTES de _channel_queue_sample.json (par famille a–e).
FAMILY_COLORS: dict[str, str] = {
    "a": "#3B82F6",  # claim_proximity
    "b": "#F0B429",  # cascade_role
    "c": "#22c55e",  # coordination
    "d": "#ef4444",  # recidivism
    "e": "#a78bfa",  # genai
    # Familles « empreinte Telegram » (mission GAN) — clés telegram_* (verrou de
    # périmètre). Ajoutées ici pour que _na_family / _family_from_result les
    # mettent en forme comme n'importe quelle famille (indexées par clé).
    "telegram_visibility": "#38bdf8",
    "telegram_velocity": "#fb923c",
    "telegram_source_diversity": "#34d399",
    "telegram_disclosure_precision": "#f43f5e",
    "telegram_propagation": "#facc15",
    "telegram_adverse_attention": "#c084fc",
}
FAMILY_LABELS: dict[str, str] = {
    "a": "Proximité revendication",
    "b": "Rôle en cascade",
    "c": "Coordination",
    "d": "Récidivisme inter-épisodes",
    "e": "Probabilité origine IA",
    "telegram_visibility": "Visibilité Telegram",
    "telegram_velocity": "Vélocité Telegram",
    "telegram_source_diversity": "Diversité des sources",
    "telegram_disclosure_precision": "Précision de divulgation (EEFI)",
    "telegram_propagation": "Propagation Telegram",
    "telegram_adverse_attention": "Attention adverse",
}

# Seuil multi-source (base.py / cascade_role.py / etc.) — verrou à >= 2 familles.
GATE_THRESHOLD = 0.3
MIN_FAMILIES_FOR_GATE = 2

# --------------------------------------------------------------------------- #
# Couche infrastructure adverse — modulateur de SÉVÉRITÉ (jamais un filtre).   #
# Graine minimale ; à EXTERNALISER (TODO) vers data/catalogue/. Reprend les    #
# domaines documentés du projet (cf. src/dossier/evidence.py, sample JSON :    #
# réseau Douguine/Geopolitika, Multipolar) + ancres réseau Pravda.             #
# --------------------------------------------------------------------------- #
# TODO(externaliser) : déplacer cette graine vers data/catalogue/adversary_domains.txt
# alimentée par le DFRLab Pravda Dashboard + TGStat
# (docs/method/03-suspicion-score.md §3.8). Conservée
# ici comme constante de module pour rester pure/testable sans I/O fichier.
ADVERSARY_DOMAINS: frozenset[str] = frozenset(
    {
        # Réseau eurasianiste Douguine / Geopolitika (evidence.py, sample JSON)
        "geopolitika.ru",
        "katehon.com",
        "multipolarpress.com",
        "4pt.su",
        # Réseau Pravda / content-laundering aligné RU (DFRLab / CheckFirst)
        "pravda-fr.com",
        "news-pravda.com",
        "pravda.ru",
        # Doppelganger / RRN amplificateurs documentés
        "rrn.media",
        "waronfakes.com",
        "southfront.press",
    }
)

# Bande de « pas de signal » pour la combinaison de Stouffer (défaut D4).
# Une famille dont la p-value unilatérale atteint ce seuil est indiscernable de
# l'absence de signal et sort de la combinaison. Fixé juste sous 1.0 pour que
# l'exclusion soit continue au voisinage de zéro-valeur : la famille (c) tire sa
# pseudo-p de ``1 - value``, donc ce seuil correspond à ``value <= 0.01``.
NO_SIGNAL_PVALUE = 0.99

# Pondération de combinaison des familles déclenchées (base = signaux b/c/d ;
# a/e = 0 en v0). Transparente : chaque part est justifiable (NFR-8). La
# coordination et la récidive (épine dorsale) pèsent autant que le rôle.
BASE_FAMILY_WEIGHTS: dict[str, float] = {
    "a": 0.15,
    "b": 0.30,
    "c": 0.25,
    "d": 0.30,
    "e": 0.15,
}

# Modulateurs de sévérité (montent le score, bornés [0,1], NE FILTRENT JAMAIS).
#   - reforward_suspect : fraction des forwards entrants venant d'origines
#                         à crédibilité « suspect » (relaie de l'adverse).
#   - adversary_domain  : cite des domaines d'infrastructure adverse.
MAX_REFORWARD_BOOST = 0.20  # +20 % max si 100 % des reforwards sont suspects
MAX_ADVERSARY_DOMAIN_BOOST = 0.15  # +15 % max si forte citation adverse
ADVERSARY_DOMAIN_SATURATION = 5  # nb de citations adverses pour saturer le boost
#   - france_targeting  : ciblage thématique France (cross-langue), src/
#                         normalizer/france_targeting.py. Modulateur MONTANT et
#                         BORNÉ. Choix de +20 % (= MAX_REFORWARD_BOOST) : on lui
#                         donne le même plafond que l'épine dorsale reforward —
#                         le ciblage-France est la pertinence-périmètre (§2.1) et
#                         pèse donc autant que le relais d'adverse, sans pour
#                         autant pouvoir DOUBLER un score (plafond cumulé borné).
MAX_FRANCE_TARGETING_BOOST = 0.20  # +20 % max si ciblage France maximal (∈[0,1])

# Âge (jours) au-delà duquel la confiance d'un canal est « dégradée / périmée ».
STALE_DAYS = 14

# Profil de scoring PAR DÉFAUT = mission russosphère = constantes historiques
# ci-dessus. Utilisé quand ``profile=None`` -> chemin IDENTIQUE (zéro-régression,
# golden test). Les autres missions (GAN…) passent leur propre ScoringProfile.
# IMPORTANT : ``family_weights`` ordonné a/b/c/d/e (stabilité du bundle — R3).
_DEFAULT_PROFILE = ScoringProfile(
    family_weights=BASE_FAMILY_WEIGHTS,
    active_families=frozenset({"b", "c", "d"}),  # a/e = N/A en v0
    gate_threshold=GATE_THRESHOLD,
    min_families_for_gate=MIN_FAMILIES_FOR_GATE,
    max_reforward_boost=MAX_REFORWARD_BOOST,
    max_adversary_domain_boost=MAX_ADVERSARY_DOMAIN_BOOST,
    adversary_domain_saturation=ADVERSARY_DOMAIN_SATURATION,
    max_targeting_boost=MAX_FRANCE_TARGETING_BOOST,
    stale_days=STALE_DAYS,
    relevance_signal="france_targeting",
    credibility_prior_enabled=True,
    adversary_domains=ADVERSARY_DOMAINS,
)


# --------------------------------------------------------------------------- #
# Projection FORWARD : MultiDiGraph multiplex -> DiGraph de forward.           #
# --------------------------------------------------------------------------- #
def forward_digraph(multi: nx.MultiDiGraph) -> nx.DiGraph:
    """Projette les arêtes FORWARD du multiplex en un ``DiGraph`` de forward.

    - Ne garde que les nœuds CANAL (``kind != "domain"``) ; les nœuds domaine
      (cibles de CITES_DOMAIN) sont écartés.
    - Ne garde que les arêtes ``edge_type == "FORWARD"`` (famille propagation),
      orientation ORIGIN -> RELAYER (cf. edges.py — confirmé).
    - Reporte ``count`` ; **mappe ``delay_seconds`` (multiplex) ->
      ``min_delay_s`` (attendu par cascade_role)**. Plusieurs arêtes FORWARD
      parallèles (ne devrait pas arriver vu l'unicité (src,dst,type) côté DB)
      sont agrégées : ``count`` sommé, ``min_delay_s`` = min.
    - Préserve les attributs de nœud canal (username/title/fr_score/
      credibility_prior/engagement/member_count) pour le scoring aval.

    Fonction PURE (pas de DB). Renvoie un ``DiGraph`` directement consommable
    par ``score_cascade_role`` et ``score_recidivism`` sans modification.
    """
    g = nx.DiGraph()

    # 1) Nœuds canal (on exclut les domaines).
    for n, data in multi.nodes(data=True):
        if data.get("kind") == "domain":
            continue
        g.add_node(n, **{k: v for k, v in data.items()})

    # 2) Arêtes FORWARD agrégées (origin -> relayer).
    for u, v, key, data in multi.edges(keys=True, data=True):
        if data.get("edge_type", key) != "FORWARD":
            continue
        if u == v:
            continue  # self-loop exclu (cohérent avec edges.py / loader.to_igraph)
        # Sécurité : une extrémité domaine n'a rien à faire dans un FORWARD.
        if u not in g or v not in g:
            # Un canal source/cible non catalogué peut manquer ses features ;
            # on l'ajoute en nœud minimal (cohérent avec build_graph du loader).
            for endpoint in (u, v):
                if endpoint not in g and multi.nodes.get(endpoint, {}).get("kind") != "domain":
                    g.add_node(endpoint, **multi.nodes.get(endpoint, {}))
            if u not in g or v not in g:
                continue  # une extrémité est un domaine -> on ignore l'arête

        count = int(data.get("count") or 0)
        delay = data.get("delay_seconds")
        if g.has_edge(u, v):
            ed = g.edges[u, v]
            ed["count"] = int(ed.get("count", 0)) + count
            if delay is not None:
                cur = ed.get("min_delay_s")
                ed["min_delay_s"] = int(delay) if cur is None else min(int(cur), int(delay))
        else:
            g.add_edge(
                u,
                v,
                count=count,
                # MAPPING delay_seconds -> min_delay_s (attendu par cascade_role).
                min_delay_s=int(delay) if delay is not None else 0,
            )

    return g


# --------------------------------------------------------------------------- #
# Modulateurs de SÉVÉRITÉ (jamais des filtres). MÉTA-CONTRAINTE 1.             #
# --------------------------------------------------------------------------- #
def reforward_from(fwd: nx.DiGraph) -> dict[int, dict[str, float]]:
    """Provenance des forwards ENTRANTS de chaque canal-RELAYEUR, par crédibilité.

    Pour chaque canal en tant que RELAYEUR, on classe ses arêtes FORWARD
    ENTRANTES (origin -> ce canal) selon le ``credibility_prior`` de l'ORIGINE,
    pondéré par ``count``, en proportions ``{suspect, legit, other}`` sommant à 1
    (ou tout à 0 si aucun forward entrant).

    Le loader ne fournit que {suspect, other} (credibility_prior). « legit » est
    une catégorie réservée (origine explicitement marquée legit) ; faute de
    signal bon marché, elle reste à 0 et le poids non-suspect tombe dans
    « other » — documenté, pas un défaut.

    Une forte fraction ``suspect`` => relaie surtout de l'adverse => MONTE la
    sévérité (lecture aval). Ce n'est JAMAIS un filtre.
    """
    out: dict[int, dict[str, float]] = {}
    for relayer in fwd.nodes:
        buckets = {"suspect": 0.0, "legit": 0.0, "other": 0.0}
        total = 0.0
        for origin, _r, data in fwd.in_edges(relayer, data=True):
            w = float(data.get("count") or 0) or 1.0
            prior = fwd.nodes.get(origin, {}).get("credibility_prior", "other")
            if prior == "suspect":
                buckets["suspect"] += w
            elif prior == "legit":
                buckets["legit"] += w
            else:
                buckets["other"] += w
            total += w
        if total > 0:
            out[relayer] = {k: round(v / total, 6) for k, v in buckets.items()}
        else:
            out[relayer] = {"suspect": 0.0, "legit": 0.0, "other": 0.0}
    return out


def adversary_domain_citations(
    multi: nx.MultiDiGraph,
    *,
    adversary_domains: frozenset[str] = ADVERSARY_DOMAINS,
) -> dict[int, dict[str, Any]]:
    """Compte les arêtes CITES_DOMAIN d'un canal vers des domaines adverses.

    Renvoie ``{channel_id: {"count": <citations adverses>, "domains": [...]}}``.
    Citer une infrastructure adverse documentée MONTE la sévérité (jamais un
    filtre). Le matching domaine est exact + suffixe (sous-domaines).
    """
    adv = {d.lower() for d in adversary_domains}

    def _is_adversary(domain: str) -> bool:
        d = (domain or "").lower()
        if d in adv:
            return True
        return any(d.endswith("." + a) for a in adv)

    out: dict[int, dict[str, Any]] = {}
    for u, v, key, data in multi.edges(keys=True, data=True):
        if data.get("edge_type", key) != "CITES_DOMAIN":
            continue
        if multi.nodes.get(v, {}).get("kind") != "domain":
            continue
        if not isinstance(v, str) or not _is_adversary(v):
            continue
        rec = out.setdefault(u, {"count": 0, "domains": set()})
        rec["count"] += int(data.get("count") or 1)
        rec["domains"].add(v)
    # Domaines -> liste triée pour sérialisation stable.
    return {
        cid: {"count": r["count"], "domains": sorted(r["domains"])}
        for cid, r in out.items()
    }


def _clamp01(x: float) -> float:
    """Borne dans [0, 1] (france_targeting est censé ∈ [0,1] mais on défend)."""
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _severity_modulation(
    reforward: dict[str, float],
    adversary: dict[str, Any] | None,
    france_targeting: float | None = None,
    *,
    profile: ScoringProfile | None = None,
) -> tuple[float, dict[str, Any]]:
    """Facteur multiplicatif de sévérité dans [1, 1+max_boost], + détail.

    Module VERS LE HAUT uniquement (>= 1.0), borné. Jamais < 1.0 : aucun canal
    n'est rétrogradé/filtré par ces signaux (MÉTA-CONTRAINTE 1).

    Trois termes montants additifs :
      * ``reforward_boost``   — relaie surtout de l'adverse (épine dorsale d) ;
      * ``adversary_boost``   — cite l'infrastructure adverse documentée ;
      * ``france_boost``      — ciblage thématique France cross-langue (§2.1).

    ``france_targeting`` ∈ [0,1] (None -> 0.0). Comme tous les boosts, il MONTE
    la sévérité sans jamais filtrer/exclure : un canal non-ciblant-France reste
    dans la file (sévérité plus basse seulement).
    """
    p = profile or _DEFAULT_PROFILE

    suspect_frac = float(reforward.get("suspect", 0.0))
    reforward_boost = p.max_reforward_boost * suspect_frac

    adv_count = int(adversary["count"]) if adversary else 0
    adv_norm = min(1.0, adv_count / p.adversary_domain_saturation) if adv_count else 0.0
    adversary_boost = p.max_adversary_domain_boost * adv_norm

    ft = _clamp01(float(france_targeting or 0.0))
    france_boost = p.max_targeting_boost * ft

    factor = 1.0 + reforward_boost + adversary_boost + france_boost
    detail = {
        "reforward_suspect_frac": round(suspect_frac, 6),
        "reforward_boost": round(reforward_boost, 6),
        "adversary_domain_citations": adv_count,
        "adversary_domains": (adversary["domains"] if adversary else []),
        "adversary_boost": round(adversary_boost, 6),
        "france_targeting": round(ft, 6) if france_targeting is not None else None,
        "france_boost": round(france_boost, 6),
        "factor": round(factor, 6),
    }
    return factor, detail


# --------------------------------------------------------------------------- #
# Helpers de mise en forme (familles a–e -> objets du contrat JSON).          #
# --------------------------------------------------------------------------- #
def _round(x: float | None, nd: int = 4) -> float:
    return round(float(x or 0.0), nd)


def _na_family(letter: str, status: str = "N/A (v0)") -> dict[str, Any]:
    """Objet famille « non applicable » (stubs a/e en v0)."""
    return {
        "n": FAMILY_LABELS[letter],
        "v": 0.0,
        "lo": 0.0,
        "hi": 0.0,
        "c": FAMILY_COLORS[letter],
        "na": True,
        "ev": [["statut", status]],
    }


def _family_from_result(
    letter: str,
    res: ScoreResult | None,
    *,
    ev: list[list[Any]],
    label: str | None = None,
) -> dict[str, Any]:
    """Convertit un ``ScoreResult`` en objet famille du contrat JSON."""
    if res is None:
        return _na_family(letter)
    obj: dict[str, Any] = {
        "n": FAMILY_LABELS[letter],
        "v": _round(res.value),
        "lo": _round(res.confidence_low),
        "hi": _round(res.confidence_high),
        "c": FAMILY_COLORS[letter],
        "ev": ev,
    }
    if label is not None:
        obj["label"] = label
    return obj


def _cascade_evidence(res: ScoreResult) -> list[list[Any]]:
    e = res.evidence
    return [
        ["archétype", e.get("archetype")],
        ["Bridge Score brut", _round(e.get("bridge_raw"), 4)],
        ["in-degree (origine)", _round(e.get("in_degree_centrality"), 4)],
        ["eigenvector", _round(e.get("eigenvector_centrality"), 4)],
        ["clustering coeff", _round(e.get("clustering_coefficient"), 4)],
        ["forwards émis (out_weight)", _round(e.get("out_weight"), 0)],
        ["relayeurs distincts", e.get("out_degree")],
    ]


def _coordination_evidence(res: ScoreResult) -> list[list[Any]]:
    e = res.evidence
    ev: list[list[Any]] = [
        ["types de coordination", ", ".join(e.get("coordination_types", [])) or "—"],
        ["types distincts", e.get("distinct_type_count", 0)],
        ["renfort >=2 types", e.get("multi_type_reinforced", False)],
        ["resserrement Δt max", _round(e.get("tightness_max"), 4)],
        ["pairs co-coordonnés", e.get("coforward_partners", 0)],
    ]
    for t, d in (e.get("per_type") or {}).items():
        ev.append([f"{t} (pairs · Δt min s)", f"{d.get('pairs')} · {d.get('min_dt_seconds')}"])
    return ev


def _recidivism_evidence(res: ScoreResult) -> list[list[Any]]:
    e = res.evidence
    return [
        ["forward-influence", _round(e.get("forward_influence"), 2)],
        ["relayeurs distincts", e.get("source_recurrence")],
        ["forward-influence (norm.)", _round(e.get("forward_influence_norm"), 4)],
    ]


def _generic_evidence(res: ScoreResult | None) -> list[list[Any]]:
    """Évidence générique (familles telegram_*) : aplatit ``res.evidence`` en
    paires ``[clé, valeur]`` pour le contrat JSON. ``None`` -> N/A."""
    if res is None:
        return [["statut", "N/A"]]
    return [[k, v] for k, v in res.evidence.items()]


# --------------------------------------------------------------------------- #
# Combinaison transparente -> suspicion + bande de confiance.                 #
# --------------------------------------------------------------------------- #
def _family_triggered(letter: str, res: ScoreResult | None) -> bool:
    """Une famille est-elle EFFECTIVEMENT déclenchée (pour combinaison/verrou) ?

    Garde-fou ``cascade_role`` : un canal ISOLÉ (aucune arête) reçoit un
    ``bridge_norm`` dégénéré de 1.0 (artefact de normalisation à un seul nœud)
    sans avoir AUCUN rôle de cascade (``archetype is None``). Un tel canal n'a
    pas de rôle structurel -> on ne le compte JAMAIS comme déclenché. Toutes les
    autres familles utilisent ``res.triggered`` tel quel.
    """
    if res is None or not res.triggered:
        return False
    if letter == "b" and res.evidence.get("archetype") is None:
        return False
    return True


def _family_pvalue(letter: str, res: ScoreResult) -> float:
    """p-value unilatérale d'une famille pour la combinaison de Stouffer.

    Familles rigoureuses (b/c/d) : ``evidence["p"]`` (modèle nul / référence).
    Familles sans modèle nul (telegram_*, ``a`` injecté) : fallback TRANSPARENT
    ``p = 1 - value`` (documenté ; itération suivante = nul dédié).
    """
    pv = res.evidence.get("p")
    if isinstance(pv, (int, float)):
        return max(1e-12, min(1.0, float(pv)))
    return max(1e-12, min(1.0, 1.0 - float(res.value)))


def _enrich_significance(res: ScoreResult | None, fsig) -> ScoreResult | None:
    """Remplace value/bandes/triggered d'une famille par sa significativité rigoureuse.

    ``value = 1 - p`` (significativité), ``confidence_low/high`` = IC bootstrap mappé
    en significativité, ``triggered = p < alpha`` ; l'évidence d'origine (bridge_raw,
    archétype, jaccard…) est CONSERVÉE et enrichie de ``observed/z/p/ci/null_*``.
    ``fsig is None`` (ex. famille N/A) ⇒ résultat inchangé.
    """
    if res is None or fsig is None:
        return res
    return ScoreResult(
        family=res.family,
        value=fsig.value,
        confidence_low=fsig.ci_low,
        confidence_high=fsig.ci_high,
        triggered=fsig.triggered,
        evidence={**res.evidence, **fsig.evidence},
    )


def _combine_suspicion(
    families: dict[str, ScoreResult | None],
    factor: float,
    *,
    profile: ScoringProfile | None = None,
) -> tuple[float, float, float, dict[str, Any]]:
    """Combine les familles déclenchées en une suspicion explicable dans [0,1].

    base = somme pondérée (BASE_FAMILY_WEIGHTS) des valeurs de familles
    DÉCLENCHÉES, renormalisée par la somme des poids des familles présentes
    (déclenchées ou non, stub a/e exclus s'ils sont N/A). On module ensuite par
    le facteur de sévérité (>= 1), puis on borne à [0,1].

    Chaque contribution est conservée dans ``components`` (NFR-8 : chaque part
    du score est justifiable). Renvoie (v, lo, hi, components).
    """
    p = profile or _DEFAULT_PROFILE
    components: dict[str, Any] = {}

    # Combinaison de STOUFFER pondérée des p-values par-famille (scoring rigoureux).
    # base = 1 - p_combined ; remplace la moyenne pondérée heuristique. Les bandes
    # proviennent des IC bootstrap par-famille (mappés en significativité), combinés
    # par le même Stouffer sur les bornes. La sévérité (>=1) module ensuite la base.
    weights: list[float] = []
    pvals: list[float] = []
    p_lo: list[float] = []  # p-values aux bornes BASSES de significativité (1-ci_high)
    p_hi: list[float] = []  # p-values aux bornes HAUTES (1-ci_low)
    for letter, res in families.items():
        w = p.family_weights.get(letter, 0.0)
        if res is None:
            components[letter] = {"weight": w, "value": None, "contribution": 0.0, "na": True}
            continue
        pv = _family_pvalue(letter, res)
        triggered = _family_triggered(letter, res)
        components[letter] = {
            "weight": w,
            "value": _round(res.value),
            "p": _round(pv),
            "triggered": triggered,
        }
        # NEUTRALITÉ : une famille SANS signal ne doit PAS être traitée comme une
        # preuve CONTRE (z→-∞ écraserait la combinaison). Elle est EXCLUE de
        # Stouffer : la suspicion reflète la force des familles qui portent un
        # signal.
        #
        # DÉFAUT D4 (corrigé 2026-09) — le test était ``pv >= 1.0``, une égalité
        # exacte. Comme la pseudo-p de la famille (c) vaut ``1 - value``, un
        # canal à ``value == 0.0`` donnait p == 1.0 et était exclu, tandis qu'un
        # canal à ``value == 1e-4`` donnait p == 0.9999, donc z ≈ -3.7, ce qui
        # écrasait le score combiné. Une variation infinitésimale de l'entrée
        # produisait un saut de rang : exactement ce que l'exclusion cherchait à
        # éviter. Le seuil est désormais une BANDE : toute famille dont la
        # p-value est indiscernable de « aucun signal » est exclue, ce qui rend
        # la frontière continue.
        # Voir docs/limitations.md D4.
        if pv >= NO_SIGNAL_PVALUE:
            components[letter]["combined_in"] = False
            continue
        components[letter]["combined_in"] = True
        weights.append(w)
        pvals.append(pv)
        # res.confidence_* sont en espace significativité (1-p) → p de borne = 1 - sig.
        p_hi.append(max(1e-12, min(1.0, 1.0 - res.confidence_low)))
        p_lo.append(max(1e-12, min(1.0, 1.0 - res.confidence_high)))

    if weights:
        _, p_combined = _sig.stouffer_combine(pvals, weights)
        _, p_comb_lo = _sig.stouffer_combine(p_hi, weights)  # bornes hautes p → base basse
        _, p_comb_hi = _sig.stouffer_combine(p_lo, weights)
    else:
        p_combined = p_comb_lo = p_comb_hi = 1.0

    base = max(0.0, min(1.0, 1.0 - p_combined))
    base_lo = max(0.0, min(1.0, 1.0 - p_comb_lo))
    base_hi = max(0.0, min(1.0, 1.0 - p_comb_hi))

    v = max(0.0, min(1.0, base * factor))
    lo = max(0.0, min(1.0, base_lo * factor))
    hi = max(0.0, min(1.0, base_hi * factor))
    lo = min(lo, v)
    hi = max(hi, v)

    components["_base"] = _round(base)
    components["_p_combined"] = _round(p_combined)
    components["_severity_factor"] = round(factor, 6)
    components["_combined"] = _round(v)
    return _round(v), _round(lo), _round(hi), components


def _gate(
    families: dict[str, ScoreResult | None],
    *,
    profile: ScoringProfile | None = None,
) -> dict[str, Any]:
    """Verrou multi-source (base.py) : >= N familles DISTINCTES déclenchées.

    Renvoie ``{met, families, detail}`` où ``families`` = nb de familles
    déclenchées et ``detail`` énumère lesquelles (lettres b/c/d/…).
    """
    p = profile or _DEFAULT_PROFILE
    triggered = [
        letter for letter, res in families.items() if _family_triggered(letter, res)
    ]
    n = len(triggered)
    met = n >= p.min_families_for_gate
    if n == 0:
        detail = "aucune famille déclenchée"
    else:
        joined = "/".join(triggered)
        if met:
            detail = f"{n} signaux · {n} familles ({joined})"
        else:
            detail = f"{n} famille ({joined}) — verrou multi-source non franchi"
    # gate_families : MÊME ensemble que ``families`` (le compte) compte — surfacé
    # par noms pour l'audit/traçabilité. Persisté en text[] (alembic 0008).
    return {"met": met, "families": n, "gate_families": triggered, "detail": detail}


def _confidence(
    meta: Mapping[str, Any] | None,
    *,
    profile: ScoringProfile | None = None,
) -> dict[str, Any]:
    """Bande de confiance/fraîcheur d'un canal, dérivée de ``last_polled_at``.

    - pas de méta / pas de date          -> level "ok", reason "ok"
    - polled récemment (< stale_days j)  -> level "ok"
    - polled il y a >= stale_days jours  -> level "degraded", reason "stale"
    L'âge est exposé en ``age_days`` quand calculable.
    """
    p = profile or _DEFAULT_PROFILE
    if not meta:
        return {"level": "ok", "reason": "ok"}
    last = meta.get("last_polled_at")
    if last is None:
        return {"level": "ok", "reason": "ok"}
    try:
        from datetime import datetime, timezone

        if isinstance(last, str):
            last_dt = datetime.fromisoformat(last)
        else:
            last_dt = last
        now = datetime.now(timezone.utc)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        age_days = max(0, int((now - last_dt).total_seconds() // 86400))
    except (ValueError, TypeError):
        # Date illisible/corrompue : conservateur -> « dégradé » plutôt que de
        # faire passer une date invalide pour « fraîche ».
        return {"level": "degraded", "reason": "unknown_polled_at"}
    if age_days >= p.stale_days:
        return {"level": "degraded", "reason": "stale", "age_days": age_days}
    return {"level": "ok", "reason": "ok", "age_days": age_days}


# --------------------------------------------------------------------------- #
# Archétypes (helper exposé pour l'endpoint voisinage).                       #
# --------------------------------------------------------------------------- #
def channel_archetypes(multi: nx.MultiDiGraph) -> dict[int, str]:
    """Map ``channel_id -> archétype`` (depuis la famille (b) sur le forward).

    Helper pour annoter les nœuds du voisinage (endpoint neighborhood). Renvoie
    uniquement les canaux ayant un archétype non nul (rôle dans la cascade).
    """
    fwd = forward_digraph(multi)
    cascade = score_cascade_role(fwd)
    out: dict[int, str] = {}
    for cid, res in cascade.items():
        arch = res.evidence.get("archetype")
        if arch:
            out[cid] = arch
    return out


# --------------------------------------------------------------------------- #
# CŒUR PUR : multiplex -> bloc ``queue`` (contrat JSON).                       #
# --------------------------------------------------------------------------- #
def compute_channel_queue(
    multi: nx.MultiDiGraph,
    channels_meta: Mapping[int, Mapping[str, Any]] | None = None,
    *,
    top_k: int | None = 50,
    claim_proximity: dict[int, float] | None = None,
    france_targeting: dict[int, float] | None = None,
    window_delta_seconds: int = 72 * 3600,
    profile: ScoringProfile | None = None,
    extra_families: dict[str, dict[int, ScoreResult]] | None = None,
) -> dict[str, Any]:
    """Calcule le bloc ``queue`` (sans ``generated_at`` — l'API l'estampille).

    Paramètres
    ----------
    multi            : graphe multiplex (``build_graph`` du loader).
    channels_meta    : ``{channel_id: {... last_polled_at ...}}`` optionnel
                       (fraîcheur). Les attributs de nœud du graphe priment pour
                       username/title/fr_score/credibility_prior.
    top_k            : nb max de canaux affichés (le reste -> ``hidden``).
    claim_proximity  : SEAM v+1 — ``{channel_id: value∈[0,1]}`` famille (a)
                       précalculée (BGE-M3). ``None`` -> (a) reste N/A.
    france_targeting : ``{channel_id: value∈[0,1]}`` ciblage thématique France
                       (≠ fr_score, cross-langue). CÂBLÉ comme modulateur de
                       SÉVÉRITÉ multiplicatif (montant, borné par
                       ``MAX_FRANCE_TARGETING_BOOST`` ; jamais un filtre). Un
                       canal absent de la map (ou la map None) -> france_boost 0.
                       Multiplicatif : n'amplifie qu'un canal DÉJÀ suspect — un
                       canal à base 0 reste à 0 (presse FR légitime non promue).

    Le tri final est par ``suspicion.v`` décroissant ; on tronque à ``top_k``.
    AUCUN filtrage par ``fr_score`` (MÉTA-CONTRAINTE 1).
    """
    meta = channels_meta or {}
    p = profile or _DEFAULT_PROFILE  # défaut = russosphère (chemin identique)
    if top_k is not None:
        top_k = max(0, top_k)  # garde-fou : top_k négatif -> slice Python erroné
    # top_k=None => univers complet, sans troncature (matérialisation build_scores).

    # 1) Projection forward + familles structurelles (b)/(d) sur le forward.
    fwd = forward_digraph(multi)
    cascade = score_cascade_role(fwd)
    recidivism = score_recidivism(fwd)

    # 2) Coordination (c) depuis les arêtes matérialisées du multiplex.
    coordination = score_coordination_edges(
        multi,
        window_delta_seconds=window_delta_seconds,
        coordination_edge_types=COORDINATION_EDGE_TYPES,
    )

    # 2bis) Significativité rigoureuse (modèle nul + bootstrap) pour b/c/d.
    # Calculée UNE fois (ensemble nul partagé b/d). rng seedé ⇒ bundle
    # byte-reproductible. Remplace les valeurs/bandes heuristiques par 1-p / IC.
    rng = _sig.make_rng(p.rng_seed)
    fam_sig = _rigor.compute_family_significance(
        fwd, cascade, recidivism,
        alpha=p.alpha, n_null=p.n_null, n_bootstrap=p.n_bootstrap, rng=rng,
    )

    # 3) Modulateurs de sévérité (jamais des filtres) : reforward + domaines.
    refwd = reforward_from(fwd)
    adv = adversary_domain_citations(multi)

    # 3bis) Familles « empreinte Telegram » (mission GAN) — calculées UNIQUEMENT
    # si la mission les demande (``extra_family_scorers``). Sur le chemin par
    # défaut (russosphère), ``p.extra_family_scorers`` est vide -> bloc inerte ->
    # bundle identique. Les familles de GRAPHE sont calculées ici ; la précision
    # de divulgation (texte) arrive via ``extra_families`` (injectée par l'I/O).
    tele: dict[str, dict[int, ScoreResult]] = {}
    if p.extra_family_scorers:
        from src.scorer.telegram_footprint import (
            score_telegram_adverse_attention,
            score_telegram_propagation,
            score_telegram_source_diversity,
            score_telegram_velocity,
            score_telegram_visibility,
        )

        want = set(p.extra_family_scorers)
        if "telegram_visibility" in want:
            tele["telegram_visibility"] = score_telegram_visibility(fwd)
        if "telegram_propagation" in want:
            tele["telegram_propagation"] = score_telegram_propagation(fwd)
        if "telegram_source_diversity" in want:
            tele["telegram_source_diversity"] = score_telegram_source_diversity(fwd)
        if "telegram_velocity" in want:
            tele["telegram_velocity"] = score_telegram_velocity(fwd)
        if "telegram_adverse_attention" in want:
            # Canaux « alignés adverse » = ceux qui citent un domaine adverse
            # documenté (proxy russosphère). L'attention adverse d'un canal = part
            # de ses forwards entrants venant de ces origines.
            tele["telegram_adverse_attention"] = score_telegram_adverse_attention(
                fwd, set(adv.keys())
            )
    # Précision de divulgation (texte) + tout autre extra injecté par l'I/O.
    if extra_families:
        for fam_key, fam_map in extra_families.items():
            tele[fam_key] = fam_map

    # 4) Univers des canaux à scorer = nœuds CANAL du multiplex.
    channel_nodes = [
        n for n, d in multi.nodes(data=True) if d.get("kind") != "domain"
    ]

    rows: list[dict[str, Any]] = []
    for cid in channel_nodes:
        node = multi.nodes[cid]

        # --- familles a–e -------------------------------------------------- #
        # (b) cascade et (d) récidive : valeurs/bandes/déclenchement RIGOUREUX
        # (modèle nul + bootstrap). (c) coordination : composite principiel
        # conservé (contribue p=1-value à Stouffer via _family_pvalue).
        cas = _enrich_significance(cascade.get(cid), fam_sig["b"].get(cid))
        coo = coordination.get(cid)
        rec = _enrich_significance(recidivism.get(cid), fam_sig["d"].get(cid))

        # (a) claim proximity : injecté si fourni, sinon N/A v0.
        if claim_proximity is not None and cid in claim_proximity:
            cp_val = max(0.0, min(1.0, float(claim_proximity[cid])))
            a_res: ScoreResult | None = ScoreResult(
                family="claim_proximity",
                value=cp_val,
                confidence_low=max(0.0, cp_val - 0.15),
                confidence_high=min(1.0, cp_val + 0.15),
                triggered=cp_val >= GATE_THRESHOLD,
                evidence={"source": "precomputed", "value": cp_val},
            )
            a_obj = _family_from_result("a", a_res, ev=[["proximité", _round(cp_val)]])
        else:
            a_res = None
            a_obj = _na_family("a", "N/A — pas de registre d'épisodes (v0)")

        # (e) GenAI : stub v0 (seam pour AASIST/GenConViT/Binoculars).
        e_res: ScoreResult | None = None
        e_obj = _na_family("e", "N/A — détecteur GenAI non câblé (v0)")

        b_obj = _family_from_result(
            "b",
            cas,
            ev=_cascade_evidence(cas) if cas else [["statut", "isolé"]],
            label=(cas.evidence.get("archetype") if cas else None),
        )
        c_obj = _family_from_result(
            "c",
            coo,
            ev=_coordination_evidence(coo) if coo else [["statut", "aucune arête de coordination"]],
        )
        d_obj = _family_from_result(
            "d",
            rec,
            ev=_recidivism_evidence(rec) if rec else [["statut", "aucun forward sortant"]],
        )

        families: dict[str, ScoreResult | None] = {
            "a": a_res,
            "b": cas,
            "c": coo,
            "d": rec,
            "e": e_res,
        }

        # Familles supplémentaires de la mission (GAN telegram_*), si demandées.
        # Chemin par défaut : extra_family_scorers vide -> boucle inerte.
        extra_objs: dict[str, dict[str, Any]] = {}
        for fam_key in p.extra_family_scorers:
            fam_res = tele.get(fam_key, {}).get(cid)
            families[fam_key] = fam_res
            extra_objs[fam_key] = _family_from_result(
                fam_key, fam_res, ev=_generic_evidence(fam_res)
            )

        # --- modulation de sévérité (montante, bornée) --------------------- #
        rf = refwd.get(cid, {"suspect": 0.0, "legit": 0.0, "other": 0.0})
        ft_val = france_targeting.get(cid) if france_targeting else None
        factor, sev_detail = _severity_modulation(rf, adv.get(cid), ft_val, profile=p)

        # --- suspicion explicable ----------------------------------------- #
        v, lo, hi, components = _combine_suspicion(families, factor, profile=p)

        gate = _gate(families, profile=p)
        # Tier : T2 si verrou franchi (récurrence comportementale), sinon T1.
        # JAMAIS T3 (hors périmètre — docs/method/07-tiers-and-governance.md §7.1).
        tier = "T2" if gate["met"] else "T1"

        archetype = cas.evidence.get("archetype") if cas else None
        cmeta = meta.get(cid)
        conf = _confidence(cmeta, profile=p)

        # Évidence de modulation conservée dans (b/d) via components + sev_detail.
        components["_severity_detail"] = sev_detail

        rows.append(
            {
                "channel_id": cid,
                "username": (
                    ("@" + node.get("username")) if node.get("username") else None
                ),
                "title": node.get("title") or "",
                "suspicion": {"v": v, "lo": lo, "hi": hi},
                "archetype": archetype,
                "credibility_prior": node.get("credibility_prior", "other"),
                "fr_score": node.get("fr_score"),
                # Ciblage thématique France (modulateur de sévérité, jamais un
                # filtre). Signal d'AFFICHAGE/sévérité — None si non fourni.
                "france_targeting": ft_val,
                "reforward_from": {
                    "suspect": rf.get("suspect", 0.0),
                    "legit": rf.get("legit", 0.0),
                    "other": rf.get("other", 0.0),
                },
                "scores": {
                    "a": a_obj,
                    "b": b_obj,
                    "c": c_obj,
                    "d": d_obj,
                    "e": e_obj,
                    # Familles mission (GAN telegram_*) — vide sur le chemin défaut.
                    **extra_objs,
                },
                "confidence": conf,
                "gate": gate,
                "tier": tier,
                # Détail de combinaison (NFR-8 : chaque part justifiable).
                "_components": components,
            }
        )

    # 4bis) Correction multi-tests Benjamini-Hochberg sur l'ENSEMBLE des canaux
    #       (p_combined de Stouffer) : définit l'ensemble `flagged` (FDR <= alpha),
    #       le signal rigoureux « à examiner ». q_value = p ajustée BH. Additif :
    #       n'altère ni suspicion.v, ni gate, ni tier.
    if rows:
        order = sorted(range(len(rows)), key=lambda i: rows[i]["channel_id"])
        pcs = [rows[i]["_components"].get("_p_combined", 1.0) for i in order]
        rejected, qvals = _sig.benjamini_hochberg(pcs, alpha=p.alpha)
        for slot, i in enumerate(order):
            r = rows[i]
            r["p_combined"] = rows[i]["_components"].get("_p_combined", 1.0)
            r["q_value"] = qvals[slot]
            r["flagged"] = bool(rejected[slot])
            r["_components"]["_q_value"] = qvals[slot]
            r["_components"]["_flagged"] = bool(rejected[slot])

    # 5) Tri par suspicion décroissante (PAS de filtre fr_score). Départage
    #    déterministe par channel_id pour la stabilité.
    rows.sort(key=lambda r: (-r["suspicion"]["v"], r["channel_id"]))

    total = len(rows)
    shown = rows if top_k is None else rows[:top_k]
    hidden = max(0, total - len(shown))

    # 6) Ratio symétrique (artefact de transparence EIP) : part de la POPULATION
    #    COMPLÈTE scorée liée à une infrastructure adverse (prior suspect OU
    #    citation de domaine adverse). Calculé sur `rows` (et non `shown`) pour
    #    être INDÉPENDANT du paramètre d'affichage `top_k` — un artefact de
    #    transparence qui varierait avec la pagination serait trompeur.
    #    adversary_infra module la SÉVÉRITÉ, pas l'inclusion (MÉTA-CONTRAINTE 1).
    if rows:
        adv_infra = sum(
            1
            for r in rows
            if r["credibility_prior"] == "suspect" or r["channel_id"] in adv
        )
        adversary_infra = round(adv_infra / len(rows), 4)
    else:
        adversary_infra = 0.0
    organic_fr = round(1.0 - adversary_infra, 4)

    return {
        "coverage_callout": COVERAGE_CALLOUT_FR,
        "top_k": top_k,
        "hidden": hidden,
        "symmetric_ratio": {
            "adversary_infra": adversary_infra,
            "organic_fr": organic_fr,
            "note": (
                "Part liée à une infrastructure adverse documentée vs. organique "
                "français. L'adversaire module la sévérité, pas l'inclusion "
                "(MÉTA-CONTRAINTE 1)."
            ),
        },
        "channels": shown,
    }


# --------------------------------------------------------------------------- #
# Enveloppes I/O (fines) — seul accès PostgreSQL (lecture seule).             #
# --------------------------------------------------------------------------- #
# Nom de la mission par défaut (= src.missions.registry.DEFAULT_MISSION). Codé en
# dur ici pour éviter d'importer le registre (qui importe paresseusement les
# packages de mission — dont celui-ci) ; gardé en phase par un test.
_DEFAULT_MISSION_NAME = "russosphere"


async def _resolve_handles_to_ids(
    conn, handles: tuple[str, ...]
) -> list[int]:
    """Résout handles (@...) → channel_ids.

    Args:
        handles: tuple de usernames (avec ou sans @)

    Returns:
        list[int] de channel_ids trouvés (peut être vide)
    """
    if not handles:
        return []
    # Strip @ si présent
    clean_handles = [h.lstrip("@") for h in handles]
    rows = await conn.fetch(
        "SELECT channel_id FROM channels WHERE username = ANY($1)",
        clean_handles,
    )
    return [r["channel_id"] for r in rows]


async def _fetch_messages_by_channel(
    conn, *, sample_limit: int = 500
) -> dict[int, list[tuple[str | None, str | None]]]:
    """Lit ``{channel_id: [(text, language), …]}`` (≤ sample_limit récents/canal).

    Pour la famille ``telegram_disclosure_precision`` (rubrique EEFI sur le texte).
    Une seule requête (pas de N+1) + cap recency en Python (cf. targeting).
    """
    rows = await conn.fetch(
        """
        SELECT channel_id, text, language
        FROM messages
        WHERE text IS NOT NULL
        ORDER BY channel_id, timestamp DESC NULLS LAST
        """
    )
    out: dict[int, list[tuple[str | None, str | None]]] = {}
    for r in rows:
        bucket = out.setdefault(r["channel_id"], [])
        if len(bucket) < sample_limit:
            bucket.append((r["text"], r["language"]))
    return out


async def _build_channel_queue_live(
    conn, *, top_k: int | None = 50, mission=None, compute_embeddings: bool = False
) -> dict[str, Any]:
    """Recalcul LIVE complet de la file (repli + utilisé par build_scores).

    ``mission`` (``MissionDefinition``) ``None`` => mission par défaut
    (russosphère) ⇒ chemin IDENTIQUE (golden). Sinon, on applique le
    ``ScoringProfile`` de la mission : prior mission-aware (R1), carte de
    pertinence via ``mission.relevance_scorer`` (modulateur de sévérité), et
    familles ``telegram_*`` (la précision-de-divulgation est calculée sur le
    texte via la rubrique EEFI injectée). Tout échec d'un signal DÉGRADE
    proprement (modulateur jamais bloquant). ``top_k=None`` => univers complet.

    ``compute_embeddings=True`` => calcule famille (f) sémantique via embeddings.
    Coût : ~30s/1000 canaux (cache hit) + inférence locale (gratuit). Optionnel.
    """
    from src.graph.loader import make_prior_policy

    profile = mission.scoring if mission is not None else None

    edge_rows = await fetch_edge_rows(conn)
    channel_rows = await fetch_channel_rows(conn)
    if profile is not None:
        # Le prior s'adosse au catalogue adverse de la mission, jamais à la
        # langue (défaut D1 — docs/limitations.md).
        multi = build_graph(
            edge_rows, channel_rows,
            prior_policy=make_prior_policy(profile.credibility_prior_enabled),
            adversary_domains=profile.adversary_domains or ADVERSARY_DOMAINS,
        )
    else:
        multi = build_graph(
            edge_rows, channel_rows, adversary_domains=ADVERSARY_DOMAINS
        )

    # Méta de fraîcheur : last_polled_at par canal (si la colonne est lue).
    channels_meta: dict[int, dict[str, Any]] = {}
    for c in channel_rows:
        cid = c.get("channel_id")
        if cid is None:
            continue
        if "last_polled_at" in c:
            channels_meta[cid] = {"last_polled_at": c.get("last_polled_at")}

    # Carte de PERTINENCE (modulateur de sévérité). Défaut = ciblage France ;
    # mission = son relevance_scorer (ex. gan_targeting). Import paresseux ;
    # toute défaillance -> None (dégradé MAIS VISIBLE).
    relevance: dict[int, float] | None = None
    try:
        if mission is not None and mission.relevance_scorer is not None:
            relevance = await mission.relevance_scorer(conn)
        else:
            from src.normalizer.france_targeting import (
                score_all_channels_france_targeting,
            )

            relevance = await score_all_channels_france_targeting(conn)
    except Exception as e:  # noqa: BLE001
        log.warning(
            "relevance_targeting_unavailable",
            error=str(e),
            mission=(mission.name if mission is not None else _DEFAULT_MISSION_NAME),
        )
        relevance = None

    # Familles telegram_* basées sur le TEXTE (précision de divulgation EEFI).
    # Les familles de graphe sont calculées dans compute_channel_queue.
    extra_families: dict[str, dict[int, ScoreResult]] | None = None
    if (
        profile is not None
        and profile.disclosure_rubric is not None
        and "telegram_disclosure_precision" in profile.extra_family_scorers
    ):
        try:
            from src.scorer.telegram_footprint import (
                score_telegram_disclosure_precision,
            )

            msgs_by_channel = await _fetch_messages_by_channel(conn)
            extra_families = {
                "telegram_disclosure_precision": score_telegram_disclosure_precision(
                    msgs_by_channel, profile.disclosure_rubric
                )
            }
        except Exception as e:  # noqa: BLE001
            log.warning("disclosure_precision_unavailable", error=str(e))
            extra_families = None

    # Famille (f) embedding semantic coherence (optionnelle, coût inférence locale).
    # ponytail: compute_embeddings=False par défaut — activer dans build_scores.py.
    if compute_embeddings and mission is not None and profile is not None:
        try:
            from src.embed.encoder import Embedder
            from src.scorer.embedding_signals import (
                build_adversary_embeddings,
                build_baseline_embedding,
                compute_channel_embeddings,
                score_embedding_coherence,
            )

            embedder = Embedder()  # lazy import, cache offline
            chan_emb = await compute_channel_embeddings(conn, embedder, sample_size=15)

            # Baseline FR organique (handles → IDs). Si absent, skip famille (f).
            baseline_ids = []
            if profile.embedding_baseline_channels:
                baseline_ids = await _resolve_handles_to_ids(
                    conn, profile.embedding_baseline_channels
                )
            baseline_emb = await build_baseline_embedding(conn, embedder, baseline_ids)

            # Adversary (RT, Sputnik, Geopolitika...).
            adversary_ids = []
            if profile.embedding_adversary_channels:
                adversary_ids = await _resolve_handles_to_ids(
                    conn, profile.embedding_adversary_channels
                )
            adversary_emb = await build_adversary_embeddings(
                conn, embedder, adversary_ids
            )

            family_f = await score_embedding_coherence(
                conn, chan_emb, baseline_emb, adversary_emb
            )
            if extra_families is None:
                extra_families = {}
            extra_families["f"] = family_f

        except Exception as e:  # noqa: BLE001
            log.warning("embedding_coherence_unavailable", error=str(e))
            # Dégradé proprement : famille (f) absente, scoring continue

    return compute_channel_queue(
        multi,
        channels_meta,
        top_k=top_k,
        france_targeting=relevance,
        profile=profile,
        extra_families=extra_families,
    )
