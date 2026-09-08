"""Aggregation + inter-annotator agreement for gold-labeling (Story 1.1, T5/T6).

All core functions are PURE (no file I/O) and take parsed objects so they are
fully unit-testable without touching the filesystem.

Garde-fous enforced:
  #5  kappa measurement + human arbitration on disagreements
  #6  judge anonymization + order shuffle before aggregation (anti position/auto-
      preference bias)

Library-first (NFR-20):
  - Cohen pairwise kappa  → sklearn.metrics.cohen_kappa_score
  - Fleiss multi-judge kappa → statsmodels.stats.inter_rater.fleiss_kappa +
                               aggregate_raters
  NEVER hand-rolled.
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections import Counter
from typing import Any

from src.labeling.schema import JudgeVerdict, Verdict

# Fixed ordering of the 5 verdict categories so the Fleiss table is stable
# even when some categories have zero observations.
_VERDICT_ORDER: list[str] = [v.value for v in Verdict]
_VERDICT_TO_INT: dict[str, int] = {v: i for i, v in enumerate(_VERDICT_ORDER)}

# A gold label requires corroboration: an item labeled by fewer than this many
# judges can NEVER become gold (it goes to the arbitration/screening queue).
DEFAULT_MIN_JUDGES = 2

# Provider/model names that must never leak into the anonymized arbitration queue
# (garde-fou #6): if a judge names itself in its rationale, redact it.
_PROVIDER_TOKENS = [
    "claude", "anthropic", "gemini", "bard", "gpt", "chatgpt", "openai",
    "copilot", "mistral", "llama", "grok", "deepseek", "qwen",
]


def _strip_accents(s: str) -> str:
    """Return *s* with combining diacritics removed (NFKD + drop marks).

    Used to build an accent-insensitive view of the text so e.g. "Gémini"
    matches the token "gemini".
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


# A short alphanumeric/dot/hyphen run that names a model version immediately
# after a provider token, e.g. "gpt-4o", "claude-3.5", "gemini 1.5", "grok_v2".
# Consumed together with the provider so the whole model name becomes "[juge]"
# and no version tail leaks. Kept short and bounded so it cannot swallow a
# following sentence — only a contiguous version-like token.
_VERSION_SUFFIX = r"(?:[-_ ](?:v)?[0-9][0-9a-z.]*)?"


def _redact_providers(text: str, extra_slugs: list[str] | None = None) -> str:
    """Replace any provider/model/slug name with ``[juge]``.

    Matching is BOTH case-insensitive AND accent-insensitive, so self-naming
    variants like "Gémini" cannot defeat the anonymization (garde-fou #6).
    A trailing version suffix (``-4o``, ``-3.5``, `` 1.5``, ``_v2``) is consumed
    with the provider so the full model name is redacted, not just the brand.
    Explicit ``extra_slugs`` (the real judge slugs) are additionally matched as
    plain substrings (no word boundary) when multi-char, so a fused slug like
    "claudeopus" is still caught.

    Because matching happens on an accent-stripped *copy*, the original text is
    rebuilt by mapping match spans back onto the source string (accent stripping
    via NFKD-drop-combining is length-preserving for the diacritics we handle).
    """
    if not text:
        return text

    extra = [s.lower() for s in (extra_slugs or [])]
    # Accent-stripped lowercase view used only for locating matches; spans map
    # 1:1 back onto the original because we only drop zero-width combining marks.
    norm = _strip_accents(text).lower()

    # Collect (start, end) spans to redact in the ORIGINAL string.
    spans: list[tuple[int, int]] = []

    # Generic brand tokens: word-boundary anchored + version suffix.
    for tok in sorted(set(_PROVIDER_TOKENS), key=len, reverse=True):
        pattern = rf"\b{re.escape(_strip_accents(tok).lower())}{_VERSION_SUFFIX}"
        for m in re.finditer(pattern, norm):
            spans.append((m.start(), m.end()))

    # Explicit judge slugs: plain substring (no \b) when multi-char, also with
    # an optional version suffix.
    for slug in sorted(set(extra), key=len, reverse=True):
        slug_n = _strip_accents(slug).lower()
        if len(slug_n) < 2:
            continue
        pattern = rf"{re.escape(slug_n)}{_VERSION_SUFFIX}"
        for m in re.finditer(pattern, norm):
            spans.append((m.start(), m.end()))

    if not spans:
        return text

    # Merge overlapping/adjacent spans, then splice "[juge]" into the original.
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    out: list[str] = []
    cursor = 0
    for start, end in merged:
        out.append(text[cursor:start])
        out.append("[juge]")
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# ---------------------------------------------------------------------------
# Step 1 — build per-item judge map
# ---------------------------------------------------------------------------

