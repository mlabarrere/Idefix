# Limitations and known defects

This is the single register of everything that bounds what Idéfix can claim. It
covers both **permanent limits** (properties of the data source and the problem)
and **open defects** (things that are wrong and could be fixed).

The rule this repository follows: *what is measured above chance is reported as
such; what is not measurable is declared blocked, never filled in with prose.*

Nothing in this file is hypothetical. Every defect below was verified against the
code at the line references given.

---

## Part I — Permanent limits

### L1. Single-platform coverage

Telegram public channels only. An operation reaching its audience mainly through
other platforms, without a Telegram stage, **will not be detected**. What is
measured is a Telegram-observable footprint, never a total footprint.

This is the load-bearing limitation of the system and a mandatory field of every
exported bundle.

### L2. The graph is a partial projection

Cross-platform relays, screenshots, re-cropped media and private channels are
invisible. Channels under a French legal block are invisible to an EU-anchored
collector account. Deletion is detected by polling diff (roughly 15 minutes
latency on hot channels); no platform firehose exists.

### L3. Earliest-observed is not origin

"First-visible seeding channel" is a statement about the observation window, not
about causation. The system cannot and does not establish that a channel
originated anything.

### L4. No negative class exists

The system has never been tested against **organic** coordination — legitimate
communities that coordinate for ordinary reasons. Without that negative class,
no experiment can distinguish "detects hostile coordination" from "detects
coordination", or from "detects prominence in an adversarial ecosystem". This
blocks the discriminant experiment and any global ROC-AUC.

Closing it requires human annotation. No amount of engineering substitutes.

### L5. No real external gold

Episode-recovery evaluation requires a seed list produced independently of this
system. The only gold available so far was **hypothetical** rather than sourced
from an institutional investigation, which makes the experiment
non-falsifiable in practice.

### L6. No measured inter-annotator agreement

`src/labeling/aggregate.py` implements Cohen's and Fleiss' kappa correctly, and
handles the degenerate perfect-agreement case. But the repository contains
exactly **one** judge file, so `compute_kappa` returns `n_judges: 1` and both
kappas `None`. There is no measured agreement, and none may be claimed.

---

## Part II — Open defects

Ordered by severity. Each is a concrete, fixable problem.

### D1. `credibility_prior` is a language partition — **critical**

`src/graph/loader.py:66,128` sets `credibility_prior = "suspect"` **iff
`fr_score < 0.15`**, where `fr_score` (`scripts/tag_france.py:35`) is simply the
fraction of a channel's messages matching a French-keyword regex.

"Suspect" therefore means **"writes in few French keywords"**.

That prior then drives `suspect_reforward_fraction`, the largest of the three
severity modulators (`03-suspicion-score.md` §3.8). On the June 2026 run the
suspicion ranking correlated far more strongly with adversary linkage than with
coordination value — that is, **the ranking was substantially a ranking by
language, not by coordination structure.** The figures behind that statement are
quarantined and may not be cited; the effect must be re-measured by the
language-prior ablation protocol before any magnitude is quoted.

Two things follow. First, the system's own discriminant result is explained by
this defect rather than by the method. Second, versions of the methodology up to
and including 0.3.0 asserted the opposite in so many words — *"`fr_score` is a
display field only and is never used as a filter or anchor"* — which was false.
That sentence has been removed.

*Fix:* replace the language-derived prior with an explicit prior sourced from the
documented adversary catalogue, or remove the prior. The ranking will change;
that is the point. Measuring the delta is a publishable result in itself.

### D2. Family (c) has no null model — **critical**

`rigor.py:111-130` excludes coordination from rigorous treatment. Its p-value
falls back to `p = 1 - value` (`channel_suspicion.py:501`), a monotone rescaling
of the value rather than a tail probability under any hypothesis. The same
fallback applies to the six `telegram_*` families and to injected family (a) —
so on the `gan` mission, eight of ten combined "p-values" are not p-values.

Because this pseudo-p enters a Stouffer combination alongside genuine p-values,
the combined figure is not a p-value either.

*Fix:* build a degree-preserving or edge-swapping null on the coordination graph,
or exclude (c) from the combination until one exists.

### D3. Stouffer independence is violated

Families (b) and (d) are computed on the **same forward graph**, against the
**same null ensemble** (`rigor.py:136-138`) and the **same bootstrap draws**
(`:142-149`). Stouffer assumes independence; correlated inputs make the combined
p anticonservative — it overstates significance.

