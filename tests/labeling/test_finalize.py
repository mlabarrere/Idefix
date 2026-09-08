"""Tests pour finalize_gold.py — merge gold candidats + arbitrage humain.

Couvre les correctifs de revue :
  #1  l'arbitrage humain SUPPLANTE un candidat auto pour le même item_id
      (n'est PAS compté comme conflit) ;
  #2  la confiance d'arbitrage n'est pas fabriquée (convention 1.0 = décidé-humain,
      jamais un 0.5 trompeur) ;
  + idempotence et conflit réel (même source-type, contenu différent → existant gardé).

Le module scripts/finalize_gold.py est chargé via importlib (script hors package),
comme tests/labeling/test_batch.py. On teste l'assistant pur ``merge_gold`` sans
toucher au vrai data/annotations/gold.jsonl ; un test de bout-en-bout monkeypatche
io.GOLD_FILE vers un tmp_path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# ---------------------------------------------------------------------------
# Chargement du module scripts/finalize_gold.py sans exécuter __main__
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "finalize_gold.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("finalize_gold", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_mod = _load_module()

merge_gold = _mod.merge_gold
ARBITRATED_DEFAULT_CONFIDENCE = _mod.ARBITRATED_DEFAULT_CONFIDENCE

from src.labeling import io  # noqa: E402

# ---------------------------------------------------------------------------
# Fabriques de lignes gold (dicts sérialisés, tels que produits par model_dump_json)
# ---------------------------------------------------------------------------


def _gold_row(
    item_id: str,
    verdict: str = "Faux",
    confidence: float = 0.9,
    rationale: str = "Démenti par AFP Factuel.",
    sources: list[str] | None = None,
    agreement: str = "unanimous",
    arbitrated: bool = False,
) -> dict:
    """Une ligne gold sérialisée minimale (forme dict, pas un GoldLabel)."""
    return {
        "item_id": item_id,
        "channel_id": 100,
        "message_id": 200,
        "candidate_claim_id": "CLAIM-001",
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
        "sources": sources if sources is not None else ["AFP Factuel"],
        "provenance": {
            "judges": ["juge-1", "juge-2"],
            "n_judges": 2,
            "agreement": agreement,
            "pairwise_kappa": 0.8,
            "arbitrated": arbitrated,
            "arbiter": "Micky" if arbitrated else None,
            "arbiter_note": "",
            "methodology_version_hash": "sha256:deadbeef0000",
        },
    }


# ---------------------------------------------------------------------------
# merge_gold — assistant pur
# ---------------------------------------------------------------------------


class TestMergeGoldPure:
    def test_empty_existing_plus_new_candidate_is_added(self):
        cand = [_gold_row("X-1")]
        merged, stats = merge_gold([], cand, [])
        assert len(merged) == 1
        assert stats["added"] == 1
        assert stats["updated"] == 0
        assert stats["superseded"] == 0
        assert stats["conflicts"] == []

    def test_idempotent_rerun_no_duplicate(self):
        """Rejouer avec un contenu identique ne duplique pas et ne crée pas de conflit."""
        existing = [_gold_row("X-1")]
        cand = [_gold_row("X-1")]  # contenu sémantique identique
        merged, stats = merge_gold(existing, cand, [])
        assert len(merged) == 1
        assert stats["added"] == 0
        assert stats["updated"] == 1  # rafraîchi en place
        assert stats["conflicts"] == []
        # une seule ligne pour cet item_id
        assert [r["item_id"] for r in merged] == ["X-1"]

    def test_genuine_conflict_keeps_existing(self):
        """Même item_id, même autorité (candidat), verdict différent → existant gardé."""
        existing = [_gold_row("X-1", verdict="Faux")]
        cand = [_gold_row("X-1", verdict="Trompeur")]  # contenu divergent
        merged, stats = merge_gold(existing, cand, [])
        assert len(merged) == 1
        assert "X-1" in stats["conflicts"]
        assert stats["added"] == 0
        assert stats["updated"] == 0
        # l'existant (Faux) est conservé, le candidat divergent est rejeté
        kept = {r["item_id"]: r for r in merged}
        assert kept["X-1"]["verdict"] == "Faux"

    def test_arbitration_supersedes_candidate_same_item(self):
        """Correctif #1 : une décision d'arbitrage humaine supplante un candidat auto."""
        cand = [_gold_row("X-1", verdict="Faux", agreement="majority")]
        arb = [
            _gold_row(
                "X-1",
                verdict="Trompeur",
                agreement="arbitrated",
                arbitrated=True,
                confidence=ARBITRATED_DEFAULT_CONFIDENCE,
            )
        ]
        merged, stats = merge_gold([], cand, arb)
        assert len(merged) == 1
        kept = {r["item_id"]: r for r in merged}
        # la décision humaine gagne
        assert kept["X-1"]["verdict"] == "Trompeur"
        assert kept["X-1"]["provenance"]["arbitrated"] is True
        # et ce n'est PAS un conflit
        assert stats["conflicts"] == []
        assert stats["superseded"] >= 1

    def test_arbitration_supersedes_existing_finalized_row(self):
        """Une décision humaine l'emporte aussi sur une ligne déjà finalisée (autorité)."""
        existing = [_gold_row("X-1", verdict="Faux", agreement="unanimous")]
        arb = [
            _gold_row(
                "X-1",
                verdict="Décontextualisé",
                agreement="arbitrated",
                arbitrated=True,
            )
        ]
        merged, stats = merge_gold(existing, [], arb)
        kept = {r["item_id"]: r for r in merged}
        assert kept["X-1"]["verdict"] == "Décontextualisé"
        assert stats["conflicts"] == []
        assert stats["superseded"] == 1

    def test_distinct_items_all_kept(self):
        cand = [_gold_row("A"), _gold_row("B")]
        arb = [_gold_row("C", agreement="arbitrated", arbitrated=True)]
        merged, stats = merge_gold([], cand, arb)
        assert {r["item_id"] for r in merged} == {"A", "B", "C"}
        assert stats["added"] == 3
        assert stats["conflicts"] == []

    def test_arbitration_idempotent_with_existing(self):
        """Rejouer un arbitrage identique sur une ligne déjà arbitrée → refresh, pas supersede."""
        existing = [
            _gold_row("X-1", verdict="Trompeur", agreement="arbitrated", arbitrated=True)
        ]
        arb = [
            _gold_row("X-1", verdict="Trompeur", agreement="arbitrated", arbitrated=True)
        ]
        merged, stats = merge_gold(existing, [], arb)
        assert len(merged) == 1
        assert stats["updated"] == 1
        assert stats["superseded"] == 0
        assert stats["conflicts"] == []


