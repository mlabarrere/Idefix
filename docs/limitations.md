# Limitations and known defects

This is the single register of everything that bounds what Idéfix can claim. It
covers both **permanent limits** (properties of the data source and the problem)
and **defects** (things that are wrong and could be fixed), open and closed.

The rule this repository follows: *what is measured above chance is reported as
such; what is not measurable is declared blocked, never filled in with prose.*

Nothing in this file is hypothetical. Every defect below was verified against
the code it names, cited as a path and a symbol, such as
`src/scorer/rigor.py::compute_family_significance`.

<a id="status"></a>

## Status

✅ fixed · 🟠 partial · 🔴 open. The permanent limits [L1](#l1) to [L6](#l6)
have no status: they are properties of the data source and the problem, not
defects.

| Defect | Summary | Status |
|---|---|---|
| [D1](#d1) | `credibility_prior` was a language partition | ✅ fixed in 0.4.0 |
| [D2](#d2) | Family (c) has no null model | 🔴 open |
| [D3](#d3) | Stouffer's independence assumption is violated | 🔴 open |
| [D4](#d4) | Discontinuity at zero in the combiner | ✅ fixed in 0.4.0 |
| [D5](#d5) | `CO_HASHTAG` manufactures coordination | 🔴 open |
| [D6](#d6) | Confidence bands are fabricated outside families (b) and (d) | 🔴 open |
| [D7](#d7) | `n_bootstrap = 100` was too low | ✅ fixed in 0.4.0 |
| [D8](#d8) | Scores are not comparable across runs | 🔴 open |
| [D9](#d9) | The Bridge Score sums terms that scale differently with corpus size | 🔴 open |
| [D10](#d10) | Family (f) fails silently | 🔴 open |
| [D11](#d11) | Two evaluation scripts were mis-specified | ✅ fixed in 0.4.0 |
| [D12](#d12) | The evaluation harness cannot run from a clean clone | 🟠 partial |
| [D13](#d13) | Uncalibrated constants inherited from other models | 🔴 open |
| [D14](#d14) | Free parameters with no derivation and no sensitivity analysis | 🔴 open |
| [D15](#d15) | Mission gate calibration is unreconciled | 🔴 open |
| [D15b](#d15b) | Isolated channels scored 1.0 in family (b) | ✅ fixed in 0.4.0 |
| [D16](#d16) | The dossier builder applies its own, contradictory gate | 🔴 open |
| [D17](#d17) | The rigorous path is untested | 🟠 partial |
| [D18](#d18) | The published snapshot carries derived tables from an earlier run | 🟠 partial |
| [D19](#d19) | Family (f) is computed but not combined into the score | 🔴 open |
| [D20](#d20) | Bundles carry no methodology hash | 🔴 open |
| [D21](#d21) | Severity escalation is not gated on the multi-source gate | 🔴 open |
| [D22](#d22) | Deletion detection is not implemented | 🔴 open |
| [D23](#d23) | The dossier hash ignores `docs/method/` | 🔴 open |
| [D24](#d24) | Protocol commands are documented for scripts that take no arguments | 🔴 open |
| [D25](#d25) | Evaluation artefacts are written under `data/eval/` | 🔴 open |
| [D26](#d26) | The gold and organic-corpus templates are gitignored | 🔴 open |
| [D27](#d27) | The methodology hash depends on the checkout's line endings | 🟠 partial: `.gitattributes` forces LF checkouts; the hash function still hashes raw bytes |
| [D28](#d28) | Staleness of a channel can never be reported | 🔴 open |
| [D29](#d29) | The collector never records message language or URLs | 🔴 open |
| [D30](#d30) | The credibility prior is evidence-based on the scoring path only | 🔴 open |
| [D31](#d31) | The analyst interface does not display the coverage callout | 🔴 open |

---

<a id="part-i"></a>

## Part I — Permanent limits

<a id="l1"></a>

### L1. Single-platform coverage

Telegram public channels only. An operation reaching its audience mainly through
other platforms, without a Telegram stage, **will not be detected**. What is
measured is a Telegram-observable footprint, never a total footprint.

This is the load-bearing limitation of the system. Every bundle manifest
carries it as its coverage callout
(`scripts/export_static.py::build_export_metadata`).

<a id="l2"></a>

### L2. The graph is a partial projection

Cross-platform relays, screenshots, re-cropped media and private channels are
invisible. Channels under a French legal block are invisible to an EU-anchored
collector account. No platform firehose exists, and posts deleted after
collection are not detected at all ([D22](#d22)).

<a id="l3"></a>

### L3. Earliest-observed is not origin

'First-visible seeding channel' is a statement about the observation window,
not about causation. The system cannot and does not establish that a channel
originated anything.

<a id="l4"></a>

### L4. No negative class exists

The system has never been tested against **organic** coordination: legitimate
communities that coordinate for ordinary reasons. Without that negative class,
no experiment can distinguish 'detects hostile coordination' from 'detects
coordination', or from 'detects prominence in an adversarial ecosystem'. This
blocks the discriminant experiment and any global ROC-AUC (area under the
receiver operating characteristic curve).

Closing it requires human annotation. No amount of engineering substitutes.

<a id="l5"></a>

### L5. No real external gold

Episode-recovery evaluation requires a seed list produced independently of this
system. The only gold available so far was **hypothetical** rather than sourced
from an institutional investigation, which makes the experiment
non-falsifiable in practice.

<a id="l6"></a>

### L6. No measured inter-annotator agreement

`src/labeling/aggregate.py` implements Cohen's and Fleiss' kappa correctly, and
handles the degenerate perfect-agreement case. But the annotation archive of
dataset `v1.0.0` contains exactly **one** judge file, and its judge is a
language model, so `src/labeling/aggregate.py::compute_kappa` returns
`n_judges: 1` and both kappas `None`. There is no measured agreement, and none
may be claimed.

---

<a id="part-ii"></a>

## Part II — Open defects

Each is a concrete, fixable problem. D2 to D18 are ordered by severity, except
D18, which describes a property of the dataset release and is appended rather
than ranked. D19 to D31 were registered in version 0.4.1 and follow in the
order they were found. The fixed defects are in [Part V](#part-v).

<a id="d2"></a>

### D2. Family (c) has no null model — **critical**

`src/scorer/rigor.py::compute_family_significance` gives families (b) and (d) a
rigorous treatment and leaves coordination out. Its p-value falls back to
`p = 1 - value` (`src/scorer/channel_suspicion.py::_family_pvalue`), a monotone
rescaling of the value rather than a tail probability under any hypothesis.
The same fallback applies to the six `telegram_*` families and to an injected
family (a). On the `gan` mission, which combines (b), (c), (d) and six
`telegram_*` families, seven of the nine combined 'p-values' are therefore not
p-values. (The module docstring of `src/scorer/rigor.py` promises (c) a
population-reference p-value; it is not implemented.)

Because this pseudo-p enters a Stouffer combination alongside genuine p-values,
the combined figure is not a p-value either.

*Fix:* build a degree-preserving or edge-swapping null on the coordination graph,
or exclude (c) from the combination until one exists.

<a id="d3"></a>

### D3. Stouffer's independence assumption is violated

Families (b) and (d) are computed on the **same forward graph** and tested
against the **same null ensemble**
(`src/scorer/rigor.py::compute_family_significance`, which builds one
`src/scorer/significance.py::build_random_endpoint_ensemble` for both). Only
their bootstrap intervals are drawn separately. Stouffer assumes independence;
correlated inputs make the combined p anticonservative: it overstates
significance.

<a id="d5"></a>

### D5. `CO_HASHTAG` manufactures coordination

Any two channels whose first use of `#Ukraine` fell within 72 hours of each
other become coordination partners. Family (c) triggers on **two distinct edge
types** regardless of timing tightness (`MIN_DISTINCT_COORD_TYPES` in
`src/scorer/coordination.py`), and two types give it a value of at least 0.5.
`CO_HASHTAG` can supply one of those two types, so a channel that shares only a
topical hashtag and one other artefact triggers (c), which is one of the two
families the multi-source gate needs.

*Fix:* drop `CO_HASHTAG`, or require it to co-occur with a stronger pivot, or
weight edge types by how surprising they are.

<a id="d6"></a>

### D6. Confidence bands are fabricated outside families (b) and (d)

Bands genuinely propagate through the Stouffer combination, and on the main
path (b) and (d) receive real bootstrap intervals, which replace their initial
`value +/- 0.15` (`src/scorer/cascade_role.py::score_cascade_role`,
`src/scorer/recidivism.py::score_recidivism`). Every other family ships a
constant: `+/- 0.10` or `+/- 0.20` for coordination
(`src/scorer/coordination.py::score_coordination_edges`), `+/- 0.15` for the
`telegram_*` families (`src/scorer/telegram_footprint.py::_result`) and for an
injected family (a) (`src/scorer/channel_suspicion.py::compute_channel_queue`),
and `+/- 0.10` for family (f)
(`src/scorer/embedding_signals.py::score_embedding_coherence`). The module
docstring of `src/scorer/significance.py` calls them 'bandes +/-0.15
factices'. The coordination bands enter the Stouffer bound calculation as
though they were intervals.

A published interval on any family other than (b) or (d) is a formatting
convention, not an uncertainty estimate.

<a id="d8"></a>

### D8. Scores are not comparable across runs

On the main path the values of (b) and (d) are significances, `1 - p`, against
a null ensemble built from the run's own forward graph. The raw families still
divide by the corpus maximum (`src/scorer/cascade_role.py::compute_bridge_scores`,
`src/scorer/recidivism.py::score_recidivism`), and those raw values survive in
the archetype assignment and the dossier builder. Either way a channel's value
depends on every other channel in the run: one new hub rescales the raw values
and reshapes the null. Values are comparable within a single export and **not**
across exports, corpora or time.

<a id="d9"></a>

### D9. The Bridge Score sums terms that scale differently with corpus size

`src/scorer/cascade_role.py::compute_bridge_scores` adds three quantities with
different asymptotics, weighted by `W_IN_DEGREE`, `W_EIGENVECTOR` and
`W_CLUSTERING`: `in_degree_centrality` is normalized by `n-1`, so it decays as
`1/n`; `eigenvector_centrality_numpy` returns an L2-normalized vector, which
does not decay the same way; `clustering` is scale-free in `[0,1]`. The sum,
`bridge_raw`, is also the statistic that the rigorous path tests
(`src/scorer/rigor.py::compute_family_significance`).

Measured on a synthetic core-plus-tail graph, holding the topology fixed and
growing only the corpus (median contribution per node):

| Nodes | `10 * in_degree` | `7 * eigenvector` |
|---:|---:|---:|
| 110 | 0.092 | 0.049 |
| 510 | 0.020 | 0.049 |
| 2,010 | 0.005 | 0.047 |
| 8,010 | 0.001 | 0.042 |

The two terms **cross over** at a few hundred nodes. On a small corpus the score
is driven by in-degree; on a large one, by eigenvector centrality, by a factor
of about 33 at 8,000 nodes.

The consequence is worse than an arbitrary weighting. The published weights
`10 / 7 / 7` do not express the relative importance of the three signals at any
particular scale, and **the composite silently changes character as the corpus
grows**. Two runs on differently sized corpora are not measuring the same
thing, which compounds [D8](#d8).

*Fix:* standardize the three components (z-score or rank) before combining, so
that the weights mean what they appear to mean.

Reproduced by `tests/scorer/test_cascade_role.py::test_term_scaling_crossover`.

<a id="d10"></a>

### D10. Family (f) fails silently

When none of the mission's baseline handles resolves,
`src/scorer/embedding_signals.py::build_baseline_embedding` falls back to
`np.zeros(384)`. Cosine against zero is 0, so `baseline_distance` becomes 1.0
for **every** channel, adding a uniform `+0.4` with no error raised. Any run
using family (f) must verify anchor resolution first.

Its two terms are also strongly anti-correlated cosines in the same space, so the
weighted sum largely reduces to 'cosine to the adversary centroid': it is one
signal presented as two.

While [D19](#d19) holds, this defect changes no score; it becomes live the day
(f) is wired in.

<a id="d12"></a>

### D12. The evaluation harness cannot run from a clean clone

`scripts/_eval_common.py::load_channels` and `scripts/_eval_common.py::load_graph`
require `data/channels.json` and `data/graph.json`, neither of which a clone
contains. Of the nine `eval_*` scripts, eight cannot complete:

- six read those files unconditionally: `eval_ablation_centrality.py`,
  `eval_discriminant_organic.py`, `eval_episode_recovery.py`,
  `eval_france_targeting_audit.py`, `eval_embedding_discrimination.py` (which
  first needs `data/eval/baseline_organic_fr.json`, written by
  `scripts/bootstrap_baseline.py`) and `eval_scoring_significance.py` (which
  exits even earlier, for lack of `data/eval/channel_gold.json`);
- `eval_mistral_classification.py` and `eval_embeddings_classification.py` exit
  for lack of a `data/eval/gold_<target>.json` (and `channel_llm_scores` is
  empty in dataset `v1.0.0`).

Only `eval_organic_control.py` runs: it falls back to the exported
`webapp/public/data/russosphere/channels.json` and reports that no organic
corpus was found.

**Narrowed by the public corpus, still open.** A clean clone can now rebuild
the database those files are derived from: the bootstrap restores dataset
`v1.0.0` and recomputes `channel_scores` and `edges` locally. But the only tool
that writes `data/channels.json` and `data/graph.json`,
`scripts/prep_eval_inputs.py`, reads them over the Supabase REST API (it reads
`SUPABASE_URL` at import and fails without it), not over a PostgreSQL
connection, so it cannot read the local database. `channel_gold.json` comes
from `scripts/derive_channel_gold.py`, which needs external gold files that do
not exist ([L4](#l4), [L5](#l5)).

*Fix:* build the two snapshot files from `DATABASE_URL`, as every pipeline
stage does.

<a id="d13"></a>

### D13. Uncalibrated constants inherited from other models

`src/graph/edges.py::TEXT_SIM_THRESHOLD` (0.715) and
`src/graph/edges.py::TRANSLATION_THRESHOLD` (0.85) come from VIGINUM's D3lta and
from BGE-M3, and are applied to multilingual MiniLM-L12-v2. The source comment
says so. Any output of these edge types is uncalibrated. The pipeline does not
derive them today (`build_edges` runs without `--embed`), and `TRANSLATION`
could not fire anyway ([D29](#d29)).

<a id="d14"></a>

### D14. Free parameters with no derivation and no sensitivity analysis

Each of the following is a degree of freedom that the literature does not
justify and no experiment has probed:

| Constant | Location |
|---|---|
| Family weights `a .15 / b .30 / c .25 / d .30 / e .15` (`russosphere`; `gan` sets its own) | `src/scorer/channel_suspicion.py::BASE_FAMILY_WEIGHTS`, `src/missions/gan/__init__.py` |
| Severity bounds `0.20 / 0.15 / 0.20`, saturation at 5 | `src/scorer/channel_suspicion.py::MAX_REFORWARD_BOOST`, `::MAX_ADVERSARY_DOMAIN_BOOST`, `::MAX_FRANCE_TARGETING_BOOST`, `::ADVERSARY_DOMAIN_SATURATION` |
| `TRIGGER_THRESHOLD = 0.3`, duplicated in five modules | `src/scorer/{cascade_role,coordination,recidivism,embedding_signals,telegram_footprint}.py::TRIGGER_THRESHOLD`, plus `src/scorer/channel_suspicion.py::GATE_THRESHOLD` and `src/dossier/builder.py::_MULTI_SOURCE_THRESHOLD` |
| Internal splits `0.5/0.5`, `0.6/0.4`, `0.4/0.6`, `0.7/0.3` | coordination, recidivism, embedding, and the legacy `src/scorer/coordination.py::score_coordination` |
| Targeting weights `0.55 / 0.30 / 0.15`, saturation `4.0` (`russosphere`) | `src/normalizer/france_targeting.py::_FRANCE_WEIGHTS`; every mission carries its own `TargetingProfile` |
| `EMB_SIM` `k = 5`, threshold `0.5`, scale `3.0` | `src/embed/community.py::add_embedding_edges` |
| Leiden `resolution = 1.6` | `scripts/analyze_communities.py::detect_communities` |
| 27 regex themes, `MIN_COVER .12`, `MIN_SCORE .18` | `scripts/analyze_communities.py::TAXONOMY`, `::MIN_COVER`, `::MIN_SCORE` |
| EEFI severities, all in [0.75, 1.00] | `src/scorer/eefi_rubric.py::_INDICATORS` |
| 10 hard-coded adversary domains | `src/scorer/channel_suspicion.py::ADVERSARY_DOMAINS` |
| 5 baseline and 3 adversary handles for family (f) | `embedding_baseline_channels` and `embedding_adversary_channels` in `src/missions/russosphere/__init__.py` |

Every EEFI (essential elements of friendly information) severity lies in
[0.75, 1.00], which makes that family effectively binary: any regex match
yields roughly 0.9. Its header correctly labels the weights a business decision
pending sponsor calibration.

<a id="d15"></a>

### D15. Mission gate calibration is unreconciled

The `gan` mission combines nine families that can trigger (b, c, d and six
`telegram_*` families, each triggering at a value of 0.3), while `russosphere`
combines three, and both gate at the same `min_families_for_gate = 2`
(`src/scorer/channel_suspicion.py::_gate`). Meeting the gate is therefore far
easier on `gan`, and T2 counts are not comparable across the two missions.
Until the gates are harmonized and documented, `gan` T2 counts are
uninterpretable.

<a id="d16"></a>

### D16. The dossier builder applies its own, contradictory gate

`src/dossier/builder.py::build_episode_dossier`, which `scripts/build_dossier.py`
uses to write `dugin_cluster.json`, gates on `n_signals >= 3 and
n_families >= 2` over families (b), (c) and (d) only, so its rule is exactly
'all three of (b), (c) and (d) reach 0.3'. Its (c) comes from the legacy
`src/scorer/coordination.py::score_coordination`, not the coordination family
of the production queue. The production queue gates on two distinct triggered
families (`src/scorer/channel_suspicion.py::_gate`, `MIN_FAMILIES_FOR_GATE`).
The two paths can therefore disagree about whether the same channels met the
gate, and a dossier can contradict the queue it came from. Worse,
`scripts/build_dossier.py::main` hard-codes `attribution_tier="T2"` whatever
that gate decides.

A second builder, `src/dossier/builder.py::build_dossier`, constructs five
`ScoreResult` objects, four of whose evidence is a literal '… stub — v0' note,
and grades severity through `src/scorer/base.py::ScoreSummary`. Nothing in the
pipeline calls it.

*Fix:* one gate definition, imported by both paths, and a dossier tier derived
from it.

<a id="d17"></a>

### D17. The rigorous path is untested — **partly fixed in 0.4.0**

The September 2026 audit found that `cascade_role.py`, `recidivism.py` and
`rigor.py` had **no dedicated test file**, despite carrying families (b) and (d)
and the entire rigorous path. Families (b) and (d) now have one each
(`tests/scorer/test_cascade_role.py`, `tests/scorer/test_recidivism.py`).
`src/scorer/rigor.py`, the null model and bootstrap behind both, still has
none. The end-to-end statistical test
(`tests/scorer/test_combination_significance.py`) runs on a synthetic planted
graph.

<a id="d18"></a>

### D18. The published snapshot carries derived tables from an earlier pipeline run

Dataset `v1.0.0` is the **complete** database snapshot named as
`source_snapshot` in `dataset/manifest.json`. Besides the collected tables
(`channels`, `messages`, `comments`), it holds the derived tables as they stood
when it was taken (`edges`, `channel_scores`, `scores_run_meta`) and the
`channels.extra` keys written by the tagging stages (`fr_score`,
`gan_targeting`). Nothing was emptied. The source snapshot was at schema
revision `0006`; the release script applied the two additive migrations `0007`
and `0008` before dumping, so the published dump is at `0008`, the current
Alembic head, and the bootstrap's `alembic upgrade head` after a restore is a
no-op. `channel_llm_scores` is empty, and the `channel_scores` rows have no
`gate_families` until scores are recomputed.

Those derived values come from an **earlier pipeline run**: before the D1, D4
and D15b fixes, with code that is not recorded. They are not results. **Cite
only numbers regenerated by `scripts/pipeline.py`**, never a value read from a
derived table as restored. The bootstrap runs the pipeline right after the
restore, so in normal use the restored values are overwritten, with two
caveats:

- `scripts/build_scores.py::main` deletes and rewrites `channel_scores` and
  `scores_run_meta` **per mission** (`DELETE … WHERE mission = $1`). A mission
  the pipeline did not run keeps its restored rows.
- `build_edges` only upserts (`src/graph/edges.py::_UPSERT_SQL`, used by
  `src/graph/edges.py::_upsert_edges`) and never deletes. An edge the earlier
  run produced and the current code no longer produces survives a rebuild; a
  fully regenerated `edges` table requires clearing it before `build_edges`
  runs.

Regenerated numbers are not expected to match anything in
`archive/2026-06-russosphere/` (quarantined, may not be cited): the archive was
produced by a different combiner ([Part III](#part-iii)), before the same
fixes, and whether those runs read exactly the state captured in the snapshot
is not recorded. Reading the restored derived tables does not reproduce the
archive either. A discrepancy between a regenerated figure and an archived one
is therefore not evidence of a bug in either, and an agreement is not a
validation.

The corpus is also a **frozen snapshot**: it does not reflect posts edited or
deleted after it was taken, nor channels created since. Its collection window
is recorded in `dataset/manifest.json`.

<a id="d19"></a>

### D19. Family (f) is computed but not combined into the score

**Symptom.** Earlier documentation described the semantic family (f) as an
active, opt-in family that could help a channel cross the multi-source gate.
It cannot: its result never reaches the score.

**Evidence.** `src/scorer/channel_suspicion.py::_build_channel_queue_live`
computes (f) only when called with `compute_embeddings=True`, which
`scripts/build_scores.py` passes only under `--embeddings`, a flag
`scripts/pipeline.py::STAGES` never sets; `scripts/export_static.py` never
asks for it. When it does run, the result is placed under the key `"f"` of
`extra_families`. `src/scorer/channel_suspicion.py::compute_channel_queue` then
copies into the family set handed to `_combine_suspicion` and `_gate` only the
keys a mission lists in `ScoringProfile.extra_family_scorers`
(`src/missions/spec.py`), and no mission lists `"f"`. `BASE_FAMILY_WEIGHTS`
has no weight for it, and the row written to `channel_scores` and to the bundle
has no `f` entry.

**Impact.** Family (f) moves no ranking, no gate and no tier, it is stored
nowhere, and an analyst never sees it. Every statement that it provides
content-based corroboration is void. A run with `--embeddings` pays the
encoding cost for nothing.

**Planned fix.** Either wire (f) into the combiner with an explicit weight and
a null model, as a versioned normative change, or remove it from the scorer.
Wiring it while [D10](#d10) is open would add a uniform `+0.4` to every
channel's family value.

<a id="d20"></a>

### D20. Bundles carry no methodology hash

**Symptom.** The documentation said that the hash of `METHODOLOGY.md` ships in
every export, so that a methodology revision is detectable in the chain of
custody.

**Evidence.** `scripts/export_static.py::METHODOLOGY_VERSION` is the fixed
string `"idefix-methodology/2026-06-15"`, written into each bundle manifest as
`methodology_version` (overridable by the `IDEFIX_METHODOLOGY_VERSION`
environment variable). The only callers of
`src/shared/dossier.py::get_methodology_version_hash` are the two builders in
`src/dossier/builder.py`. `build_dossier` returns the hash in a
`DossierOutput`, but nothing in the pipeline calls it; `build_episode_dossier`,
which `scripts/build_dossier.py` uses, validates a `DossierSchema` that holds
the hash and then leaves the hash out of the `dugin_cluster.json` it writes. No
file the pipeline writes carries the hash.

**Impact.** The version string predates methodology 0.4.0 and 0.4.1 and has
moved with neither, so no output can tell which methodology produced it.

**Planned fix.** Write the methodology hash, once [D23](#d23) and [D27](#d27)
are fixed, into the bundle manifest and the dossier beside the version string.

<a id="d21"></a>

### D21. Severity escalation is not gated on the multi-source gate

**Symptom.** The governance commitments said that no channel receives an
escalated severity without at least two triggered families.

**Evidence.** In `src/scorer/channel_suspicion.py::compute_channel_queue`, the
factor from `_severity_modulation` is computed for every channel and applied by
`_combine_suspicion` (`value = clamp01(base * factor)`); `_gate` is evaluated
afterwards and decides only the tier. The dossier path does not wait for the
gate either: `scripts/build_dossier.py::main` maps the strongest of (b), (c)
and (d) straight to a severity tier.

**Impact.** A channel with a single triggered family is boosted by up to the
full severity factor (at most 1.55), and so can outrank a channel that meets
the gate. The tier vocabulary stays correct; the ranking does not respect the
corroboration rule that was documented for it.

**Planned fix.** Apply the severity factor only to channels that meet the
gate, as a versioned normative change, or keep the current behaviour and state
it as the rule.

<a id="d22"></a>

### D22. Deletion detection is not implemented

**Symptom.** [L2](#l2) used to say that deletions are detected by a polling
diff with roughly 15 minutes of latency, and migration `0003` records deletion
propagation, retention bounds and an access journal as constraints on the
`comments` table.

**Evidence.** The column `messages.is_deleted` exists
(`alembic/versions/0001_baseline.py`) and is read as a filter by
`scripts/build_channel_digests.py` and `scripts/build_label_batch.py`, but no
code in `src/` or `scripts/` ever sets it. The datasheet records it as false on
every row of dataset `v1.0.0`. No code deletes, purges or flags comments, and
none keeps an access journal.

**Impact.** A post deleted on Telegram after collection stays in the corpus as
if it were live, and keeps contributing edges and scores. A commenter's deleted
comment stays in the `comments` table, and the published dataset keeps it.

**Planned fix.** Implement deletion detection in the collector (a periodic
re-read of recent message IDs) and propagate it to `comments`, or keep the
corpus explicitly append-only and say so.

<a id="d23"></a>

### D23. The dossier hash ignores `docs/method/`

**Symptom.** The methodology hash is presented as identifying the method.

**Evidence.** `src/shared/dossier.py::get_methodology_version_hash` hashes
`METHODOLOGY.md` alone. Since version 0.4.0 that file is a cover page, and the
method lives in `docs/method/`.

**Impact.** A change to any method chapter, or to the code, leaves the hash
unchanged unless the cover page is edited too.

**Planned fix.** Hash `METHODOLOGY.md` together with every file under
`docs/method/`, in a fixed order, on normalized line endings ([D27](#d27)).

<a id="d24"></a>

### D24. Protocol commands are documented for scripts that take no arguments

**Symptom.** Experiment protocols documented invocations such as
`scripts/eval_ablation_centrality.py --mission russosphere` and
`scripts/eval_episode_recovery.py --gold …`.

**Evidence.** `scripts/eval_ablation_centrality.py`,
`scripts/eval_episode_recovery.py`, `scripts/eval_discriminant_organic.py`,
`scripts/eval_organic_control.py` and `scripts/eval_france_targeting_audit.py`
parse no arguments at all: none uses `argparse` or `sys.argv`.
`scripts/eval_embedding_discrimination.py` accepts `--mission` but uses it only
to name its output.

**Impact.** The flags are silently ignored. A run 'for the `gan` mission' reads
the inputs the script hard-codes (the snapshot files under `data/` and, for
episode recovery, the `russosphere` dossier), whatever the reader asked for, so
the artefact cannot be attributed to the protocol's inputs.

**Planned fix.** Give each evaluation script an argument parser for the inputs
its protocol names. Until then the protocols document the invocation without
flags.

<a id="d25"></a>

### D25. Evaluation artefacts are written under `data/eval/`

**Symptom.** Each protocol names its artefact under
`docs/experiments/results/`, where `scripts/check_docs.py` looks for the
figures it allows in prose.

**Evidence.** `scripts/_eval_common.py::EVAL_OUT` is `data/eval/`, and every
evaluation script writes there, through `scripts/_eval_common.py::write_report`
or directly; `.gitignore` excludes `data/eval/`. The module docstring of
`scripts/eval_embedding_discrimination.py` says it writes to
`docs/experiments/results/`; it does not.

**Impact.** A protocol run leaves its artefact in an ignored directory, so it
can be neither committed nor cited as the protocol requires, and the
documentation gate never sees it.

**Planned fix.** Write every evaluation artefact to
`docs/experiments/results/`, with the commit and dataset version that produced
it.

<a id="d26"></a>

### D26. The gold and organic-corpus templates are gitignored

**Symptom.** The validation-lab contracts and several scripts tell the reader
to copy a template from `data/eval/templates/`.

**Evidence.** `.gitignore` excludes `data/eval/`, so no file under
`data/eval/templates/` is tracked (`git ls-files data/eval` is empty).
`scripts/eval_mistral_classification.py`, `scripts/eval_organic_control.py`
and `scripts/derive_channel_gold.py` point at
`data/eval/templates/*.example.json` nonetheless.

**Impact.** On a fresh clone the templates do not exist, so the first step of
building an external gold or an organic control corpus fails.

**Planned fix.** Track the templates under a path that is not ignored, or
un-ignore `data/eval/templates/`.

<a id="d27"></a>

### D27. The methodology hash depends on the checkout's line endings

**Symptom.** Two checkouts of the same commit can compute different
methodology hashes.

**Evidence.** `src/shared/dossier.py::get_methodology_version_hash` hashes the
raw bytes of the working copy (`Path.read_bytes`). Until the setup pull
request added `.gitattributes`, Git on Windows with `core.autocrlf=true`
checked `METHODOLOGY.md` out with CRLF line endings, and the hash differed from
the one computed on the LF bytes Git stores. `.gitattributes` now forces LF
for `METHODOLOGY.md` and `docs/method/**`, but a copy whose line endings change
outside Git (an editor, an archive tool) still hashes differently.

**Impact.** The hash cannot identify a methodology version across operating
systems. The hashes recorded in `CHANGELOG.md` are computed on LF bytes.

**Planned fix.** The `.gitattributes` rule is in place. Normalizing line
endings inside the hash function would make it independent of how the file
was obtained altogether.

<a id="d28"></a>

### D28. Staleness of a channel can never be reported

**Symptom.** The scorer is meant to mark a channel's confidence as degraded
once it has not been polled for `STALE_DAYS` (14) days.

**Evidence.** `src/scorer/channel_suspicion.py::_confidence` degrades a channel
only when its metadata carries `last_polled_at`.
`src/scorer/channel_suspicion.py::_build_channel_queue_live` fills that
metadata only from columns present in the channel rows, and
`src/graph/loader.py::fetch_channel_rows` does not select `last_polled_at`. The
metadata is therefore always empty, and `_confidence` always returns
`"ok"`.

**Impact.** Every channel's confidence reads 'ok', however old its data. On a
frozen snapshot such as dataset `v1.0.0`, every channel is in fact stale.

**Planned fix.** Select `last_polled_at` in `fetch_channel_rows`, as a
versioned change (it alters a bundle field, not the ranking).

<a id="d29"></a>

### D29. The collector never records message language or URLs

**Symptom.** The graph model and the episode miner describe a `TRANSLATION`
edge type and a URL pivot.

**Evidence.** `src/ingestor/handlers.py::_parse_message` writes `language` as
NULL, and `src/ingestor/queries.py::insert_message` writes `urls` as NULL;
`src/normalizer/handlers.py::detect_language` has no caller. The datasheet
records both columns as NULL on every row of dataset `v1.0.0`.

**Impact.** `TRANSLATION` edges (`src/graph/edges.py::derive_text_sim_edges`)
and the URL pivot of episode discovery (`scripts/mine_episodes.py::url_pivots`)
can never fire, on the public corpus or on any corpus this code collects. URL
signals reach the graph only through the edge derivers, which re-extract URLs
from message text.

**Planned fix.** Detect the language and store the extracted URLs at
collection time, or drop the two features from the method.

<a id="d30"></a>

### D30. The credibility prior is evidence-based on the scoring path only

**Symptom.** The documentation describes `credibility_prior` as derived from
documented adversary linkage everywhere.

**Evidence.** `src/graph/loader.py::build_graph` needs the adversary domain
catalogue to mark a channel `suspect`. The scoring path passes it
(`src/scorer/channel_suspicion.py::_build_channel_queue_live`), but
`scripts/analyze_communities.py::load_graph`,
`scripts/analyze_communities_embed.py` and the `graph.json` export of
`scripts/export_static.py` call `build_graph` without it, so every node there is
`other`. The second condition of the prior, being a catalogued channel, never
applies anywhere: `catalogued_adversaries` is passed only in
`tests/graph/test_prior_policy.py`.

**Impact.** The community snapshots and the exported graph mark no channel
`suspect`, and so disagree with the scored queue about the same channels.

**Planned fix.** Pass the mission's adversary catalogue to every `build_graph`
call, and supply the catalogued-channel list or remove that branch.

<a id="d31"></a>

### D31. The analyst interface does not display the coverage callout

**Symptom.** The documentation called the single-platform coverage callout
([L1](#l1)) permanently visible in the analyst interface: sidebar, drawer, and
a per-mission caveat.

**Evidence.** The bundle manifest carries it
(`scripts/export_static.py::build_export_metadata`), but no component under
`webapp/src/` renders `coverage_callout` or the per-mission caveat keys; only
the `gan` footprint view shows a caveat of its own. The end-to-end test
`webapp/tests/e2e/mission.spec.ts` asserts that the coverage banner is gone.

**Impact.** An analyst can read a ranking without ever being told that
operations without a Telegram stage are invisible to it, which is the
load-bearing limitation of the system.

**Planned fix.** Render the manifest's coverage callout permanently in the
interface, and turn the end-to-end assertion around.

---

<a id="part-iii"></a>

## Part III — Reproducibility status

**The corpus is reproducible; no result has been regenerated from it yet.**

The PostgreSQL instance that held the corpus behind the historical figures has
been decommissioned. A complete snapshot of that database survived and is now
published as **dataset `v1.0.0`**: channels, channel posts and comments
collected from public Telegram channels and their public discussion groups,
plus the derived tables of an earlier pipeline run ([D18](#d18)), as a GitHub
Release asset pinned by SHA-256 in `dataset/manifest.json`, described by
`dataset/DATASHEET.md`. `scripts/bootstrap.py` fetches and verifies it,
restores it into a local PostgreSQL 17 and recomputes the derived tables and
analyst bundles with the current pipeline, from a clean clone and with no
Telegram credentials.

What that does and does not make reproducible:

- **Reproducible:** the release files, byte for byte (each is pinned by its
  SHA-256), and everything the pipeline derives from them, which anyone can
  recompute. Whether two recomputations agree exactly has not been checked;
  random seeds and the downloaded embedding model are the obvious places they
  could diverge, and every export stamps its own generation time.
- **Not results:** the derived values restored with the snapshot. They come
  from an earlier pipeline run; only regenerated numbers may be cited
  ([D18](#d18)).
- **Not yet runnable on it:** the evaluation harness, which still cannot run
  from a clean clone ([D12](#d12)), writes its artefacts outside the results
  directory ([D25](#d25)), and ignores the arguments its protocols document
  ([D24](#d24)).
- **Not reproduced by it:** the historical metrics. They stay quarantined under
  `archive/2026-06-russosphere/` and **may not be cited**; see that
  directory's README. Regenerated numbers are not expected to match them
  ([D18](#d18)).
- `docs/experiments/` contains **protocols**, not results: hypothesis,
  falsification criterion, command, expected artefact.
- `docs/experiments/results/` is still empty. It will hold only figures
  regenerated from the public corpus, each with the commit and dataset version
  that produced it.

There is a further consequence worth stating plainly. The historical bundles
were produced by a **renormalized weighted average** of family values, whereas
the implementation combines p-values by Stouffer's method under
Benjamini–Hochberg control. Verified directly: no shipped channel file contains
`p_combined`. **Nothing ever published was produced by the statistics this
project describes.** The implementation is now the canonical method
(`03-suspicion-score.md` §3.5), and the historical numbers document a method
that is no longer claimed.

---

<a id="part-iv"></a>

## Part IV — Priority order for closing these

**Closed in September 2026:** D1 (language prior), D4 (combiner
discontinuity), D7 (bootstrap size), D11 (both evaluation bugs) and D15b
(isolated channels scoring 1.0), all in [Part V](#part-v). D9 was re-measured
and its description corrected: the original claim had the direction of the
effect backwards.

Still open, in order:

1. **[L4](#l4)**: an organic-coordination corpus. Unblocks the discriminant
   experiment and any global ROC-AUC. Human annotation; nothing else
   substitutes.
2. **[D2](#d2)**: a null model for family (c). Removes the placebo p-value.
3. **[L5](#l5)**: a real external gold. Makes episode recovery falsifiable.
4. **[D5](#d5)**: `CO_HASHTAG` manufacturing coordination edges.
5. **[D21](#d21)**: decide whether severity is gated, and make the code and
   the governance commitments agree.
6. **[D6](#d6)**: fabricated confidence bands outside families (b) and (d).
7. **[D9](#d9)**: standardize the Bridge Score components so that the weights
   mean something stable across corpus sizes.
8. **[D3](#d3)**: the Stouffer independence violation.
9. **[D12](#d12), [D24](#d24), [D25](#d25), [D26](#d26)**: make the evaluation
   harness runnable from a clean clone, so that the first protocol can run.
10. **[D20](#d20), [D23](#d23), [D27](#d27)**: one methodology hash, covering
    the method chapters, computed on normalized bytes, written into every
    output.
11. **[D14](#d14)**: sensitivity analysis on the free parameters, starting with
    `EMB_SIM` and the Leiden resolution.
12. **[D16](#d16)**: unify the two gate definitions.

**Measuring the effect of the D1 fix is itself a priority.** The ranking has
changed, and by how much is unknown. The public corpus now makes the comparison
possible; it has not been run.

[D18](#d18) needs no fix to the method, only discipline: cite regenerated
numbers, never restored or archived ones. Its `edges` caveat is closed by
clearing the table before a full rebuild. [D19](#d19) and [D10](#d10) should be
decided together: wiring family (f) in is only safe once its silent failure is
fixed.

---

<a id="part-v"></a>

## Part V — Closed defects

Kept with their original numbers so that existing references stay valid.

<a id="d1"></a>

### D1. `credibility_prior` was a language partition — **fixed in 0.4.0**

`src/graph/loader.py` used to set `credibility_prior = "suspect"` **if and only
if `fr_score < 0.15`**, where `fr_score` is simply the fraction of a channel's
messages matching a French-keyword regex. 'Suspect' therefore meant **'writes
in few French keywords'**.

That prior drives `suspect_reforward_fraction` (the detail key
`reforward_suspect_frac`), one of the two largest severity modulators, tied at
0.20 with thematic targeting (`03-suspicion-score.md` §3.8). On the June 2026
run the suspicion ranking correlated far more strongly with adversary linkage
than with coordination value: **the ranking was substantially a ranking by
language, not by coordination structure.** The figures behind that statement
are quarantined and may not be cited; the effect must be re-measured by the
language-prior ablation protocol before any magnitude is quoted.

Two things follow. First, the system's own discriminant result is explained by
this defect rather than by the method. Second, versions of the methodology up to
and including 0.3.0 asserted the opposite in so many words, *'`fr_score` is a
display field only and is never used as a filter or anchor'*, which was false.
That sentence has been removed.

**Fixed.** The prior is now evidence-based: a channel is `suspect` when it cites
documented adversary infrastructure (`CITES_DOMAIN` edges into the catalogue)
(`src/graph/loader.py::credibility_prior`). Language is no longer an input to
the score. Missions keep the ability to disable the prior entirely
(`credibility_prior_enabled`, used by `gan`). The rule's second branch, a
catalogued channel, never applies, and the prior is only evidence-based on the
scoring path ([D30](#d30)).

Locked by `tests/graph/test_prior_policy.py::test_prior_follows_evidence_not_language`,
which asserts the exact inversion: a French-writing channel citing adversary
infrastructure is `suspect`, a non-French-writing channel with no documented
link is not.

**The ranking changes as a result, and the size of that change is unmeasured.**
The public corpus (dataset `v1.0.0`, [Part III](#part-iii)) now makes the
measurement possible; it has not been run. The protocol is
[`exp-language-prior-ablation.md`](./experiments/exp-language-prior-ablation.md).

<a id="d4"></a>

### D4. Discontinuity at zero in the combiner — **fixed in 0.4.0**

The combiner dropped families on the exact equality `p >= 1.0`. Given family
(c)'s pseudo-p of `1 - value`, a channel with `coord_value = 0.0` was dropped,
while `coord_value = 0.0001` gave `p = 0.9999`, `z ~ -3.7`, crushing the
combined score. An arbitrarily small input change produced a large rank change.

**Fixed** by replacing the exact threshold with a band,
`src/scorer/channel_suspicion.py::NO_SIGNAL_PVALUE` (0.99): a p-value
indistinguishable from 'no signal' is excluded, so the frontier is continuous.
Locked by
`tests/scorer/test_combination_significance.py::test_combination_is_continuous_near_zero_signal`.

<a id="d7"></a>

### D7. `n_bootstrap = 100` was too low — **fixed in 0.4.0**

Raised to 1,000 in `src/missions/spec.py`. Cost is linear and it does not touch
the p-values (which come from `n_null`), so it cannot shift the ranking.

<a id="d11"></a>

### D11. Two evaluation scripts were mis-specified — **fixed in 0.4.0**

`scripts/eval_episode_recovery.py` computed `len(members)*k/n` and labelled it
`random_control_recall@k`. That is an **expected hit count**, not a recall, yet
it was printed beside a genuine `recall@k`. Depending on which pair a reader
compared, the same output file supported both 'at chance' and 'an order of
magnitude above chance'.

`scripts/eval_embedding_discrimination.py` built its texts as
`[f"@{u}" for u in usernames]`: it embedded **channel handles**, not message
content. It therefore did not test the deployed semantic family at all, and its
near-chance ROC-AUC measured only the inseparability of handle strings.

**Both fixed.** In `scripts/eval_episode_recovery.py::_evaluate` the recovery
control is now `k/n`, in the same unit as `recall@k`; the expected-count figure
is kept under the honest name `expected_hits_random@k`; and a run with fewer
than `MIN_MATCHED_FOR_VERDICT` (10) gold members in the corpus is reported
`NON CONCLUANT` (inconclusive) rather than interpreted. The embedding
experiment now calls
`src/scorer/embedding_signals.py::compute_channel_embeddings`, the same
function the scorer uses, so experiment and deployment share one code path,
and it refuses to report when either class has fewer than 10 usable channels.

<a id="d15b"></a>

### D15b. Isolated channels scored 1.0 in family (b) — **fixed in 0.4.0**

Found while writing the tests D17 called for. Not present in any earlier audit.

`nx.in_degree_centrality` returns 1 for the only node of a singleton graph, and
the eigenvector of a 1x1 matrix is 1. A channel with **no edges at all**
therefore produced `bridge_raw = 10*1 + 7*1 = 17`, which became the corpus
maximum, so `bridge_norm = 1.0` and `triggered = True`: **the maximum possible
cascade score for a channel with no edges**.

The main scoring path masked the symptom, because the rigorous layer overwrites
value and trigger status for family (b), and an isolated channel has no
archetype. But `scripts/build_dossier.py::main` consumes
`src/scorer/cascade_role.py::score_cascade_role` directly and was exposed.

**Fixed** by a degenerate-centrality guard in
`src/scorer/cascade_role.py::compute_bridge_scores`: a node whose in-degree and
out-degree are both zero scores 0.0, which is what
`src/scorer/cascade_role.py::classify_archetype` already implied by returning
`None`. Locked by two tests in `tests/scorer/test_cascade_role.py`.