def build_matrix(
    judge_to_verdicts: dict[str, list[JudgeVerdict]],
) -> dict[str, dict[str, JudgeVerdict]]:
    """Build a mapping ``{item_id: {judge_slug: JudgeVerdict}}``.

    Items that a judge did not label simply have no entry for that judge.
    All metadata (confidence, rationale, sources, atomic_claims) is preserved
    inside the JudgeVerdict object.
    """
    matrix: dict[str, dict[str, JudgeVerdict]] = {}
    for judge, verdicts in judge_to_verdicts.items():
        for jv in verdicts:
            matrix.setdefault(jv.item_id, {})[judge] = jv
    return matrix


# ---------------------------------------------------------------------------
# Step 2 — anonymization (garde-fou #6)
# ---------------------------------------------------------------------------

def _anon_label(i: int) -> str:
    """Map a 0-based index to an Excel-style base-26 label: A, B, … Z, AA, AB, …

    Replaces ``chr(ord('A') + i)`` which silently broke past 26 judges.
    """
    letters = ""
    n = i
    while True:
        n, rem = divmod(n, 26)
        letters = chr(ord("A") + rem) + letters
        if n == 0:
            break
        n -= 1  # shift for 1-based bijective base-26
    return f"Juge {letters}"

def anonymize_and_shuffle(
    per_item_judge_map: dict[str, dict[str, JudgeVerdict]],
    seed: int = 42,
) -> dict[str, dict[str, JudgeVerdict]]:
    """Return a copy of *per_item_judge_map* with judge slugs replaced by
    anonymous labels ("Juge A", "Juge B", …) and the judge order shuffled
    deterministically within each item.

    The slug→anonymous mapping is derived from a *globally* shuffled list of
    all unique judge slugs (under *seed*) so the mapping is consistent across
    all items in a run but never reveals the real identity.

    The original map is not mutated.
    """
    rng = random.Random(seed)

    # Build a single global slug → anonymous label mapping (consistent across items)
    all_slugs = sorted({slug for judges in per_item_judge_map.values() for slug in judges})
    shuffled_slugs = list(all_slugs)
    rng.shuffle(shuffled_slugs)
    anon_map = {slug: _anon_label(i) for i, slug in enumerate(shuffled_slugs)}

    result: dict[str, dict[str, JudgeVerdict]] = {}
    for item_id, judges in per_item_judge_map.items():
        # Shuffle the judge order for this item deterministically
        slugs_for_item = list(judges.keys())
        rng.shuffle(slugs_for_item)
        result[item_id] = {anon_map[slug]: judges[slug] for slug in slugs_for_item}
    return result


# ---------------------------------------------------------------------------
# Step 3 — agreement classification per item
# ---------------------------------------------------------------------------

def compute_agreement(
    per_item_judge_map: dict[str, dict[str, JudgeVerdict]],
    min_judges: int = DEFAULT_MIN_JUDGES,
) -> dict[str, str]:
    """Return ``{item_id: agreement_label}`` where label is one of:
    ``"insufficient_judges"`` — fewer than *min_judges* labeled it (never gold),
    ``"unanimous"`` — all judges gave the same verdict,
    ``"majority"``  — a strict plurality winner exists,
    ``"disagreement"`` — a tie; no clear winner.

    The *min_judges* gate (garde-fou #5: corroboration) prevents a single judge's
    label from being promoted to gold as a spurious "unanimous".
    """
    result: dict[str, str] = {}
    for item_id, judges in per_item_judge_map.items():
        verdicts = [jv.verdict.value for jv in judges.values()]
        n = len(verdicts)

        if n < min_judges:
            result[item_id] = "insufficient_judges"
            continue

        counts = Counter(verdicts)
        top_count = counts.most_common(1)[0][1]

        if top_count == n:
            result[item_id] = "unanimous"
        elif top_count > n / 2:
            result[item_id] = "majority"
        else:
            # Strict tie: no single verdict has more than half the votes
            result[item_id] = "disagreement"
    return result