### D4. Discontinuity at zero in the combiner

`channel_suspicion.py:568-576` drops families with `p >= 1.0`. Given family (c)'s
pseudo-p of `1 - value`, a channel with `coord_value = 0.0` is dropped, while
`coord_value = 0.0001` gives `p = 0.9999`, `z ~ -3.7`, crushing the combined
score. An arbitrarily small input change produces a large rank change.

### D5. `CO_HASHTAG` manufactures coordination

Any two channels posting `#Ukraine` within 72 hours become coordination
partners. Since family (c) triggers on **two distinct edge types** regardless of
timing tightness, `CO_HASHTAG` alone can push a channel through the multi-source
gate. On the June 2026 run a large fraction of the coordination-triggered
population saturated at the maximum value.

*Fix:* drop `CO_HASHTAG`, or require it to co-occur with a stronger pivot, or
weight edge types by how surprising they are.

### D6. Confidence bands are fabricated outside families (b) and (d)

Bands genuinely propagate through the Stouffer combination, and (b) and (d)
receive real bootstrap intervals. Everything else ships hardcoded constants —
`value +/- 0.15`, `+/- 0.10`, `+/- 0.20` (`cascade_role.py:212`,
`recidivism.py:93`, `coordination.py:326`, `telegram_footprint.py:41`,
`embedding_signals.py:165`). `significance.py:16` calls them
"bandes +/-0.15 factices" in the source. Family (c)'s interval collapses to a
point because it has no null model.

A published interval on any family other than (b) or (d) is a formatting
convention, not an uncertainty estimate.

### D7. `n_bootstrap = 100` is too low

`src/missions/spec.py:127`. Bootstrap intervals at n = 100 are unstable; 1000 or
more is standard. Cheap to fix.

### D8. Scores are max-normalized and so not comparable across runs

Families (b) and (d) divide by the corpus maximum
(`cascade_role.py:103`, `recidivism.py:87-89`). A channel's value depends on every
other channel in the run; one new hub rescales everyone. Values are comparable
within a single export and **not** across exports, corpora or time.

### D9. Bridge Score sums incompatible scales

`cascade_role.py:93-97` adds `in_degree_centrality` (normalized by `n-1`, in
[0,1]), `eigenvector_centrality_numpy` (L2-normalized, entries of order
`1/sqrt(n)`) and `clustering` (in [0,1]). At corpus scale the eigenvector term is
numerically negligible, so the published "three-component composite" is in
practice two components.

### D10. Family (f) fails silently

`embedding_signals.py:98` falls back to `np.zeros(384)` when an anchor handle
does not resolve. Cosine against zero is 0, so `baseline_distance` becomes 1.0
for **every** channel, adding a uniform `+0.4` with no error raised. Any run
using family (f) must verify anchor resolution first.

Its two terms are also strongly anti-correlated cosines in the same space, so the
weighted sum largely reduces to "cosine to the adversary centroid" — it is one
signal presented as two.

### D11. Two evaluation scripts are mis-specified

`eval_episode_recovery.py:49` computes `len(members)*k/n` and labels it
`random_control_recall@k`. That is an **expected hit count**, not a recall, yet
it is printed beside a genuine `recall@k`. Depending on which pair a reader
compares, the same output file supports both "at chance" and "an order of
magnitude above chance" — and the verdict logic uses the count comparison.

`eval_embedding_discrimination.py:77` builds its texts as
`[f"@{u}" for u in usernames]` — it embeds **channel handles**, not message
content. It therefore does not test the deployed semantic family at all, and its
ROC-AUC of 0.506 measures the inseparability of handle strings, which is expected
and uninformative.

### D12. The evaluation harness cannot run from a clean clone

`scripts/_eval_common.py:22-27` requires `data/channels.json` and
`data/graph.json`, neither of which is present, and `data/eval/` is gitignored.
Five of the seven `eval_*` scripts cannot execute. `eval_scoring_significance.py`
exits immediately for lack of `data/eval/channel_gold.json`.

### D13. Uncalibrated constants inherited from other models

`TEXT_SIM_THRESHOLD = 0.715` and `TRANSLATION_THRESHOLD = 0.85`
(`graph/edges.py:454-455`) come from VIGINUM's D3lta and from BGE-M3, and are
applied to multilingual MiniLM-L12-v2. The source comment says so. Any output of
these families is uncalibrated.

### D14. Free parameters with no derivation and no sensitivity analysis

