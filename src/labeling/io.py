"""Shared IO helpers and canonical paths for the labeling pipeline (Story 1.1).

Centralizes file locations and JSONL read/write so the batch builder, validator,
aggregator and finalizer all agree on conventions. Library-first: stdlib json only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

# repo_root = .../Idefix  (this file is src/labeling/io.py → parents[2])
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
ANNOTATIONS_DIR = DATA_DIR / "annotations"
JUDGMENTS_DIR = ANNOTATIONS_DIR / "judgments"
CLAIMS_FILE = DATA_DIR / "claims" / "claims_fr.jsonl"
GOLD_FILE = ANNOTATIONS_DIR / "gold.jsonl"

# Documents that actually GOVERN the labeling methodology — these are hashed for
# provenance, NOT the project-wide METHODOLOGY.md (which is stale and predates the
# 7 garde-fous; see review finding #8). Order matters for the hash.
LABELING_METHODOLOGY_FILES = [
    ANNOTATIONS_DIR / "PROTOCOLE_LABELLISATION.md",
    REPO_ROOT
    / "_bmad-output"
    / "planning-artifacts"
    / "research"
    / "domain-labellisation-desinfo-llm-judge-research-2026-06-04.md",
]


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts. Blank lines are skipped.

    Uses utf-8-sig so a UTF-8 BOM (common on Windows-saved files) is stripped
    rather than crashing json.loads on the first line.
    """
    p = Path(path)
    rows: list[dict[str, Any]] = []
    with p.open(encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> int:
    """Write an iterable of dicts / pydantic models to JSONL (UTF-8). Returns count.

    Pydantic models are serialized via model_dump_json (handles enums/datetimes).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8") as fh:
        for row in rows:
            if hasattr(row, "model_dump_json"):
                fh.write(row.model_dump_json())
            else:
                fh.write(json.dumps(row, ensure_ascii=False, default=str))
            fh.write("\n")
            n += 1
    return n


def load_claims() -> list[dict[str, Any]]:
    """Load the seed claim registry (data/claims/claims_fr.jsonl).

    NOTE: the PostgreSQL `episodes` table is empty in the PoC, so the seed file
    is the authoritative claim source for sampling context.
    """
    return read_jsonl(CLAIMS_FILE)


def methodology_source_files() -> list[str]:
    """Names of the governing methodology files present (for provenance display)."""
    return [f.name for f in LABELING_METHODOLOGY_FILES if f.exists()]


def methodology_version_hash() -> str:
    """Return a short content hash of the labeling-governing documents.

    Hashes PROTOCOLE_LABELLISATION.md + the labeling-methodology research doc (the
    artifacts that encode the 7 garde-fous), so a gold label's provenance is tied to
    the exact methodology that produced it. If none exist yet, return a clearly
    marked unversioned stub so provenance is never silently empty.
    """
    present = [f for f in LABELING_METHODOLOGY_FILES if f.exists()]
    if not present:
        return f"UNVERSIONED-{date.today().isoformat()}"
    h = hashlib.sha256()
    for f in present:
        h.update(f.read_bytes())
    return f"sha256:{h.hexdigest()[:12]}"