# ---------------------------------------------------------------------------
# Step 4 — inter-annotator agreement (kappa)
# ---------------------------------------------------------------------------

def compute_kappa(
    judge_to_verdicts: dict[str, list[JudgeVerdict]],
) -> dict[str, Any]:
    """Compute Cohen (pairwise mean) + Fleiss (multi-judge) kappa.

    Returns a dict with keys:
      ``mean_pairwise_cohen`` — mean Cohen kappa across all judge pairs on
                                their common items; None if <2 judges or <2 common items.
      ``fleiss_kappa``        — Fleiss kappa over the items ALL judges labeled;
                                None if <2 judges or <2 common items.
      ``n_common_items``      — items all judges labeled (used for Fleiss).
      ``n_judges``            — number of judges.
    """
    judges = list(judge_to_verdicts.keys())
    n_judges = len(judges)

    if n_judges < 2:
        return {
            "mean_pairwise_cohen": None,
            "fleiss_kappa": None,
            "n_common_items": 0,
            "n_judges": n_judges,
        }

    # Build per-judge item→int maps
    judge_items: dict[str, dict[str, int]] = {}
    for judge, verdicts in judge_to_verdicts.items():
        judge_items[judge] = {jv.item_id: _VERDICT_TO_INT[jv.verdict.value] for jv in verdicts}

    # --- Cohen pairwise ---
    import math

    from sklearn.metrics import cohen_kappa_score

    pairwise_kappas: list[float] = []
    for i in range(n_judges):
        for j in range(i + 1, n_judges):
            j1_items = judge_items[judges[i]]
            j2_items = judge_items[judges[j]]
            common = sorted(set(j1_items) & set(j2_items))
            if len(common) < 2:
                continue
            y1 = [j1_items[iid] for iid in common]
            y2 = [j2_items[iid] for iid in common]
            # Degenerate-agreement case: two judges who agree on EVERY common
            # item. sklearn returns NaN for constant input (no variance), which
            # would be (mis)read as "uncomputable" and dropped. Two raters that
            # always coincide are by definition in perfect agreement → kappa 1.0.
            if y1 == y2:
                pairwise_kappas.append(1.0)
                continue
            try:
                k = cohen_kappa_score(y1, y2, labels=list(range(len(_VERDICT_ORDER))))
            except ValueError:
                # Genuine failure (e.g. malformed input); skip this pair rather
                # than crash the whole batch. Documented intentional swallow.
                continue
            if math.isfinite(k):
                pairwise_kappas.append(k)

    mean_cohen = (sum(pairwise_kappas) / len(pairwise_kappas)) if pairwise_kappas else None

    # --- Fleiss over items ALL judges labeled ---
    all_sets = [set(judge_items[j].keys()) for j in judges]
    common_all = sorted(set.intersection(*all_sets))
    n_common = len(common_all)

    fleiss_k: float | None = None
    if n_common >= 2:
        try:
            from statsmodels.stats.inter_rater import fleiss_kappa as sm_fleiss

            # Build (n_items × n_judges) rating matrix with integer codes
            n_cats = len(_VERDICT_ORDER)
            # aggregate_raters expects a matrix shape (items, raters)
            ratings_matrix = [
                [judge_items[j][iid] for j in judges]
                for iid in common_all
            ]
            # Build the count table manually so all 5 categories are always present
            # (statsmodels would otherwise infer categories from observed values only).
            import numpy as np

            count_table = np.zeros((n_common, n_cats), dtype=int)
            for row_idx, ratings_row in enumerate(ratings_matrix):
                for cat_code in ratings_row:
                    count_table[row_idx, cat_code] += 1

            # statsmodels divides by (1 - P_e); when only one category is
            # observed P_e == 1 and it emits a benign "invalid value" warning
            # before returning NaN. We handle the NaN explicitly below, so
            # silence the expected warning rather than letting it pollute logs.
            with np.errstate(invalid="ignore", divide="ignore"):
                fleiss_val = float(sm_fleiss(count_table))
            # statsmodels returns NaN when only a single category is ever
            # observed (P_e == 1, division degenerate). NaN is not valid JSON
            # downstream, so normalize it to None.
            fleiss_k = None if math.isnan(fleiss_val) else fleiss_val
        except (ValueError, ZeroDivisionError):
            # Genuine computation failure — report as uncomputable, do not crash.
            fleiss_k = None

    return {
        "mean_pairwise_cohen": mean_cohen,
        "fleiss_kappa": fleiss_k,
        "n_common_items": n_common,
        "n_judges": n_judges,
    }


