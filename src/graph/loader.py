"""Chargeur du graphe multiplex centré-canal + voisinage ego-graph borné.

Reconstruit **à la demande, en mémoire** (NetworkX) le graphe multiplex
centré-canal défini dans
``_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md``
(§2 modèle, §2.2 nœud canal + features, §2.4 reconstruction PostgreSQL →
igraph/NetworkX à la demande). La source de vérité persistante est la table
``edges`` (alembic 0002) ; les attributs de nœud viennent de ``channels``.

Conception (docs/method/02-graph-model.md — library-first, pas de Neo4j/Kùzu) :

  * **I/O DB séparée des transformations.** ``fetch_edge_rows`` /
    ``fetch_channel_rows`` font le seul accès PostgreSQL (asyncpg, lecture
    seule, cohérent avec ``src/api/main.py``). Tout le reste — construction du
    graphe, voisinage, sérialisation — est une **fonction pure** testable sans
    base (lignes simulées → graphe → voisinage → dict JSON).

  * **Graphe** : ``networkx.MultiDiGraph``. Multiplex natif (plusieurs types
    d'arête entre deux mêmes canaux coexistent, chaque arête porte
    ``edge_type`` + ``family``). Les nœuds **canal** sont des ``int``
    (``channel_id``, stable aux rebrands — graph-model §2.2) ; les nœuds
    **domaine** sont des ``str`` distincts (cible de ``CITES_DOMAIN`` —
    graph-model §2.2 : le domaine est un *type* de nœud, pas une table).

  * **Engagement = poids de NŒUD** (vues/réactions/forwards agrégés par canal),
    jamais une arête (graph-model §2.2). Porté comme attribut de nœud canal.

Aucun appel Telegram. Lecture seule PostgreSQL.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable, Mapping

import networkx as nx

# --------------------------------------------------------------------------- #
# Modèle d'arête — type -> famille (graph-model §2.3 ; UX doc contrat §5).
# --------------------------------------------------------------------------- #
EDGE_FAMILIES: dict[str, str] = {
    "FORWARD": "propagation",
    "MENTIONS": "influence",
    "CITES_DOMAIN": "influence",
    "CO_FORWARD": "coordination",
    "COPYPASTA": "coordination",
    "TEXT_SIM": "coordination",
    "TRANSLATION": "coordination",
    "CO_URL": "coordination",
    "CO_URL_EXACT": "coordination",
    "CO_HASHTAG": "coordination",
    "MEDIA_REUSE": "coordination",
}

# Arêtes ciblant un domaine (nœud string) plutôt qu'un canal (graph-model §2.2).
DOMAIN_EDGE_TYPES: frozenset[str] = frozenset({"CITES_DOMAIN"})

# Arêtes de coordination : non orientées, fenêtrées Δt (graph-model §2.3.2).
COORDINATION_EDGE_TYPES: frozenset[str] = frozenset(
    {"CO_FORWARD", "COPYPASTA", "TEXT_SIM", "TRANSLATION", "CO_URL", "CO_URL_EXACT",
     "CO_HASHTAG", "MEDIA_REUSE"}
)

# Seuil fr_score sous lequel un canal est a priori « suspect » (graph-model
# §3.1 ; tag_france.py / detect_clusters.py). credibility_prior est un a priori
# d'ÉCHANTILLONNAGE, jamais une cible de supervision (graph-model §1.2/§3.1).
SUSPECT_FR_SCORE_MAX = 0.15


# --------------------------------------------------------------------------- #
# I/O DB — seul accès PostgreSQL (asyncpg, lecture seule). Tout le reste est pur.
# --------------------------------------------------------------------------- #
async def fetch_edge_rows(conn) -> list[dict]:
    """Lit toutes les arêtes de la table ``edges`` (toutes familles).

    ``conn`` est une connexion asyncpg (cf. ``src/api/main.py`` ->
    ``app.state.pool.acquire()``). La table peut être **vide** → liste vide →
    graphe vide (cas accepté, graph-model : matérialisation en cours).
    """
    rows = await conn.fetch(
        """
        SELECT src_channel_id, dst_channel_id, dst_domain, edge_type,
               count, weight, delay_seconds, text_sim,
               window_delta_seconds, attrs
        FROM edges
        """
    )
    return [dict(r) for r in rows]


async def fetch_channel_rows(conn) -> list[dict]:
    """Lit les attributs de nœud canal depuis ``channels`` (graph-model §2.2).

    ``engagement`` = vues + réactions + forwards agrégés par canal = **poids de
    nœud** (graph-model §2.2). Les réactions ne sont pas stockées séparément ;
    on agrège views + forwards depuis ``messages`` (proxy d'engagement).
    """
    rows = await conn.fetch(
        """
        SELECT c.channel_id, c.username, c.title, c.member_count,
               (c.extra->>'fr_score')::float AS fr_score,
               COALESCE(e.engagement, 0) AS engagement
        FROM channels c
        LEFT JOIN (
            SELECT channel_id,
                   COALESCE(SUM(views), 0) + COALESCE(SUM(forwards), 0) AS engagement
            FROM messages
            GROUP BY channel_id
        ) e ON e.channel_id = c.channel_id
        """
    )
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Dérivations pures de features de nœud.
# --------------------------------------------------------------------------- #
def credibility_prior(fr_score: float | None) -> str:
    """A priori d'échantillonnage {legit, suspect, other} dérivé du fr_score.

    graph-model §3.1 : ``fr_score < 0.15`` => cluster pro-RU francophone
    (suspect). Un ``fr_score`` élevé n'implique pas « legit » (un canal orienté
    France peut être propagateur) — on renvoie ``other`` quand le signal ne
    tranche pas, ``None`` => ``other``. ``credibility_prior`` n'est JAMAIS la
    cible de supervision (graph-model §1.2).
    """
    if fr_score is None:
        return "other"
    if fr_score < SUSPECT_FR_SCORE_MAX:
        return "suspect"
    return "other"


def make_prior_policy(suspect_threshold: float | None) -> Callable[[float | None], str]:
    """Fabrique la politique de credibility_prior d'une mission (résout R1).

    ``suspect_threshold=0.15`` -> comportement russosphère historique
    (``signal < 0.15`` => « suspect »). ``None`` -> **prior NEUTRE** « other »
    pour toute la mission (cas GAN : aucune présomption de suspicion sur les
    canaux discutant d'un actif ami ; l'attention adverse y est portée par la
    famille ``telegram_adverse_attention``, pas par le prior).
    """
    if suspect_threshold is None:
        return lambda _v: "other"

    def _policy(v: float | None) -> str:
        if v is None:
            return "other"
        return "suspect" if v < suspect_threshold else "other"

    return _policy


def edge_family(edge_type: str) -> str:
    """Famille (propagation / influence / coordination) d'un type d'arête."""
    return EDGE_FAMILIES.get(edge_type, "influence")


# --------------------------------------------------------------------------- #
# Construction du graphe multiplex (PUR : lignes -> MultiDiGraph).
# --------------------------------------------------------------------------- #
def build_graph(
    edge_rows: Iterable[Mapping[str, Any]],
    channel_rows: Iterable[Mapping[str, Any]] | None = None,
    *,
    prior_policy: Callable[[float | None], str] | None = None,
) -> nx.MultiDiGraph:
    """Construit le graphe multiplex centré-canal en mémoire.

    Nœuds canal = ``int`` (channel_id) ; nœuds domaine = ``str``. Plusieurs
    arêtes de types différents entre deux mêmes canaux coexistent (multiplex).
    Engagement / fr_score / credibility_prior sont des **attributs de nœud**.

    Fonction pure : ne touche pas la base. ``edge_rows`` et ``channel_rows``
    sont des séquences de mappings (dicts ou Record asyncpg).
    """
    g = nx.MultiDiGraph()
    # Politique de prior par mission (défaut = credibility_prior historique).
    policy = prior_policy or credibility_prior

    # 1) Nœuds canal + attributs (graph-model §2.2). Posés d'abord pour que les
    #    canaux connus aient leurs features même s'ils n'ont aucune arête.
    for c in channel_rows or ():
        cid = c["channel_id"]
        fr = c.get("fr_score")
        g.add_node(
            cid,
            kind="channel",
            username=c.get("username") or "",
            title=c.get("title") or "",
            member_count=c.get("member_count"),
            fr_score=fr,
            credibility_prior=policy(fr),
            engagement=int(c.get("engagement") or 0),
        )

    # 2) Arêtes. Pour CITES_DOMAIN, la cible est un nœud domaine (string).
    for e in edge_rows:
        src = e["src_channel_id"]
        etype = e["edge_type"]
        family = edge_family(etype)

        if etype in DOMAIN_EDGE_TYPES or e.get("dst_domain") is not None:
            dst = e.get("dst_domain")
            if dst is None:
                continue  # ligne incohérente : type domaine sans domaine
            if dst not in g:
                g.add_node(dst, kind="domain")
        else:
            dst = e.get("dst_channel_id")
            if dst is None:
                continue  # ligne incohérente : ni domaine ni canal
            # Canal cible non catalogué (découverte snowball) : nœud minimal.
            if dst not in g:
                g.add_node(dst, kind="channel")

        # Canal source non catalogué : nœud minimal, pas de features.
        if src not in g:
            g.add_node(src, kind="channel")

        g.add_edge(
            src,
            dst,
            key=etype,  # un seul agrégat par (src, dst, type) — cf. uq_edges
            edge_type=etype,
            family=family,
            count=e.get("count") or 0,
            weight=e.get("weight"),
            delay_seconds=e.get("delay_seconds"),
            text_sim=e.get("text_sim"),
            window_delta_seconds=e.get("window_delta_seconds"),
            attrs=e.get("attrs"),
        )

    return g


def _edge_weight(data: Mapping[str, Any]) -> float:
    """Poids d'une arête pour le bornage top-K.

    Priorité au ``weight`` dérivé s'il existe, sinon ``count`` (occurrences
    agrégées). Le bornage garde les arêtes les plus fortes (forward-influence,
    UX doc NFR-21).
    """
    w = data.get("weight")
    if w is not None:
        return float(w)
    return float(data.get("count") or 0)




def to_igraph(graph: nx.MultiDiGraph):
    """Conversion optionnelle vers igraph (détection de communautés).

    NetworkX suffit au voisinage ego-graph borné ; igraph est utile aux
    communautés pondérées (cf. ``scripts/detect_clusters.py``). On replie le
    multiplex en un graphe non orienté pondéré (somme des poids d'arête entre
    deux nœuds), comme ``build_igraph`` du script de clustering.

    Import paresseux : igraph n'est requis que pour cette fonction.
    """
    import igraph as ig

    nodes = list(graph.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    w: dict[tuple[int, int], float] = defaultdict(float)
    for u, v, data in graph.edges(data=True):
        a, b = sorted((idx[u], idx[v]))
        if a == b:
            continue  # ignore les self-loops (cf. build_graph.py)
        w[(a, b)] += _edge_weight(data)

    g = ig.Graph(n=len(nodes), edges=list(w.keys()), directed=False)
    g.vs["node_id"] = nodes
    g.es["weight"] = list(w.values())
    return g
