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

Ordered by severity. Each is a concrete, fixable problem, except D18: added
with the public dataset release, it describes a property of that release and is
appended rather than ranked.

### D1. `credibility_prior` was a language partition — **FIXED 2026-09**

`src/graph/loader.py` used to set `credibility_prior = "suspect"` **iff
`fr_score < 0.15`**, where `fr_score` is simply the fraction of a channel's
messages matching a French-keyword regex. "Suspect" therefore meant **"writes
in few French keywords"**.

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

**Fixed.** The prior is now evidence-based: a channel is `suspect` when it cites
documented adversary infrastructure (`CITES_DOMAIN` edges into the catalogue) or
is itself catalogued. Language is no longer an input, which finally makes the old
claim about `fr_score` true rather than false. Missions keep the ability to
disable the prior entirely (`credibility_prior_enabled`, used by `gan`).

Locked by `tests/graph/test_prior_policy.py::test_prior_follows_evidence_not_language`,
which asserts the exact inversion: a French-writing channel citing adversary
infrastructure is `suspect`, a non-French-writing channel with no documented link
is not.

**The ranking changes as a result, and the size of that change is unmeasured.**
The public corpus (dataset `v1.0.0`, Part III) now makes the measurement
possible; it has not been run. The protocol is
`docs/experiments/exp-language-prior-ablation.md`.

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

### D4. Discontinuity at zero in the combiner — **FIXED 2026-09**

The combiner dropped families on the exact equality `p >= 1.0`. Given family
(c)'s pseudo-p of `1 - value`, a channel with `coord_value = 0.0` was dropped,
while `coord_value = 0.0001` gave `p = 0.9999`, `z ~ -3.7`, crushing the combined
score. An arbitrarily small input change produced a large rank change.

**Fixed** by replacing the exact threshold with a band, `NO_SIGNAL_PVALUE = 0.99`:
a p-value indistinguishable from "no signal" is excluded, so the frontier is
continuous. Locked by
`tests/scorer/test_combination_significance.py::test_combination_is_continuous_near_zero_signal`.

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

### D7. `n_bootstrap = 100` is too low — **FIXED 2026-09**

Raised to 1000 in `src/missions/spec.py`. Cost is linear and it does not touch
the p-values (which come from `n_null`), so it cannot shift the ranking.

### D8. Scores are max-normalized and so not comparable across runs

Families (b) and (d) divide by the corpus maximum
(`cascade_role.py:103`, `recidivism.py:87-89`). A channel's value depends on every
other channel in the run; one new hub rescales everyone. Values are comparable
within a single export and **not** across exports, corpora or time.

### D9. Bridge Score sums terms that scale differently with corpus size

`cascade_role.py:93-97` adds three quantities with different asymptotics:
`in_degree_centrality` is normalized by `n-1`, so it decays as `1/n`;
`eigenvector_centrality_numpy` returns an L2-normalized vector, which does not
decay the same way; `clustering` is scale-free in `[0,1]`.

Measured on a synthetic core-plus-tail graph, holding the topology fixed and
growing only the corpus (median contribution per node):

| nodes | `10 * in_degree` | `7 * eigenvector` |
|---|---|---|
| 110 | 0.092 | 0.049 |
| 510 | 0.020 | 0.049 |
| 2010 | 0.005 | 0.047 |
| 8010 | 0.001 | 0.042 |

The two terms **cross over** at a few hundred nodes. On a small corpus the score
is driven by in-degree; on a large one, by eigenvector centrality — by a factor
of ~33 at 8 000 nodes.

The consequence is worse than an arbitrary weighting. The published weights
`10 / 7 / 7` do not express the relative importance of the three signals at any
particular scale, and **the composite silently changes character as the corpus
grows**. Two runs on differently-sized corpora are not measuring the same thing,
which compounds D8.

*Fix:* standardize the three components (z-score or rank) before combining, so
that the weights mean what they appear to mean.

Reproduced by `tests/scorer/test_cascade_role.py::test_term_scaling_crossover`.

### D10. Family (f) fails silently

`embedding_signals.py:98` falls back to `np.zeros(384)` when an anchor handle
does not resolve. Cosine against zero is 0, so `baseline_distance` becomes 1.0
for **every** channel, adding a uniform `+0.4` with no error raised. Any run
using family (f) must verify anchor resolution first.

Its two terms are also strongly anti-correlated cosines in the same space, so the
weighted sum largely reduces to "cosine to the adversary centroid" — it is one
signal presented as two.

### D11. Two evaluation scripts are mis-specified — **FIXED 2026-09**

