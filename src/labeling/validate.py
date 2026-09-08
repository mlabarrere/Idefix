"""Validation helpers + CLI for judge verdict files (Story 1.1, T4, AC4).

Garde-fous enforced:
  #3  graded taxonomy (Verdict enum — Pydantic rejects unknown values)
  #6  sourced rationale (non-empty rationale + >=1 source)
  #4  authoritative anchoring — at least one source must be a NAMED fact-checker
      (soft allow-list) or a URL; a bare ``["foo"]`` is rejected
  #2  atomic decomposition (>=1 atomic_claims entry)

Design note: validation is strict and loud — errors carry 1-based PHYSICAL line
numbers (blank lines counted) and a malformed JSON line is reported, never raised.

CLI:
    python -m src.labeling.validate data/annotations/judgments/<batch>__<judge>.jsonl
exits 1 if any error, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from src.labeling import io
from src.labeling.schema import JudgeVerdict

# ---------------------------------------------------------------------------
# Authoritative-source policy (garde-fou #4) — flexible allow-list
# ---------------------------------------------------------------------------

# Soft allow-list of named fact-checkers / weak-label sources. Kept intentionally
# permissive (we would rather accept a real citation than reject one) but a few
# tokens were tightened after review to kill false positives:
#   - bare "clef" removed: it collides with the French word *clef* ("la clef du
#     problème"); the CLEF CheckThat! corpus is anchored on "checkthat" instead.
#   - "20 minutes" kept as-is for the outlet (20 Minutes Fake Off): tolerated
#     false positive (e.g. "20 minutes de marche") — acceptable risk, the outlet
#     citation matters more than the rare collision.
#   - "fact check" / "factcheck" kept as-is: intentionally permissive generic
#     anchors (e.g. "my fact check notes" would pass) — defensible because a
#     judge citing fact-checking work is the behaviour we want, not a placeholder.
_FACT_CHECKER_TOKENS = [
    "afp", "factuel", "décodeur", "decodeur", "checknews", "20 minutes", "20minutes",
    "fake off", "viginum", "checkthat", "surligneur", "conspiracy watch",
    "disinfolab", "euvsdisinfo", "newsguard", "fact check", "factcheck", "claimreview",
]
# Require a host containing a dot so bare hostnames like "http://x" are rejected
# while real citations like "https://factuel.afp.com/article" pass.
_URL_RE = re.compile(r"https?://[^\s/]+\.[^\s/]+", re.IGNORECASE)


def has_named_source(sources: list[str]) -> bool:
    """True if at least one source names a known fact-checker or is a URL.

    Soft allow-list so legitimate citations pass while a bare placeholder like
    ``["foo"]`` is rejected (defensibility — garde-fou #4).
    """
    for s in sources:
        if not s:
            continue
        low = s.lower()
        if _URL_RE.search(s) or any(tok in low for tok in _FACT_CHECKER_TOKENS):
            return True
    return False


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

_JUDGE_FILE_RE = re.compile(r"^(?P<batch_id>.+)__(?P<judge_slug>[^.]+)\.jsonl$")


def parse_judge_filename(path: str | Path) -> tuple[str, str]:
    """Extract (batch_id, judge_slug) from a judge file name.

    Expected pattern: ``<batch_id>__<judge_slug>.jsonl``

    Raises
    ------
    ValueError
        If the filename does not match the expected pattern.
    """
    name = Path(path).name
    m = _JUDGE_FILE_RE.match(name)
    if not m:
        raise ValueError(
            f"Judge filename '{name}' does not match '<batch_id>__<judge_slug>.jsonl'"
        )
    return m.group("batch_id"), m.group("judge_slug")


def discover_judge_files(
    batch_id: str,
    judgments_dir: Path | None = None,
) -> list[Path]:
    """Return all judge files for *batch_id* found under *judgments_dir*.

    Pattern: ``<batch_id>__*.jsonl``.  Files are returned in sorted order for
    deterministic processing.
    """
    if judgments_dir is None:
        judgments_dir = io.JUDGMENTS_DIR
    judgments_dir = Path(judgments_dir)
    if not judgments_dir.exists():
        return []
    return sorted(judgments_dir.glob(f"{batch_id}__*.jsonl"))


# ---------------------------------------------------------------------------
# Per-file validation (line-by-line, robust to malformed JSON)
# ---------------------------------------------------------------------------

def validate_judge_file(
    path: str | Path,
) -> tuple[list[JudgeVerdict], list[str]]:
    """Load and validate a judge JSONL file, one physical line at a time.

    Returns
    -------
    verdicts : list[JudgeVerdict]
        The valid verdicts parsed from the file.
    errors : list[str]
        Human-readable error strings with 1-based PHYSICAL line numbers for every
        invalid line: malformed JSON, wrong verdict enum, empty/blank sources,
        empty rationale, missing atomic_claims, or no named/authoritative source.
        Invalid lines are skipped — never raised.
    """
    p = Path(path)
    # utf-8-sig transparently strips a UTF-8 BOM if present (Windows-saved judge
    # files) so the first line does not become invalid JSON; it also reads plain
    # UTF-8 unchanged.
    text = p.read_text(encoding="utf-8-sig")

    verdicts: list[JudgeVerdict] = []
    errors: list[str] = []
    seen_item_ids: dict[str, int] = {}

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue  # blank line — counted but ignored

        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(f"Line {lineno}: invalid JSON — {exc.msg}")
            continue

        try:
            jv = JudgeVerdict.model_validate(raw)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
                for e in exc.errors()
            )
            errors.append(f"Line {lineno}: {details}")
            continue

        if not has_named_source(jv.sources):
            errors.append(
                f"Line {lineno}: no named/authoritative source (garde-fou #4); "
                f"sources={jv.sources}"
            )
            continue

        # Duplicate item_id within a single judge file — downstream aggregation is
        # last-write-wins, so flag it loudly and skip the repeat (keep the first).
        if jv.item_id in seen_item_ids:
            errors.append(
                f"Line {lineno}: duplicate item_id '{jv.item_id}' "
                f"(already on line {seen_item_ids[jv.item_id]})"
            )
            continue
        seen_item_ids[jv.item_id] = lineno

        verdicts.append(jv)

    return verdicts, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a judge verdict JSONL file.")
    parser.add_argument("path", help="Path to a <batch>__<judge>.jsonl file")
    args = parser.parse_args(argv)

    verdicts, errors = validate_judge_file(args.path)
    for err in errors:
        print(err, file=sys.stderr)
    print(f"{len(verdicts)} valid verdict(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
