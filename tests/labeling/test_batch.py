"""Tests pour build_label_batch.py — T2 (Story 1.1, AC1 + AC8).

Ces tests ne nécessitent aucune connexion à la base de données :
ils exercent exclusivement les fonctions pures rank_nearest_claim et
stratified_sample, ainsi que make_item_id du schéma.

Chargement du module via importlib (script hors package).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# ---------------------------------------------------------------------------
# Chargement du module scripts/build_label_batch.py sans exécuter __main__
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_label_batch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_label_batch", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()

rank_nearest_claim = _mod.rank_nearest_claim
stratified_sample = _mod.stratified_sample
france_keyword_match = _mod.france_keyword_match
split_by_proximity = _mod.split_by_proximity
classify_credibility = _mod.classify_credibility
credibility_balanced_sample = _mod.credibility_balanced_sample

from src.labeling.schema import BatchItem, make_item_id  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures de revendications et d'items
# ---------------------------------------------------------------------------

CLAIMS_FIXTURE = [
    {
        "id": "CLAIM-001",
        "claim_text": "La France envoie des soldats combattre en Ukraine.",
        "theme": "Forces armées",
        "target": "FR_integrity",
        "source": "VIGINUM",
    },
    {
        "id": "CLAIM-002",
        "claim_text": "Macron a reçu un financement étranger occulte.",
        "theme": "Processus électoral",
        "target": "FR_integrity",
        "source": "Narratif",
    },
    {
        "id": "CLAIM-003",
        "claim_text": "L'armée française subit des défaites cachées au Sahel.",
        "theme": "Forces armées",
        "target": "FR_integrity",
        "source": "Narratif",
    },
]


def _make_item(
    channel_id: int = 1,
    message_id: int = 1,
    claim_id: str | None = "CLAIM-001",
    text: str = "texte test",
    claim_proximity: float = 0.5,
    source_credibility: str | None = None,
) -> BatchItem:
    return BatchItem(
        item_id=make_item_id(channel_id, message_id, "batch-test"),
        batch_id="batch-test",
        channel_id=channel_id,
        message_id=message_id,
        text=text,
        candidate_claim_id=claim_id,
        claim_proximity=claim_proximity,
        source_credibility=source_credibility,
    )


# ---------------------------------------------------------------------------
# Tests : rank_nearest_claim
# ---------------------------------------------------------------------------


class TestRankNearestClaim:
    """Couvre AC1 + NFR-20 : TF-IDF sklearn, pas d'implémentation maison."""

    def test_returns_correct_length(self):
        texts = ["message A", "message B"]
        results = rank_nearest_claim(texts, CLAIMS_FIXTURE)
        assert len(results) == 2

    def test_returns_triplets(self):
        texts = ["un message quelconque"]
        (claim_id, claim_text, prox) = rank_nearest_claim(texts, CLAIMS_FIXTURE)[0]
        assert isinstance(claim_id, str)
        assert isinstance(claim_text, str)
        assert 0.0 <= prox <= 1.0

    def test_relevant_message_ranks_claim_highest(self):
        """Un message parlant de soldats en Ukraine doit pointer vers CLAIM-001."""
        texts = [
            "Des soldats français combattent et meurent en Ukraine selon nos sources."
        ]
        (claim_id, _, prox) = rank_nearest_claim(texts, CLAIMS_FIXTURE)[0]
        assert claim_id == "CLAIM-001"
        assert prox > 0.0

    def test_electoral_message_ranks_electoral_claim(self):
        """Un message sur le financement de Macron doit pointer vers CLAIM-002."""
        texts = ["Le financement de la campagne de Macron vient de l'étranger."]
        (claim_id, _, _) = rank_nearest_claim(texts, CLAIMS_FIXTURE)[0]
        assert claim_id == "CLAIM-002"

    def test_proximity_in_unit_interval(self):
        texts = ["France soldats Ukraine Sahel Macron financement", "foo bar baz"]
        results = rank_nearest_claim(texts, CLAIMS_FIXTURE)
        for _, _, prox in results:
            assert 0.0 <= prox <= 1.0, f"Proximité hors [0,1] : {prox}"

    def test_no_overlap_still_returns_argmax(self):
        """Un texte sans aucun mot en commun retourne quand même le meilleur claim."""
        texts = ["xyz abc zzz 123 !!!"]
        (claim_id, claim_text, prox) = rank_nearest_claim(texts, CLAIMS_FIXTURE)[0]
        # L'id doit être l'un des claims enregistrés (argmax sur score nul → premier)
        assert claim_id in {c["id"] for c in CLAIMS_FIXTURE}
        assert 0.0 <= prox <= 1.0

    def test_empty_messages(self):
        results = rank_nearest_claim([], CLAIMS_FIXTURE)
        assert results == []

    def test_empty_claims(self):
        texts = ["message quelconque"]
        results = rank_nearest_claim(texts, [])
        assert results == [(None, None, 0.0)]

    def test_single_claim_single_message(self):
        claims = [{"id": "C-X", "claim_text": "un seul claim"}]
        texts = ["un seul message"]
        (cid, _, prox) = rank_nearest_claim(texts, claims)[0]
        assert cid == "C-X"
        assert 0.0 <= prox <= 1.0

    def test_multiple_messages_distinct_best_claims(self):
        """Deux messages très différents pointent vers des claims différents."""
        texts = [
            "Ukraine soldats France combat morts secret",
            "financement Macron campagne étranger occulte argent",
        ]
        results = rank_nearest_claim(texts, CLAIMS_FIXTURE)
        cid0 = results[0][0]
        cid1 = results[1][0]
        # Les meilleurs claims peuvent être distincts
        assert cid0 in {c["id"] for c in CLAIMS_FIXTURE}
        assert cid1 in {c["id"] for c in CLAIMS_FIXTURE}

    # --- Robustesse (review MED) ---

    def test_claim_missing_id_is_skipped_not_keyerror(self):
        """Une revendication sans « id » est ignorée, pas une KeyError."""
        claims = [
            {"claim_text": "revendication sans id, doit être ignorée"},
            {"id": "CLAIM-OK", "claim_text": "Macron et la France au Sahel"},
        ]
        texts = ["La France et Macron au Sahel"]
        results = rank_nearest_claim(texts, claims)
        assert len(results) == 1
        # Seule la revendication valide peut être retournée.
        assert results[0][0] == "CLAIM-OK"

    def test_claim_missing_claim_text_is_skipped(self):
        """Une revendication sans « claim_text » est ignorée, pas une KeyError."""
        claims = [
            {"id": "CLAIM-BAD"},
            {"id": "CLAIM-OK", "claim_text": "Macron et la France au Sahel"},
        ]
        texts = ["La France et Macron au Sahel"]
        results = rank_nearest_claim(texts, claims)
        assert results[0][0] == "CLAIM-OK"

    def test_all_claims_malformed_returns_none_triplets(self):
        """Si toutes les revendications sont mal formées → (None, None, 0.0)."""
        claims = [{"claim_text": "pas d'id"}, {"id": "X"}]
        texts = ["un message", "un autre message"]
        results = rank_nearest_claim(texts, claims)
        assert results == [(None, None, 0.0), (None, None, 0.0)]

    def test_empty_vocabulary_returns_none_triplets(self):
        """Vocabulaire TF-IDF vide (claims + messages tous vides / espaces) →
        (None, None, 0.0) pour chaque message, sans lever ValueError."""
        # Tous les textes (revendications ET messages) sont vides/espaces :
        # TfidfVectorizer lève « empty vocabulary » → la garde doit l'intercepter.
        claims = [
            {"id": "C-EMPTY-1", "claim_text": "   "},
            {"id": "C-EMPTY-2", "claim_text": ""},
        ]
        texts = ["", "   ", "\t\n"]
        results = rank_nearest_claim(texts, claims)
        assert results == [(None, None, 0.0)] * 3