`eval_episode_recovery.py:49` computes `len(members)*k/n` and labels it
`random_control_recall@k`. That is an **expected hit count**, not a recall, yet
it is printed beside a genuine `recall@k`. Depending on which pair a reader
compares, the same output file supports both "at chance" and "an order of
magnitude above chance" — and the verdict logic uses the count comparison.

`eval_embedding_discrimination.py:77` built its texts as
`[f"@{u}" for u in usernames]` — it embedded **channel handles**, not message
content. It therefore did not test the deployed semantic family at all, and its
near-chance ROC-AUC measured only the inseparability of handle strings.

**Both fixed.** The recovery control is now `k/n`, in the same unit as
`recall@k`; the expected-count figure is kept under the honest name
`expected_hits_random@k`; and a run with fewer than 10 gold members in the corpus
is reported `NON CONCLUANT` rather than interpreted. The embedding experiment now
calls `compute_channel_embeddings` — the same function the scorer uses — so
experiment and deployment share one code path, and it refuses to report when
either class has fewer than 10 usable channels.

### D12. The evaluation harness cannot run from a clean clone

`scripts/_eval_common.py:22-27` requires `data/channels.json` and
`data/graph.json`, neither of which is present, and `data/eval/` is gitignored.
Five of the seven `eval_*` scripts cannot execute. `eval_scoring_significance.py`
exits immediately for lack of `data/eval/channel_gold.json`.

**Narrowed by the public corpus, still open.** A clean clone can now rebuild
the database those files are derived from: the bootstrap restores dataset
`v1.0.0` and recomputes `channel_scores` and `edges` locally. But the only tool
that writes `data/channels.json` and `data/graph.json`,
`scripts/prep_eval_inputs.py`, reads them over the Supabase REST API
(`SUPABASE_URL`), not over a PostgreSQL connection, so it cannot read the local
database. `channel_gold.json` comes from `scripts/derive_channel_gold.py`, which
needs external gold files that do not exist (L4, L5).

*Fix:* build the two snapshot files from `DATABASE_URL`, as every pipeline
stage does.

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

### D15b. Isolated channels scored 1.0 in family (b) — **FIXED 2026-09**

Found while writing the tests D17 called for. Not present in any earlier audit.

`nx.in_degree_centrality` returns 1 for the only node of a singleton graph, and
the eigenvector of a 1x1 matrix is 1. A channel with **no edges at all**
therefore produced `bridge_raw = 10*1 + 7*1 = 17`, which became the corpus
maximum, so `bridge_norm = 1.0` and `triggered = True` — **the maximum possible
cascade score for a channel with no edges**.

The main scoring path masked the symptom, because the rigorous layer overwrites
value and trigger status for family (b). But `scripts/build_dossier.py:198` and
`channel_archetypes` consume `score_cascade_role` directly and were exposed.

**Fixed** by a degenerate-centrality guard: a node whose in-degree and
out-degree are both zero scores 0.0, which is what `classify_archetype` already
implied by returning `None`. Locked by two tests in
`tests/scorer/test_cascade_role.py`.

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

### D17. The rigorous path is untested — **partly fixed 2026-09**

The September 2026 audit found that `cascade_role.py`, `recidivism.py` and
`rigor.py` had **no dedicated test file**, despite carrying families (b) and (d)
and the entire rigorous path. Families (b) and (d) now have one each
(`tests/scorer/test_cascade_role.py`, `tests/scorer/test_recidivism.py`).
`rigor.py` — the null model and bootstrap behind both — still has none. The
end-to-end statistical test (`tests/scorer/test_combination_significance.py`)
runs on a synthetic planted graph.

### D18. The published snapshot carries derived tables from an earlier pipeline run

Dataset `v1.0.0` is the **complete** database snapshot named as
`source_snapshot` in `dataset/manifest.json`. Besides the collected tables
(`channels`, `messages`, `comments`), it holds the derived tables as they stood
when it was taken — `edges`, `channel_scores`, `scores_run_meta` — and the
`channels.extra` keys written by the tagging stages (`fr_score`,
`gan_targeting`). Nothing was emptied. The snapshot predates schema revisions
`0007` and `0008`; the bootstrap applies those two additive migrations, so the
restored `channel_scores` rows have no `gate_families` until scores are
recomputed.

Those derived values come from an **earlier pipeline run**: before the D1, D4
and D15b fixes, with code that is not recorded. They are not results. **Cite
only numbers regenerated by `scripts/pipeline.py`**, never a value read from a
derived table as restored. The bootstrap runs the pipeline right after the
restore, so in normal use the restored values are overwritten — with two
caveats:

