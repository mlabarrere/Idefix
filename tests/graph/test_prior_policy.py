"""credibility_prior — prior adossé aux preuves (défaut D1), pur, SANS DB.

Le prior dérivait de la densité de mots-clés français (``fr_score < 0.15``),
ce qui faisait du classement un classement par langue. Il s'adosse désormais au
catalogue d'infrastructure adverse documentée. Ces tests VERROUILLENT la
propriété qui manquait : **la langue n'influence plus le prior**.

Voir docs/limitations.md D1.
"""
from src.graph.loader import (
    adversary_citation_counts,
    build_graph,
    credibility_prior,
    make_prior_policy,
    neutral_prior,
)

ADV = frozenset({"pravda-fr.com", "rrn.media"})


def _cites(src, domain):
    return {
        "src_channel_id": src,
        "dst_channel_id": None,
        "dst_domain": domain,
        "edge_type": "CITES_DOMAIN",
        "count": 1,
        "weight": 1.0,
    }


# --------------------------------------------------------------------------- #
# La fonction de prior elle-même.
# --------------------------------------------------------------------------- #
def test_citing_documented_adversary_infra_is_suspect():
    assert credibility_prior({"adversary_domain_citations": 1}) == "suspect"
    assert credibility_prior({"adversary_domain_citations": 7}) == "suspect"


def test_channel_in_the_catalogue_is_suspect():
    assert credibility_prior({"catalogued_adversary": True}) == "suspect"


def test_absence_of_evidence_is_not_suspicion():
    assert credibility_prior({}) == "other"
    assert credibility_prior({"adversary_domain_citations": 0}) == "other"
    assert credibility_prior({"catalogued_adversary": False}) == "other"


def test_neutral_prior_never_marks_anyone():
    assert neutral_prior({"adversary_domain_citations": 99}) == "other"
    assert neutral_prior({"catalogued_adversary": True}) == "other"


def test_make_prior_policy_switch():
    assert make_prior_policy(True) is credibility_prior
    assert make_prior_policy(False) is neutral_prior


# --------------------------------------------------------------------------- #
# La preuve : comptage des citations adverses.
# --------------------------------------------------------------------------- #
def test_adversary_citation_counts_distinct_domains():
    edges = [
        _cites(1, "pravda-fr.com"),
        _cites(1, "pravda-fr.com"),  # doublon -> ne compte qu'une fois
        _cites(1, "rrn.media"),
        _cites(2, "lemonde.fr"),     # hors catalogue
    ]
    counts = adversary_citation_counts(edges, ADV)
    assert counts == {1: 2}


def test_adversary_citation_counts_is_case_insensitive():
    assert adversary_citation_counts([_cites(1, "PRAVDA-FR.com")], ADV) == {1: 1}


def test_no_catalogue_means_no_evidence():
    assert adversary_citation_counts([_cites(1, "pravda-fr.com")], frozenset()) == {}


# --------------------------------------------------------------------------- #
# Intégration dans build_graph — le point qui portait le défaut.
# --------------------------------------------------------------------------- #
def _rows():
    return [
        # Écrit en français, mais cite l'infra adverse -> suspect sur PREUVE.
        {"channel_id": 1, "username": "fr_citing_adv", "fr_score": 0.95},
        # N'écrit pas français, ne cite rien de documenté -> PAS suspect.
        {"channel_id": 2, "username": "ru_clean", "fr_score": 0.0},
    ]


def test_prior_follows_evidence_not_language():
    """LE test de non-régression du défaut D1.

    Sous l'ancien prior, le canal 1 (fr_score 0.95) était « other » et le canal
    2 (fr_score 0.0) était « suspect » — l'exact inverse de la preuve.
    """
    g = build_graph([_cites(1, "pravda-fr.com")], _rows(), adversary_domains=ADV)
    assert g.nodes[1]["credibility_prior"] == "suspect"
    assert g.nodes[2]["credibility_prior"] == "other"


def test_fr_score_alone_never_marks_a_channel_suspect():
    """fr_score redevient ce que la doc prétendait : un champ d'affichage."""
    g = build_graph([], _rows(), adversary_domains=ADV)
    assert all(
        g.nodes[n]["credibility_prior"] == "other" for n in (1, 2)
    ), "aucune preuve adverse => aucun canal suspect, quelle que soit la langue"
    # …mais fr_score reste exposé pour l'affichage.
    assert g.nodes[1]["fr_score"] == 0.95
    assert g.nodes[2]["fr_score"] == 0.0


def test_catalogued_adversary_by_username():
    g = build_graph(
        [], _rows(), catalogued_adversaries=frozenset({"@RU_CLEAN"})
    )
    assert g.nodes[2]["credibility_prior"] == "suspect"
    assert g.nodes[1]["credibility_prior"] == "other"


def test_build_graph_neutral_prior_for_gan():
    g = build_graph(
        [_cites(1, "pravda-fr.com")],
        _rows(),
        prior_policy=make_prior_policy(False),
        adversary_domains=ADV,
    )
    # GAN : aucune présomption de suspicion, même avec la preuve.
    assert g.nodes[1]["credibility_prior"] == "other"
    assert g.nodes[2]["credibility_prior"] == "other"


def test_edge_rows_may_be_a_generator():
    """build_graph parcourt les arêtes deux fois : un générateur doit passer."""
    g = build_graph(
        (e for e in [_cites(1, "pravda-fr.com")]), _rows(), adversary_domains=ADV
    )
    assert g.nodes[1]["credibility_prior"] == "suspect"
    assert g.has_edge(1, "pravda-fr.com")
