"""Tests du score de suspicion par canal (src/scorer/channel_suspicion.py).

PUR — aucun I/O DB, aucun appel Telegram. On construit de PETITS graphes
multiplex synthétiques (mêmes lignes ``edges``/``channels`` que le loader) puis
on assert :

  * projection FORWARD : orientation ORIGIN -> RELAYER, mapping delay_seconds ->
    min_delay_s, exclusion des nœuds domaine ;
  * agrégation des familles b/c/d ;
  * la MODULATION DE SÉVÉRITÉ monte le score (reforward suspect + domaine adverse) ;
  * MÉTA-CONTRAINTE 1 : un canal adverse à fr_score BAS reste classable en tête —
    AUCUN filtrage par fr_score ;
  * verrou multi-source (>= 2 familles) ;
  * tier T1/T2 uniquement, JAMAIS T3 ;
  * forme du bloc queue = clés de l'échantillon JSON ;
  * graphe vide -> queue vide ;
  * score_coordination_edges : règle des >= 2 types distincts.
"""

from __future__ import annotations

import dataclasses

from src.graph.loader import build_graph
from src.scorer.channel_suspicion import (
    _DEFAULT_PROFILE,
    ADVERSARY_DOMAINS,
    MAX_ADVERSARY_DOMAIN_BOOST,
    MAX_FRANCE_TARGETING_BOOST,
    MAX_REFORWARD_BOOST,
    adversary_domain_citations,
    channel_archetypes,
    compute_channel_queue,
    forward_digraph,
    reforward_from,
)
from src.scorer.coordination import score_coordination_edges

# Profil RAPIDE pour les tests de scoring rigoureux : peu de rewirings/bootstraps
# (déterministe, suffisant pour les assertions de significativité). Le défaut de
# production reste n_null=200 / n_bootstrap=100.
_FAST = dataclasses.replace(_DEFAULT_PROFILE, n_null=120, n_bootstrap=60)


# --------------------------------------------------------------------------- #
# Fabriques de lignes simulées (forme = sortie de fetch_edge_rows/channel_rows).
# --------------------------------------------------------------------------- #
def edge_row(
    src,
    *,
    dst_channel=None,
    dst_domain=None,
    etype="FORWARD",
    count=1,
    weight=None,
    delay_seconds=None,
    window_delta_seconds=None,
):
    return {
        "src_channel_id": src,
        "dst_channel_id": dst_channel,
        "dst_domain": dst_domain,
        "edge_type": etype,
        "count": count,
        "weight": weight,
        "delay_seconds": delay_seconds,
        "text_sim": None,
        "window_delta_seconds": window_delta_seconds,
        "attrs": None,
    }


def channel_row(cid, *, username="", title="", member_count=0, fr_score=None, engagement=0):
    return {
        "channel_id": cid,
        "username": username,
        "title": title,
        "member_count": member_count,
        "fr_score": fr_score,
        "engagement": engagement,
    }


# --------------------------------------------------------------------------- #
# 1) Projection FORWARD : orientation + mapping délai + exclusion domaines.   #
# --------------------------------------------------------------------------- #
def test_forward_digraph_orientation_and_delay_mapping():
    # 1 (origine) -> 2 (relayeur), délai 7200s ; + une arête CITES_DOMAIN à écarter.
    edges = [
        edge_row(1, dst_channel=2, etype="FORWARD", count=5, delay_seconds=7200),
        edge_row(2, dst_domain="geopolitika.ru", etype="CITES_DOMAIN", count=3),
    ]
    chans = [channel_row(1, username="origin"), channel_row(2, username="relay")]
    multi = build_graph(edges, chans)

    fwd = forward_digraph(multi)

    # Orientation : l'arête va de l'ORIGINE (1) vers le RELAYEUR (2).
    assert fwd.has_edge(1, 2)
    assert not fwd.has_edge(2, 1)
    # Le nœud domaine est exclu de la projection forward.
    assert "geopolitika.ru" not in fwd
    assert set(fwd.nodes) == {1, 2}
    # Mapping delay_seconds -> min_delay_s + report du count.
    assert fwd.edges[1, 2]["count"] == 5
    assert fwd.edges[1, 2]["min_delay_s"] == 7200
    # Attributs de nœud préservés.
    assert fwd.nodes[1]["username"] == "origin"


def test_forward_digraph_only_forward_edges():
    # Une arête MENTIONS (influence) ne doit PAS entrer dans le graphe forward.
    edges = [
        edge_row(1, dst_channel=2, etype="FORWARD", count=2, delay_seconds=60),
        edge_row(3, dst_channel=1, etype="MENTIONS", count=4),
    ]
    multi = build_graph(edges, [channel_row(1), channel_row(2), channel_row(3)])
    fwd = forward_digraph(multi)
    assert fwd.has_edge(1, 2)
    assert not fwd.has_edge(3, 1)  # MENTIONS exclue


