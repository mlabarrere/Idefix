"""Tests for labeling IO helpers (Story 1.1, T1 foundation)."""

from src.labeling import io
from src.labeling.schema import Verdict, make_item_id


def test_write_then_read_jsonl_roundtrip(tmp_path):
    rows = [{"a": 1, "txt": "éàü"}, {"a": 2, "txt": "ok"}]
    p = tmp_path / "sub" / "x.jsonl"
    n = io.write_jsonl(p, rows)
    assert n == 2
    assert p.exists()  # parent dir auto-created
    back = io.read_jsonl(p)
    assert back == rows


def test_write_jsonl_serializes_enums_and_unicode(tmp_path):
    p = tmp_path / "e.jsonl"
    io.write_jsonl(p, [{"v": Verdict.DECONTEXTUALISE.value}])
    back = io.read_jsonl(p)
    assert back[0]["v"] == "Décontextualisé"


def test_read_jsonl_skips_blank_lines(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text('{"a":1}\n\n   \n{"a":2}\n', encoding="utf-8")
    assert io.read_jsonl(p) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_handles_utf8_bom(tmp_path):
    # A judge file saved as UTF-8-with-BOM must not crash the first line.
    p = tmp_path / "bom.jsonl"
    p.write_text('{"a":1}\n{"a":2}\n', encoding="utf-8-sig")
    assert io.read_jsonl(p) == [{"a": 1}, {"a": 2}]


def test_methodology_hash_is_stable_string():
    h = io.methodology_version_hash()
    assert isinstance(h, str) and h
    assert h.startswith("sha256:") or h.startswith("UNVERSIONED-")


def test_canonical_paths_point_into_repo():
    assert io.CLAIMS_FILE.name == "claims_fr.jsonl"
    assert io.ANNOTATIONS_DIR.name == "annotations"
    assert io.GOLD_FILE.parent == io.ANNOTATIONS_DIR


def test_load_claims_reads_seed_registry():
    # The seed file ships in the repo with 15 France-targeting claims.
    claims = io.load_claims()
    assert len(claims) >= 1
    assert "claim_text" in claims[0]
    assert "id" in claims[0]


def test_make_item_id_reexported_consistently():
    assert make_item_id(7, 8, "z").startswith("z-")
