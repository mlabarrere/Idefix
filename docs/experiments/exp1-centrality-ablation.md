# Experiment 1 — Centrality ablation

**Status:** `NOT YET RUN` (the public corpus exists; the harness cannot yet read it, [D12](../limitations.md#d12))
**Script:** `scripts/eval_ablation_centrality.py`
**Artefact:** `results/ablation_centrality.json` (the script writes `data/eval/ablation_centrality.json` today, [D25](../limitations.md#d25))

## Question

Is the suspicion score just a graph-centrality measure wearing a different name?

## Hypothesis

The score carries signal that is **separable** from raw prominence measures. If
it does not, the pipeline is an expensive way to compute in-degree.

## Falsification criterion

Fixed in the script (`scripts/eval_ablation_centrality.py::FALSIFY_SPEARMAN`,
`scripts/eval_ablation_centrality.py::FALSIFY_JACCARD`). The hypothesis is
**falsified** if, against either centrality baseline (in-degree or eigenvector
centrality):

```text
Spearman(suspicion, baseline) > 0.90   OR   Jaccard@50(suspicion, baseline) > 0.80
```

The script also reports forward-influence out-weight and activity or
engagement as baselines, but its verdict tests only the two centralities. The
cascade composite is reported as a **positive control**: it is a component of
the score, so a high correlation there is expected and confirms the harness
works. On the current scoring path the script reads family (b) as stored in the
channel record, which is the rigorous significance `1 - p`, not the raw
composite.

## Method

Rank all scored channels by suspicion and by each baseline. Report Spearman rank
correlation over the full population, and Jaccard overlap of the top-50 sets.
Both are label-free: this experiment needs **no gold data**, which is why it is
the only one not blocked by the annotation gaps of
[`../limitations.md`](../limitations.md).

## Command

The script takes no arguments ([D24](../limitations.md#d24)); it reads
`data/channels.json` and `data/graph.json`, which only
`scripts/prep_eval_inputs.py` writes, from the Supabase REST API
([D12](../limitations.md#d12)).

```bash
uv run python scripts/prep_eval_inputs.py --mission russosphere
uv run python scripts/eval_ablation_centrality.py
```

## What a pass would establish — and what it would not

A pass establishes only that the score is **not a relabelled centrality**. It is
a necessary condition, not evidence of validity.

It would say nothing about whether high-ranked channels are coordinated, whether
they are manipulative, or whether the ranking would survive contact with organic
coordination. Those are Experiment 3 and the language-prior ablation.

Two caveats specific to this experiment:

- Suspicion and the baselines are computed on the **same forward graph**, so some
  correlation is structural rather than informative.
- Because family values are corpus-relative ([D8](../limitations.md#d8)), the
  rank ordering is too. The experiment tests one corpus at a time and its result
  does not transfer.

## History

A June 2026 run reported a pass. That artefact is quarantined in
`archive/2026-06-russosphere/` and **may not be cited**: the database it read
was decommissioned, and the run used a combiner that is no longer the method.
A re-run on the public corpus is a new result, not a reproduction of that one.
The protocol above is unchanged; only the result is withdrawn.