# --------------------------------------------------------------------------- #
# Helper : petit réseau adverse (origine relayée largement, fr_score BAS).    #
# --------------------------------------------------------------------------- #
def _adversary_network():
    """Origine 'dugin' (fr_score 0.05) relayée par plusieurs canaux suspects,
    qui co-forwardent ET co-citent -> 2 types de coordination, + citation
    d'un domaine adverse. Tout en fr_score bas (adversaire RU/EN).
    """
    chans = [
        channel_row(1001, username="Dugin", title="Alexander Dugin", fr_score=0.05),
        channel_row(1002, username="relayA", title="Relay A", fr_score=0.03),
        channel_row(1003, username="relayB", title="Relay B", fr_score=0.04),
        channel_row(1004, username="relayC", title="Relay C", fr_score=0.02),
    ]
    edges = [
        # FORWARD : 1001 (origine) relayé par 1002/1003/1004 (fan-out fort).
        edge_row(1001, dst_channel=1002, etype="FORWARD", count=20, delay_seconds=3600),
        edge_row(1001, dst_channel=1003, etype="FORWARD", count=18, delay_seconds=5400),
        edge_row(1001, dst_channel=1004, etype="FORWARD", count=15, delay_seconds=7200),
        # les relais se relaient un peu entre eux (récidive / pont)
        edge_row(1002, dst_channel=1003, etype="FORWARD", count=6, delay_seconds=1800),
        edge_row(1003, dst_channel=1004, etype="FORWARD", count=5, delay_seconds=2400),
        # COORDINATION type 1 : CO_FORWARD (mêmes origines), Δt serré.
        edge_row(1002, dst_channel=1003, etype="CO_FORWARD", count=4, window_delta_seconds=1200),
        edge_row(1002, dst_channel=1004, etype="CO_FORWARD", count=3, window_delta_seconds=1800),
        # COORDINATION type 2 : CO_URL (même domaine cité), Δt serré.
        edge_row(1002, dst_channel=1003, etype="CO_URL", count=2, window_delta_seconds=900),
        # Domaine adverse cité par 1002.
        edge_row(1002, dst_domain="geopolitika.ru", etype="CITES_DOMAIN", count=8),
    ]
    return build_graph(edges, chans)


def _signal_network():
    """Réseau ASSEZ GRAND pour que le modèle nul établisse une significativité
    (le scoring rigoureux exige une population, pas un graphe-jouet de 4 nœuds).

    - ``100`` : hub relayé par 201..208 avec des counts ÉLEVÉS → forte
      forward-influence ⇒ famille (d) significative (vs nul à endpoints randomisés).
    - ``201`` : AUSSI un sous-hub (relayé par 301..305) ⇒ (d) significative, ET
      membre d'un trio coordonné (CO_FORWARD + CO_URL avec 202/203) ⇒ (c) renforcée
      ⇒ DEUX familles ⇒ verrou franchi (T2) + cite un domaine adverse.
    - Tous fr_score BAS (adversaire RU/EN) pour les tests « pas de filtre fr_score ».
    """
    chans = [channel_row(100, username="hub", title="Hub", fr_score=0.05)]
    chans += [channel_row(200 + i, username=f"r{i}", fr_score=0.04) for i in range(1, 9)]
    chans += [channel_row(300 + i, username=f"s{i}", fr_score=0.03) for i in range(1, 6)]
    chans += [channel_row(900 + i, username=f"bg{i}", fr_score=0.04) for i in range(1, 4)]
    edges = [
        edge_row(100, dst_channel=200 + i, etype="FORWARD", count=25 + i, delay_seconds=600)
        for i in range(1, 9)
    ]
    edges += [
        edge_row(201, dst_channel=300 + i, etype="FORWARD", count=20 + i, delay_seconds=600)
        for i in range(1, 6)
    ]
    for a, b in [(201, 202), (201, 203), (202, 203)]:
        edges.append(
            edge_row(a, dst_channel=b, etype="CO_FORWARD", count=5, window_delta_seconds=600)
        )
        edges.append(
            edge_row(a, dst_channel=b, etype="CO_URL", count=4, window_delta_seconds=800)
        )
    edges.append(edge_row(201, dst_domain="geopolitika.ru", etype="CITES_DOMAIN", count=8))
    edges += [
        edge_row(901, dst_channel=902, etype="FORWARD", count=2, delay_seconds=600),
        edge_row(902, dst_channel=903, etype="FORWARD", count=1, delay_seconds=600),
    ]
    return build_graph(edges, chans)


