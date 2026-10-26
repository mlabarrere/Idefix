# Experiment f — Embedding discrimination

**Status:** `NOT YET RUN` (the harness cannot yet read the public corpus, [D12](../limitations.md#d12))
**Script:** `scripts/eval_embedding_discrimination.py`
**Artefact:** `results/embedding_discrimination_russosphere.json` (the script writes `data/eval/embedding_discrimination_russosphere.json` and a `.png` today, [D25](../limitations.md#d25))

## Question

Does the representation behind semantic family (f) separate an external
organic-French baseline from the scored population?

## Hypothesis

Channel embeddings place organic French outlets and scored channels in
distinguishable regions of the embedding space.

## Falsification criterion

Fixed in the script: the representation is **not discriminative** if

```text
ROC-AUC < 0.7    OR    silhouette < 0.3
```

ROC-AUC is computed on each channel's distance to the centroid of the scored
channels in the same run.

## Precondition

Family (f) is computed, not scored ([D19](../limitations.md#d19)). A pass would
therefore show that the representation could carry signal, not that the score
uses it.

The script builds its own two classes, from the baseline file and the scored
channels, and does not use the mission's anchor handles, so the silent
zero-vector fallback of [D10](../limitations.md#d10) does not affect it. Its
module docstring promises a refusal when anchors fail to resolve; no such check
exists.

## Method

Encode the external organic-FR baseline channels and the scored channels with
the deployed representation,
`src/scorer/embedding_signals.py::compute_channel_embeddings` (the mean of each
channel's 15 longest messages, L2-normalized, `05-semantic-family.md` §5.1).
Report ROC-AUC of the baseline-versus-scored separation, silhouette, and
centroid separation. The script refuses to report when either class has fewer
than 10 usable channels.

## Command

`scripts/bootstrap_baseline.py` writes the baseline file
`data/eval/baseline_organic_fr.json`. The evaluation script accepts
`--mission`, but uses it only to name its output: the scored channels always
come from `data/channels.json`, which a clean clone does not have
([D12](../limitations.md#d12), [D24](../limitations.md#d24)).

```bash
uv run python scripts/bootstrap_baseline.py
uv run python scripts/eval_embedding_discrimination.py --mission russosphere
```

## Interpretation limits

The organic-FR baseline supplies **anchors**, not the organic *negatives*
Experiment 3 needs. A pass here would show that the embedding space distinguishes
mainstream French outlets from the scored corpus, which is a much weaker claim
than distinguishing hostile from organic coordination, and must not be reported
as the latter.

## History

Until version 0.4.0 the script embedded channel handles (the literal string
`@somechannel`) instead of message content, so it did not test the family it
named ([D11](../limitations.md#d11)). The June 2026 run produced a near-chance
result that was recorded as a weak result for family (f). That reading was
wrong. The artefact is quarantined and may not be cited; see
`archive/2026-06-russosphere/README.md`.
