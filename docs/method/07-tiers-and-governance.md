# 7 — Attribution tiers, output discipline and governance

## 7.1 Attribution tiers

Every claim the system makes carries a tier. The vocabulary is mandatory in all
output, and conflating tiers is a reportable defect.

| Tier | Claim | Evidence | Stance |
|---|---|---|---|
| **T1** — Observable diffusion | First-visible seeding channel, forward hubs, fan-out shape | MTProto public-channel data plus graph reconstruction | **Primary deliverable** |
| **T2** — Behavioural recurrence | Same channels or motifs recurring, multi-family corroboration | Multi-episode aggregation plus the multi-source gate | **Secondary deliverable** |
| **T3** — Real-world attribution | A person, organization, state, sponsor | Off-platform corroboration | **Out of scope. Never claimed** |

Tier assignment is mechanical: gate met implies T2, otherwise T1
(`channel_suspicion.py:874`). The triggered family set is persisted as
`gate_families`, so any assignment can be audited from the stored record.

**"First-visible seeding channel" means first visible *within the Telegram
corpus*.** It never means originator. The corpus is a partial projection of a
partial platform; earliest-observed is a statement about the observation window,
not about causation.

**A caveat on T2 as currently implemented.** The tier vocabulary implies that T2
rests on independent corroboration. The gate counts *distinct families*, but
family (c) triggers on two coordination edge types alone, and one of those types
(`CO_HASHTAG`) is close to noise on a topical corpus. Episode-level tiering has
the same shape: it counts pivot types. Until family (c) has a null model and
`CO_HASHTAG` is reconsidered, T2 should be read as "two distinct signal types
fired", which is weaker than what the label suggests. Tracked in
`docs/limitations.md`.

A separate T1–T5 *severity* ladder appears in `src/scorer/base.py`. That module
is a dead v0 stub whose families all return 0.0; its ladder contradicts the
T1/T2-only doctrine enforced elsewhere (`src/shared/dossier.py:91-96` raises on
T3). Ignore it. It is scheduled for removal.

## 7.2 Output discipline

- **Arm-only.** Outputs go to designated institutional recipients. Never to
  platforms, never to the public, never to candidates or press.
- **Mandatory coverage callout.** The single-platform-blindness disclosure of
  `01-problem-and-scope.md` §1.3 is a validated field of every exported bundle.
- **Evidence-first.** Every component of every channel's score is preserved in
  the output — weights, per-family values, p-values, trigger status, boost
  detail — so that an analyst can justify any ranking from the dossier alone
  without re-running the pipeline.
- **Chain of custody.** Each bundle carries a hash of the methodology document,
  timestamps and stable identifiers, so a methodology revision is detectable
  after the fact.
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
terms of use are in `dataset/DATASHEET.md`. Telegram session and API
credentials are scrubbed by key and by value from every export.

Deletion detection runs by polling diff, with latency of roughly 15 minutes on
hot channels. No platform firehose exists.

Two further collection blind spots are permanent and accepted: channels under a
French legal block are invisible to an EU-anchored collector account, and
private channels are invisible entirely.

## 7.4 Governance commitments

- The methodology is published before any live detection output ships, and
  bundles embed its hash.
- **No T2 label and no escalated severity without at least 2 triggered
  families** — enforced structurally by the gate, not by review.
- The validation state ships **with** the methodology and is updated whenever the
  falsification battery is re-run. Claims are bounded by the weakest relevant
  experiment.
- A **symmetric transparency ratio** — the share of the full scored population
  linked to documented adversary infrastructure versus organic — is computed on
  every full scoring run and published with the bundle. Its interpretation is
  currently limited by the language bias of `04-thematic-relevance.md` §4.1,
  since the "suspect" side of the ratio is partly a language partition.

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