# --------------------------------------------------------------------------- #
# 2) Agrégation b/c/d sur le réseau synthétique.                              #
# --------------------------------------------------------------------------- #
def test_families_bcd_aggregate():
    # Scoring RIGOUREUX : la significativité exige une population (réseau ample).
    multi = _signal_network()
    queue = compute_channel_queue(multi, top_k=50, profile=_FAST)
    by_id = {c["channel_id"]: c for c in queue["channels"]}

    # 100 = hub fortement relayé -> forward-influence significative (famille d).
    hub = by_id[100]
    assert hub["scores"]["d"]["v"] > 0.0
    # Sortie rigoureuse : p-value combinée + q-value FDR + drapeau au niveau canal.
    assert "p_combined" in hub and "q_value" in hub and "flagged" in hub
    assert 0.0 <= hub["p_combined"] <= 1.0
    assert hub["archetype"] in {
        "seeding-source", "forward-hub", "cross-channel-bridge", "reactivator",
    }
    # 201 participe à 2 types de coordination -> famille (c) non N/A, valeur > 0.
    relay = by_id[201]
    assert relay["scores"]["c"]["v"] > 0.0
    assert relay["scores"]["c"].get("na") is not True


# --------------------------------------------------------------------------- #
# 3) Modulation de sévérité : monte le score (reforward suspect + domaine).   #
# --------------------------------------------------------------------------- #
def test_severity_modulation_raises_score():
    multi = _adversary_network()

    # Canal de contrôle : même topologie forward que 1002 mais SANS reforward
    # suspect ni citation adverse. On compare le facteur de sévérité.
    fwd = forward_digraph(multi)
    rf = reforward_from(fwd)
    # 1002 relaie 1001 (suspect) -> fraction suspect élevée.
    assert rf[1002]["suspect"] > 0.0

    adv = adversary_domain_citations(multi)
    assert 1002 in adv  # cite geopolitika.ru
    assert adv[1002]["count"] == 8

    # Le composant de combinaison doit refléter un facteur > 1 pour 1002.
    queue = compute_channel_queue(multi, top_k=50)
    by_id = {c["channel_id"]: c for c in queue["channels"]}
    comp = by_id[1002]["_components"]
    assert comp["_severity_factor"] > 1.0
    assert comp["_severity_detail"]["adversary_domain_citations"] == 8
    # Le score combiné est au moins égal à la base (modulation montante seule).
    assert comp["_combined"] >= comp["_base"]


def test_severity_only_modulates_up_never_down():
    """Sévérité bornée >= 1.0 : un canal sans signal adverse n'est jamais
    rétrogradé (MÉTA-CONTRAINTE 1 — modulation montante uniquement)."""
    from src.scorer.channel_suspicion import _severity_modulation

    factor, _ = _severity_modulation(
        {"suspect": 0.0, "legit": 0.0, "other": 1.0}, None
    )
    assert factor == 1.0  # aucun boost -> facteur neutre, jamais < 1


# --------------------------------------------------------------------------- #
# 4) MÉTA-CONTRAINTE 1 : fr_score BAS ne filtre/dégrade JAMAIS le classement. #
# --------------------------------------------------------------------------- #
def test_low_fr_score_adversary_ranks_high_no_filter():
    """Le réseau adverse a un fr_score TRÈS bas (0.02–0.05). Il doit malgré
    tout produire des canaux en tête de file — aucun filtrage par fr_score."""
    multi = _signal_network()
    queue = compute_channel_queue(multi, top_k=50, profile=_FAST)

    # Tous les canaux affichés ont un fr_score bas — et la file n'est pas vide.
    assert len(queue["channels"]) >= 3
    top = queue["channels"][0]
    assert top["fr_score"] is not None and top["fr_score"] < 0.15
    assert top["suspicion"]["v"] > 0.0  # un adverse fr-bas est en tête (pas filtré)
    # Le canal de plus forte suspicion est un canal adverse (fr_score bas).
    assert all(c["fr_score"] < 0.15 for c in queue["channels"])


