"""Tests for src/labeling/validate.py (Story 1.1, T4/T7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.labeling.validate import (
    discover_judge_files,
    parse_judge_filename,
    validate_judge_file,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_verdicts(path: Path, rows: list[dict]) -> None:
    """Write a list of dicts as JSONL to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


def _valid_row(item_id: str = "b-001", verdict: str = "Vrai") -> dict:
    return {
        "item_id": item_id,
        "verdict": verdict,
        "confidence": 0.9,
        "rationale": "Confirmé par AFP Factuel.",
        "sources": ["AFP Factuel"],
        "atomic_claims": ["la France enverrait des troupes"],
    }


# ---------------------------------------------------------------------------
# parse_judge_filename
# ---------------------------------------------------------------------------

class TestParseJudgeFilename:
    def test_normal_case(self):
        batch, slug = parse_judge_filename("batch-001__claude.jsonl")
        assert batch == "batch-001"
        assert slug == "claude"

    def test_batch_with_dashes_and_slug_with_dashes(self):
        batch, slug = parse_judge_filename("my-batch-2026__gemini-pro.jsonl")
        assert batch == "my-batch-2026"
        assert slug == "gemini-pro"

    def test_path_object(self, tmp_path: Path):
        f = tmp_path / "b__j.jsonl"
        batch, slug = parse_judge_filename(f)
        assert batch == "b"
        assert slug == "j"

    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="does not match"):
            parse_judge_filename("no_double_underscore.jsonl")

    def test_double_underscore_in_batch_id(self):
        # batch_id may technically contain __ — parser keeps the LAST __ as separator?
        # By design the regex is greedy on batch_id; let's verify it handles a simple case
        batch, slug = parse_judge_filename("batch__001__claude.jsonl")
        # batch_id captures everything up to the LAST __ thanks to greedy .+
        assert slug == "claude"
        assert "__" in batch  # "batch__001"


# ---------------------------------------------------------------------------
# discover_judge_files
# ---------------------------------------------------------------------------

class TestDiscoverJudgeFiles:
    def test_finds_matching_files(self, tmp_path: Path):
        (tmp_path / "batch-001__claude.jsonl").touch()
        (tmp_path / "batch-001__gemini.jsonl").touch()
        (tmp_path / "batch-002__claude.jsonl").touch()

        found = discover_judge_files("batch-001", judgments_dir=tmp_path)
        names = [f.name for f in found]
        assert "batch-001__claude.jsonl" in names
        assert "batch-001__gemini.jsonl" in names
        assert "batch-002__claude.jsonl" not in names
        assert len(found) == 2

    def test_returns_empty_if_dir_missing(self, tmp_path: Path):
        result = discover_judge_files("batch-001", judgments_dir=tmp_path / "nonexistent")
        assert result == []

    def test_returns_sorted(self, tmp_path: Path):
        (tmp_path / "batch-001__zzz.jsonl").touch()
        (tmp_path / "batch-001__aaa.jsonl").touch()
        found = discover_judge_files("batch-001", judgments_dir=tmp_path)
        assert found[0].name < found[1].name  # sorted ascending


# ---------------------------------------------------------------------------
# validate_judge_file
# ---------------------------------------------------------------------------

