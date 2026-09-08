"""credibility_prior mission-aware (R1) — make_prior_policy + build_graph (pur, SANS DB)."""
from src.graph.loader import build_graph, credibility_prior, make_prior_policy


def test_default_policy_matches_credibility_prior():
    p = make_prior_policy(0.15)
    assert p(0.0) == "suspect"
    assert p(0.10) == "suspect"
    assert p(0.20) == "other"
    assert p(None) == "other"
    # équivalent à la fonction historique
    for v in (None, 0.0, 0.14, 0.15, 0.9):
        assert p(v) == credibility_prior(v)


def test_neutral_policy_for_none_threshold():
    p = make_prior_policy(None)  # cas GAN : prior neutre
    for v in (None, 0.0, 0.14, 0.9):
        assert p(v) == "other"


def _rows():
    return [
        {"channel_id": 1, "username": "a", "fr_score": 0.0},   # suspect en défaut
        {"channel_id": 2, "username": "b", "fr_score": 0.9},   # other
    ]


def test_build_graph_default_prior_unchanged():
    g = build_graph([], _rows())
    assert g.nodes[1]["credibility_prior"] == "suspect"
    assert g.nodes[2]["credibility_prior"] == "other"


def test_build_graph_neutral_prior_for_gan():
    g = build_graph([], _rows(), prior_policy=make_prior_policy(None))
    # GAN : aucun canal n'est marqué « suspect » par le prior (R1).
    assert g.nodes[1]["credibility_prior"] == "other"
    assert g.nodes[2]["credibility_prior"] == "other"