# ---------------------------------------------------------------------------
# Step 5 — full batch aggregation
# ---------------------------------------------------------------------------

def aggregate_batch(
    judge_to_verdicts: dict[str, list[JudgeVerdict]],
    min_judges: int = DEFAULT_MIN_JUDGES,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Main aggregation entry point.

    Parameters
    ----------
    judge_to_verdicts : dict[judge_slug → list[JudgeVerdict]]
        All verdicts for all judges in the batch.
    min_judges : int
        Minimum judges required for an item to be eligible for gold. Items below
        this go to the arbitration/screening queue, never to gold (garde-fou #5).

    Returns
    -------
    report : dict
        Batch-level summary: judges, n_items, kappa metrics, agreement counts.
    gold_candidates : list[dict]
        Items with unanimous or majority agreement among >= min_judges judges.
    arbitration_records : list[dict]
        Disagreement AND insufficient-judge items, with judge identities anonymized
        and provider names redacted (garde-fou #6). Verdict/rationale/sources AND
        atomic_claims are included so the human arbiter has full context.
    """
    judges = list(judge_to_verdicts.keys())
    per_item = build_matrix(judge_to_verdicts)

    kappa_metrics = compute_kappa(judge_to_verdicts)
    agreement_map = compute_agreement(per_item, min_judges=min_judges)

    # Anonymize for the arbitration queue (garde-fou #6)
    anon_per_item = anonymize_and_shuffle(per_item)

    gold_candidates: list[dict[str, Any]] = []
    arbitration_records: list[dict[str, Any]] = []

    agreement_counts: dict[str, int] = {
        "unanimous": 0, "majority": 0, "disagreement": 0, "insufficient_judges": 0,
    }

    for item_id, item_judges in per_item.items():
        agr = agreement_map[item_id]
        agreement_counts[agr] = agreement_counts.get(agr, 0) + 1

        counts = Counter(jv.verdict.value for jv in item_judges.values())

        if agr in ("unanimous", "majority"):
            # Winner = the verdict with the most votes
            winner_value = counts.most_common(1)[0][0]

            # Agreeing judges: those who voted for the winner
            agreeing_judges = {
                slug: jv
                for slug, jv in item_judges.items()
                if jv.verdict.value == winner_value
            }

            confidence = (
                sum(jv.confidence for jv in agreeing_judges.values()) / len(agreeing_judges)
            )
            # Rationale: merge ALL agreeing judges' rationales, deduplicated, in order
            rationale = " | ".join(
                dict.fromkeys(jv.rationale.strip() for jv in agreeing_judges.values())
            )
            # Sources: union of sources from agreeing judges, deduplicated, ordered
            sources: list[str] = list(
                dict.fromkeys(
                    src
                    for jv in agreeing_judges.values()
                    for src in jv.sources
                )
            )

            gold_candidates.append(
                {
                    "item_id": item_id,
                    "verdict": winner_value,
                    "confidence": round(confidence, 4),
                    "rationale": rationale,
                    "sources": sources,
                    "agreement": agr,
                    "judges": sorted(item_judges.keys()),
                }
            )
        else:
            # Disagreement OR insufficient judges — anonymize + redact for arbitration.
            # extra_slugs = the real judge slugs, so a self-naming rationale is redacted.
            extra_slugs = list(judge_to_verdicts.keys())
            anon_judges = anon_per_item[item_id]
            arbitration_records.append(
                {
                    "item_id": item_id,
                    "agreement": agr,
                    "judges": {
                        anon_label: {
                            "verdict": jv.verdict.value,
                            "confidence": jv.confidence,
                            "rationale": _redact_providers(jv.rationale, extra_slugs),
                            "sources": [
                                _redact_providers(s, extra_slugs) for s in jv.sources
                            ],
                            "atomic_claims": [
                                _redact_providers(c, extra_slugs) for c in jv.atomic_claims
                            ],
                        }
                        for anon_label, jv in anon_judges.items()
                    },
                }
            )

    report: dict[str, Any] = {
        "judges": judges,
        "n_judges": len(judges),
        "n_items": len(per_item),
        "min_judges": min_judges,
        "agreement_counts": agreement_counts,
        "kappa": kappa_metrics,
    }

    return report, gold_candidates, arbitration_records
