# 1 — Problem, scope and what this system is not

## 1.1 The problem

Coordinated influence operations on Telegram are visible as **structure** before
they are legible as **content**. The same material appears across channels in a
short window; a small set of channels is consistently early; the same relays
recur across unrelated topics. Those regularities are observable without
adjudicating whether any individual message is true.

Idéfix reconstructs that structure from public Telegram channels and produces a
**ranked, explainable examination queue** for human analysts: which channels to
read first, and the concrete signals that justify each rank.

## 1.2 What this system is not

**It is not a fake-news detector.** No component estimates the truth value of a
message. There is no fact-checking corpus on the production path, no veracity
label in the schema, and no output field that asserts one.

**It is not a validated manipulation detector.** The system ranks channels by
structural and semantic signals. Whether a high rank corresponds to coordinated
manipulation, rather than to ordinary prominence within an adversarial media
ecosystem, is an open empirical question that this project has **not** answered.
The experiment that would answer it requires a corpus of *organic* coordination
as a negative class, and no such corpus exists. See `docs/limitations.md`.

**It does not attribute.** Attribution to a person, organization, state or
sponsor requires off-platform corroboration the system does not have and never
collects. Tier T3 is out of scope by construction (`07-tiers-and-governance.md`).

**It does not act.** Output goes to designated institutional recipients. The
system never executes platform action and never publishes attribution itself.

## 1.3 The load-bearing limitation: single-platform coverage

Idéfix observes **Telegram public channels only**. An operation that reaches its
audience mainly through other platforms, without a Telegram stage, will not be
detected. What is measured is a *Telegram-observable* footprint, never the total
footprint of a phenomenon.

This is not a caveat appended for modesty. It is a structural property of the
data source, and it is a mandatory, validated field of every exported bundle.
The full standing-limits register is `docs/limitations.md`.

## 1.4 Unit of analysis

The **channel**, not the message. Channels are followed by numeric `channel_id`,
which is stable across handle rebrands. Confidence in a channel is marked
degraded once it has not been polled for 14 days (`STALE_DAYS`).

The choice is deliberate: per-message weak labelling against fact-check corpora
was piloted and abandoned because the resulting gold was approximately 97%
"true" and therefore uninformative. Supervision, if it ever arrives, will be at
channel level.

## 1.5 One engine, N missions

A mission is a **configuration** — source universe, lexicon, targeting weights,
scoring profile, dashboard, export — never a code fork. The structural families
(b), (c) and (d) are theme-agnostic; missions differ in seeds, lexicons,
relevance signals, weights and any additional families. Missions are
auto-discovered from `src/missions/` by the registry.

| Mission | `implemented` | Object |
|---|---|---|
| `russosphere` | `True` | Coordinated disinformation targeting the image, integrity or sovereignty of France |
| `france_ukraine` | `True` | Narratives targeting France in the Ukraine conflict |
| `gan` | `True` | Telegram-observable informational footprint of the French Carrier Strike Group, with an OPSEC-minimization objective |
| `dircom_minarm` | `False` | Reuse and distortion of official French MoD communication. Packaged and registered, refuses live selection until a crawl populates it |

The `gan` mission names all its own families `telegram_*` as a deliberate
perimeter lock: it measures the observable-on-Telegram footprint, never the total
footprint. None of those families has a null model; they all use the
`p = 1 - value` fallback of `03-suspicion-score.md` §3.3, which means eight of
its ten combined "p-values" are not p-values. Its gate calibration has never
been reconciled with `russosphere`, and the two missions have produced T2 volumes
differing by more than an order of magnitude. Treat `gan` T2 counts as
uninterpretable until the gates are harmonized.

## 1.6 Reading order

| | |
|---|---|
| `02-graph-model.md` | What is extracted from Telegram and how the graph is built |
| `03-suspicion-score.md` | The score, its combiner, its null model, its defects |
| `04-thematic-relevance.md` | Targeting and the `fr_score` confusion |
| `05-semantic-family.md` | The embedding family and embedding-based communities |
| `06-episodes-and-communities.md` | Episode discovery, Leiden, labelling |
| `07-tiers-and-governance.md` | Attribution tiers, output discipline, governance |
| `../limitations.md` | Every standing limit and every known defect, in one place |
| `../experiments/` | Falsification protocols |
