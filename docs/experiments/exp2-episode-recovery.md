# Experiment 2 — Known-episode recovery

**Status:** `BLOCKED` — no real external gold exists
**Script:** `scripts/eval_episode_recovery.py` (**contains a defect, see below**)
**Artefact:** `results/episode_recovery.json`

## Question

Does the ranking surface the channels of an operation that was documented
independently of this system?

## Hypothesis

Channels belonging to a documented operation rank materially higher than chance.

## Falsification criterion

To be fixed **before** the run, against a gold list of size `m` in a corpus of
size `n`:

```
recall@50 <= expected_recall@50 under uniform random ranking = 50/n
```

i.e. the hypothesis fails if the ranking does no better than shuffling. A gold
overlap below 10 in-corpus channels makes the comparison too underpowered to
report either way, and the run must be declared inconclusive rather than
interpreted.

## Why it is blocked

The gold must be produced **independently** of Idéfix, or the experiment is
circular. The only gold assembled so far was *hypothetical* — constructed by the
authors rather than sourced from an institutional investigation — and only 3 of
its 12 channels were in the corpus.

A hypothetical gold cannot falsify anything: if the ranking misses it, the gold
is blamed; if it hits, the gold was built from the same priors as the scorer.
The blocker is a **real** external seed list. See `../limitations.md` L5.

Gold files are validated against `ExternalGoldEpisode`
(`src/validation_lab/schema.py`) and must carry
`excluded_from_scorer_inputs = True`.

## Defect in the current script — fix before any run

`eval_episode_recovery.py:49`:

```python
out[f"random_control_recall@{k}"] = len(members) * k / n
```

That expression is the **expected number of hits** under a uniform random
ranking, not a recall. It is emitted beside a genuine `recall@k = hits/len(members)`
and read as if comparable, and the verdict logic at `:57-61` uses the count
comparison. The consequence is that one output file supports two contradictory
readings of the same run.

The correct control for `recall@k` is `k/n`. The count comparison, if kept, must
be renamed to `expected_hits@k` and reported separately.

## Command

```bash
uv run python scripts/eval_episode_recovery.py --mission <mission> \
    --gold data/eval/gold_episode_<name>.json
```

## What a pass would establish

That the ranking surfaces one documented operation, on one corpus. Recovering a
single episode is weak evidence for a general detector, and it says nothing
about false positives — which is Experiment 3.