Each of the following is a degree of freedom that the literature does not
justify and no experiment has probed:

| Constant | Location |
|---|---|
| Family weights `a .15 / b .30 / c .25 / d .30 / e .15` | `channel_suspicion.py:145-151` |
| Severity bounds `0.20 / 0.15 / 0.20`, saturation at 5 | `channel_suspicion.py:157-167` |
| `TRIGGER_THRESHOLD = 0.3`, duplicated in five modules | `cascade_role.py:42` and others |
| Internal splits `0.5/0.5`, `0.6/0.4`, `0.4/0.6`, `0.7/0.3` | coordination, recidivism, embedding |
| Targeting weights `0.55 / 0.30 / 0.15`, saturation `4.0` | `france_targeting.py:136-141` |
| `EMB_SIM` `k = 5`, threshold `0.5`, scale `3.0` | `embed/community.py:52` |
| Leiden `resolution = 1.6` | `analyze_communities.py:293` |
| 28 regex themes, `MIN_COVER .12`, `MIN_SCORE .18` | `analyze_communities.py:105-209` |
| EEFI severities, all in [0.75, 1.00] | `eefi_rubric.py:30-74` |
| 10 hardcoded adversary domains | `channel_suspicion.py:124-140` |
| 5 baseline + 3 adversary handles for family (f) | `russosphere/__init__.py:109-114` |

The EEFI rubric's severities being nearly all in [0.75, 1.00] makes that family
effectively binary: any regex match yields roughly 0.9. Its header correctly
labels the weights a business decision pending sponsor calibration.

### D15. Mission gate calibration is unreconciled

The `gan` and `russosphere` missions have produced T2 volumes differing by more
than an order of magnitude. This is a calibration artefact of the `telegram_*`
families and their gate, not a finding about relative prevalence. Until the gates
are harmonized and documented, `gan` T2 counts are uninterpretable.

### D16. A second, contradictory gate exists in the dossier builder

`src/dossier/builder.py:339` gates on `n_signals >= 3 and n_families >= 2`,
while the production queue gates on `n_families >= 2`
(`channel_suspicion.py:617`). With only four families ever firing, the stricter
rule is close to "all of them". The two paths can therefore disagree about
whether the same channel met the gate, and a dossier can contradict the queue it
came from.

`src/dossier/builder.py:79-103` additionally constructs five `ScoreResult`
objects whose evidence is the literal note `"stub — v0"`.

*Fix:* one gate definition, imported by both paths.

### D17. Two flagship families are untested

`cascade_role.py`, `recidivism.py` and `rigor.py` have **no dedicated test
file**, despite carrying families (b) and (d) and the entire rigorous path. The
end-to-end statistical test (`tests/scorer/test_combination_significance.py`) is
62 lines on a synthetic planted graph.

---

## Part III — Reproducibility status

**No result in this repository is currently reproducible.** The PostgreSQL
instance holding the corpus behind every published figure has been
decommissioned.

Consequently:

- All historical metrics are quarantined under `archive/2026-06-russosphere/`
  and **may not be cited**. See that directory's README for the three reasons.
- `docs/experiments/` contains **protocols**, not results: hypothesis,
  falsification criterion, command, expected artefact.
- `docs/experiments/results/` is empty and will hold only figures regenerated
  against a corpus a third party can rebuild.

There is a further consequence worth stating plainly. The historical bundles were
produced by a **renormalized weighted average** of family values, whereas the
implementation combines p-values by Stouffer under BH control. Verified directly: no shipped
channel file contains `p_combined`. **Nothing ever
published was produced by the statistics this project describes.** The
implementation is now the canonical method (`03-suspicion-score.md` §3.5), and
the historical numbers document a method that is no longer claimed.

---

## Part IV — Priority order for closing these

1. **D1** — the language prior. It invalidates the interpretation of the one
   discriminant number the project had.
2. **L4** — an organic-coordination corpus. Unblocks the discriminant experiment
   and any global ROC-AUC. Human annotation.
3. **D2** — a null model for family (c). Removes the placebo p-value.
4. **D11** — the two evaluation bugs. Cheap, and both currently produce
   misleading output.
5. **L5** — a real external gold. Makes episode recovery falsifiable.
6. **D5, D6, D7, D9** — noise, fabricated intervals, bootstrap size, scale
   mismatch. All cheap.
7. **D14** — sensitivity analysis on the free parameters, starting with
   `EMB_SIM` and the Leiden resolution.