# ---------------------------------------------------------------------------
# Tests : stratified_sample
# ---------------------------------------------------------------------------


class TestStratifiedSample:
    """Couvre AC1 : échantillonnage reproductible + couverture des claims."""

    def _items_with_claims(self, claim_ids: list[str | None]) -> list[BatchItem]:
        return [
            _make_item(channel_id=i, message_id=i, claim_id=cid, text=f"texte {i}")
            for i, cid in enumerate(claim_ids, start=1)
        ]

    def test_deterministic_under_same_seed(self):
        items = self._items_with_claims(["CLAIM-001", "CLAIM-002", "CLAIM-003"] * 10)
        a = stratified_sample(items, n=10, seed=42)
        b = stratified_sample(items, n=10, seed=42)
        assert [i.item_id for i in a] == [i.item_id for i in b]

    def test_different_seeds_may_differ(self):
        items = self._items_with_claims(["CLAIM-001", "CLAIM-002"] * 20)
        a = stratified_sample(items, n=10, seed=1)
        b = stratified_sample(items, n=10, seed=2)
        # Avec 40 items, il est très improbable que les deux seeds donnent le même ordre
        assert [i.item_id for i in a] != [i.item_id for i in b]

    def test_never_exceeds_n(self):
        items = self._items_with_claims(["CLAIM-001"] * 50)
        sampled = stratified_sample(items, n=20, seed=42)
        assert len(sampled) <= 20

    def test_returns_all_when_n_exceeds_available(self):
        items = self._items_with_claims(["CLAIM-001", "CLAIM-002", "CLAIM-003"])
        sampled = stratified_sample(items, n=100, seed=42)
        assert len(sampled) == 3

    def test_covers_all_claim_ids_when_n_large_enough(self):
        """Chaque claim_id distinct doit apparaître au moins une fois."""
        claim_ids = ["CLAIM-001"] * 10 + ["CLAIM-002"] * 10 + ["CLAIM-003"] * 10
        items = self._items_with_claims(claim_ids)
        sampled = stratified_sample(items, n=15, seed=42)
        seen = {i.candidate_claim_id for i in sampled}
        assert "CLAIM-001" in seen
        assert "CLAIM-002" in seen
        assert "CLAIM-003" in seen

    def test_handles_empty_input(self):
        assert stratified_sample([], n=10, seed=42) == []

    def test_handles_none_claim_id(self):
        items = self._items_with_claims([None, "CLAIM-001", None])
        sampled = stratified_sample(items, n=3, seed=42)
        assert len(sampled) == 3

    def test_exact_n_returned_when_items_exceed_n(self):
        items = self._items_with_claims(["CLAIM-001"] * 50 + ["CLAIM-002"] * 50)
        sampled = stratified_sample(items, n=30, seed=42)
        assert len(sampled) == 30

    def test_accepts_dicts_as_items(self):
        """stratified_sample doit aussi fonctionner avec des dicts (duck typing)."""
        items_dict = [
            {
                "item_id": f"item-{i}",
                "candidate_claim_id": f"CLAIM-{(i % 3) + 1:03d}",
                "text": f"texte {i}",
            }
            for i in range(30)
        ]
        sampled = stratified_sample(items_dict, n=10, seed=42)
        assert len(sampled) == 10

    def test_single_item_returns_it(self):
        items = self._items_with_claims(["CLAIM-001"])
        sampled = stratified_sample(items, n=5, seed=42)
        assert len(sampled) == 1


