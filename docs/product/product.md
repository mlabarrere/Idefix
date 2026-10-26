# Idéfix — product view

The functional picture: what the system delivers, to whom, and what it refuses
to do. For how it works, see [`../method/`](../method/). For what bounds every
claim here, see [`../limitations.md`](../limitations.md).

## What Idéfix is

A **propagation and coordination analysis system for Telegram**. It maps how
material spreads through networks of public channels, identifies channels that
play a structural role in that spread, and produces ranked, explainable case
files for human analysts.

**It is not a fake-news detector.** It never judges whether a message is true.
It describes *observable structures* — who forwards what, how fast, alongside
whom — and never issues a verdict.

**It is not a validated manipulation detector either.** Whether a high rank
means coordinated manipulation, rather than prominence inside an adversarial
media ecosystem, is an open question this project has not answered. The
experiment that would settle it needs a corpus of *organic* coordination as a
negative class, and none exists.

## The problem

Coordinated influence operations on Telegram leave structural traces: a small
number of channels are consistently early, relays repropagate material into
several communities at once, and the same infrastructure recurs across episodes.

Those traces are observable in the public forward graph without analysing
content or knowing anyone's intent. Reading thousands of channels by hand is not
possible. Idéfix does the reading and hands an analyst a queue.

## What it produces

### A prioritized examination queue

Each channel receives a **suspicion score** built from families of signals,
combined as per-family p-values by Stouffer's method, with Benjamini–Hochberg
control of the false discovery rate (FDR) across channels.

