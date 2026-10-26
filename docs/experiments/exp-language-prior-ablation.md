# Experiment: Language-prior ablation

**Status:** `NOT YET RUN`—the code fix has landed, the measurement has not; script to be written
**Artefact:** `results/language_prior_ablation.json`
**Addresses:** [D1](../limitations.md#d1)

## 🧭 Question

How much of the suspicion ranking is explained by the fact that a channel does
not write in French?

## 🧭 Why this experiment exists

Until September 2026 `src/graph/loader.py` set `credibility_prior = "suspect"`
**iff `fr_score < 0.15`**—iff the channel's messages rarely matched a
French-keyword regex. That prior drives `suspect_reforward_fraction`, the
largest severity modulator.

**The code has since been fixed** ([D1](../limitations.md#d1)): the prior is
now derived from documented adversary linkage. What has *not* happened is the
measurement—nobody knows how much the ranking moved. Until now no corpus was
available to run both variants against; the public corpus (dataset `v1.0.0`)
removes that obstacle. What remains is the script named under *Command*, which
does not exist yet. This protocol stays open until it is run, and it is the
first thing to run on that corpus.

A ranking that is substantially a language partition would be a serious defect
for a system whose stated meta-constraint is that thematic relevance modulates
severity but never inclusion, and whose documentation asserted for several
versions that `fr_score` was never used as an anchor.

This experiment measures the size of the effect, so the fix can be justified and
its consequences understood rather than asserted.

## 🧪 Hypothesis

The ranking is **not** substantially explained by the language prior.

## 🧪 Falsification criterion

Fixed before the run. Let `S` be the suspicion ranking as shipped and `S'` the
ranking with `credibility_prior` neutralized (all channels `"other"`, so the
suspect-reforward fraction, detail key `reforward_suspect_frac`, is 0). The
hypothesis is **falsified** if either:

```text
Spearman(suspicion_shipped, fr_score) < -0.50
```

(the score is strongly anti-correlated with writing in French), **or**

```text
Jaccard@50(S, S') < 0.60
```

(neutralizing a keyword-density threshold reshuffles most of the operational
queue).

## 🧪 Method

Run the full scoring pipeline three times on the same corpus, changing only the
prior:

1. **Legacy**—`credibility_prior` from `fr_score < 0.15` (the pre-fix
   behaviour, reconstructible from git history).
2. **Neutral**—prior disabled (`credibility_prior_enabled=False`).
3. **Catalogue**—the shipped behaviour since September 2026: prior from
   documented adversary linkage.

Report, for each pair: Spearman over the full population, Jaccard@50 and
Jaccard@100, rank displacement of the top 50, and `Spearman(suspicion, fr_score)`
within each variant.

Also report the language composition of the top 50 in each variant. If the
shipped top 50 is overwhelmingly non-French-writing while the ablated one is
not, the defect is demonstrated directly and legibly.

## 🔧 Command

No script exists yet. The planned one, `scripts/eval_language_prior_ablation.py`, should take
the mission as an argument (`--mission russosphere`) and write the artefact
above; until it is written there is no command to run.

## 📊 What this would establish

A **within-system** measurement: how much of the output is attributable to one
threshold. It does not establish that the ablated ranking is correct—only that
the shipped one was partly measuring language.

It is also a precondition for Experiment 3. Until the language confound is
removed, `adversary_linkage` and 'does not write in French' cannot be told
apart, so any discriminant result is uninterpretable.