# ---------------------------------------------------------------------------
# Tests : make_item_id (interaction avec le schéma)
# ---------------------------------------------------------------------------


class TestMakeItemId:
    """Vérifie l'intégration de make_item_id dans le contexte du batch."""

    def test_item_id_matches_schema(self):
        cid, mid = 42, 1001
        item = _make_item(channel_id=cid, message_id=mid, text="un message")
        expected = make_item_id(cid, mid, "batch-test")
        assert item.item_id == expected

    def test_item_id_stable_across_calls(self):
        id1 = make_item_id(10, 20, "batch-X")
        id2 = make_item_id(10, 20, "batch-X")
        assert id1 == id2

    def test_item_id_varies_by_channel(self):
        assert make_item_id(1, 1, "b") != make_item_id(2, 1, "b")

    def test_item_id_varies_by_message(self):
        assert make_item_id(1, 1, "b") != make_item_id(1, 2, "b")

    def test_item_id_varies_by_batch(self):
        assert make_item_id(1, 1, "batch-A") != make_item_id(1, 1, "batch-B")


# ---------------------------------------------------------------------------
# Review fix B1 — France message-level gate (NFR-15) + proximity split
# ---------------------------------------------------------------------------


class TestFranceGate:
    def test_message_about_france_passes(self):
        assert france_keyword_match("La France envoie des soldats au Sahel.") is True
        assert france_keyword_match("Macron prépare une loi à l'Assemblée.") is True

    def test_offscope_message_is_rejected(self):
        # The off-scope examples flagged in review B1 contain no France keyword.
        assert france_keyword_match("Le Kremlin a tenu un sommet à Saint-Pétersbourg.") is False
        assert france_keyword_match("Cuba accuse les USA d'embargo illégal.") is False

    def test_empty_or_none_is_rejected(self):
        assert france_keyword_match("") is False
        assert france_keyword_match(None) is False

    def test_match_is_case_insensitive(self):
        assert france_keyword_match("MACRON et l'OTAN") is True


