# 5 — Semantic coherence, family (f)

**Status:** implemented, **opt-in and off by default**
(`compute_embeddings=False` in `channel_suspicion.py::_build_channel_queue_live`),
enabled with `build_scores.py --embeddings`, which `scripts/pipeline.py` does
not pass. Code: `src/scorer/embedding_signals.py`, `src/embed/`.

> [!WARNING]
> Family (f) is **computed, not scored**. Even when it runs, its result is
> discarded: it is never read by the combiner, the gate, the tier or the
> export, and it is not stored anywhere ([D19](../limitations.md#d19)).
> Everything below describes what the family computes, not something that
> currently moves a ranking.

## 5.1 What it computes

A scored channel is represented by the mean of the embeddings of its **15
longest messages**, L2-renormalized
(`embedding_signals.py::compute_channel_embeddings`); each anchor channel uses
its 20 longest. The default encoder is
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions,
French, Russian, and English), run locally and deterministically, with an
offline cache keyed by `sha256(model || text)`—so re-runs cost nothing and
require no paid API. `IDEFIX_EMBED_MODEL` overrides the model
(`src/embed/encoder.py::Embedder`), but the anchor fallback below stays
hard-coded to 384 dimensions.

```text
baseline_distance = 1 - cos(channel, organic_FR_centroid)
adversary_proximity = max_i cos(channel, adversary_i)
value = (0.4*baseline_distance + 0.6*adversary_proximity) / (0.4 + 0.6)
```

The family's evidence records the contributing distances and the identifier of
the closest adversary channel, so that, were (f) scored, a ranking driven by it
could be read as 'this channel reads like @X and sits far from the
French-press baseline'. Today that evidence is discarded with the result.

## 5.2 Three properties that bound its interpretation

**The two terms are not independent.** `baseline_distance` and
`adversary_proximity` are cosines in the same 384-dimensional space, computed
against two anchor sets that sit in different regions of it. They are strongly
anti-correlated, so the weighted sum is close to a monotone function of 'cosine
to the adversary centroid' plus a constant. Presenting it as a combination of two
distinct signals overstates what it measures.

**The anchors are a handful of hard-coded handles.** Five baseline channels and
three adversary channels for the `russosphere` mission
(`embedding_baseline_channels` and `embedding_adversary_channels` in
`src/missions/russosphere/__init__.py`), carrying an explicit debt marker in the
source. A centroid over five channels is not a model of 'the French
press'.

**Silent failure inflates the score.** When an anchor handle does not resolve,
the fallback vector is `np.zeros(384)`
(`embedding_signals.py::build_baseline_embedding`). Cosine against a zero vector is
0, so `baseline_distance` becomes `1.0` for **every channel**, adding a uniform
`+0.4` to the family value with no error and no warning. Any run using family (f)
must verify that the anchors resolved before the numbers are read
([D10](../limitations.md#d10)).

## 5.3 Independence from the graph — a claim to state carefully

Family (f) is a **content** signal computed from message text, while (b), (c) and
(d) are computed from the graph. In that narrow structural sense it is
independent, and that is why it was meant to help a channel cross the
multi-source gate. Today it cannot, because its result never reaches the gate
([D19](../limitations.md#d19)).

It does **not** follow that a channel cleared by 'structure plus semantics'
carries independent corroboration of coordination. Family (f) measures
*resemblance to a small set of adversary channels*. A channel can resemble them
because it is part of the same operation, or because it covers the same topics in
the same register. Nothing in (f) distinguishes those. Treat it as a topical and
stylistic similarity signal, which is what it is.

## 5.4 Degradation

If embeddings cannot be computed at all (the encoder fails to load, or the
embedding step raises), family (f) is absent and the structural score is
returned unchanged. Anchors that do not resolve are a different case: they do
not make (f) absent. The family is still computed, against a zero vector or an
empty adversary set (§5.2, [D10](../limitations.md#d10)). Either way (f) never
filters a channel out, and today it does not change any score
([D19](../limitations.md#d19)).

## 5.5 Communities from embeddings

`src/embed/community.py::add_embedding_edges` adds in-memory `EMB_SIM` edges to the channel
graph before running Leiden: for each channel, the top `k = 5` neighbours above
cosine `0.5`, weighted `3.0 * cosine`.

All three constants are arbitrary and **no sensitivity analysis has been run on
any of them**. Because these edges are added before community detection, they
change the partition; the outputs therefore depend on three unaudited numbers.
The protocol that would close this is
[`exp-parameter-sensitivity.md`](../experiments/exp-parameter-sensitivity.md).
