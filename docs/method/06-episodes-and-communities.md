# 6 — Episode discovery and community detection

**Status:** implemented. `scripts/mine_episodes.py`,
`scripts/analyze_communities.py`, `scripts/analyze_communities_embed.py`,
`src/embed/community.py`.

## 6.1 Episode discovery

An **episode** is a relation between one Russian-side channel and one
French-side channel (`scripts/mine_episodes.py::group_by_pair`): every raw pivot is
keyed on the first RU seeder and the first FR receiver it lists, and the
pivots that share that pair form one episode. An RU side is required, and no
time window is applied. Discovery pivots
on three shared artefacts: reused media (`file_unique_id`,
`scripts/mine_episodes.py::media_pivots`), exact-match URLs
(`scripts/mine_episodes.py::url_pivots`), and forward republication
(`scripts/mine_episodes.py::forward_pivots`). The URL pivot reads `messages.urls`, which
the collector never fills (`src/ingestor/queries.py::insert_message` writes it
as NULL), so it never fires on any corpus this code collects
([D29](../limitations.md#d29)).

Each episode is labelled by the top-5 TF-IDF terms of its vocabulary, against a
hand-written multilingual stop list of 56 distinct words
(`scripts/mine_episodes.py::_STOP`, `scripts/mine_episodes.py::label_topics`).

**Tier assignment is a count of pivot types**, not a test: `tier = "T2"` when
corroboration `>= 2`, where corroboration is the number of distinct pivot types
observed (`scripts/mine_episodes.py::finalize`). Two channels sharing a URL *and* a forward is enough. This is
the same structural weakness as family (c): distinct signal *types* are treated
as independent corroboration without anything establishing that they are.

The `side` attribution (`FR` if `fr_score >= 0.15` else `RU`,
`scripts/mine_episodes.py::FR_SIDE_MIN` and `scripts/mine_episodes.py::load_sides`) is the same
keyword-density measure discussed in `04-thematic-relevance.md` §4.1. It no
longer reaches the score, but it decides which side of an episode a channel
sits on, and so which channels can appear in episodes at all.

The semantic enrichment block (`scripts/mine_episodes.py::calculate_embeddings`)
computes intra-cluster cohesion and distance to a baseline—but the baseline it
uses is 'all FR texts across all episodes', that is, **the corpus explains
itself**. The source labels this a simplification. It is not comparable to the external organic baseline of
`05-semantic-family.md` and should not be reported as one.

## 6.2 Community detection

Leiden via igraph (`scripts/analyze_communities.py::detect_communities`), `objective_function =
"modularity"`, `n_iterations = -1`, **`resolution = 1.6`**.

The resolution was not selected by any criterion. The source docstring is candid:
at 1.0 the algorithm produced clusters of 500+ channels that could not be
labelled honestly. It is a legibility choice, and it changes the partition.

Two tracks are run and compared:

- **analytics** — the whole multiplex graph of `02-graph-model.md`, folded into
  one undirected weighted graph (`src/graph/loader.py::to_igraph`): forwards,
  mentions, every coordination type and the cited-domain nodes
- **embeddings** — the same graph plus the `EMB_SIM` edges of
  `05-semantic-family.md` §5.5

### The trade-off, stated correctly

The `EMB_SIM` edges connect channels that *write* alike. Those edges cut across
the communities defined by *who forwards whom*, so moving from the analytics
track to the embeddings track is expected to raise semantic cohesion.

The two modularity figures are **not comparable**. Each track's modularity is
computed on the graph that track partitioned
(`scripts/analyze_communities_embed.py` calls `detect_communities` on the link
graph plus the `EMB_SIM` edges): the analytics figure is modularity of the link
graph, the embeddings figure is modularity of a different, denser graph. A
difference between them is neither a regression nor an improvement, and
reporting it as either would be a framing error. Maximizing semantic cohesion
and maximizing structural modularity are different objectives in any case.

This is a statement about what the two metrics measure. It is not a result.
Whether the semantic track adds non-redundant signal on any given corpus is an
empirical question, and the protocol for answering it is in
`docs/experiments/`. Numbers previously quoted here came from a decommissioned
database; they are quarantined and may not be cited—see
`archive/2026-06-russosphere/README.md`.

## 6.3 Topic labelling is a regex vote

Community topic labels come from **27 hand-written tuples** of
`(theme, handle-regex, domain-regex)` (`scripts/analyze_communities.py::TAXONOMY`), scored
by `coverage * idf` where coverage is the fraction of channels in the community
whose handle or title matches, plus `0.10` if a characteristic domain is present,
and `idf = log((N+1)/(1+df))`. Thresholds: `MIN_COVER = 0.12`,
`MIN_SCORE = 0.18`, `COMPOSITE = 0.80` (`scripts/analyze_communities.py::MIN_COVER`,
`MIN_SCORE`, `COMPOSITE`).

This is a keyword vote over channel names, not a classifier, and its coverage is
bounded by whatever the 27 patterns happen to capture. Labels are a navigation
aid for an analyst; they are not evidence.

## 6.4 Bridges

`nx.betweenness_centrality(h, weight=None, normalized=True)` on the channel
projection (`scripts/analyze_communities.py::build_snapshot`). Note `weight=None`: the
call **discards the edge weights the projection just computed** in
`scripts/analyze_communities.py::channel_projection`. Bridge rankings are therefore
unweighted betweenness, whatever the underlying forward volumes.

## 6.5 Layout

`scripts/precompute_galaxy_layout.py` is pure visualization — per-component
`spring_layout(seed=42)` packed by golden-angle phyllotaxis. It carries no
analytical content and none of its constants affect any score.