def test_no_fr_score_gating_against_high_fr_channel():
    """Un canal à fr_score ÉLEVÉ mais sans rôle ne doit pas être promu
    artificiellement ; un canal adverse fr_score bas avec rôle le dépasse.
    Aucun chemin de code ne lit fr_score pour inclure/exclure."""
    chans = [
        channel_row(2001, username="adv", fr_score=0.01),  # adverse, fr bas
        channel_row(2002, username="adv2", fr_score=0.02),
        channel_row(2003, username="adv3", fr_score=0.02),
        channel_row(2004, username="adv4", fr_score=0.02),
        channel_row(9001, username="fr_heavy", fr_score=0.95),  # très "France"
    ]
    edges = [
        # réseau adverse actif : hub 2001 relayé avec counts variés -> (d) signif.
        edge_row(2001, dst_channel=2002, etype="FORWARD", count=30, delay_seconds=600),
        edge_row(2001, dst_channel=2003, etype="FORWARD", count=20, delay_seconds=600),
        edge_row(2001, dst_channel=2004, etype="FORWARD", count=10, delay_seconds=600),
        # le canal "France" 9001 n'a AUCUNE arête -> aucun rôle structurel
    ]
    multi = build_graph(edges, chans)
    queue = compute_channel_queue(multi, top_k=50, profile=_FAST)
    by_id = {c["channel_id"]: c for c in queue["channels"]}

    # Le canal fr_score élevé sans rôle (isolé) a une suspicion 0 (non promu).
    assert by_id[9001]["suspicion"]["v"] == 0.0
    # Le canal adverse fr_score bas AVEC rôle est strictement au-dessus.
    assert by_id[2001]["suspicion"]["v"] > by_id[9001]["suspicion"]["v"]


# --------------------------------------------------------------------------- #
# 5) Verrou multi-source : >= 2 familles déclenchées.                         #
# --------------------------------------------------------------------------- #
def test_gate_requires_two_families():
    multi = _adversary_network()
    queue = compute_channel_queue(multi, top_k=50)
    by_id = {c["channel_id"]: c for c in queue["channels"]}

    relay = by_id[1002]
    gate = relay["gate"]
    # gate.met <=> au moins 2 familles distinctes déclenchées.
    assert gate["met"] == (gate["families"] >= 2)
    if gate["met"]:
        assert gate["families"] >= 2

    # Un canal isolé (aucune arête) ne franchit pas le verrou.
    iso = build_graph([], [channel_row(5000, username="iso")])
    q2 = compute_channel_queue(iso, top_k=10)
    only = q2["channels"][0]
    assert only["gate"]["met"] is False
    assert only["gate"]["families"] == 0


# --------------------------------------------------------------------------- #
# 6) Tier T1/T2 uniquement, JAMAIS T3.                                        #
# --------------------------------------------------------------------------- #
def test_tier_t1_t2_never_t3():
    multi = _adversary_network()
    queue = compute_channel_queue(multi, top_k=50)
    for c in queue["channels"]:
        assert c["tier"] in {"T1", "T2"}
        assert c["tier"] != "T3"
        # T2 ssi le verrou multi-source est franchi.
        assert (c["tier"] == "T2") == c["gate"]["met"]


# --------------------------------------------------------------------------- #
# 7) Forme du bloc queue = clés de l'échantillon JSON.                        #
# --------------------------------------------------------------------------- #
def test_queue_shape_matches_sample_contract():
    multi = _adversary_network()
    queue = compute_channel_queue(multi, top_k=50)

    # Clés du bloc queue (générées ici ; generated_at ajouté par l'API).
    for key in ("coverage_callout", "top_k", "hidden", "symmetric_ratio", "channels"):
        assert key in queue
    assert "generated_at" not in queue  # estampillé par l'API
    assert set(queue["symmetric_ratio"]) >= {"adversary_infra", "organic_fr", "note"}

    chan = queue["channels"][0]
    expected_keys = {
        "channel_id",
        "username",
        "title",
        "suspicion",
        "archetype",
        "credibility_prior",
        "fr_score",
        "reforward_from",
        "scores",
        "confidence",
        "gate",
        "tier",
    }
    assert expected_keys <= set(chan)
    assert set(chan["suspicion"]) == {"v", "lo", "hi"}
    assert set(chan["reforward_from"]) == {"suspect", "legit", "other"}
    assert set(chan["gate"]) == {"met", "families", "gate_families", "detail"}

    # Familles a–e présentes, avec couleurs hex EXACTES de l'échantillon.
    scores = chan["scores"]
    assert set(scores) == {"a", "b", "c", "d", "e"}
    assert scores["a"]["c"] == "#3B82F6"
    assert scores["b"]["c"] == "#F0B429"
    assert scores["c"]["c"] == "#22c55e"
    assert scores["d"]["c"] == "#ef4444"
    assert scores["e"]["c"] == "#a78bfa"
    # a et e sont N/A en v0.
    assert scores["a"]["na"] is True
    assert scores["e"]["na"] is True
    # chaque famille a n/v/lo/hi/c/ev.
    for f in scores.values():
        assert {"n", "v", "lo", "hi", "c", "ev"} <= set(f)
        assert isinstance(f["ev"], list)

    # confidence dérive un niveau ok/degraded.
    assert chan["confidence"]["level"] in {"ok", "degraded"}


