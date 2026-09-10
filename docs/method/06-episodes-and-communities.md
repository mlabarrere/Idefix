# 6 — Episode discovery and community detection

**Status:** implemented. `scripts/mine_episodes.py`,
`scripts/analyze_communities.py`, `scripts/analyze_communities_embed.py`,
`src/embed/community.py`.

## 6.1 Episode discovery

An **episode** is a set of channels propagating the same material over a bounded
window. Discovery pivots on three shared artefacts: reused media
(`file_unique_id`), exact-match URLs, and forward republication.

Each candidate cluster is labelled by the top-5 TF-IDF terms of its vocabulary,
against a hand-written 40-word multilingual stop list
(`mine_episodes.py:75-81, 271-286`).

**Tier assignment is a count of pivot types**, not a test: `tier = "T2"` when
corroboration `>= 2`, where corroboration is the number of distinct pivot types
observed (`:348`). Two channels sharing a URL *and* a forward is enough. This is
the same structural weakness as family (c): distinct signal *types* are treated
as independent corroboration without anything establishing that they are.

The `side` attribution (`FR` if `fr_score >= 0.15` else `RU`, `:63,112`) is the
same keyword-density threshold discussed in `04-thematic-relevance.md` §4.1 and
carries the same defect.

The semantic enrichment block (`:410-419`) computes intra-cluster cohesion and
distance to a baseline — but the baseline it uses is "all FR texts across all
episodes", i.e. **the corpus explains itself**. The source labels this a
simplification (`:387`). It is not comparable to the external organic baseline of
`05-semantic-family.md` and should not be reported as one.

## 6.2 Community detection

Leiden via igraph (`analyze_communities.py:293-313`), `objective_function =
"modularity"`, `n_iterations = -1`, **`resolution = 1.6`**.

The resolution was not selected by any criterion. The source docstring is candid:
at 1.0 the algorithm produced clusters of 500+ channels that could not be
labelled honestly. It is a legibility choice, and it changes the partition.

Two tracks are run and compared:

- **analytics** — the link graph (forwards, mentions, co-citations)
- **embeddings** — the same graph plus the `EMB_SIM` edges of
  `05-semantic-family.md` §5.5

### The trade-off, stated correctly

The `EMB_SIM` edges connect channels that *write* alike. Those edges cut across
the communities defined by *who forwards whom*. Consequently, moving from the
analytics track to the embeddings track raises semantic cohesion and lowers
Newman modularity — because modularity is computed on the link graph, which the
semantic edges deliberately cross.

Falling modularity is therefore **not** a regression: maximizing semantic
cohesion and maximizing structural modularity are different objectives, and
gaining on one costs the other. Reporting the modularity drop as a degradation
would be a framing error.

This is a statement about what the two metrics measure. It is not a result.
Whether the semantic track adds non-redundant signal on any given corpus is an
empirical question, and the protocol for answering it is in
`docs/experiments/`. Numbers previously quoted here came from a corpus that no
longer exists; they are quarantined and may not be cited — see
`archive/2026-06-russosphere/README.md`.

## 6.3 Topic labelling is a regex vote

Community topic labels come from **28 hand-written tuples** of
`(theme, handle-regex, domain-regex)` (`analyze_communities.py:105-202`), scored
by `coverage * idf` where coverage is the fraction of channels in the community
whose handle or title matches, plus `0.10` if a characteristic domain is present,
and `idf = log((N+1)/(1+df))`. Thresholds: `MIN_COVER = 0.12`,
`MIN_SCORE = 0.18`, `COMPOSITE = 0.80` (`:207-209`).

This is a keyword vote over channel names, not a classifier, and its coverage is
bounded by whatever the 28 patterns happen to capture. Labels are a navigation
aid for an analyst; they are not evidence.

## 6.4 Bridges

`nx.betweenness_centrality(h, weight=None, normalized=True)` on the channel
projection (`:353`). Note `weight=None`: the call **discards the edge weights the
projection just computed** at `:327-331`. Bridge rankings are therefore
unweighted betweenness, whatever the underlying forward volumes.

## 6.5 Layout

`scripts/precompute_galaxy_layout.py` is pure visualization — per-component
`spring_layout(seed=42)` packed by golden-angle phyllotaxis. It carries no
analytical content and none of its constants affect any score.
