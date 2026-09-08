"""CLI: aggregate judge files for a batch and produce agreement report + queues.

Usage
-----
    python scripts/aggregate_labels.py --batch-id <batch_id>

Outputs (all under data/annotations/):
  <batch_id>__agreement.json               — batch-level report (kappa + agreement counts)
  <batch_id>__gold_candidates.jsonl        — unanimous/majority items
  <batch_id>__arbitration_queue.jsonl      — disagreements (judges anonymized)
  <batch_id>__arbitration_resolved.template.jsonl  — template for Micky to fill

The template file is the human-arbitration mechanism (NO Streamlit).
Micky copies it to <batch_id>__arbitration_resolved.jsonl, fills in
verdict/rationale/sources for each item, then runs finalize_gold.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import structlog

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.labeling import io  # noqa: E402
from src.labeling.aggregate import aggregate_batch  # noqa: E402
from src.labeling.validate import (  # noqa: E402
    discover_judge_files,
    parse_judge_filename,
    validate_judge_file,
)

log = structlog.get_logger()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate multi-LLM judge files for a labeling batch."
    )
    parser.add_argument("--batch-id", required=True, help="Batch identifier (e.g. batch-001)")
    parser.add_argument(
        "--min-judges", type=int, default=2,
        help="Min judges for an item to be gold-eligible (default 2; below → arbitration).",
    )
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="Proceed even if a judge file has validation errors (default: fail).",
    )
    args = parser.parse_args()
    batch_id: str = args.batch_id

    # --- Guard min_judges (garde-fou #5: corroboration) ---
    # A gold label requires at least TWO judges. --min-judges 1 (or 0) would re-open
    # the single-judge-becomes-gold hole, so we clamp to 2 with a warning rather than
    # silently honour an unsafe value.
    min_judges: int = args.min_judges
    if min_judges < 2:
        log.warning(
            "min_judges_below_floor_clamped",
            requested=min_judges,
            clamped_to=2,
            reason="garde-fou #5 — a single-judge item can never become gold",
        )
        min_judges = 2

    # --- Discover judge files ---
    judge_files = discover_judge_files(batch_id)
    if not judge_files:
        log.error("no_judge_files_found", batch_id=batch_id, dir=str(io.JUDGMENTS_DIR))
        return 1

    # --- Validate + load (fail-closed on invalid files unless --allow-partial) ---
    judge_to_verdicts: dict[str, list] = {}
    total_errors = 0
    for jf in judge_files:
        try:
            _batch_id_parsed, judge_slug = parse_judge_filename(jf)
        except ValueError as exc:
            log.warning("judge_filename_parse_error", path=str(jf), error=str(exc))
            continue

        verdicts, errors = validate_judge_file(jf)
        if errors:
            total_errors += len(errors)
            for err in errors:
                log.warning("judge_validation_error", judge=judge_slug, error=err)
        if verdicts:
            judge_to_verdicts[judge_slug] = verdicts
        else:
            log.warning("judge_file_has_no_valid_verdicts", judge=judge_slug, path=str(jf))

    if total_errors and not args.allow_partial:
        log.error(
            "judge_files_invalid",
            batch_id=batch_id,
            total_errors=total_errors,
            hint="fix the judge files, or re-run with --allow-partial to skip invalid lines",
        )
        return 1

    if not judge_to_verdicts:
        log.error("no_valid_verdicts_loaded", batch_id=batch_id)
        return 1

    # --- Load the batch for arbitration context (text + candidate claim) ---
    batch_path = io.ANNOTATIONS_DIR / f"{batch_id}.jsonl"
    batch_ctx: dict[str, dict] = {}
    if batch_path.exists():
        for row in io.read_jsonl(batch_path):
            batch_ctx[row["item_id"]] = {
                "text": row.get("text"),
                "channel_name": row.get("channel_name"),
                "candidate_claim_id": row.get("candidate_claim_id"),
                "candidate_claim_text": row.get("candidate_claim_text"),
            }
    else:
        log.warning("batch_file_missing_for_context", path=str(batch_path))

    # --- Aggregate ---
    report, gold_candidates, arbitration_records = aggregate_batch(
        judge_to_verdicts, min_judges=min_judges
    )

    # Enrich each arbitration record with the batch item context so the human
    # arbiter does not have to cross-reference by hand (review finding B3).
    for rec in arbitration_records:
        ctx = batch_ctx.get(rec["item_id"], {})
        rec["message_text"] = ctx.get("text")
        rec["channel_name"] = ctx.get("channel_name")
        rec["candidate_claim_id"] = ctx.get("candidate_claim_id")
        rec["candidate_claim_text"] = ctx.get("candidate_claim_text")

    log.info(
        "aggregation_complete",
        batch_id=batch_id,
        n_judges=report["n_judges"],
        n_items=report["n_items"],
        agreement_counts=report["agreement_counts"],
        mean_pairwise_cohen=report["kappa"].get("mean_pairwise_cohen"),
        fleiss_kappa=report["kappa"].get("fleiss_kappa"),
    )

    # --- Write outputs ---
    ann_dir = io.ANNOTATIONS_DIR
    ann_dir.mkdir(parents=True, exist_ok=True)

    # 1. Agreement report (JSON)
    agreement_path = ann_dir / f"{batch_id}__agreement.json"
    with agreement_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    log.info("wrote_agreement_report", path=str(agreement_path))

    # 2. Gold candidates (JSONL)
    gold_candidates_path = ann_dir / f"{batch_id}__gold_candidates.jsonl"
    io.write_jsonl(gold_candidates_path, gold_candidates)
    log.info("wrote_gold_candidates", path=str(gold_candidates_path), n=len(gold_candidates))

    # 3. Arbitration queue (JSONL, anonymized)
    arb_queue_path = ann_dir / f"{batch_id}__arbitration_queue.jsonl"
    io.write_jsonl(arb_queue_path, arbitration_records)
    log.info("wrote_arbitration_queue", path=str(arb_queue_path), n=len(arbitration_records))

    # 4. Arbitration resolved template (JSONL)
    # Micky copies this file, renames to *_resolved.jsonl, and fills the placeholders.
    template_path = ann_dir / f"{batch_id}__arbitration_resolved.template.jsonl"
    template_rows = [
        {
            "item_id": rec["item_id"],
            "verdict": "<FILL: Vrai|Faux|Trompeur|Décontextualisé|Non-étayé>",
            # Confidence of the HUMAN arbitration decision in [0,1]. Placeholder 1.0
            # means "human-decided" (finalize_gold treats a missing confidence as 1.0
            # too); set a lower value if the arbiter is uncertain. Never left blank so
            # finalize_gold does not have to fabricate a misleading mid value.
            "confidence": 1.0,
            "rationale": "<FILL>",
            "sources": ["<FILL>"],
            "arbiter": "Micky",
            "arbiter_note": "",
        }
        for rec in arbitration_records
    ]
    io.write_jsonl(template_path, template_rows)
    log.info("wrote_arbitration_template", path=str(template_path), n=len(template_rows))

    return 0


if __name__ == "__main__":
    sys.exit(main())
