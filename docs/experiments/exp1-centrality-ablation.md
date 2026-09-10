# Experiment 1 — Centrality ablation

**Status:** `NOT YET RUN` (corpus unavailable)
**Script:** `scripts/eval_ablation_centrality.py`
**Artefact:** `results/ablation_centrality.json`

## Question

Is the suspicion score just a graph-centrality measure wearing a different name?

## Hypothesis

The score carries signal that is **separable** from raw prominence measures. If
it does not, the pipeline is an expensive way to compute in-degree.

## Falsification criterion

Fixed in the script (`:30-31`). The hypothesis is **falsified** if, against any
baseline:

```
Spearman(suspicion, baseline) > 0.90   OR   Jaccard@50(suspicion, baseline) > 0.80
```

Baselines: in-degree centrality, eigenvector centrality, forward-influence
out-weight, activity/engagement. The cascade composite is included as a
**positive control** — it is a component of the score, so a high correlation
there is expected and confirms the harness works.

## Method

Rank all scored channels by suspicion and by each baseline. Report Spearman rank
correlation over the full population, and Jaccard overlap of the top-50 sets.
Both are label-free: this experiment needs **no gold data**, which is why it is
the only one not blocked by the annotation gaps of `../limitations.md`.

## Command

```bash
uv run python scripts/prep_eval_inputs.py --mission russosphere
uv run python scripts/eval_ablation_centrality.py --mission russosphere
```

## What a pass would establish — and what it would not

A pass establishes only that the score is **not a relabelled centrality**. It is
a necessary condition, not evidence of validity.

It would say nothing about whether high-ranked channels are coordinated, whether
they are manipulative, or whether the ranking would survive contact with organic
coordination. Those are Experiments 3 and the language-prior ablation.

Two caveats specific to this experiment:

- Suspicion and the baselines are computed on the **same forward graph**, so some
  correlation is structural rather than informative.
- Because families (b) and (d) are **max-normalized** (`../limitations.md` D8),
  the rank ordering is corpus-relative. The experiment tests one corpus at a
  time and its result does not transfer.

## History

A June 2026 run reported a pass. That artefact is quarantined in
`archive/2026-06-russosphere/` and **may not be cited**: the corpus is gone, and
the run used a combiner that is no longer the method. The protocol above is
unchanged; only the result is withdrawn.