| Family | Signal | Caveat |
|---|---|---|
| **(b) Cascade role** | Structural position in the forward graph — hub, cross-community bridge, seeding source | Corpus-relative, not comparable across runs |
| **(c) Coordination** | Time-windowed co-forwarding, shared domains and exact URLs, shared hashtags, reused media | **No null model.** Near-binary in practice |
| **(d) Forward influence** | Out-degree and out-strength on the aggregate forward graph | **Not** cross-episode, despite its name in the code |
| **(f) Semantic coherence** | Distance to an organic-French baseline, proximity to known adversary channels | **Computed, not scored**: it reaches neither the score nor the gate ([D19](../limitations.md#d19)) |

**Multi-source rule:** a channel meets the gate, and is labelled T2, only when
**at least two distinct families** trigger. A single signal is insufficient by
construction. Two caveats weaken the rule in practice: family (c) can trigger
on two edge types alone ([D5](../limitations.md#d5)), and the severity
modulation applies whether or not the gate is met
([D21](../limitations.md#d21)). A channel is **flagged** in a separate sense:
Benjamini–Hochberg control rejects it at the mission's `alpha`.

### Episodes and one scoring dossier

Episode discovery (`scripts/mine_episodes.py`) lists RU → FR channel pairs with
the pivots that link them and a tier from the count of pivot types. Each
episode gets an index entry in the bundle, without scores.

Only one episode gets a scoring dossier: the `russosphere` registry episode
`dugin_cluster` (`scripts/build_dossier.py::main`), a cluster selected around
channels with `fr_score` below a threshold
(`scripts/build_dossier.py::select_dugin_cluster`). It holds the cluster's
strongest value for families (b), (c) and (d), with (a) and (e) stubbed at 0;
a 24-bucket timeline of forward counts; the dossier gate's detail; and an
attribution tier hard-coded to T2 ([D16](../limitations.md#d16)). The analyst
interface does not display it.

Per-channel scores are where the evidence is complete: every component of a
channel's score is preserved in its bundle file, so an analyst can justify a
ranking from it without re-running the pipeline.

### An interactive community galaxy

Communities as nebulae (Leiden), bridges between them (betweenness centrality),
dated narrative scenarios, and the per-channel score breakdown on click.

Community topic labels come from a hand-written regex vote over channel names,
not a classifier. They are a navigation aid, not evidence.

## What it does not do

| Out of scope | Reason |
|---|---|
| Judge whether a message is true or false | Structural analysis only |
| Observe platforms other than Telegram | Telegram-only coverage, declared in every export |
| Attribute to a sponsor (T3) | Crosses into investigation — out of scope by construction |
| Act on platforms (reporting, takedown) | Arm-only: output goes to designated institutional recipients |
| Analyse private messages or closed groups | MTProto read-only, public channels only |
| Deanonymize members | Channel member lists are never collected. Commenters in public linked discussion groups are: their identifier, username and text are stored (`comments` table) and published in dataset `v1.0.0`, and the identifiers and usernames of each channel's most frequent commenters are written into the analyst bundle and shown in the interface — see [`DATASHEET.md`](../../dataset/DATASHEET.md) |

## Architecture, in two halves

```text
OFFLINE PIPELINE (Python)
  MTProto collection -> normalization -> edges -> scores -> JSON bundles
           |
ANALYST INTERFACE (React, static)
  reads JSON bundles -> galaxy -> channel drawer -> no backend at consultation time
```

The two halves are **strictly disjoint** at consultation time: the browser
never touches the database and never calls Telegram. It reads precomputed JSON
only, so an analyst can work a mission while collection is idle. One build-time
exception: `npm run build` first runs `webapp/scripts/pull-snapshots.mjs` and
`webapp/scripts/pull-bundle.mjs`, which download bundles from Supabase when
`SUPABASE_URL` and `SUPABASE_KEY` are set.

Bundles are **not published in this repository**: they are corpus-specific by
construction. Generate them with `scripts/pipeline.py`; several of its stages
write into the bundle, `scripts/export_static.py` among them.

## Missions

The engine is theme-agnostic. A mission is a configuration (a Python package
under `src/missions/` holding one `MissionDefinition`: source universe,
lexicon, weights, dashboard), never a code fork.

| Mission | Object | Status |
|---|---|---|
| `russosphere` | Coordinated disinformation targeting the image, integrity or sovereignty of France | Active |
| `france_ukraine` | Narratives targeting France in the Ukraine conflict | Active |
| `gan` | Telegram-observable informational footprint of the Carrier Strike Group (OPSEC objective) | Active, but gate calibration is **not reconciled** with `russosphere` — its T2 counts are not interpretable |
| `dircom_minarm` | Reuse and distortion of official French MoD communication | Packaged, `implemented=False` — refuses live selection |

## Tiers

| Tier | Definition |
|---|---|
| **T1** | Observable diffusion structure — the primary deliverable |
| **T2** | Behavioural recurrence: the multi-source gate is met (at least 2 families triggered) |
| **T3** | Real-world attribution to a person, organization or sponsor — **out of scope** |

Assignment is mechanical: gate met implies T2, otherwise T1, with the triggered
family set persisted for audit. A T3 claim in any output is a reportable defect.

## Governance and limits

### The load-bearing limitation, declared in every bundle

> **Telegram only.** An operation reaching France mainly through other
> platforms, without a Telegram stage, **will not be detected.** What is measured
> is a footprint observable on Telegram, never the total footprint of a
> phenomenon.

A field of every bundle manifest. The analyst interface no longer displays it:
the coverage banner was removed, and only the `gan` footprint view shows a
caveat of its own ([D31](../limitations.md#d31)).

### Arm-only

Output goes to designated institutional recipients. The system never acts on
platforms and never publishes attribution itself.

### ToS-respecting collection

Public channels only. One dedicated account, serialized, never parallelized.
Strict `FLOOD_WAIT` discipline. Channel member lists are not collected.
Commenters are: `scripts/enrich_recrawl.py` stores the identifier, username and
text of people who commented in public discussion groups linked to collected
channels (`comments` table). Those are personal data of private individuals,
and the public dataset (`v1.0.0`) includes that table; its terms of use are in
[`DATASHEET.md`](../../dataset/DATASHEET.md). The pipeline also republishes part
of it: `scripts/build_commenters.py` writes, for each channel, the identifiers,
usernames and comment counts of its most frequent commenters (not their text)
into the bundle file `commenters.json`, and the channel drawer displays them.
A bundle deployed where others can reach it therefore publishes those
usernames. Secrets are scrubbed by key and by value from the static export.

### Published methodology

[`METHODOLOGY.md`](../../METHODOLOGY.md) is the versioned cover page of the
method. It must be public **before** any production detection output. Bundles
carry a static methodology version string, and no output carries a hash of the
methodology ([D20](../limitations.md#d20)); the hash the dossier schema defines
would ignore `docs/method/` in any case ([D23](../limitations.md#d23)). A
methodology revision is therefore not detectable from an output.

## Further reading

- **Install:** [`docs/ops/install.md`](../ops/install.md)
- **Quickstart:** [`docs/ops/quickstart.md`](../ops/quickstart.md)
- **Method:** [`docs/method/`](../method/)
- **Limitations:** [`docs/limitations.md`](../limitations.md)
- **Pipeline scripts:** [`scripts/README.md`](../../scripts/README.md)
- **Contributing:** [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
