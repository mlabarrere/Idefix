"""Snapshot statique « russosphère » — détection de communautés + ponts.

But (démonstration auto-suffisante) : à partir d'une SEULE graine légitime
(@France24_fr), montrer que l'analyse de graphe a reconstruit toute seule
l'appareil d'influence russe en **communautés thématiques cohérentes** et a
identifié les **nœuds-pivots** (ponts inter-communautés) — sans qu'on lui dise
de chercher « les Russes ».

Pipeline (formalise ``scripts/_explore_clusters.py``) :
  1. ``build_graph`` (MultiDiGraph) depuis PostgreSQL (lecture seule, loader).
  2. Leiden (igraph ``community_leiden``, modularité, poids) → communautés.
  3. Pour chaque communauté : taille, canaux (id/username/title/engagement/
     credibility_prior), domaines, **label thématique auto** (heuristique sur
     les handles/domaines/titres).
  4. Betweenness sur la **projection canal** (non orientée, pondérée) → ponts.
  5. Vue **méta-nœuds** : une communauté = un nœud ; arêtes inter-communautés
     agrégées et pondérées.
  6. Écrit ``webapp/public/data/russosphere/russosphere_snapshot.json``
     (``--mission <m>`` : même snapshot sous ``webapp/public/data/<m>/``).

AUCUN appel Telegram / réseau. Lecture seule PostgreSQL via le loader existant.
Library-first : igraph (Leiden), networkx (betweenness), asyncpg (I/O DB).

Usage (Windows) :
    .venv\\Scripts\\python.exe scripts\\analyze_communities.py

References (cf. docs/reference/references.md):
  - Leiden (détection de communautés) : Traag, Waltman & van Eck (2019), Sci. Rep. 9:5233.
  - Modularité (qualité de partition) : Newman (2006), PNAS 103(23).
  - TF-IDF (labels thématiques auto) : Spärck Jones (1972), J. Documentation 28(1).
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shared.db import db_connect  # noqa: E402
import asyncpg  # noqa: E402
import networkx as nx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.graph.loader import (  # noqa: E402
    build_graph,
    fetch_channel_rows,
    fetch_edge_rows,
    to_igraph,
)
from src.missions.loader import add_mission_arg, resolve_mission  # noqa: E402

load_dotenv()

# La graine d'amorçage du snowball (channel_id stable aux rebrands). Toute la
# russosphère (421 canaux + 183 domaines) a été découverte par expansion depuis
# ce seul nœud légitime — c'est le cœur de la démonstration.
SEED_CHANNEL_ID = -1001508539275
SEED_USERNAME = "France24_fr"

OUT_PATH = ROOT / "webapp" / "public" / "data" / "russosphere" / "russosphere_snapshot.json"

# Palette stable (cohérente avec le langage visuel navy/gold de la console).
# Assignée par rang de taille de communauté (les plus grosses en premier).
PALETTE = [
    "#C9880A", "#DC2626", "#2563EB", "#16A34A", "#9333EA",
    "#0891B2", "#EA580C", "#DB2777", "#65A30D", "#0D9488",
    "#7C3AED", "#CA8A04", "#E11D48", "#0EA5E9", "#84CC16",
    "#A855F7", "#F59E0B", "#EF4444", "#3B82F6", "#10B981",
]

# --------------------------------------------------------------------------- #
# Étiquetage thématique automatique (heuristique transparente, pas de modèle).
# Chaque thème = liste de motifs (regex) testés sur les handles + domaines +
# titres de la communauté. Le thème dont les motifs matchent le plus de
# canaux/domaines gagne. Conçu pour être LISIBLE et auditable — c'est un
# résumé descriptif, pas une classification supervisée.
# --------------------------------------------------------------------------- #
#
# Ordre = priorité (le premier thème dont les motifs couvrent le PLUS de
# membres gagne ; à égalité, le plus haut dans la liste l'emporte). Les thèmes
# spécifiques (diaspora, OSINT, Tsargrad) sont placés AVANT les thèmes larges
# (« géopolitique ») pour éviter que le motif générique n'avale tout.
# --------------------------------------------------------------------------- #
# TAXONOMIE THÉMATIQUE (refonte 2026-06-10, ancrée sur les données réelles).
# Chaque entrée = (thème, motifs handles/titres, motifs domaines). Étiquetage par
# COUVERTURE-PAR-CANAL × IDF (cf. label_pass) : un motif ubiquitaire (geopolit,
# \bfr\b) pèse ~0 ; un motif rare et discriminant (arktos, akhmat) pèse fort.
# Ordre = du plus spécifique au plus large (sert de tie-break uniquement).
# --------------------------------------------------------------------------- #
TAXONOMY: list[tuple[str, list[str], list[str]]] = [
    ("Eurasianisme / 4e théorie (Douguine)",
     [r"\bdugin", r"agdchan", r"geopolitika", r"evrazia", r"\besm\b", r"rossia_3",
      r"multipolar", r"katehon", r"paideuma", r"occvltimperium", r"4pt", r"yuzhinsk"],
     [r"geopolitika\.ru", r"evrazia", r"katehon", r"izborsk", r"eurasianist", r"dugin"]),
    ("Néopaganisme / New Right (Arktos-Iliade)",
     [r"arktos", r"iliade", r"imperiumpress", r"antelopehill", r"countercurrent",
      r"\bprav", r"venner", r"bowden", r"runic", r"wandervogel"],
     [r"arktos\.com", r"imperiumpress", r"counter-currents", r"antelopehill", r"institut-iliade", r"eurosiberia"]),
    ("Accélérationnisme / Active-Club / NS",
     [r"activeclub", r"\bac\b", r"action$", r"waffen", r"nsheathen", r"_88",
      r"aryan", r"whiteyouth", r"risingrace", r"blacksun", r"\bsiege"],
     [r"patriotfront", r"will2rise", r"returntotheland", r"hatecomestomainstreet"]),
    ("Chudosphère / meme far-right (US)",
     [r"\bchud", r"posting", r"goypost", r"schizo", r"4chan", r"\bpol\b", r"shitpost",
      r"brainrot", r"cobson", r"stonetoss", r"telechud"],
     [r"stonetoss", r"boards\.4chan", r"88streams", r"fixvx", r"fixupx"]),
    ("Antisémitisme doctrinal (JQ)",
     [r"\bjew", r"talmud", r"khazar", r"judaic", r"amalek", r"antiabrahamic",
      r"goyim", r"\bjq\b", r"holohoax"],
     [r"\bjta\b", r"jweekly", r"betemunah"]),
    ("Nationalisme identitaire FR",
     [r"nationalist", r"actionfranc", r"jeunenation", r"partidelafrance", r"benedetti",
      r"chouan", r"\bgud\b", r"ephemerides", r"caryatid", r"memorianatio", r"comitedu9mai",
      r"visages_de_france", r"auvergnenationaliste"],
     [r"jeune-nation", r"actionfrancaise"]),
    ("Réinfosphère / médias dissidents FR",
     [r"fdesouche", r"mediaspresse", r"faitsetdocuments", r"rtenfrancais", r"icimoscou",
      r"reinfo", r"legrandreveil", r"liberta", r"kompromat"],
     [r"breizh-info", r"faitsetdocuments", r"aubedigitale", r"crowdbunker", r"epochtimes"]),
    ("Catholicisme traditionaliste",
     [r"cathol", r"porte?latine", r"chevalerie", r"serviam", r"riposte", r"croise",
      r"lefebvr", r"fsspx", r"saintbarth", r"peinturecatholique", r"subversionprotestante"],
     [r"laportelatine", r"riposte-catholique", r"catholicarena", r"catholique", r"fides"]),
    ("Soraliens / E&R / dieudosphère",
     [r"egaliteetrecon", r"\ber_", r"kontrekulture", r"soral", r"dieudo", r"quenelle"],
     [r"kontrekulture", r"egaliteetreconciliation"]),
    ("Souverainisme / Frexit / Gilets jaunes",
     [r"asselineau", r"frexit", r"giletsjaunes", r"\bgj\b", r"souverain", r"\bupr\b",
      r"constituant"],
     [r"\bupr\.fr", r"frexit\.fr"]),
    ("Multipolarité italo/latino (Strategic Culture)",
     [r"scf_", r"strategic.?culture", r"antidiplomatico", r"saker", r"byoblu",
      r"donbass.?antinaz", r"multipolare", r"comedonchisciotte", r"reseauinternational"],
     [r"strategic-culture", r"byoblu", r"comedonchisciotte", r"contropiano", r"reseauinternational"]),
    ("Multipolarité anglophone anti-impérialiste",
     [r"grayzone", r"escobar", r"hinkle", r"consortium", r"lordbebo", r"candace",
      r"geopoliticaleconomy", r"multipolarista", r"rocknrollgeopolitics"],
     [r"thegrayzone", r"consortiumnews", r"asiatimes", r"klarenberg"]),
    ("OSINT-guerre « Rybar » (franchise)",
     [r"rybar", r"_majors", r"intelslava", r"slavyangrad", r"geopolitics_prime",
      r"ddgeopolitics", r"grandmaster", r"osintwarfare", r"two_majors"],
     [r"dva-majors", r"infobrics"]),
    ("Milbloggers stars / Z-correspondants",
     [r"soloviev", r"voenkor", r"voenac", r"wargonzo", r"milinfo", r"colonelcassad",
      r"rozhin", r"\bzov\b", r"\bsvo\b", r"rsotm", r"opersvodki", r"sashakots", r"rvvoenkor"],
     [r"lostarmour", r"rusvesna"]),
    ("Brigades / médecine tactique (Akhmat)",
     [r"akhmat", r"tacmed", r"tacticalmedicine", r"brigada", r"\bspn\b", r"bataillon",
      r"\bbars\b", r"shturm", r"\bpolk", r"vostok", r"healer"],
     [r"healertacmed", r"milcatpro", r"zaslontactical", r"grozny-inform"]),
    ("Drones / industrie militaire RU",
     [r"\buav\b", r"\bbpla\b", r"\bdron", r"rogozin", r"\boak\b", r"\buac\b",
      r"rusengineer", r"texbpla", r"\bfpv\b"],
     [r"uac\.ru", r"defence-blog", r"dronefront"]),
    ("État russe / diplomatie (MID)",
     [r"mid_?russia", r"\bmfa\b", r"kremlin", r"ambrus", r"rusemb", r"botschaft",
      r"mod_russia", r"posolstvo", r"\bconsul", r"government_rus", r"genproc"],
     [r"\bmid\.ru", r"kdmid", r"duma\.gov", r"government\.ru"]),
    ("Soft-power / Rossotrudnichestvo",
     [r"rossotrud", r"russkiy?dom", r"rushouse", r"roscongress", r"premiyaevrazia"],
     [r"russiaislove", r"\bdobro\.ru", r"russia\.study", r"eccis"]),
    ("Orthodoxie politique / Église RU",
     [r"pravoslav", r"orthodox", r"\bfoma", r"lavra", r"mitropoli", r"eparhia",
      r"sobor", r"patriarch", r"prichod", r"legoyda", r"tserkov", r"indiktion"],
     [r"patriarchia", r"foma\.ru", r"azbyka", r"pravmir", r"ruskline", r"moseparh"]),
    ("Mobilisation domestique RU (#МЫВМЕСТЕ)",
     [r"myvmest", r"\bdobro", r"\bksvo", r"lantratova", r"ombudsman", r"mintrud",
      r"volunteer", r"trudvsem", r"findchild"],
     [r"dobro\.ru", r"gosuslugi", r"\bonf\.ru"]),
    ("Complosphère santé / anti-vax / QAnon",
     [r"ivermectin", r"qanon", r"wwg1wga", r"qlobal", r"mccullough", r"tenpenny",
      r"vaccin", r"plandemic", r"redpill", r"marik", r"avocado"],
     [r"childrenshealthdefense", r"brownstone", r"expose-news", r"thepeoplesvoice", r"davidicke"]),
    ("Axe de la résistance / médias iraniens",
     [r"khamenei", r"tasnim", r"farsna", r"presstv", r"resistance", r"mehrnews", r"\birib"],
     [r"presstv", r"tasnim", r"mehrnews", r"\.ir\b"]),
    ("Souverainistes germanophones (AfD-sphère)",
     [r"auf1", r"janich", r"evaherman", r"wisnewski", r"kulturstudio", r"\bafd\b",
      r"_deutsch", r"reichsb", r"querdenk"],
     [r"auf1\.tv", r"jungefreiheit", r"rtde", r"tichyseinblick", r"apollo-news"]),
    ("Vétérans / blogs militaires RU (SVO)",
     [r"veteran", r"notes_vet", r"rogatkin", r"atomiccherry", r"opersvodki",
      r"frontov", r"\bsvo\b", r"\bzov\b", r"boevoy", r"sledcom", r"antiskrepa"],
     [r"lostarmour", r"\biz\.ru"]),
    ("Actualité militaire RU (russophone)",
     [r"война", r"войн", r"фронт", r"сводк", r"бойц", r"наступлен", r"передов",
      r"спецоп", r"ополчен", r"армия", r"вс\s?рф", r"воен", r"бои\b", r"штурм",
      r"гвардия", r"батальон", r"артиллер", r"truejpg", r"barantchik"],
     [r"\briafan", r"\briak", r"\btass", r"\bria\.ru"]),
    ("Agrégateurs news anglophones (breaking)",
     [r"watcherguru", r"insiderpaper", r"disclosetv", r"osintupdates", r"breaking",
      r"spectatorindex", r"visegrad", r"intelsky", r"megatron_ron", r"sentdefender"],
     [r"insiderpaper", r"disclose\.tv"]),
    ("Relais / agrégateurs FR neutres",
     [r"alertefr", r"mediavenir", r"\bneodia\b", r"cerfia", r"actu17"],
     []),
]

# Motifs de « boîte enregistreuse » (relais/archive/mirror, sans ligne propre).
RELAY_PAT = [r"archive", r"mirror", r"relais", r"\brelay", r"reserve", r"backup",
             r"\bdump", r"repost", r"_v\d{1,2}\b", r"\bv1\d\b", r"_bot\b"]
MIN_COVER = 0.12     # couverture mini d'un thème pour compter (df IDF + label)
MIN_SCORE = 0.18     # score (couverture×IDF) mini pour un label confiant
COMPOSITE = 0.80     # 2e thème ≥ 80 % du 1er ⇒ label composite « A + B »


def _ctext(c: dict) -> str:
    return ((c.get("username") or "") + " " + (c.get("title") or "")).lower()


def theme_coverage(channels: list[dict], domains: list[str]) -> dict[str, float]:
    """thème -> fraction de canaux de la communauté qui matchent (par CANAL,
    normalisé par taille). Un domaine caractéristique présent ajoute un bonus
    de soutien. C'est la base du score, indépendante de la taille du cluster."""
    n = max(1, len(channels))
    texts = [_ctext(c) for c in channels]
    doms = [d.lower() for d in domains]
    cov: dict[str, float] = {}
    for theme, tp, dp in TAXONOMY:
        hits = sum(1 for t in texts if t and any(re.search(p, t) for p in tp))
        frac = hits / n
        if dp and any(re.search(p, d) for d in doms for p in dp):
            frac += 0.10  # un domaine caractéristique conforte le thème
        if frac > 0:
            cov[theme] = round(frac, 4)
    return cov


