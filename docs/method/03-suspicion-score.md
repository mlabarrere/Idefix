# 3 — The per-channel suspicion score

**Status:** implemented. Traceable to `src/scorer/channel_suspicion.py`,
`rigor.py`, `significance.py` and the per-family modules.

The score is a **rank ordering for triage**, not a probability of manipulation.
It answers 'which channels should an analyst read first', and every ranking it
produces must be justifiable from the channel's own evidence block.

## 3.1 Score families

| Family | Name in code | Status | What it actually computes |
|---|---|---|---|
| (a) | `claim_proximity` | **Not wired.** Always N/A | Injection seam only; nothing supplies a value |
| (b) | `cascade_role` | Active, with null model | §3.2 |
| (c) | `coordination` | Active, **no null model** | §3.3 |
| (d) | `recidivism` | Active, with null model | §3.4 |
| (e) | `genai_origin` | **Not wired.** Always N/A | `e_res = None`, hard-coded |
| (f) | `embedding_signals` | **Computed, not scored** ([D19](../limitations.md#d19)) | `05-semantic-family.md` |

Families (a) and (e) have never produced a value. They are named here because
the code reserves the letters, not because they contribute anything. Family (f)
is computed when embeddings are available, but its result is never read by the
combiner, the gate or the export, so it contributes nothing to the score
either.

## 3.2 Family (b) — cascade role

`src/scorer/cascade_role.py::compute_bridge_scores`, after Shah, Ranka, Ng & Mehta (2024),
arXiv:2411.05922:

```text
bridge_raw  = 10*in_degree_centrality + 7*eigenvector_centrality + 7*clustering
bridge_norm = bridge_raw / max(bridge_raw over the corpus)
```

**Two properties a reader must know before using this number.**

The three terms are on **incompatible scales, and they scale differently with
corpus size**. `in_degree_centrality` is normalized by `n-1` and therefore
decays as `1/n`; `eigenvector_centrality_numpy` returns an L2-normalized vector
and does not decay the same way; `clustering` is scale-free in [0,1].

Measured, the in-degree and eigenvector contributions **cross over** at a few
hundred nodes: below that the score is driven by in-degree, above it by
eigenvector centrality. The weights `10 / 7 / 7` therefore do not express the
relative importance of the three signals at any particular scale, and the
composite changes character as the corpus grows. See
[D9](../limitations.md#d9) for the measurements.

The normalization is **max-scaling across the corpus**. A channel's `bridge_norm`
therefore depends on every other channel in the run: adding one large hub
rescales everyone. Values are comparable *within* one export and **not across
exports, corpora or time**. Do not treat `bridge_norm` as a measurement.

In production, `bridge_norm` does not reach the combined score. The rigorous
path (`src/scorer/rigor.py::compute_family_significance`) tests the raw
statistic `bridge_raw` against the null model of §3.6 and replaces the family's
value with its significance, `1 - p`; the family triggers when `p < alpha`, the
result is not degenerate, and the channel has an archetype
(`src/scorer/channel_suspicion.py::_family_triggered`). The max-normalized `bridge_norm`
no longer reaches the score or the bundle, but it still decides the archetype
(`src/scorer/cascade_role.py::classify_archetype`) and feeds the dossier builder.

Archetype assignment (`src/scorer/cascade_role.py::classify_archetype`) is a hard-coded priority cascade over
`reactivator` / `cross-channel-bridge` / `forward-hub` / `seeding-source`. Note
that the terminal `else` branch returns `forward-hub`, the same label as an
earlier branch with a different structural condition — two distinct situations
share one name.

## 3.3 Family (c) — coordination

`src/scorer/coordination.py::score_coordination_edges`, over the materialized
coordination edges of `02-graph-model.md`:

```text
tightness = 1 - dt / window            (linear, window = 72 h)
diversity = min(n_edge_types, 2) / 2
value     = 0.5*tightness_max + 0.5*diversity
triggered = value >= 0.3 and n_edge_types >= 2
```

**This family is close to binary.** Two distinct edge types give
`diversity = 1.0`, hence `value >= 0.5`, hence triggered — *regardless of how
loose the timing is*. A single coordination edge type already gives
`diversity = 0.5`, hence `value >= 0.25`; `value = 1.0` needs two edge types
*and* an artefact shared at the same instant (`Δt = 0`). Combined with the
`CO_HASHTAG` defect (`02-graph-model.md` §2.4), a large share of any topical
corpus clears the trigger on diversity alone.

**This family has no null model**, and this is the most serious statistical
weakness in the system ([D2](../limitations.md#d2)).
`src/scorer/rigor.py::compute_family_significance` covers (b) and (d) only. Its p-value
therefore falls back to `p = 1 - value` (`src/scorer/channel_suspicion.py::_family_pvalue`), which is a
monotone rescaling of the value, not a tail probability under any hypothesis.
Nothing in family (c) estimates how surprising an observation is. The same
fallback applies to the six `telegram_*` families and to injected family (a).

A second implementation, `src/scorer/coordination.py::score_coordination` (Jaccard of
shared forward origins), does not feed the score. It is used by the dossier
builder (`scripts/build_dossier.py`), which is a pipeline stage.

## 3.4 Family (d) — recidivism

`src/scorer/recidivism.py::score_recidivism`:

```text
value = 0.6*(out_strength / max_out_strength) + 0.4*(out_degree / max_out_degree)
```

**There is no cross-episode component.** Earlier documentation called this family
'cross-episode recidivism'; the module's own docstring corrects it. With no
populated episode table, it measures out-degree and out-strength on a single
aggregate forward graph, max-normalized — and so inherits the same
non-comparability as §3.2. Read it as *forward influence*, which is what it is.
In production this composite does not reach the score either: the rigorous
path tests raw out-strength alone against the null model
(`src/scorer/rigor.py::compute_family_significance`) and replaces the value with its
significance (`1 - p`, triggered when `p < alpha`), so the out-degree term and
the `0.6 / 0.4` split play no part in the ranking.

## 3.5 Combination — Stouffer under Benjamini–Hochberg

This is the **canonical combiner** and the one implemented in
`src/scorer/channel_suspicion.py::_combine_suspicion`. It is not a weighted average of
family values.

1. Each family yields a one-sided p-value. Families (b) and (d) get a genuine one
   from the null model of §3.6; every other family gets the `p = 1 - value`
   fallback of §3.3.
2. Families whose p-value reaches `NO_SIGNAL_PVALUE = 0.99` are **excluded**
   from the combination rather than counted as evidence against, so that a
   silent family does not drive `z` to minus infinity. The threshold is a band
   rather than an exact equality so that the frontier is continuous — see
   [D4](../limitations.md#d4).
3. The survivors are combined by weighted Stouffer,
   `Z = sum(w_i*z_i)/sqrt(sum(w_i^2))` with `z_i = Phi^-1(1-p_i)`, using
   `src/scorer/channel_suspicion.py::BASE_FAMILY_WEIGHTS`
   (`{a: 0.15, b: 0.30, c: 0.25, d: 0.30, e: 0.15}`). There is no weight for
   (f), which is never passed to the combiner ([D19](../limitations.md#d19)).
4. `base = 1 - p_combined`, then `value = clamp01(base * severity_factor)`.
5. Benjamini–Hochberg control of the false discovery rate (FDR) is applied
   across channels (`src/scorer/significance.py::benjamini_hochberg`, via `statsmodels`),
   yielding `q_value` and `flagged`. **`flagged` is the Benjamini–Hochberg
   rejection set** (FDR at most `alpha`). It is independent of the multi-source
   gate of §3.9: it changes neither the score, nor the gate, nor the tier.

**One defect in this combination remains open.**

*Independence is violated.* Stouffer assumes independent p-values. Families (b)
and (d) are computed on the same forward graph and tested against the **same
null ensemble** (`src/scorer/rigor.py::compute_family_significance`); only their bootstrap
intervals are drawn separately. They are strongly correlated, so the combined
p-value is anticonservative: it overstates significance
([D3](../limitations.md#d3)).

The family weights themselves have **no derivation**. The source comment asserts
that 'each share is justifiable'; no justification is recorded anywhere. Treat
them as five free parameters.

## 3.6 The null model

`src/scorer/significance.py::randomize_endpoints` holds the node set and edge count
fixed, permutes the weight multiset, and reassigns both endpoints uniformly at
random.

Chosen because Telegram's propagation primitive is a depth-1 forward star, where
classical degree-preserving rewiring is degenerate. The trade-off is explicit:
this null **does not preserve degree**, so a channel's p-value is a comparison
against a random channel in a network of the same size, density and weight
distribution — not against a channel of the same degree.

Implementation notes that bound the result: the routine gives up after 8 attempts
to avoid a self-loop and silently skips the edge, so null graphs carry
slightly fewer edges than observed. The p-value is the add-one, one-sided
upper-tail estimate `p = (1 + #{null >= obs}) / (n + 1)`
(`src/scorer/significance.py::null_significance`)—correct, and never zero.
Defaults: `n_null = 200`, `n_bootstrap = 1000`, `rng_seed = 1312`,
`alpha = 0.05` (`src/missions/spec.py`).

## 3.7 Confidence bands

Bands do propagate: `rigor.py` replaces value, bands and trigger status for
families (b) and (d) with the bootstrap confidence interval mapped into
significance space, and `src/scorer/channel_suspicion.py::_combine_suspicion` carries the
bounds through the same Stouffer combination.

**But the inputs are only real for (b) and (d).** Family (c) has no null model,
so it keeps a fixed band—`value +/- 0.10` when two or more edge types reinforce
it, `+/- 0.20` otherwise (`src/scorer/coordination.py::score_coordination_edges`)—and
those bounds do enter the Stouffer bound calculation. Every other family, and
every family before rigorous enrichment, ships a hard-coded band:
`value +/- 0.15` in `src/scorer/cascade_role.py::score_cascade_role`,
`src/scorer/recidivism.py::score_recidivism` and `src/scorer/telegram_footprint.py::_result`, and
`value +/- 0.10` in `src/scorer/embedding_signals.py::score_embedding_coherence`. The
docstring of
`src/scorer/significance.py` calls these 'bandes +/-0.15 factices'
([D6](../limitations.md#d6)).
A published interval on a non-(b)/(d) family is a formatting convention, not an
uncertainty estimate.

## 3.8 Severity modulation

`src/scorer/channel_suspicion.py::_severity_modulation`. Bounded, upward-only, multiplicative:

```text
factor = 1 + 0.20*suspect_reforward_fraction
           + 0.15*min(1, adversary_citations / 5)
           + 0.20*clamp01(thematic_targeting)          # max factor 1.55
value  = clamp01(base * factor)
```

Because the modulation is multiplicative, a channel with zero base score stays at
zero whatever its thematic relevance: relevance modulates **severity**, never
**inclusion**. That property holds.

The factor is **not gated**. It multiplies every channel's base score, whether
or not the channel crosses the multi-source gate of §3.9
([D21](../limitations.md#d21)).

`suspect_reforward_fraction` is computed against `credibility_prior`. Until
September 2026 that prior was set from French-keyword density, which made the
largest severity modulator a language bias and contradicted this document's own
claim about `fr_score`. It is now evidence-based — a channel is `suspect` when
it cites documented adversary infrastructure or is itself catalogued
(`04-thematic-relevance.md` §4.1). `fr_score` no longer enters the score,
though it still steers episodes, the porosity view and the snowball crawl
(§4.1). See [D1](../limitations.md#d1); the size of the ranking change has not
yet been measured on the public corpus.

The `0.20` bound on thematic targeting was chosen by analogy with the reforward
bound, per the source comment. It is not calibrated.

## 3.9 The multi-source gate

`src/scorer/channel_suspicion.py::_gate`. A channel crosses the gate when **at least 2
distinct families are triggered** (`min_families_for_gate`, per-mission). The
triggered set is materialized per channel as `gate_families` (Alembic `0008`), so
tier assignment is auditable from the stored record: gate met implies T2,
otherwise T1.

The mechanism is sound. Its **inputs** are what limit it: with (a) and (e) never
firing and (f) never passed to the gate ([D19](../limitations.md#d19)), the
gate is effectively '2 of {b, c, d}' (plus the `telegram_*` families for
`gan`), and family (c) triggers on two edge types alone. The gate does not
currently establish independent corroboration in the sense the tier vocabulary
implies, and it does not bound severity (§3.8).
