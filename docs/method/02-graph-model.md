# 2 — Graph model

**Status:** implemented. Every statement below is traceable to
`src/graph/edges.py` and `src/graph/loader.py`.

The unit of analysis is the **channel**. Messages carry edges; they are not
first-class nodes in the scoring model. The graph is a channel-centric multiplex
rebuilt in memory (NetworkX / igraph) from a relational store on every run —
there is no graph database.

## 2.1 Nodes

| Node | Source |
|---|---|
| `Channel` | `channels` table, keyed by `channel_id` (stable across handle rebrands) |
| `Domain` | registrable host of a cited URL, excluding platform hosts and shorteners |

## 2.2 Edge types

`derive_all_edges` (`src/graph/edges.py::derive_all_edges`) derives eight edge
types: three directed and five undirected, time-windowed coordination types.
Two further undirected types, `TEXT_SIM` and `TRANSLATION`, are derived
separately by `derive_text_sim_edges`, only when an embedder is supplied
(§2.3). The loader also recognizes a legacy `COPYPASTA` type
(`src/graph/loader.py::edge_family`) that no current deriver emits.

| Type | Direction | Derived from | Code |
|---|---|---|---|
| `FORWARD` | origin → relayer | `messages.forward_from_channel_id`, aggregated, self-loops excluded; carries count and `forward_delay_seconds` | `src/graph/edges.py::derive_forward_edges` |
| `MENTIONS` | A → B | `extract_mentions(text)`, resolved against known usernames | `src/graph/edges.py::derive_mention_edges` |
| `CITES_DOMAIN` | channel → domain | `extract_urls` + `canonical_domain` on the message text, `is_platform_host` filtered out | `src/graph/edges.py::derive_cites_domain_edges` |
| `CO_FORWARD` | undirected | both channels relayed the same origin channel | `src/graph/edges.py::derive_co_forward_edges` |
| `CO_URL` | undirected | both cited the same registrable domain | `src/graph/edges.py::derive_co_url_edges` |
| `CO_URL_EXACT` | undirected | both posted the same full URL | `src/graph/edges.py::derive_co_url_exact_edges` |
| `CO_HASHTAG` | undirected | both posted the same hashtag | `src/graph/edges.py::derive_co_hashtag_edges` |
| `MEDIA_REUSE` | undirected | both posted the same media (`media_hash`) | `src/graph/edges.py::derive_media_reuse_edges` |
| `TEXT_SIM` | undirected | cosine over sentence embeddings above a threshold | `src/graph/edges.py::derive_text_sim_edges` |
| `TRANSLATION` | undirected | as `TEXT_SIM`, across two different message languages, above a higher threshold | `src/graph/edges.py::derive_text_sim_edges` |

### The windowing rule

The five coordination types of `derive_all_edges` share one pairing routine
(`src/graph/edges.py::_coordination_edges`): group messages by the shared artefact, keep
each channel's **earliest** touch of it, and emit a pair when `|Δt| ≤ window`.
The edge's `window_delta_seconds` is the minimum Δt over all shared artefacts.
`src/graph/edges.py::DEFAULT_WINDOW_SECONDS` is `72 * 3600`. `TEXT_SIM` and `TRANSLATION`
apply the same window in their own pairing loop.

This is a coincidence filter, not a coordination test. It establishes that two
channels touched the same object within three days. Nothing in the routine
estimates how surprising that is.

## 2.3 What is materialized in practice

Two points differ from what earlier versions of this page said:

- **`MEDIA_REUSE`** is materialized. `media_hash` holds Telegram's
  `file_unique_id`, recorded at collection without downloading the media
  (`src/ingestor/handlers.py`), and the published snapshot carries
  `MEDIA_REUSE` edges (counts in
  [`dataset/DATASHEET.md`](../../dataset/DATASHEET.md)). The comments in
  `graph/edges.py` that say the field is NULL corpus-wide are out of date.
- **`TEXT_SIM` and `TRANSLATION`** are only derived when an embedder is
  explicitly injected (`src/graph/edges.py::derive_and_upsert_edges` with `embedder=…`,
  which `scripts/build_edges.py --embed` does); `derive_all_edges` does not
  include them, and the pipeline runs `build_edges` without `--embed`, so it
  never derives them. The scan is O(N²) and capped at
  `src/graph/edges.py::MAX_TEXT_SIM_MESSAGES`. `TRANSLATION` also needs a language on
  both messages, and the collector never records one
  (`src/ingestor/handlers.py::_parse_message` writes `language` as NULL), so
  `TRANSLATION` cannot fire on any corpus this code collects, the public one
  included ([D29](../limitations.md#d29)).

Their thresholds—`src/graph/edges.py::TEXT_SIM_THRESHOLD` (0.715) and
`src/graph/edges.py::TRANSLATION_THRESHOLD` (0.85)—were taken from VIGINUM's D3lta (its
rewording and translation cut-offs). **They are model-specific values applied
to a different model** (multilingual MiniLM-L12-v2) and have never been
calibrated for it. The source comment says so. Treat any output of these two
types as uncalibrated.

## 2.4 Known defect — `CO_HASHTAG`

`CO_HASHTAG` makes any two channels whose first use of `#Ukraine` fell within
72 hours of each other coordination partners. On a topical corpus it links many
channels that share nothing but a topical hashtag.

This matters beyond noise, because score family (c) triggers on **two distinct
edge types alone**, independently of timing tightness (see
`03-suspicion-score.md` §3.3). `CO_HASHTAG` plus any one other coordination
type is therefore enough to trigger (c), which is one of the two families the
multi-source gate needs. Recorded as [D5](../limitations.md#d5).

## 2.5 Priors attached at load time

`src/graph/loader.py` decorates nodes as the graph is built.
`credibility_prior` (`src/graph/loader.py::credibility_prior`) is derived from documented
adversary linkage: a channel is `suspect` when its `CITES_DOMAIN` edges reach
the adversary catalogue, or when it is itself catalogued. The second condition
never applies in production, because the list of catalogued channels is never
passed outside the tests. The prior is evidence-based on the scoring path only:
`scripts/analyze_communities.py`, `scripts/analyze_communities_embed.py` and the
`graph.json` written by `scripts/export_static.py` build the graph without the
adversary catalogue, so every node there is `other`
([D30](../limitations.md#d30)). The prior was previously derived from
French-keyword density, which was a defect, now fixed
([D1](../limitations.md#d1)).

`engagement` (`src/graph/loader.py::fetch_channel_rows`) is `SUM(views) + SUM(forwards)`.
Reactions are not stored and are not part of it, whatever earlier documentation
and the function's docstring claim.