class TestValidateJudgeFile:
    def test_well_formed_file_passes(self, tmp_path: Path):
        rows = [_valid_row("item-1"), _valid_row("item-2", "Faux")]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 2
        assert errors == []

    def test_all_verdict_values_accepted(self, tmp_path: Path):
        rows = [_valid_row(f"item-{i}", v) for i, v in enumerate(
            ["Vrai", "Faux", "Trompeur", "Décontextualisé", "Non-étayé"]
        )]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 5
        assert errors == []

    def test_bad_verdict_is_rejected_with_line_number(self, tmp_path: Path):
        rows = [
            _valid_row("item-1"),
            {**_valid_row("item-2"), "verdict": "INVALIDE"},  # bad — line 2
            _valid_row("item-3"),
        ]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 2  # item-1 and item-3 pass
        assert len(errors) == 1
        assert "Line 2" in errors[0]

    def test_empty_sources_is_rejected(self, tmp_path: Path):
        rows = [
            _valid_row("item-1"),
            {**_valid_row("item-2"), "sources": []},  # bad — line 2
        ]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 1
        assert len(errors) == 1
        assert "Line 2" in errors[0]

    def test_blank_only_source_is_rejected(self, tmp_path: Path):
        rows = [{**_valid_row("item-1"), "sources": ["   "]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "Line 1" in errors[0]

    def test_empty_rationale_is_rejected(self, tmp_path: Path):
        rows = [{**_valid_row("item-1"), "rationale": "   "}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "Line 1" in errors[0]

    def test_missing_atomic_claims_is_rejected(self, tmp_path: Path):
        rows = [{**_valid_row("item-1"), "atomic_claims": []}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "Line 1" in errors[0]

    def test_multiple_bad_lines_all_reported(self, tmp_path: Path):
        rows = [
            {**_valid_row("item-1"), "verdict": "BAD"},   # line 1
            _valid_row("item-2"),                          # line 2 — OK
            {**_valid_row("item-3"), "sources": []},       # line 3
        ]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)

        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 1
        assert len(errors) == 2
        line_numbers = [int(e.split(":")[0].replace("Line ", "")) for e in errors]
        assert 1 in line_numbers
        assert 3 in line_numbers

    def test_empty_file_returns_empty(self, tmp_path: Path):
        p = tmp_path / "b__j.jsonl"
        p.write_text("", encoding="utf-8")

        verdicts, errors = validate_judge_file(p)
        assert verdicts == []
        assert errors == []


# ---------------------------------------------------------------------------
# Review fixes: robust parsing (#improvement), named-source policy (#6), CLI (#7)
# ---------------------------------------------------------------------------

class TestRobustParsingAndPolicy:
    def test_malformed_json_line_is_reported_not_raised(self, tmp_path: Path):
        p = tmp_path / "b__j.jsonl"
        p.write_text(
            json.dumps(_valid_row("item-1")) + "\n"
            + "{ this is not json\n"
            + json.dumps(_valid_row("item-3")) + "\n",
            encoding="utf-8",
        )
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 2  # lines 1 and 3
        assert len(errors) == 1
        assert "Line 2" in errors[0]
        assert "invalid JSON" in errors[0]

    def test_line_numbers_are_physical_after_blank_lines(self, tmp_path: Path):
        p = tmp_path / "b__j.jsonl"
        p.write_text(
            json.dumps(_valid_row("item-1")) + "\n"
            + "\n"  # blank physical line 2
            + json.dumps({**_valid_row("item-3"), "verdict": "BAD"}) + "\n",  # line 3
            encoding="utf-8",
        )
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 1
        assert len(errors) == 1
        assert "Line 3" in errors[0]

    def test_unnamed_source_is_rejected(self, tmp_path: Path):
        # garde-fou #4: a bare placeholder source must not pass.
        rows = [{**_valid_row("item-1"), "sources": ["foo"]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "named/authoritative source" in errors[0]

    def test_url_source_is_accepted(self, tmp_path: Path):
        rows = [{**_valid_row("item-1"), "sources": ["https://factuel.afp.com/article"]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 1
        assert errors == []

    def test_named_factchecker_variants_accepted(self, tmp_path: Path):
        for src in ["VIGINUM", "Les Décodeurs", "CheckNews", "CLEF CheckThat! 2025 FR"]:
            rows = [{**_valid_row("item-1"), "sources": [src]}]
            p = tmp_path / "b__j.jsonl"
            _write_verdicts(p, rows)
            verdicts, errors = validate_judge_file(p)
            assert len(verdicts) == 1, f"source {src!r} should be accepted"
            assert errors == []

    def test_hostless_url_is_rejected(self, tmp_path: Path):
        # "http://x" has no dotted host — tightened URL check must reject it.
        rows = [{**_valid_row("item-1"), "sources": ["http://x"]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "named/authoritative source" in errors[0]

    def test_dotted_url_is_accepted(self, tmp_path: Path):
        rows = [{**_valid_row("item-1"), "sources": ["https://factuel.afp.com/article"]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 1
        assert errors == []

    def test_french_word_clef_is_rejected(self, tmp_path: Path):
        # "clef" (French for "key") must no longer pass — it collided with the
        # CLEF CheckThat! corpus token before the fix.
        rows = [{**_valid_row("item-1"), "sources": ["la clef du problème"]}]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 0
        assert len(errors) == 1
        assert "named/authoritative source" in errors[0]


class TestBomHandling:
    def test_utf8_sig_first_line_validates(self, tmp_path: Path):
        # A judge file saved on Windows with a UTF-8 BOM must not corrupt line 1.
        p = tmp_path / "b__j.jsonl"
        with p.open("w", encoding="utf-8-sig") as fh:
            fh.write(json.dumps(_valid_row("item-1"), ensure_ascii=False))
            fh.write("\n")
            fh.write(json.dumps(_valid_row("item-2", "Faux"), ensure_ascii=False))
            fh.write("\n")
        verdicts, errors = validate_judge_file(p)
        assert errors == []
        assert len(verdicts) == 2
        assert verdicts[0].item_id == "item-1"


class TestDuplicateItemId:
    def test_duplicate_item_id_is_reported_and_skipped(self, tmp_path: Path):
        rows = [
            _valid_row("dup-1"),                 # line 1 — kept
            _valid_row("other"),                 # line 2 — kept
            _valid_row("dup-1", "Faux"),         # line 3 — duplicate, skipped
        ]
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, rows)
        verdicts, errors = validate_judge_file(p)
        assert len(verdicts) == 2
        assert [v.item_id for v in verdicts] == ["dup-1", "other"]
        assert len(errors) == 1
        assert "Line 3" in errors[0]
        assert "duplicate item_id 'dup-1'" in errors[0]
        assert "line 1" in errors[0]


class TestValidateCLI:
    def test_cli_returns_1_on_errors(self, tmp_path: Path):
        from src.labeling.validate import main
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, [{**_valid_row("item-1"), "sources": ["foo"]}])
        assert main([str(p)]) == 1

    def test_cli_returns_0_when_clean(self, tmp_path: Path):
        from src.labeling.validate import main
        p = tmp_path / "b__j.jsonl"
        _write_verdicts(p, [_valid_row("item-1")])
        assert main([str(p)]) == 0