- `build_scores.py` deletes and rewrites `channel_scores` and
  `scores_run_meta` **per mission** (`scripts/build_scores.py:106-114`). A
  mission the pipeline did not run keeps its restored rows.
- `build_edges.py` only upserts (`src/graph/edges.py:594`) and never deletes. An
  edge the earlier run produced and the current code no longer produces
  survives a rebuild; a fully regenerated `edges` table requires clearing it
  before `build_edges` runs.

Regenerated numbers are not expected to match anything in
`archive/2026-06-russosphere/` (quarantined, may not be cited): the archive was
produced by a different combiner (Part III), before the same fixes, and whether
those runs read exactly the state captured in the snapshot is not recorded.
Reading the restored derived tables does not reproduce the archive either. A
discrepancy between a regenerated figure and an archived one is therefore not
evidence of a bug in either — and an agreement is not a validation.

The corpus is also a **frozen snapshot**: it does not reflect posts edited or
deleted after it was taken, nor channels created since. Its collection window
is recorded in `dataset/manifest.json`.

---

## Part III — Reproducibility status

**The corpus is reproducible; no result has been regenerated from it yet.**

The PostgreSQL instance that held the corpus behind the historical figures has
been decommissioned. A complete snapshot of that database survived and is now
published as **dataset `v1.0.0`**: channels, channel posts and comments
collected from public Telegram channels and their public discussion groups,
plus the derived tables of an earlier pipeline run (D18), as a GitHub Release
asset pinned by SHA-256 in `dataset/manifest.json`, described by
`dataset/DATASHEET.md`. `scripts/bootstrap.py` fetches and verifies it,
restores it into a local PostgreSQL 17 and recomputes the derived tables and
analyst bundles with the current pipeline — from a clean clone, with no
Telegram credentials.

What that does and does not make reproducible:

- **Reproducible:** the snapshot, byte for byte (the SHA-256 pin); and
  everything the pipeline derives from it can be recomputed by anyone. Whether
  two recomputations agree exactly has not been checked — random seeds and the
  downloaded embedding model are the obvious places they could diverge.
- **Not results:** the derived values restored with the snapshot. They come
  from an earlier pipeline run; only regenerated numbers may be cited (D18).
- **Not yet runnable on it:** the evaluation harness, which still cannot run
  from a clean clone (D12).
- **Not reproduced by it:** the historical metrics. They stay quarantined under
  `archive/2026-06-russosphere/` and **may not be cited** — see that
  directory's README. Regenerated numbers are not expected to match them
  (D18).
- `docs/experiments/` contains **protocols**, not results: hypothesis,
  falsification criterion, command, expected artefact.
- `docs/experiments/results/` is still empty. It will hold only figures
  regenerated from the public corpus, each with the commit and dataset version
  that produced it.

There is a further consequence worth stating plainly. The historical bundles were
produced by a **renormalized weighted average** of family values, whereas the
implementation combines p-values by Stouffer under BH control. Verified directly: no shipped
channel file contains `p_combined`. **Nothing ever
published was produced by the statistics this project describes.** The
implementation is now the canonical method (`03-suspicion-score.md` §3.5), and
the historical numbers document a method that is no longer claimed.

---

## Part IV — Priority order for closing these

**Closed in September 2026:** D1 (language prior), D4 (combiner
discontinuity), D7 (bootstrap size), D11 (both evaluation bugs), D15b (isolated
channels scoring 1.0). D9 was re-measured and its description corrected — the
original claim had the direction of the effect backwards.

Still open, in order:

1. **L4** — an organic-coordination corpus. Unblocks the discriminant experiment
   and any global ROC-AUC. Human annotation; nothing else substitutes.
2. **D2** — a null model for family (c). Removes the placebo p-value.
3. **L5** — a real external gold. Makes episode recovery falsifiable.
4. **D5** — `CO_HASHTAG` manufacturing coordination edges.
5. **D6** — fabricated confidence bands outside families (b) and (d).
6. **D9** — standardize the Bridge Score components so that the weights mean
   something stable across corpus sizes.
7. **D3** — the Stouffer independence violation.
8. **D14** — sensitivity analysis on the free parameters, starting with
   `EMB_SIM` and the Leiden resolution.
9. **D16** — unify the two gate definitions.

**Measuring the effect of the D1 fix is itself a priority.** The ranking has
changed, and by how much is unknown. The public corpus now makes the comparison
possible; it has not been run.

D18 needs no fix to the method, only discipline: cite regenerated numbers,
never restored or archived ones. Its `edges` caveat is closed by clearing the
table before a full rebuild.