def test_coverage_callout_present():
    multi = _adversary_network()
    queue = compute_channel_queue(multi, top_k=50)
    assert queue["coverage_callout"]
    assert len(queue["coverage_callout"]) > 10


def test_top_k_truncation_and_hidden():
    # 6 canaux en étoile autour d'une origine -> top_k=3 -> hidden=3.
    chans = [channel_row(i, username=f"c{i}", fr_score=0.05) for i in range(10, 17)]
    edges = [
        edge_row(10, dst_channel=i, etype="FORWARD", count=i, delay_seconds=100)
        for i in range(11, 17)
    ]
    multi = build_graph(edges, chans)
    queue = compute_channel_queue(multi, top_k=3)
    assert queue["top_k"] == 3
    assert len(queue["channels"]) == 3
    assert queue["hidden"] == 7 - 3  # 7 canaux totaux, 3 affichés
    # tri décroissant par suspicion.
    vals = [c["suspicion"]["v"] for c in queue["channels"]]
    assert vals == sorted(vals, reverse=True)


# --------------------------------------------------------------------------- #
# 8) Graphe vide -> queue vide.                                               #
# --------------------------------------------------------------------------- #
def test_empty_graph_yields_empty_queue():
    multi = build_graph([], [])
    queue = compute_channel_queue(multi, top_k=50)
    assert queue["channels"] == []
    assert queue["hidden"] == 0
    assert queue["symmetric_ratio"]["adversary_infra"] == 0.0
    # le callout de couverture reste présent même à vide.
    assert queue["coverage_callout"]


# --------------------------------------------------------------------------- #
# 9) Seam : injection de claim_proximity (a).                                 #
# --------------------------------------------------------------------------- #
def test_claim_proximity_seam_injection():
    multi = _adversary_network()
    queue = compute_channel_queue(multi, top_k=50, claim_proximity={1001: 0.8})
    by_id = {c["channel_id"]: c for c in queue["channels"]}
    a = by_id[1001]["scores"]["a"]
    assert a.get("na") is not True
    assert a["v"] == 0.8
    # Un canal sans valeur fournie garde (a) en N/A.
    assert by_id[1002]["scores"]["a"]["na"] is True


# --------------------------------------------------------------------------- #
# 10) channel_archetypes helper (endpoint voisinage).                         #
# --------------------------------------------------------------------------- #
def test_channel_archetypes_helper():
    multi = _adversary_network()
    arch = channel_archetypes(multi)
    # L'origine 1001 (relayée) a un archétype.
    assert 1001 in arch
    assert arch[1001] in {
        "seeding-source",
        "forward-hub",
        "cross-channel-bridge",
        "reactivator",
    }


# --------------------------------------------------------------------------- #
# 11) score_coordination_edges : règle des >= 2 types distincts.              #
# --------------------------------------------------------------------------- #
def test_coordination_edges_two_distinct_types_reinforced():
    # 1002 participe à CO_FORWARD + CO_URL -> renfort ; 1004 à un seul type.
    multi = _adversary_network()
    res = score_coordination_edges(multi, window_delta_seconds=72 * 3600)

    assert 1002 in res
    ev = res[1002].evidence
    assert ev["distinct_type_count"] >= 2
    assert ev["multi_type_reinforced"] is True
    # déclenchement éligible au verrou (renfort multi-type + valeur >= seuil).
    assert res[1002].triggered is True

    # 1004 ne participe qu'à un seul type (CO_FORWARD) -> pas de renfort.
    assert 1004 in res
    ev4 = res[1004].evidence
    assert ev4["distinct_type_count"] == 1
    assert ev4["multi_type_reinforced"] is False
    assert res[1004].triggered is False  # un seul type -> jamais gate-eligible


def test_coordination_edges_window_filters_out_late_pairs():
    # Une arête CO_FORWARD au-delà de la fenêtre est ignorée.
    chans = [channel_row(1, fr_score=0.05), channel_row(2, fr_score=0.05)]
    edges = [
        edge_row(1, dst_channel=2, etype="CO_FORWARD", count=3, window_delta_seconds=10**7),
    ]
    multi = build_graph(edges, chans)
    res = score_coordination_edges(multi, window_delta_seconds=72 * 3600)
    # Δt 10^7 s >> fenêtre 72h -> aucune coordination retenue.
    assert res == {} or all(r.value == 0.0 for r in res.values())


