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

## 2.2 Edge families

Nine families are derived by `derive_all_edges` (`src/graph/edges.py:558`).
Three are directed, six are undirected and time-windowed.

| Family | Direction | Derived from | Code |
|---|---|---|---|
| `FORWARD` | origin → relayer | `messages.forward_from_channel_id`, aggregated, self-loops excluded; carries count and `forward_delay_seconds` | `:146` |
| `MENTIONS` | A → B | `extract_mentions(text)`, resolved against known usernames | `:180` |
| `CITES_DOMAIN` | channel → domain | `extract_urls` + `canonical_domain`, `is_platform_host` filtered out | `:206` |
| `CO_FORWARD` | undirected | both channels relayed the same origin channel | `:308` |
| `CO_URL` | undirected | both cited the same registrable domain | `:331` |
| `CO_URL_EXACT` | undirected | both posted the same full URL | `:362` |
| `CO_HASHTAG` | undirected | both posted the same hashtag | `:396` |
| `MEDIA_REUSE` | undirected | both posted the same `media_hash` | `:424` |
| `TEXT_SIM` / `TRANSLATION` | undirected | cosine over sentence embeddings above a threshold | `:469` |

### The windowing rule

All six undirected families share one pairing routine (`_coordination_edges`,
`:231`): group messages by the shared artefact, keep each channel's **earliest**
touch of it, and emit a pair when `|Δt| ≤ window`. The edge's
`window_delta_seconds` is the minimum Δt over all shared artefacts.
`DEFAULT_WINDOW_SECONDS = 72 * 3600` (`:86`).

This is a coincidence filter, not a coordination test. It establishes that two
channels touched the same object within three days. Nothing in the routine
estimates how surprising that is.

## 2.3 What is materialized in practice

Two families are specified and wired but produce nothing in the corpora observed
so far:

- **`MEDIA_REUSE`** returns `[]` because `media_hash` is NULL corpus-wide
  (`:428-430`) — computing it requires downloading the media file, which the
  ingestion path does not do.
- **`TEXT_SIM` / `TRANSLATION`** are only derived when an embedder is explicitly
  injected (`derive_and_upsert_edges(embedder=…)`, `:624`). `derive_all_edges`
  does not include them. The scan is O(N²) and capped at
  `MAX_TEXT_SIM_MESSAGES = 3000`.

Their thresholds — `TEXT_SIM_THRESHOLD = 0.715`, `TRANSLATION_THRESHOLD = 0.85`
(`:454-455`) — were taken from VIGINUM's D3lta and from BGE-M3. **They are
model-specific values applied to a different model** (multilingual MiniLM-L12-v2)
and have never been calibrated for it. The source comment says so. Treat any
output of these two families as uncalibrated.

## 2.4 Known defect — `CO_HASHTAG`

`CO_HASHTAG` makes any two channels that used `#Ukraine` within 72 hours
coordination partners. On a topical corpus this is close to a complete graph over
active channels.

This matters beyond noise, because score family (c) reaches a triggering value
from **two distinct edge types alone**, independently of timing tightness
(see `03-suspicion-score.md` §3.3). `CO_HASHTAG` can therefore push a channel
through the multi-source gate on its own. Recorded in `docs/limitations.md`.

## 2.5 Priors attached at load time

`src/graph/loader.py` decorates nodes as the graph is built. `credibility_prior`
is derived from documented adversary linkage: a channel is `suspect` when its
`CITES_DOMAIN` edges reach the adversary catalogue, or when it is itself
catalogued. It was previously derived from French-keyword density, which was a
defect — see `docs/limitations.md` D1.

`engagement` (`loader.py:105`) is `SUM(views) + SUM(forwards)`. Reactions are not
stored and are not part of it, despite what earlier documentation claimed.
