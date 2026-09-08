"""CLI: merge gold candidates + human arbitration decisions into gold.jsonl.

Usage
-----
    python scripts/finalize_gold.py --batch-id <batch_id> [--batch-file <path>]

Reads:
  data/annotations/<batch_id>__gold_candidates.jsonl   (from aggregate_labels.py)
  data/annotations/<batch_id>__agreement.json           (for kappa provenance)
  data/annotations/<batch_id>__arbitration_resolved.jsonl (optional; human decisions)
  data/annotations/<batch_id>.jsonl                     (batch file for channel/message lookup)

Writes:
  data/annotations/gold.jsonl  (merged by item_id; validated GoldLabel objects only)

Re-runs are idempotent (same content overwrites itself); a changed verdict for an
already-finalized item of equal authority is reported as a CONFLICT and the existing
label is kept. A human arbitration decision SUPERSEDES an auto-candidate for the same
item_id (it does not conflict with it). Any GoldLabel that fails Pydantic validation is
skipped and reported. The final gold count is printed to stdout.

Human-arbitration mechanism (AC6 — no Streamlit):
  After running aggregate_labels.py, Micky copies
  <batch_id>__arbitration_resolved.template.jsonl
  to <batch_id>__arbitration_resolved.jsonl, fills verdict/rationale/sources
  for each disagreement item, then runs this script.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.labeling import io  # noqa: E402
from src.labeling.schema import GoldLabel, Provenance, Verdict  # noqa: E402

# Confidence assigned to a human arbitration decision whose row omits `confidence`.
# 1.0 = "human-decided" (the aggregate template ships this as the placeholder). We do
# NOT fall back to a fabricated 0.5: a deliberate human ruling is not a coin flip, and
# a silent mid value would misrepresent it in the provenance record.
ARBITRATED_DEFAULT_CONFIDENCE = 1.0


def _semantic(d: dict) -> tuple:
    """Content fingerprint used to decide idempotent refresh vs. genuine conflict."""
    return (
        d.get("verdict"),
        d.get("rationale"),
        tuple(d.get("sources", [])),
        d.get("confidence"),
    )


def merge_gold(
    existing: list[dict],
    candidates: list[dict],
    arbitrated: list[dict],
) -> tuple[list[dict], dict]:
    """Merge candidate + arbitrated gold rows into the existing gold set, by item_id.

    Pure (no file I/O) so it is unit-testable. Rules:

    * **Arbitration supersedes candidate.** Human arbitration decisions are applied
      AFTER candidates and are authoritative: for any item_id present in both an
      auto-candidate and an arbitration decision, the arbitrated row REPLACES the
      candidate — this is NOT logged as a conflict (review fix #1).
    * **Idempotent.** A new row whose content (``_semantic``) matches the already-
      finalized row refreshes it in place (e.g. provenance/hash update) without a
      conflict.
    * **Genuine conflict.** A new row whose content differs from an already-finalized
      row of the SAME source authority is reported and the existing row is KEPT.
      (Arbitration over a candidate is a supersede, not a conflict, because the human
      decision is a higher authority — only collisions of equal authority conflict.)

    Parameters
    ----------
    existing : list[dict]
        Rows currently in gold.jsonl (each a serialized GoldLabel dict).
    candidates : list[dict]
        Auto-derived (unanimous/majority) gold rows.
    arbitrated : list[dict]
        Human arbitration gold rows. These win over a same-item candidate.

    Returns
    -------
    merged_rows : list[dict]
        The merged gold set, item_id-unique.
    stats : dict
        ``{"added", "updated", "superseded", "conflicts": [item_id, ...]}``.
    """
    merged: dict[str, dict] = {row["item_id"]: row for row in existing}

    # item_ids that arbitration will rule on — a candidate for the same id must yield.
    arbitrated_ids = {row["item_id"] for row in arbitrated}

    added = updated = superseded = 0
    conflicts: list[str] = []

    def _apply(d: dict, *, authoritative: bool) -> None:
        """Apply one new row. authoritative=True (arbitration) supersedes any prior."""
        nonlocal added, updated, superseded
        iid = d["item_id"]
        if iid not in merged:
            merged[iid] = d
            added += 1
        elif _semantic(merged[iid]) == _semantic(d):
            merged[iid] = d  # idempotent refresh
            updated += 1
        elif authoritative:
            merged[iid] = d  # human arbitration replaces a prior (auto) row
            superseded += 1
        else:
            conflicts.append(iid)

    # Candidates first, but skip any item an arbitration decision will rule on, so the
    # human decision is never even momentarily overwritten or flagged as a conflict.
    for d in candidates:
        if d["item_id"] in arbitrated_ids:
            superseded += 1
            continue
        _apply(d, authoritative=False)

    # Arbitration decisions last and authoritative.
    for d in arbitrated:
        _apply(d, authoritative=True)

    return list(merged.values()), {
        "added": added,
        "updated": updated,
        "superseded": superseded,
        "conflicts": conflicts,
    }


def _load_batch_lookup(batch_file: Path) -> dict[str, dict]:
    """Return {item_id: {channel_id, message_id, candidate_claim_id}} from batch file."""
    if not batch_file.exists():
        return {}
    rows = io.read_jsonl(batch_file)
    return {
        row["item_id"]: {
            "channel_id": row.get("channel_id"),
            "message_id": row.get("message_id"),
            "candidate_claim_id": row.get("candidate_claim_id"),
        }
        for row in rows
        if "item_id" in row
    }


def _load_report(report_path: Path) -> dict:
    """Load the agreement report JSON for kappa provenance."""
    if not report_path.exists():
        return {}
    with report_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize gold.jsonl from gold candidates + arbitrated decisions."
    )
    parser.add_argument("--batch-id", required=True, help="Batch identifier (e.g. batch-001)")
    parser.add_argument(
        "--batch-file",
        default=None,
        help="Path to the batch JSONL (default: data/annotations/<batch_id>.jsonl)",
    )
    args = parser.parse_args()
    batch_id: str = args.batch_id

    ann_dir = io.ANNOTATIONS_DIR
    batch_file = Path(args.batch_file) if args.batch_file else ann_dir / f"{batch_id}.jsonl"
    candidates_path = ann_dir / f"{batch_id}__gold_candidates.jsonl"
    report_path = ann_dir / f"{batch_id}__agreement.json"
    resolved_path = ann_dir / f"{batch_id}__arbitration_resolved.jsonl"

    # --- Load batch lookup (channel_id / message_id / candidate_claim_id) ---
    batch_lookup = _load_batch_lookup(batch_file)

    # --- Load report (kappa provenance) ---
    report = _load_report(report_path)
    kappa_metrics = report.get("kappa", {})
    mean_pairwise_cohen: float | None = kappa_metrics.get("mean_pairwise_cohen")
    report_judges: list[str] = report.get("judges", [])
    methodology_hash = io.methodology_version_hash()

    # Candidate labels (auto: unanimous/majority) and arbitrated labels (human) are
    # kept SEPARATE so the merge can let a human arbitration decision SUPERSEDE an
    # auto-candidate for the same item_id instead of treating it as a conflict.
    candidate_labels: list[GoldLabel] = []
    arbitrated_labels: list[GoldLabel] = []
    skipped = 0

    def _build_gold(
        item_id: str,
        verdict_value: str,
        confidence: float,
        rationale: str,
        sources: list[str],
        agreement: str,
        judges: list[str],
        arbitrated: bool = False,
        arbiter: str | None = None,
        arbiter_note: str | None = None,
    ) -> GoldLabel | None:
        lookup = batch_lookup.get(item_id, {})
        channel_id = lookup.get("channel_id")
        message_id = lookup.get("message_id")
        candidate_claim_id = lookup.get("candidate_claim_id")

        if channel_id is None or message_id is None:
            print(
                f"  SKIP {item_id}: not found in batch file (channel_id/message_id missing)",
                file=sys.stderr,
            )
            return None

        try:
            verdict = Verdict(verdict_value)
        except ValueError:
            print(
                f"  SKIP {item_id}: invalid verdict '{verdict_value}'",
                file=sys.stderr,
            )
            return None

        provenance = Provenance(
            judges=judges if judges else report_judges,
            n_judges=len(judges) if judges else len(report_judges),
            agreement=agreement,
            pairwise_kappa=mean_pairwise_cohen,
            arbitrated=arbitrated,
            arbiter=arbiter,
            arbiter_note=arbiter_note,
            methodology_version_hash=methodology_hash,
        )
        try:
            return GoldLabel(
                item_id=item_id,
                channel_id=int(channel_id),
                message_id=int(message_id),
                candidate_claim_id=candidate_claim_id,
                verdict=verdict,
                confidence=float(confidence),
                rationale=rationale,
                sources=sources,
                provenance=provenance,
            )
        except ValidationError as exc:
            print(f"  SKIP {item_id}: GoldLabel validation failed — {exc}", file=sys.stderr)
            return None

    # --- Process gold candidates (unanimous / majority) ---
    if not candidates_path.exists():
        print(f"WARNING: gold candidates file not found: {candidates_path}", file=sys.stderr)
    else:
        for row in io.read_jsonl(candidates_path):
            gl = _build_gold(
                item_id=row["item_id"],
                verdict_value=row["verdict"],
                confidence=row.get("confidence", 0.5),
                rationale=row["rationale"],
                sources=row["sources"],
                agreement=row.get("agreement", "unanimous"),
                judges=row.get("judges", []),
            )
            if gl:
                candidate_labels.append(gl)
            else:
                skipped += 1

    # --- Process human arbitration decisions ---
    if resolved_path.exists():
        for row in io.read_jsonl(resolved_path):
            # Skip unfilled templates
            v = row.get("verdict", "")
            if v.startswith("<FILL"):
                print(
                    f"  SKIP {row.get('item_id', '?')}: arbitration not filled (still template)",
                    file=sys.stderr,
                )
                skipped += 1
                continue
            # Arbitration confidence convention (review fix): the template now ships a
            # `confidence` field (placeholder 1.0). If the human left it absent we use
            # 1.0 = "human-decided", NOT a fabricated 0.5 mid value that would falsely
            # signal uncertainty about a deliberate human ruling.
            gl = _build_gold(
                item_id=row["item_id"],
                verdict_value=v,
                confidence=row.get("confidence", ARBITRATED_DEFAULT_CONFIDENCE),
                rationale=row.get("rationale", ""),
                sources=row.get("sources", []),
                agreement="arbitrated",
                judges=report_judges,
                arbitrated=True,
                arbiter=row.get("arbiter", "Micky"),
                arbiter_note=row.get("arbiter_note", ""),
            )
            if gl:
                arbitrated_labels.append(gl)
            else:
                skipped += 1

    # --- Merge into gold.jsonl by item_id (idempotent; conflicts reported) ---
    # NOTE: io.write_jsonl truncates; we therefore read the existing gold first and
    # merge by item_id so repeated finalize runs accumulate instead of overwriting
    # (review finding B4). Re-running with identical content is idempotent; a changed
    # verdict for an already-finalized item of equal authority is a CONFLICT — existing
    # is kept, reported. A human arbitration decision SUPERSEDES an auto-candidate for
    # the same item_id (review fix #1) and is NOT a conflict.
    existing_rows: list[dict] = (
        io.read_jsonl(io.GOLD_FILE) if io.GOLD_FILE.exists() else []
    )
    candidate_rows = [json.loads(gl.model_dump_json()) for gl in candidate_labels]
    arbitrated_rows = [json.loads(gl.model_dump_json()) for gl in arbitrated_labels]

    merged_rows, stats = merge_gold(existing_rows, candidate_rows, arbitrated_rows)
    conflicts: list[str] = stats["conflicts"]
    for iid in conflicts:
        print(
            f"  CONFLICT {iid}: differs from already-finalized gold; keeping existing.",
            file=sys.stderr,
        )

    if not merged_rows:
        print(f"No gold labels produced (skipped {skipped}).", file=sys.stderr)
        return 1

    # Atomic write: temp file then replace
    tmp = io.GOLD_FILE.with_suffix(".jsonl.tmp")
    io.write_jsonl(tmp, merged_rows)
    tmp.replace(io.GOLD_FILE)
    print(
        f"gold.jsonl now has {len(merged_rows)} labels "
        f"(+{stats['added']} new, {stats['updated']} refreshed, "
        f"{stats['superseded']} superseded by arbitration, "
        f"{len(conflicts)} conflicts skipped, {skipped} invalid skipped)"
    )
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