def test_coordination_edges_ignores_domain_nodes():
    # CITES_DOMAIN n'est pas une arête de coordination : le canal reçoit une
    # valeur 0 (présence uniforme pour le dénominateur), mais AUCUN type de
    # coordination -> non déclenché. Le nœud domaine, lui, n'est jamais scoré.
    chans = [channel_row(1, fr_score=0.05)]
    edges = [edge_row(1, dst_domain="geopolitika.ru", etype="CITES_DOMAIN", count=5)]
    multi = build_graph(edges, chans)
    res = score_coordination_edges(multi)
    assert set(res) == {1}  # le domaine n'apparaît pas
    assert res[1].value == 0.0
    assert res[1].triggered is False
    assert res[1].evidence["distinct_type_count"] == 0
    assert res[1].evidence["coordination_types"] == []


# --------------------------------------------------------------------------- #
# 12) adversary domains : matching exact + sous-domaine.                      #
# --------------------------------------------------------------------------- #
def test_adversary_domain_subdomain_match():
    chans = [channel_row(1, fr_score=0.05)]
    edges = [
        edge_row(1, dst_domain="news.geopolitika.ru", etype="CITES_DOMAIN", count=2),
        edge_row(1, dst_domain="example.com", etype="CITES_DOMAIN", count=9),
    ]
    multi = build_graph(edges, chans)
    adv = adversary_domain_citations(multi)
    assert 1 in adv
    # sous-domaine adverse compté ; domaine neutre ignoré.
    assert adv[1]["count"] == 2
    assert "news.geopolitika.ru" in adv[1]["domains"]
    assert "geopolitika.ru" in ADVERSARY_DOMAINS


# --------------------------------------------------------------------------- #
# 13) RÉGRESSIONS revue de code (Vague C).                                    #
# --------------------------------------------------------------------------- #
def test_forward_digraph_excludes_self_loop():
    """P7 : une arête FORWARD self-loop (src==dst) n'entre pas dans le forward
    (sinon elle gonfle artificiellement cascade/récidivisme)."""
    edges = [
        edge_row(1, dst_channel=1, etype="FORWARD", count=9, delay_seconds=100),
        edge_row(1, dst_channel=2, etype="FORWARD", count=3, delay_seconds=200),
    ]
    multi = build_graph(edges, [channel_row(1), channel_row(2)])
    fwd = forward_digraph(multi)
    assert not fwd.has_edge(1, 1)  # self-loop exclu
    assert fwd.has_edge(1, 2)


def test_negative_top_k_yields_empty_not_wrong_slice():
    """P1 : un top_k négatif est clampé à 0 (et non un slice Python rows[:-n]
    qui afficherait total+top_k canaux en droppant les MOINS suspects)."""
    multi = _adversary_network()  # 4 canaux
    queue = compute_channel_queue(multi, top_k=-2)
    assert queue["channels"] == []
    assert queue["top_k"] == 0
    assert queue["hidden"] == 4


def test_symmetric_ratio_independent_of_top_k():
    """P2 : le ratio symétrique (transparence EIP) est calculé sur la POPULATION
    COMPLÈTE, donc indépendant du paramètre d'affichage top_k."""
    chans = [
        channel_row(1, username="adv", fr_score=0.02),    # suspect (fr<0.15)
        channel_row(2, username="adv2", fr_score=0.03),   # suspect
        channel_row(3, username="news", fr_score=0.80),   # other
        channel_row(4, username="news2", fr_score=0.90),  # other
    ]
    edges = [  # seul le sous-réseau adverse a un rôle -> remonte en tête
        edge_row(1, dst_channel=2, etype="FORWARD", count=20, delay_seconds=600),
        edge_row(1, dst_channel=2, etype="CO_FORWARD", count=4, window_delta_seconds=600),
        edge_row(1, dst_channel=2, etype="CO_URL", count=3, window_delta_seconds=800),
    ]
    multi = build_graph(edges, chans)
    q_top1 = compute_channel_queue(multi, top_k=1)
    q_all = compute_channel_queue(multi, top_k=50)
    # 2 suspects / 4 au total = 0.5, que l'on affiche 1 ou 50 canaux.
    assert q_all["symmetric_ratio"]["adversary_infra"] == 0.5
    assert q_top1["symmetric_ratio"]["adversary_infra"] == 0.5


def test_coordination_none_delta_does_not_reinforce_gate():
    """P3 : une arête de coordination à Δt None (malformée) ne compte PAS vers
    le verrou >= 2 types et ne déclenche pas la coordination."""
    chans = [channel_row(1, fr_score=0.05), channel_row(2, fr_score=0.05)]
    edges = [
        edge_row(1, dst_channel=2, etype="CO_URL", count=3, window_delta_seconds=600),
        edge_row(1, dst_channel=2, etype="CO_FORWARD", count=4, window_delta_seconds=None),
    ]
    multi = build_graph(edges, chans)
    res = score_coordination_edges(multi, window_delta_seconds=72 * 3600)
    ev = res[1].evidence
    assert ev["distinct_type_count"] == 1  # seul CO_URL (Δt valide) compte
    assert "CO_URL" in ev["coordination_types"]
    assert "CO_FORWARD" not in ev["coordination_types"]
    assert ev["multi_type_reinforced"] is False
    assert res[1].triggered is False


