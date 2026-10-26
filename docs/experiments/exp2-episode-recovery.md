# Experiment 2: Known-episode recovery

**Status:** `BLOCKED`—no real external gold exists
**Script:** `scripts/eval_episode_recovery.py`
**Artefact:** `results/episode_recovery.json` (the script writes `data/eval/episode_recovery.json` today, [D25](../limitations.md#d25))

## 🧭 Question

Does the ranking surface the channels of an operation that was documented
independently of this system?

## 🧪 Hypothesis

Channels belonging to a documented operation rank materially higher than chance.

## 🧪 Falsification criterion

To be fixed **before** the run, against a gold list of size `m` in a corpus of
size `n`:

```text
recall@50 <= expected_recall@50 under uniform random ranking = 50/n
```

That is, the hypothesis fails if the ranking does no better than shuffling. A
gold overlap below `MIN_MATCHED_FOR_VERDICT` (10) in-corpus channels makes the
comparison too underpowered to report either way, and the run must be declared
inconclusive rather than interpreted.

The script's own verdict (`scripts/eval_episode_recovery.py::_evaluate`) is
stricter than this criterion and is only indicative: it reports `FAIBLE` (weak)
when the top-50 hits are at most twice the random expectation or when the
median rank of the gold sources exceeds 200, and `NON CONCLUANT`
(inconclusive) when fewer than 10 gold channels are in the corpus.

## 🧭 Why it is blocked

The gold must be produced **independently** of Idéfix, or the experiment is
circular. The only gold assembled so far was *hypothetical*, constructed by the
authors rather than sourced from an institutional investigation, and only 3 of
its 12 channels were in the corpus.

A hypothetical gold cannot falsify anything: if the ranking misses it, the gold
is blamed; if it hits, the gold was built from the same priors as the scorer.
The blocker is a **real** external seed list. See
[L5](../limitations.md#l5).

Gold files are validated against `ExternalGoldEpisode`
(`src/validation_lab/schema.py::ExternalGoldEpisode`) and must carry
`excluded_from_scorer_inputs = True`. The script falls back to a legacy
`{episode, seeds, relays}` format when a file fails that validation, so the
independence guard does not protect a file written in the legacy format.

The script also scores the `russosphere` dossier `dugin_cluster.json` whenever
the pipeline has produced it. That cluster was selected by the system itself,
so recovering it is circular and says nothing about the hypothesis.

## 🔧 Command

The script takes no arguments ([D24](../limitations.md#d24)): it reads every
`data/eval/gold_episode_*.json` it finds, and `data/channels.json`, which a
clean clone does not have ([D12](../limitations.md#d12)).

```bash
uv run python scripts/eval_episode_recovery.py
```

## 📊 What a pass would establish

That the ranking surfaces one documented operation, on one corpus. Recovering a
single episode is weak evidence for a general detector, and it says nothing
about false positives, which is Experiment 3.

## 📝 History

Until version 0.4.0 the script reported an expected hit count as a recall
control, so one output file supported two contradictory readings. That defect
is fixed ([D11](../limitations.md#d11)).
