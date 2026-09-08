"""compute_channel_queue paramétré par mission (profil GAN) — pur, SANS DB.

Vérifie : (1) le profil GAN fait apparaître les familles ``telegram_*`` dans le
contrat ``scores`` ; (2) le chemin par défaut (profile=None) reste limité à a–e
(zéro-régression) ; (3) MÉTA-CONTRAINTE 1 préservée (aucun canal filtré).
"""
import networkx as nx

from src.missions.registry import get
from src.scorer.channel_suspicion import compute_channel_queue


def _multi() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for cid, eng in ((1, 1000), (2, 50), (3, 5)):
        g.add_node(cid, kind="channel", username=f"c{cid}", title=f"C{cid}",
                   engagement=eng, credibility_prior="other", fr_score=None)
    g.add_node("geopolitika.ru", kind="domain")
    g.add_edge(1, 2, key="FORWARD", edge_type="FORWARD", family="propagation",
               count=5, delay_seconds=60)
    g.add_edge(1, 3, key="FORWARD", edge_type="FORWARD", family="propagation",
               count=2, delay_seconds=7200)
    g.add_edge(1, "geopolitika.ru", key="CITES_DOMAIN", edge_type="CITES_DOMAIN",
               family="influence", count=3)
    return g


def test_gan_profile_emits_telegram_families():
    m = get("gan")
    q = compute_channel_queue(_multi(), profile=m.scoring, top_k=50)
    by = {c["channel_id"]: c for c in q["channels"]}
    sc = by[1]["scores"]
    # Familles de graphe calculées.
    for fam in ("telegram_visibility", "telegram_velocity", "telegram_propagation",
                "telegram_source_diversity", "telegram_adverse_attention"):
        assert fam in sc, f"famille manquante: {fam}"
    # Visibilité du hub (engagement max) non nulle.
    assert sc["telegram_visibility"]["v"] > 0
    # Précision de divulgation présente mais N/A (aucun texte injecté ici).
    assert sc["telegram_disclosure_precision"].get("na") is True
    # Attention adverse : le canal 2 reçoit des forwards du canal 1 (qui cite un
    # domaine adverse) -> attention adverse = 1.0.
    assert by[2]["scores"]["telegram_adverse_attention"]["v"] == 1.0


def test_default_profile_has_no_telegram_families():
    q = compute_channel_queue(_multi(), top_k=50)
    for c in q["channels"]:
        assert set(c["scores"].keys()) == {"a", "b", "c", "d", "e"}


def test_gan_profile_never_filters_channels():
    m = get("gan")
    q = compute_channel_queue(_multi(), profile=m.scoring, top_k=50)
    # MÉTA-CONTRAINTE 1 : tous les canaux (3) restent présents.
    assert len({c["channel_id"] for c in q["channels"]}) == 3