def cluster_type(channels: list[dict], domains: list[str], top_cov: float) -> str:
    """franchise (même opérateur décliné) · relay (boîte enregistreuse) ·
    thematic (vrai thème) · mixed (sous le seuil de confiance)."""
    n = len(channels)
    # franchise : un même préfixe de handle domine (rybar_*, geopolitika_*, scf_*)
    pref = Counter()
    for c in channels:
        u = (c.get("username") or "").lower()
        p = re.split(r"[_\d]", u, 1)[0]
        if len(p) >= 4:
            pref[p] += 1
    if pref and pref.most_common(1)[0][1] >= max(3, n * 0.5):
        return "franchise"
    # relay : aucun domaine propre + engagement médian nul + motifs-relais
    engs = sorted(c.get("engagement") or 0 for c in channels)
    med = engs[len(engs) // 2] if engs else 0
    relay_hits = sum(1 for c in channels if any(re.search(p, _ctext(c)) for p in RELAY_PAT))
    if len(domains) == 0 and med == 0 and relay_hits >= max(1, n * 0.3):
        return "relay"
    return "thematic" if top_cov >= MIN_COVER else "mixed"


def load_graph_from_bundle() -> nx.MultiDiGraph:
    """Repli sans DB : reconstruit le graphe depuis le bundle statique déjà
    exporté (``channels.json`` + ``edges_sample.json``). Source de vérité quand
    l'app tourne en mode Vercel-only (aucune base joignable). Les edges du
    bundle portent déjà les bons champs ; fr_score vit dans ``extra``,
    l'engagement n'est pas exporté → 0 (n'affecte pas la structure Leiden)."""
    d = OUT_PATH.parent
    chans = [
        {
            "channel_id": c["channel_id"],
            "username": c.get("username"),
            "title": c.get("title"),
            "member_count": c.get("member_count"),
            "fr_score": (c.get("extra") or {}).get("fr_score"),
            "engagement": 0,
        }
        for c in json.loads((d / "channels.json").read_text("utf-8"))
    ]
    edges = json.loads((d / "edges_sample.json").read_text("utf-8"))
    return build_graph(edges, chans)


async def load_graph() -> nx.MultiDiGraph:
    """Graphe multiplex depuis PostgreSQL, repli bundle statique si DB injoignable."""
    try:
        conn = await db_connect()
    except (OSError, asyncpg.PostgresError):
        print("DB injoignable → repli sur le bundle statique (mode Vercel-only)")
        return load_graph_from_bundle()
    try:
        edges = await fetch_edge_rows(conn)
        chans = await fetch_channel_rows(conn)
    finally:
        await conn.close()
    return build_graph(edges, chans)


def detect_communities(g: nx.MultiDiGraph, resolution: float = 1.6) -> tuple[dict, float]:
    """Leiden (igraph, modularité, poids) → {node_id: community_index}, modularité.

    ``resolution`` > 1 CASSE les méga-communautés hétérogènes (à 1.0 on obtenait
    des clusters de 500+ canaux impossibles à étiqueter honnêtement). ~1.6 vise
    des communautés plus fines et thématiquement cohérentes. ``n_iterations=-1``
    itère jusqu'à stabilité (recommandé igraph)."""
    ig = to_igraph(g)
    try:
        part = ig.community_leiden(
            objective_function="modularity", weights="weight",
            resolution=resolution, n_iterations=-1,
        )
    except TypeError:  # igraph plus ancien : nom de paramètre différent
        part = ig.community_leiden(
            objective_function="modularity", weights="weight",
            resolution_parameter=resolution,
        )
    node_ids = ig.vs["node_id"]
    comm = {node_ids[i]: part.membership[i] for i in range(len(node_ids))}
    return comm, float(part.modularity)


def channel_projection(g: nx.MultiDiGraph) -> nx.Graph:
    """Projection canal non orientée pondérée (domaines + self-loops exclus).

    Le poids d'une arête canal↔canal = somme des ``count`` de toutes les arêtes
    multiplex entre ces deux canaux. Base de la betweenness (ponts).
    """
    h = nx.Graph()
    h.add_nodes_from(n for n, d in g.nodes(data=True) if d.get("kind") != "domain")
    for u, v, data in g.edges(data=True):
        if isinstance(u, str) or isinstance(v, str) or u == v:
            continue
        w = float(data.get("count") or 1)
        if h.has_edge(u, v):
            h[u][v]["weight"] += w
        else:
            h.add_edge(u, v, weight=w)
    return h


def build_snapshot(
    g: nx.MultiDiGraph,
    comm: dict | None = None,
    modularity: float | None = None,
) -> dict:
    # Membership can be injected (e.g. the embedding-reweighted detection in
    # scripts/analyze_communities_embed.py) so the snapshot and the comparison
    # block share ONE partition; default recomputes it on the given graph.
    if comm is None:
        comm, modularity = detect_communities(g)

    # Regroupe les nœuds par communauté.
    by_comm: dict[int, list] = defaultdict(list)
    for n, cidx in comm.items():
        by_comm[cidx].append(n)

    # Betweenness sur la projection canal (ponts).
    h = channel_projection(g)
    bet = nx.betweenness_centrality(h, weight=None, normalized=True)

    # On ne garde que les communautés ayant ≥2 canaux (les singletons domaine
    # ne sont pas des « communautés » au sens décideur). Triées par taille.
    ordered = sorted(
        by_comm.items(),
        key=lambda kv: -sum(1 for m in kv[1] if isinstance(m, int)),
    )

    # ── PASSE 1 : assembler les communautés gardées (≥2 canaux) + couverture ──
    raw: list[dict] = []
    for cidx, members in ordered:
        chan_ids = [m for m in members if isinstance(m, int)]
        dom_ids = sorted(m for m in members if isinstance(m, str))
        if len(chan_ids) < 2:
            continue
        channels = []
        for cid in chan_ids:
            d = g.nodes[cid]
            channels.append({
                "channel_id": cid,
                "username": d.get("username") or "",
                "title": d.get("title") or "",
                "engagement": int(d.get("engagement") or 0),
                "credibility_prior": d.get("credibility_prior") or "other",
                "fr_score": d.get("fr_score"),
                "member_count": d.get("member_count"),
                "betweenness": round(bet.get(cid, 0.0), 4),
                "is_seed": cid == SEED_CHANNEL_ID,
            })
        channels.sort(key=lambda c: -(c["engagement"] or 0))
        raw.append({
            "cidx": cidx, "channels": channels, "domains": dom_ids,
            "cov": theme_coverage(channels, dom_ids),
        })

    # ── IDF : un thème présent dans beaucoup de communautés est peu distinctif ──
    N = max(1, len(raw))
    df: Counter = Counter()
    for r in raw:
        for theme, f in r["cov"].items():
            if f >= MIN_COVER:
                df[theme] += 1
    idf = {theme: math.log((N + 1) / (1 + df.get(theme, 0))) for theme, _, _ in TAXONOMY}

    # ── PASSE 2 : label = meilleur (couverture × IDF), composite si 2 proches ──
    communities: list[dict] = []
    comm_label: dict[int, str] = {}
    comm_color: dict[int, str] = {}
    kept_comm_ids: set[int] = set()
    color_i = 0
    for r in raw:
        channels, dom_ids, cov = r["channels"], r["domains"], r["cov"]
        scored = sorted(
            ((t, f * idf.get(t, 0.0), f) for t, f in cov.items()),
            key=lambda x: -x[1],
        )
        top_cov = scored[0][2] if scored else 0.0
        ctype = cluster_type(channels, dom_ids, top_cov)

        if not scored or scored[0][1] < MIN_SCORE:
            # Aucun thème confiant : on nomme par le TYPE technique, pas un thème inventé.
            top = next((c["username"] for c in channels if c["username"]), f"#{channels[0]['channel_id']}")
            label = {
                "franchise": f"Franchise · @{top}",
                "relay": f"Relais / archives · @{top}",
            }.get(ctype, f"Cluster mixte · @{top}")
            confidence = "low"
            evidence = [t for t, _, _ in scored[:3]]
        else:
            label = scored[0][0]
            if len(scored) > 1 and scored[1][1] >= COMPOSITE * scored[0][1] and scored[1][1] >= MIN_SCORE:
                label = f"{scored[0][0]} + {scored[1][0]}"
            confidence = "high" if scored[0][1] >= 2 * MIN_SCORE else "medium"
            evidence = [t for t, _, _ in scored[:3]]

        color = PALETTE[color_i % len(PALETTE)]
        color_i += 1
        comm_label[r["cidx"]] = label
        comm_color[r["cidx"]] = color
        kept_comm_ids.add(r["cidx"])
        communities.append({
            "id": r["cidx"],
            "label": label,
            "color": color,
            "size": len(channels),
            "n_domains": len(dom_ids),
            "n_suspects": sum(1 for c in channels if c["credibility_prior"] == "suspect"),
            "cluster_type": ctype,
            "theme_confidence": confidence,
            "theme_evidence": evidence,
            "channels": channels,
            "domains": dom_ids,
        })

    # Filet de sécurité : si deux communautés gardent un label IDENTIQUE (rare
    # après labeling distinctif), suffixer par le canal le plus engageant.
    label_counts = Counter(c["label"] for c in communities)
    for c in communities:
        if label_counts[c["label"]] > 1:
            top = next((ch["username"] for ch in c["channels"] if ch["username"]), None)
            if top and "@" not in c["label"]:
                c["label"] = f"{c['label']} · @{top}"
                comm_label[c["id"]] = c["label"]

    # --- Ponts : top canaux par betweenness, avec communautés reliées. ------ #
    bridges: list[dict] = []
    for cid, b in sorted(bet.items(), key=lambda kv: -kv[1]):
        if b <= 0:
            continue
        own = comm.get(cid)
        # Communautés des voisins (combien d'arêtes vers chaque communauté).
        neigh = Counter(
            comm_label.get(comm.get(v))
            for v in h.neighbors(cid)
            if comm.get(v) in kept_comm_ids and comm.get(v) != own
        )
        neigh.pop(None, None)
        connects = [{"label": lab, "edges": cnt} for lab, cnt in neigh.most_common(5)]
        d = g.nodes[cid]
        bridges.append({
            "channel_id": cid,
            "username": d.get("username") or "",
            "title": d.get("title") or "",
            "betweenness": round(b, 4),
            "credibility_prior": d.get("credibility_prior") or "other",
            "engagement": int(d.get("engagement") or 0),
            # fr_score : densité lexicale FR du canal (≠ ciblage-France). Exposé ici
            # pour permettre au frontend de remonter le côté FR/extrême-droite des
            # ponts EN AFFICHAGE — ne modifie ni le score ni l'inclusion (les ponts
            # restent tous présents). Cf. memory france-targeting-vs-fr-score.
            "fr_score": d.get("fr_score"),
            "community": comm_label.get(own, "—"),
            "community_id": own,
            "connects": connects,
            "is_seed": cid == SEED_CHANNEL_ID,
        })
        if len(bridges) >= 40:
            break

    # --- Méta-nœuds : communauté = nœud ; arêtes inter-communautés agrégées. - #
    inter: dict[tuple[int, int], float] = defaultdict(float)
    for u, v, data in g.edges(data=True):
        cu, cv = comm.get(u), comm.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        if cu not in kept_comm_ids or cv not in kept_comm_ids:
            continue
        key = tuple(sorted((cu, cv)))
        inter[key] += float(data.get("count") or 1)

    meta_nodes = [
        {
            "id": cidx,
            "label": comm_label[cidx],
            "color": comm_color[cidx],
            "size": c["size"],
            "n_suspects": c["n_suspects"],
        }
        for cidx, c in ((cc["id"], cc) for cc in communities)
    ]
    meta_edges = [
        {"source": a, "target": b, "weight": round(w, 1)}
        for (a, b), w in sorted(inter.items(), key=lambda kv: -kv[1])
    ]

    # Position de la graine dans le résultat (storytelling).
    seed_comm = comm.get(SEED_CHANNEL_ID)
    n_channels = sum(1 for n, d in g.nodes(data=True) if d.get("kind") != "domain")
    n_domains = sum(1 for n, d in g.nodes(data=True) if d.get("kind") == "domain")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": {
            "channel_id": SEED_CHANNEL_ID,
            "username": SEED_USERNAME,
            "community_id": seed_comm,
            "community_label": comm_label.get(seed_comm, "—"),
            "note": (
                "Graine d'amorçage unique : tout le graphe a été découvert par "
                "expansion snowball depuis ce seul média légitime."
            ),
        },
        "stats": {
            "n_nodes": g.number_of_nodes(),
            "n_channels": n_channels,
            "n_domains": n_domains,
            "n_edges": g.number_of_edges(),
            "n_communities": len(communities),
            "modularity": round(modularity, 4),
        },
        "communities": communities,
        "bridges": bridges,
        "meta_graph": {"nodes": meta_nodes, "edges": meta_edges},
        "coverage_callout": (
            "Couverture Telegram uniquement : la couche d'amplification de masse "
            "(X / autres plateformes) n'est pas observée (docs/limitations.md L1). "
            "L'extrême droite française est désormais dans le graphe "
            "(nationalisme identitaire, catho-trad, E&R, Arktos/Iliade) ; le "
            "RN-parti officiel n'y est PAS (peu présent/traçable sur Telegram)."
        ),
    }