# ---------------------------------------------------------------------------
# Convention de confiance d'arbitrage (correctif #2) — pas de 0.5 fabriqué
# ---------------------------------------------------------------------------


class TestArbitratedConfidenceConvention:
    def test_default_is_human_decided_not_half(self):
        assert ARBITRATED_DEFAULT_CONFIDENCE == 1.0
        assert ARBITRATED_DEFAULT_CONFIDENCE != 0.5


# ---------------------------------------------------------------------------
# Test de bout-en-bout léger : merge persisté sans toucher au vrai gold.jsonl
# ---------------------------------------------------------------------------


class TestMergePersistenceIsolated:
    def test_write_merge_uses_monkeypatched_gold_file(self, tmp_path, monkeypatch):
        """Vérifie l'isolation : on n'écrit JAMAIS dans le vrai data/annotations/gold.jsonl."""
        fake_gold = tmp_path / "gold.jsonl"
        monkeypatch.setattr(io, "GOLD_FILE", fake_gold)

        # rien n'existe encore
        existing = io.read_jsonl(io.GOLD_FILE) if io.GOLD_FILE.exists() else []
        cand = [_gold_row("X-1")]
        merged, _ = merge_gold(existing, cand, [])
        io.write_jsonl(io.GOLD_FILE, merged)

        # le fichier réel du dépôt ne doit pas être le tmp
        assert io.GOLD_FILE == fake_gold
        assert fake_gold.exists()
        reread = io.read_jsonl(fake_gold)
        assert [r["item_id"] for r in reread] == ["X-1"]