def test_coordination_family_present_even_without_coordination_edge():
    """P4 : la famille (c) est PRÉSENTE (value 0, pas N/A) même sans arête de
    coordination -> dénominateur de combinaison UNIFORME (comparabilité)."""
    chans = [channel_row(1, fr_score=0.05), channel_row(2, fr_score=0.05)]
    edges = [edge_row(1, dst_channel=2, etype="FORWARD", count=10, delay_seconds=100)]
    multi = build_graph(edges, chans)
    queue = compute_channel_queue(multi, top_k=50)
    by_id = {c["channel_id"]: c for c in queue["channels"]}
    for cid in (1, 2):
        c_fam = by_id[cid]["scores"]["c"]
        assert c_fam["v"] == 0.0
        assert c_fam.get("na") is not True
        # (c) compte dans le dénominateur de combinaison (composant non-na).
        assert by_id[cid]["_components"]["c"].get("na") is not True


def test_confidence_bad_polled_at_is_degraded_not_ok():
    """P6 : une date last_polled_at corrompue -> conservateur « degraded »,
    pas « ok » (ne pas faire passer une date invalide pour fraîche)."""
    from src.scorer.channel_suspicion import _confidence

    out = _confidence({"last_polled_at": "not-a-date"})
    assert out["level"] == "degraded"
    assert out["reason"] == "unknown_polled_at"
    # Absence de méta / de date -> ok (comportement inchangé).
    assert _confidence(None)["level"] == "ok"
    assert _confidence({"last_polled_at": None})["level"] == "ok"


# --------------------------------------------------------------------------- #
# 14) france_targeting : modulateur de sévérité MONTANT, MULTIPLICATIF,        #
#     BORNÉ, qui NE FILTRE JAMAIS (MÉTA-CONTRAINTE 1).                          #
# --------------------------------------------------------------------------- #
def test_france_targeting_raises_severity_on_suspect_channel():
    """Le même réseau coordonné, scoré AVEC vs SANS france_targeting > 0 :
    la suspicion d'un canal DÉJÀ suspect est strictement plus haute avec."""
    multi = _signal_network()

    base = compute_channel_queue(multi, top_k=50, profile=_FAST)
    boosted = compute_channel_queue(
        multi, top_k=50, france_targeting={100: 0.9}, profile=_FAST
    )
    base_by_id = {c["channel_id"]: c for c in base["channels"]}
    boost_by_id = {c["channel_id"]: c for c in boosted["channels"]}

    # 100 (hub) a une base non nulle (forward-influence significative) -> MONTE.
    assert 0.0 < base_by_id[100]["suspicion"]["v"] < 1.0
    assert (
        boost_by_id[100]["suspicion"]["v"]
        > base_by_id[100]["suspicion"]["v"]
    )
    # Le facteur de sévérité reflète bien le boost France.
    sev = boost_by_id[100]["_components"]["_severity_detail"]
    assert sev["france_targeting"] == 0.9
    assert sev["france_boost"] > 0.0


def test_france_targeting_multiplicative_does_not_promote_base_zero():
    """GARDE MULTIPLICATIVE (presse FR légitime non promue) : un canal SANS
    rôle (suspicion de base 0) et france_targeting = 1.0 reste à 0.0 —
    le modulateur est multiplicatif, il n'amplifie qu'un score déjà non nul."""
    chans = [
        channel_row(7001, username="legit_fr_news", fr_score=0.95),
        channel_row(7002, username="other", fr_score=0.05),
    ]
    # 7001 n'a AUCUNE arête -> aucun rôle structurel -> base 0.
    edges = [
        edge_row(7002, dst_channel=7002, etype="FORWARD", count=1, delay_seconds=10),
    ]
    multi = build_graph(edges, chans)
    queue = compute_channel_queue(
        multi, top_k=50, france_targeting={7001: 1.0}
    )
    by_id = {c["channel_id"]: c for c in queue["channels"]}

    # france_targeting maximal MAIS base 0 -> suspicion reste 0 (multiplicatif).
    assert by_id[7001]["suspicion"]["v"] == 0.0
    # Le champ est bien renseigné (affichage), et le facteur a bien gonflé...
    assert by_id[7001]["france_targeting"] == 1.0
    assert by_id[7001]["_components"]["_severity_factor"] > 1.0
    # ... mais 0 * facteur = 0. La presse FR légitime n'est PAS promue.


