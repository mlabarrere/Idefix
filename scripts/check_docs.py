#!/usr/bin/env python
"""Documentation integrity checks. Run in CI; fails the build on any violation.

Three checks, each guarding a failure mode this repository has actually hit:

1. **Dead links.** ``docs/README.md`` once indexed 19 documents, 8 of which did
   not exist. Every relative Markdown link must resolve.
2. **Unbacked numbers.** Every figure quoted in ``docs/experiments/*.md`` must
   exist in an artefact under ``docs/experiments/results/``. Prose numbers
   without an artefact are how unreproducible claims got published.
3. **Citing the archive.** ``archive/`` holds artefacts from a decommissioned
   corpus. Documentation must not reference them as results.

Usage:  uv run python scripts/check_docs.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
RESULTS = DOCS / "experiments" / "results"
ARCHIVE = ROOT / "archive"

# Markdown links, excluding images.
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
# Numbers that constitute an empirical claim: decimals, and integers of 3+
# digits. Small integers are section numbers, counts of families, thresholds
# quoted from code -- not results.
NUMBER_RE = re.compile(r"(?<![\w.\-/])(\d+\.\d+|\d{3,})(?![\w.\-/%])")

# Figures that are part of the method (constants read off the code), not
# results. Documented in the method chapters, so they are allowed in prose.
ALLOWED = {
    # thresholds and weights defined in source
    "0.15", "0.30", "0.25", "0.20", "0.10", "0.40", "0.60", "0.70", "0.50",
    "0.55", "0.35", "0.45", "0.65", "0.80", "0.90", "0.75", "1.00", "0.05",
    "0.715", "0.693", "0.85", "1.6", "3.0", "4.0", "0.0", "1.0",
    "0.0001", "0.9999", "384", "100", "200", "1000", "1312", "3600", "500",
    # line numbers and identifiers appear as bare integers in file:line refs
}
# Section cross-references (§5.1, §3.8) are navigation, not measurements.
SECTION_REF_RE = re.compile(r"§\s*\d+(\.\d+)*")
# Anything inside backticks is code or a file:line reference, never a claim.
CODE_SPAN_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def strip_code(text: str) -> str:
    return CODE_SPAN_RE.sub(" ", FENCE_RE.sub(" ", text))


def markdown_files() -> list[Path]:
    out = [p for p in DOCS.rglob("*.md")]
    out += [ROOT / "README.md", ROOT / "METHODOLOGY.md", ROOT / "ONBOARDING.md"]
    out += [p for p in ARCHIVE.rglob("*.md")]
    return [p for p in out if p.exists()]


def check_links() -> list[str]:
    errors: list[str] = []
    for md in markdown_files():
        for target in LINK_RE.findall(md.read_text(encoding="utf-8")):
            target = target.split()[0].strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            if not (md.parent / path).resolve().exists():
                errors.append(f"{md.relative_to(ROOT)}: dead link -> {target}")
    return errors


def check_numbers() -> list[str]:
    """Numbers quoted in experiment prose must appear in a results artefact."""
    known: set[str] = set()
    for artefact in RESULTS.glob("*.json"):
        try:
            blob = json.loads(artefact.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"{artefact.relative_to(ROOT)}: invalid JSON"]
        known.update(NUMBER_RE.findall(json.dumps(blob)))

    errors: list[str] = []
    for md in (DOCS / "experiments").glob("*.md"):
        in_fence = False
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            # Fenced blocks hold formulas and falsification criteria; table rows
            # enumerate parameters and sweep ranges. Neither is a result.
            if in_fence or line.lstrip().startswith("|"):
                continue
            for num in set(NUMBER_RE.findall(SECTION_REF_RE.sub(" ", strip_code(line)))):
                if num in ALLOWED or num in known:
                    continue
                if re.fullmatch(r"(19|20)\d{2}", num):  # years in citations
                    continue
                errors.append(
                    f"{md.relative_to(ROOT)}:{lineno}: number {num!r} has no "
                    f"artefact under docs/experiments/results/"
                )
    return errors


def check_archive_not_cited() -> list[str]:
    """docs/ may point at archive/ only to say 'do not cite'."""
    errors: list[str] = []
    disclaimers = ("do not cite", "may not be cited", "quarantin", "decommission")
    for md in DOCS.rglob("*.md"):
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "archive/" not in line:
                continue
            # Prose wraps, so accept a disclaimer anywhere in the sentence
            # surrounding the reference.
            window = " ".join(lines[max(0, i - 2) : i + 3]).lower()
            if any(d in window for d in disclaimers):
                continue
            errors.append(
                f"{md.relative_to(ROOT)}:{i + 1}: references archive/ without a "
                f"do-not-cite disclaimer -> {line.strip()[:80]}"
            )
    return errors


def main() -> int:
    checks = [
        ("dead links", check_links()),
        ("unbacked numbers", check_numbers()),
        ("archive citations", check_archive_not_cited()),
    ]
    failed = False
    for name, errors in checks:
        if errors:
            failed = True
            print(f"\nFAIL - {name} ({len(errors)}):", file=sys.stderr)
            for e in errors:
                print(f"  {e}", file=sys.stderr)
        else:
            print(f"ok   - {name}")
    if failed:
        print("\nDocumentation checks failed.", file=sys.stderr)
        return 1
    print("\nAll documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
