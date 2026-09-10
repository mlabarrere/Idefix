# Experiment 3 — Hostile versus organic coordination

**Status:** `BLOCKED` — the negative class does not exist
**Script:** `scripts/eval_discriminant_organic.py`, `scripts/eval_organic_control.py`
**Artefact:** `results/discriminant_organic.json`

## Question

Does the score separate **hostile** coordination from **organic** coordination —
fan communities, activist networks, newsrooms, anything that coordinates for
ordinary reasons?

## Why this is the experiment that matters

Every other experiment is a necessary condition. This is the one that decides
whether the system detects what it claims to detect.

Coordination is not rare and is not inherently hostile. A detector that fires on
coordination as such will fire on legitimate communities, and its operational
queue will be contaminated. Nothing in this project has yet tested that.

## Hypothesis

Among channels that trigger the coordination family, suspicion is driven by
**coordination structure**, and confirmed-organic communities do not contaminate
the top of the queue.

## Falsification criterion

Fixed before the run:

- **Contamination:** falsified if 3 or more confirmed-organic channels appear in
  the top 50 by suspicion.
- **Attribution of the signal:** if
  `Spearman(suspicion, adversary_linkage) >> Spearman(suspicion, coordination_value)`,
  then the ranking is driven by anchoring priors rather than by coordination
  structure, and the hypothesis fails on its own terms even without organic
  negatives.

## Why it is blocked

The corpus is **seeded on the adversary**. Snowball crawling from adversary seeds
produces a corpus of adversary-adjacent channels, so the count of organic
candidates is zero and `eval_organic_control.py` reports
`has_organic_corpus: false`.

With no negatives the discriminant is never stressed. The falsification rule
above is not merely unmet — it is **untestable**.

Building the negative class means deliberately crawling French-language
communities that coordinate for legitimate reasons and having a human confirm
they are organic. It is annotation work, not engineering. See
`../limitations.md` L4.

## Confound that must be removed first

The second criterion above was already met on the June 2026 run: the ranking
correlated far more strongly with adversary linkage than with coordination
value. Those figures are quarantined and may not be cited, and in any case the
result is **not interpretable as a finding about the method**,
because `adversary_linkage` was itself driven by a language partition
(`../limitations.md` D1) — `credibility_prior = "suspect"` iff the channel wrote
in few French keywords.

So the historical run cannot distinguish "the score keys on adversary anchoring"
from "the score keys on not writing in French". The language-prior ablation must
run first; only then does this experiment measure what it names.

## Command

```bash
uv run python scripts/eval_discriminant_organic.py --mission <mission>
uv run python scripts/eval_organic_control.py --mission <mission>
```

## Dependent blocked experiment

Global scoring significance (ROC-AUC against gold, permutation test,
calibration curve, `scripts/eval_scoring_significance.py`) is blocked by the same
gap. `channel_gold` holds positives and **zero** negatives, so ROC-AUC is
undefined. The script exits immediately. No global performance figure can be
stated until L4 closes.