def snapshot_path(mission: str | None = None) -> Path:
    """Chemin du snapshot pour la mission (``None`` => russosphère, chemin historique).

    Le snapshot est calculé sur le graphe COMPLET (indépendant de la mission) ;
    ``--mission`` ne choisit que le dossier du bundle, sous le nom canonique
    ``russosphere_snapshot.json`` que la webapp lit pour toute mission.
    """
    if mission is None:
        return OUT_PATH
    subdir = resolve_mission(mission).export.out_subdir
    return ROOT / "webapp" / "public" / "data" / subdir / OUT_PATH.name


async def main(push: bool = False, mission: str | None = None) -> None:
    out_path = snapshot_path(mission)
    g = await load_graph()
    print(f"Graphe : {g.number_of_nodes()} nœuds / {g.number_of_edges()} arêtes")
    snapshot = build_snapshot(g)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
    out_path.write_text(payload, encoding="utf-8")
    if push:
        from src.shared.snapshot_store import push_snapshot
        subdir = out_path.parent.name
        push_snapshot(subdir, "analytics", snapshot)
        print(f"Push Supabase : community_snapshots[{subdir}, analytics]")
    s = snapshot["stats"]
    print(
        f"{s['n_communities']} communautés (modularité {s['modularity']}) · "
        f"{s['n_channels']} canaux · {s['n_domains']} domaines"
    )
    print("\nCommunautés (label auto) :")
    for c in snapshot["communities"]:
        print(f"  [{c['color']}] {c['label']:42s} {c['size']:3d} canaux "
              f"({c['n_suspects']} suspects) · {c['n_domains']} domaines")
    print("\nTop ponts (betweenness) :")
    for b in snapshot["bridges"][:10]:
        conn = ", ".join(f"{c['label']}({c['edges']})" for c in b["connects"])
        print(f"  {b['betweenness']:.3f}  @{b['username']:24s} [{b['community']}] "
              f"→ {conn}")
    print(f"\nÉcrit : {out_path}")


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser(description="Snapshot communautés analytics (lexical/TF-IDF).")
    _ap.add_argument("--push", action="store_true",
                     help="pousse le snapshot (scrubbé) vers Supabase community_snapshots")
    add_mission_arg(_ap)
    _args = _ap.parse_args()
    asyncio.run(main(push=_args.push, mission=_args.mission))
