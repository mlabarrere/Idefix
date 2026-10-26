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
combined as per-family p-values under Stouffer's method with
Benjamini-Hochberg FDR control.

| Family | Signal | Caveat |
|---|---|---|
| **(b) Cascade role** | Structural position in the forward graph — hub, cross-community bridge, seeding source | Corpus-relative, not comparable across runs |
| **(c) Coordination** | Time-windowed co-forwarding, shared URLs, shared hashtags | **No null model.** Near-binary in practice |
| **(d) Forward influence** | Out-degree and out-strength on the aggregate forward graph | **Not** cross-episode, despite its name in the code |
| **(f) Semantic coherence** | Distance to an organic-French baseline, proximity to known adversary channels | Opt-in; anchors are a handful of hardcoded handles |

**Multi-source rule:** a channel is only flagged when **at least 2 distinct
families** trigger. A single signal is insufficient by construction. Note that
family (c) can trigger on two edge types alone, which weakens the rule in
practice — [`../limitations.md`](../limitations.md) D5.

### Explainable episode dossiers

For each detected propagation episode:

- the channels involved, with the score decomposed per family
- the propagation chronology with observed delays
- traceability to verifiable structural evidence
- the declared tier (T1 or T2) and its justification

Every component of every score is preserved in the output, so an analyst can
justify a ranking from the dossier alone, without re-running the pipeline.

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
| Deanonymize members | Channel member lists are never collected. Commenters in public linked discussion groups are: their identifier, username and text are stored (`comments` table) and published in dataset `v1.0.0` — see [`DATASHEET.md`](../../dataset/DATASHEET.md) |

## Architecture, in two halves

```
OFFLINE PIPELINE (Python)
  MTProto collection -> normalization -> edges -> scores -> JSON export
           |
ANALYST INTERFACE (React, static)
  reads JSON bundles -> galaxy -> dossiers -> no backend at consultation time
```

The two halves are **strictly disjoint**: the webapp never touches the database
and never calls Telegram. It reads precomputed JSON only, so an analyst can work
a mission while collection is idle.

Bundles are **not published in this repository** — they are corpus-specific by
construction. Generate them with `scripts/export_static.py`.

## Missions

The engine is theme-agnostic. A mission is a configuration file — source
universe, lexicon, weights, dashboard — never a code fork.

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

### The load-bearing limitation, declared in every export

> **Telegram only.** An operation reaching France mainly through other
> platforms, without a Telegram stage, **will not be detected.** What is measured
> is a footprint observable on Telegram, never the total footprint of a
> phenomenon.

A mandatory field of every exported bundle, and permanently visible in the
analyst interface.

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
[`DATASHEET.md`](../../dataset/DATASHEET.md). Secrets are scrubbed by key and
by value from every export.

### Published methodology

[`METHODOLOGY.md`](../../METHODOLOGY.md) is the versioned cover page; its
SHA-256 hash ships in every export, so a revision is detectable in the chain of
custody. It must be public **before** any production detection output.

## Further reading

- **Install:** [`docs/ops/install.md`](../ops/install.md)
- **Quickstart:** [`docs/ops/quickstart.md`](../ops/quickstart.md)
- **Method:** [`docs/method/`](../method/)
- **Limitations:** [`docs/limitations.md`](../limitations.md)
- **Pipeline scripts:** [`scripts/README.md`](../../scripts/README.md)
- **Contributing:** [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