def test_france_targeting_bounded_factor():
    """Le facteur de sévérité ne dépasse JAMAIS le plafond cumulé des trois
    boosts montants (reforward + adverse + France)."""
    from src.scorer.channel_suspicion import _severity_modulation

    max_factor = (
        1.0
        + MAX_REFORWARD_BOOST
        + MAX_ADVERSARY_DOMAIN_BOOST
        + MAX_FRANCE_TARGETING_BOOST
    )
    # Tous les signaux à fond (reforward 100 % suspect, citations >> saturation,
    # france_targeting 1.0, et même au-delà pour tester le clamp).
    factor, detail = _severity_modulation(
        {"suspect": 1.0, "legit": 0.0, "other": 0.0},
        {"count": 9999, "domains": ["geopolitika.ru"]},
        2.0,  # > 1.0 -> clampé à 1.0
    )
    assert factor <= max_factor + 1e-9
    assert factor == max_factor  # tous les boosts saturés -> plafond exact
    assert detail["france_targeting"] == 1.0  # clamp01 appliqué


def test_france_targeting_never_filters_any_channel():
    """france_targeting sur SEULEMENT certains canaux : TOUS les canaux du
    réseau restent dans la file (aucun n'est exclu/filtré) — MÉTA-CONTRAINTE 1.
    Un canal non-ciblant-France garde une suspicion non nulle si elle l'était."""
    multi = _signal_network()
    # France-targeting seulement sur le hub 100 ; les autres absents de la map.
    queue = compute_channel_queue(
        multi, top_k=50, france_targeting={100: 0.8}, profile=_FAST
    )
    ids = {c["channel_id"] for c in queue["channels"]}
    # Aucun canal n'est droppé : toute la population reste présente.
    assert {100, 201, 202, 203} <= ids
    n_channels = sum(1 for _ in multi.nodes(data="kind") if _[1] != "domain")
    assert len(ids) == n_channels

    by_id = {c["channel_id"]: c for c in queue["channels"]}
    # Canal absent de la map -> france_targeting None, mais toujours présent.
    assert by_id[201]["france_targeting"] is None
    # Et un canal non-ciblant-France qui avait du signal le garde (hub d-signif).
    assert by_id[100]["suspicion"]["v"] > 0.0


def test_france_targeting_none_is_backward_compatible():
    """RÉGRESSION : france_targeting=None -> scores IDENTIQUES à l'existant
    (rétro-compat ; le seam mort ne change rien quand non fourni)."""
    multi = _adversary_network()
    without = compute_channel_queue(multi, top_k=50)
    none_explicit = compute_channel_queue(multi, top_k=50, france_targeting=None)

    w_by_id = {c["channel_id"]: c["suspicion"] for c in without["channels"]}
    n_by_id = {c["channel_id"]: c["suspicion"] for c in none_explicit["channels"]}
    assert w_by_id == n_by_id  # bit-pour-bit identique


def test_france_targeting_field_present_and_equals_injected():
    """Le champ par-canal ``france_targeting`` est présent et vaut la valeur
    injectée (ou None si non fournie)."""
    multi = _adversary_network()
    queue = compute_channel_queue(
        multi, top_k=50, france_targeting={1001: 0.42, 1003: 0.0}
    )
    by_id = {c["channel_id"]: c for c in queue["channels"]}

    # Champ présent partout.
    for c in queue["channels"]:
        assert "france_targeting" in c

    assert by_id[1001]["france_targeting"] == 0.42
    assert by_id[1003]["france_targeting"] == 0.0  # 0.0 explicite préservé
    assert by_id[1002]["france_targeting"] is None  # absent de la map -> None
    assert by_id[1004]["france_targeting"] is None


# --------------------------------------------------------------------------- #
# 15) top_k=None = univers complet (matérialisation build_scores).            #
# --------------------------------------------------------------------------- #
def test_compute_channel_queue_top_k_none_returns_all():
    """top_k=None => TOUS les canaux, sans troncature (pour build_scores) ;
    top_k=N tronque toujours. Le ratio symétrique (population complète) est
    identique dans les deux cas."""
    multi = _adversary_network()  # 4 canaux
    full = compute_channel_queue(multi, top_k=None)
    capped = compute_channel_queue(multi, top_k=2)

    assert len(full["channels"]) == 4
    assert full["hidden"] == 0
    assert len(capped["channels"]) == 2
    assert capped["hidden"] == 2
    assert (
        full["symmetric_ratio"]["adversary_infra"]
        == capped["symmetric_ratio"]["adversary_infra"]
    )
