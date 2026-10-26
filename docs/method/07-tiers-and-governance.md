# 7 — Attribution tiers, output discipline and governance

## 7.1 Attribution tiers

Every claim the system makes carries a tier. The vocabulary is mandatory in all
output, and conflating tiers is a reportable defect.

| Tier | Claim | Evidence | Stance |
|---|---|---|---|
| **T1** — Observable diffusion | First-visible seeding channel, forward hubs, fan-out shape | MTProto public-channel data plus graph reconstruction | **Primary deliverable** |
| **T2** — Behavioural recurrence | Same channels or motifs recurring, multi-family corroboration | For a channel: the multi-source gate (at least two distinct triggered families). For an episode: at least two distinct pivot types | **Secondary deliverable** |
| **T3** — Real-world attribution | A person, organization, state, sponsor | Off-platform corroboration | **Out of scope. Never claimed** |

Tier assignment is mechanical: for a channel, gate met implies T2, otherwise
T1 (`src/scorer/channel_suspicion.py::compute_channel_queue`); no episode
aggregation enters it. The triggered family set is persisted as
`gate_families`, so any assignment can be audited from the stored record.
Episodes carry their own tier, from the count of distinct pivot types
(`06-episodes-and-communities.md` §6.1). The pipeline's one dossier,
`dugin_cluster.json`, does not follow either rule: `scripts/build_dossier.py::main`
hard-codes its attribution tier to T2, whatever its own gate decides
([D16](../limitations.md#d16)).

**'First-visible seeding channel' means first visible *within the Telegram
corpus*.** It never means originator. The corpus is a partial projection of a
partial platform; earliest-observed is a statement about the observation window,
not about causation.

**A caveat on T2 as currently implemented.** The tier vocabulary implies that T2
rests on independent corroboration. The gate counts *distinct families*, but
family (c) triggers on two coordination edge types alone, and one of those types
(`CO_HASHTAG`) is close to noise on a topical corpus. Episode-level tiering has
the same shape: it counts pivot types. Until family (c) has a null model and
`CO_HASHTAG` is reconsidered, T2 should be read as 'two distinct signal types
fired', which is weaker than what the label suggests. Tracked as
[D2](../limitations.md#d2) and [D5](../limitations.md#d5).

A separate T1–T5 *severity* ladder exists alongside the attribution tiers. The
pipeline's dossier gets its severity from `scripts/build_dossier.py::main`,
which maps the strongest of families (b), (c) and (d) to T1–T5 without
consulting any gate. A second mapping, `src/scorer/base.py::ScoreSummary`,
grades the five original families the same way; its comment asks for 'at least
three signals from at least two families' before T4 or T5, but its
`multi_source_rule_met` counts two families and `overall_severity` ignores it
anyway. Its only consumer, `src/dossier/builder.py::build_dossier`, has no
caller in the pipeline. The dossier schema keeps the two scales apart:
`attribution_tier` accepts only T1 or T2 and rejects T3, while `severity_tier`
accepts T1 to T5 (`src/shared/dossier.py::DossierSchema`). Read a dossier's
severity tier as evidence severity, never as attribution. The contradictions
between the dossier gates are recorded as [D16](../limitations.md#d16).

## 7.2 Output discipline

- **Arm-only.** Outputs go to designated institutional recipients. Never to
  platforms, never to the public, never to candidates or press.
- **Mandatory coverage callout.** The single-platform-blindness disclosure of
  `01-problem-and-scope.md` §1.3 is written into every bundle manifest, from the
  mission's callout or a default
  (`scripts/export_static.py::build_export_metadata`).
- **Evidence-first.** Every component of every channel's score is preserved in
  the output — weights, per-family values, p-values, trigger status, boost
  detail — so that an analyst can justify any ranking from the dossier alone
  without re-running the pipeline.
- **Chain of custody.** Each bundle carries timestamps, stable identifiers, and
  a methodology version string. That string is fixed in the code
  (`scripts/export_static.py::METHODOLOGY_VERSION`, overridable by the
  `IDEFIX_METHODOLOGY_VERSION` environment variable), not derived from the
  methodology document. A hash of `METHODOLOGY.md` exists only in the dossier
  schema, and no file the pipeline writes carries it
  ([D20](../limitations.md#d20)); it would ignore `docs/method/` in any case
  ([D23](../limitations.md#d23)). A methodology revision is therefore **not**
  detectable from an output.
- **Tiered vocabulary** is mandatory in every output; a T3 claim is a reportable
  defect.

## 7.3 Collection posture

Public channels only, via MTProto, with a single dedicated read-only account,
history backfill plus tiered polling, and `FLOOD_WAIT` discipline. No grey
collection, no scraping outside the terms of service, no deanonymization.
Channel member lists are not collected. Commenters are: the enrichment pass
(`scripts/enrich_recrawl.py`) stores the identifier, username and text of
people who commented in public discussion groups linked to collected channels
(`comments` table). Those are personal data of private individuals. The public
dataset (`v1.0.0`, a complete database snapshot) **includes** that table; its
terms of use are in `dataset/DATASHEET.md`. The pipeline republishes part of
it: the `build_commenters` stage (`scripts/build_commenters.py`) writes the
identifiers, usernames and comment counts of each channel's most frequent
commenters, without their text, into the analyst bundle (`commenters.json`),
and the channel drawer displays them. Telegram session and API credentials are
scrubbed by key and by value from the static export.

Migration `0003` records the constraints that apply to the `comments` table:
public groups only, data minimization, retention bounds of 13 and 36 months
with an access journal, and deletion propagation. Those are recorded intentions;
no code in the repository enforces the retention bounds or propagates
deletions.

**Deletion detection is not implemented.** No code sets `messages.is_deleted`,
so a message deleted on Telegram after collection stays in the corpus as if it
were live ([D22](../limitations.md#d22)). No platform firehose exists.

Two further collection blind spots are permanent and accepted: channels under a
French legal block are invisible to an EU-anchored collector account, and
private channels are invisible entirely.

## 7.4 Governance commitments

- The methodology is published before any live detection output ships. Outputs
  are meant to embed its hash; today bundles embed a fixed version string
  instead, and no output embeds the hash ([D20](../limitations.md#d20)).
- **No channel is labelled T2 without at least two distinct triggered
  families**, enforced structurally by the gate, not by review. The rule does
  not reach the dossier, whose tier is hard-coded
  ([D16](../limitations.md#d16)), and severity is **not** bound by it: the
  severity factor applies whether or not the gate is met
  ([D21](../limitations.md#d21)).
- The validation state ships **with** the methodology and is updated whenever the
  falsification battery is re-run. Claims are bounded by the weakest relevant
  experiment.
- A **symmetric transparency ratio** — the share of the full scored population
  linked to documented adversary infrastructure versus organic — is computed on
  every full scoring run and published with the bundle. Until September 2026
  its 'suspect' side was partly a language partition; since the fix to the
  credibility prior ([D1](../limitations.md#d1)) it rests on documented
  adversary linkage, so its interpretation is bounded by the coverage of the
  adversary catalogue instead.

## 7.5 Standing claim

Calibrated to the evidence actually available:

> Idéfix is defensible as a **T1 demonstrator** — it reconstructs observable
> diffusion structure and presents it with per-signal evidence. It is **not** a
> validated manipulation detector, and no output should be presented as more
> than T1 or T2.

Two gaps bound every stronger claim, and neither is closed by engineering. Both
require human annotation: a corpus of **organic** coordination to serve as the
negative class, and a **real** external seed list for a documented operation.
Until they close, the standing claim above is the ceiling.
