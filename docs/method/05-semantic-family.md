# 5 — Semantic coherence, family (f)

**Status:** implemented, **opt-in and off by default**
(`compute_embeddings=False`, `channel_suspicion.py:1033`). Enabled with
`build_scores.py --embeddings`. Code: `src/scorer/embedding_signals.py`,
`src/embed/`.

## 5.1 What it computes

A channel is represented by the mean of the embeddings of its **15 longest
messages**, L2-renormalized (`:39-80`). The encoder is
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim, FR/RU/EN),
run locally, deterministic, with an offline cache keyed by
`sha256(model || text)` — so re-runs cost nothing and require no paid API.

```
baseline_distance = 1 - cos(channel, organic_FR_centroid)
adversary_proximity = max_i cos(channel, adversary_i)
value = (0.4*baseline_distance + 0.6*adversary_proximity) / (0.4 + 0.6)
```

The contributing distances and the identifier of the closest adversary channel
are preserved in the evidence block, so a ranking driven by (f) can be read as
"this channel reads like @X and sits far from the French-press baseline".

## 5.2 Three properties that bound its interpretation

**The two terms are not independent.** `baseline_distance` and
`adversary_proximity` are cosines in the same 384-dimensional space, computed
against two anchor sets that sit in different regions of it. They are strongly
anti-correlated, so the weighted sum is close to a monotone function of "cosine
to the adversary centroid" plus a constant. Presenting it as a combination of two
distinct signals overstates what it measures.

**The anchors are a handful of hardcoded handles.** Five baseline channels and
three adversary channels for the `russosphere` mission
(`src/missions/russosphere/__init__.py:109-114`), carrying an explicit debt
marker in the source. A centroid over five channels is not a model of "the French
press".

**Silent failure inflates the score.** When an anchor handle does not resolve,
the fallback vector is `np.zeros(384)` (`:98`). Cosine against a zero vector is
0, so `baseline_distance` becomes `1.0` for **every channel**, adding a uniform
`+0.4` to the family value with no error and no warning. Any run using family (f)
must verify that the anchors resolved before the numbers are read.

## 5.3 Independence from the graph — a claim to state carefully

Family (f) is a **content** signal computed from message text, while (b), (c) and
(d) are computed from the graph. In that narrow structural sense it is
independent, and that is why it can help a channel cross the multi-source gate.

It does **not** follow that a channel cleared by "structure plus semantics"
carries independent corroboration of coordination. Family (f) measures
*resemblance to a small set of adversary channels*. A channel can resemble them
because it is part of the same operation, or because it covers the same topics in
the same register. Nothing in (f) distinguishes those. Treat it as a topical and
stylistic similarity signal, which is what it is.

## 5.4 Degradation

If embeddings are unavailable, or the mission's baseline and adversary anchors do
not resolve, family (f) is simply absent and the structural score is returned
unchanged. It never filters a channel out; it can only raise a score.

## 5.5 Communities from embeddings

`src/embed/community.py:45-83` adds in-memory `EMB_SIM` edges to the channel
graph before running Leiden: for each channel, the top `k = 5` neighbours above
cosine `0.5`, weighted `3.0 * cosine`.

All three constants are arbitrary and **no sensitivity analysis has been run on
any of them**. Because these edges are added before community detection, they
change the partition; the outputs therefore depend on three unaudited numbers.
Closing this is protocol `docs/experiments/` — see the sensitivity experiment.