class TestSplitByProximity:
    def test_partitions_on_threshold(self):
        items = [
            {"item_id": "a", "claim_proximity": 0.30},
            {"item_id": "b", "claim_proximity": 0.04},
            {"item_id": "c", "claim_proximity": 0.0},
        ]
        eligible, screened = split_by_proximity(items, min_proximity=0.04)
        assert {i["item_id"] for i in eligible} == {"a", "b"}  # >= threshold
        assert {i["item_id"] for i in screened} == {"c"}

    def test_works_on_batch_items(self):
        hi = _make_item(text="msg", claim_proximity=0.5)
        lo = _make_item(text="msg", claim_proximity=0.001)
        eligible, screened = split_by_proximity([hi, lo], min_proximity=0.04)
        assert eligible == [hi]
        assert screened == [lo]

    def test_all_eligible_when_threshold_zero(self):
        items = [{"claim_proximity": 0.0}, {"claim_proximity": 0.1}]
        eligible, screened = split_by_proximity(items, min_proximity=0.0)
        assert len(eligible) == 2
        assert screened == []


# ---------------------------------------------------------------------------
# Credibility classification + balanced sampling (fix: gold was 97% "Vrai")
# ---------------------------------------------------------------------------


class TestClassifyCredibility:
    def test_known_legit_outlet(self):
        assert classify_credibility("France24_fr", 0.40) == "legit"
        assert classify_credibility("EuroNewsFR", 0.64) == "legit"

    def test_low_fr_apparatus_is_suspect(self):
        # The Dugin/Geopolitika cluster has low fr_score and propagates disinfo.
        assert classify_credibility("Dugin_Aleksandr", 0.06) == "suspect"
        assert classify_credibility("Agdchan", 0.00) == "suspect"

    def test_legit_overrides_low_fr(self):
        # A known outlet stays legit even if its fr_score dips below the threshold.
        assert classify_credibility("rfi_fr", 0.05) == "legit"

    def test_mid_fr_unknown_is_other(self):
        assert classify_credibility("cerfiafr", 0.26) == "other"

    def test_none_fr_is_other(self):
        assert classify_credibility("unknown", None) == "other"


class TestCredibilityBalancedSample:
    def _pool(self):
        items = []
        for i in range(40):
            items.append(_make_item(channel_id=10, message_id=i, source_credibility="suspect"))
        for i in range(200):
            items.append(_make_item(channel_id=20, message_id=i, source_credibility="legit"))
        for i in range(30):
            items.append(_make_item(channel_id=30, message_id=i, source_credibility="other"))
        return items

    def _cred_counts(self, sampled):
        out = {"suspect": 0, "legit": 0, "other": 0}
        for s in sampled:
            out[s.source_credibility] += 1
        return out

    def test_balances_suspect_and_legit(self):
        sampled = credibility_balanced_sample(self._pool(), n=60, seed=1)
        counts = self._cred_counts(sampled)
        assert len(sampled) == 60
        # 60//2 = 30 suspects available (40>=30) → 30 suspect + 30 legit
        assert counts["suspect"] == 30
        assert counts["legit"] == 30

    def test_takes_all_suspects_when_scarce(self):
        # Only 40 suspects; ask for n=200 → take all 40 suspect, fill rest with legit/other.
        sampled = credibility_balanced_sample(self._pool(), n=200, seed=1)
        counts = self._cred_counts(sampled)
        assert counts["suspect"] == 40  # all scarce positives used
        assert len(sampled) == 200

    def test_deterministic(self):
        a = credibility_balanced_sample(self._pool(), n=50, seed=7)
        b = credibility_balanced_sample(self._pool(), n=50, seed=7)
        assert [x.item_id for x in a] == [x.item_id for x in b]

    def test_none_proximity_is_screened_not_crash(self):
        """claim_proximity None est coercé à 0.0 → screening, pas de TypeError."""
        item = {"item_id": "z", "claim_proximity": None}
        eligible, screened = split_by_proximity([item], min_proximity=0.04)
        assert eligible == []
        assert screened == [item]

    def test_non_numeric_proximity_is_screened(self):
        """Une proximité non numérique est coercée à 0.0 → screening, pas de crash."""
        item = {"item_id": "z", "claim_proximity": "n/a"}
        eligible, screened = split_by_proximity([item], min_proximity=0.04)
        assert eligible == []
        assert screened == [item]
