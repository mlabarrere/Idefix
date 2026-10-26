# Datasheet: Idéfix public Telegram corpus `v1.0.0`

Structured after *Datasheets for Datasets* (Gebru et al., 2021). Every count
below is taken from [`manifest.json`](./manifest.json) or measured on the
release database; how to fetch and verify the files is in
[`README.md`](./README.md).

| Field | Value |
|---|---|
| Name | `idefix-telegram-public-corpus` |
| Version | `1.0.0` (release tag `dataset-v1.0.0`) |
| Source snapshot | `idefix-supabase-post-cutover-20260618-132009` |
| Format | PostgreSQL 17 `pg_dump` custom format (schema at Alembic `0008`) + `tar.gz` of annotation files |
| Post timestamps | 2018-12-14T02:45:39Z → 2026-06-10T15:16:34Z (`collection_window`) |
| Collected | 2026-06-03 → 2026-06-10 (ingestion timestamps) |
| Licence | **pending maintainer decision**—see [§ Licence](#licence-pending-maintainer-decision) |

> [!CAUTION]
> **Personal data.** The release is the complete database snapshot. It includes
> the `comments` table: the Telegram identifier, username and text of private
> individuals who commented in public discussion groups. Read
> [§ Uses](#uses) before using the data.

## Contents

- [Motivation](#motivation)
- [Composition](#composition)
- [Collection process](#collection-process)
- [Preprocessing, cleaning, labelling](#preprocessing-cleaning-labelling)
- [Uses](#uses)
- [Distribution](#distribution)
- [Maintenance](#maintenance)
- [Open decisions for the maintainer](#open-decisions-for-the-maintainer)

## Motivation

**Why was the dataset created?** Idéfix studies how content spreads across
public Telegram channels relevant to France—forwards, shared media, shared
links—to describe observable diffusion structures (who
seeded, who relayed, how fast). The method is in the repository
[`docs/`](../docs/README.md). The dataset exists so that third parties can
rerun that offline pipeline on the same corpus, check the published method
against it, and reproduce or refute its results without a Telegram account.

**Who created it?** The Idéfix maintainer (repository `mlabarrere/Idefix`),
with a single dedicated Telegram account used read-only.

**Funding.** Not stated in the repository.

## Composition

**What are the instances?** Public Telegram channels, the posts they published,
and comments posted in the channels' public linked discussion
groups—plus the tables an earlier run of the pipeline derived from them.

| Table | Rows | What a row is |
|---|---:|---|
| `channels` | 3,699 | a public channel: id, username, title, member count, bio, collection tier, `extra` JSON |
| `messages` | 166,188 | a post of a channel: text, timestamp, forward origin, views, forwards, media type and media id |
| `comments` | 9,241 | a comment in a channel's public linked discussion group: the broadcast channel's id, the comment's message id in the group, commenter id, commenter username, text, timestamp |
| `edges` | 16,275 | a derived channel-to-channel (or channel-to-domain) relation |
| `channel_scores` | 7,313 | a derived per-channel, per-mission suspicion score with its evidence payload |
| `scores_run_meta` | 2 | the envelope of one scoring run per mission |
| `episodes` | 0 | (empty in the source) |
| `evidence_dossiers` | 0 | (empty in the source) |
| `channel_llm_scores` | 0 | created empty by migration `0007` |

**Channels.** 3,699 rows, by collection tier: 3,516 `discovered` (seen as the
origin of a forward), 154 `cold` and 29 `warm`. Posts were backfilled for 687
of them (661 discovered, 26 warm, no cold). 3,492 have a username, 3,554 a
title, 534 a bio and 380 a member count. `extra` is set on those 687 channels
and holds three keys written by the pipeline: `fr_score` and `msg_sampled`
(`scripts/tag_france.py`, all 687) and `gan_targeting` (`scripts/tag_gan.py`,
685). The pipeline recomputes all three offline.

**Messages.** 166,188 posts from 687 channels: 123,492 with text, 28,386
forwards, 125,407 with media (110,170 carry a Telegram media id in
`media_hash`). Collection was capped per channel (median 300 posts, maximum
600), so most channels are covered by their most recent posts only: 104,387
posts date from May or June 2026 and 22,373 from before 2026. `language`,
`urls` and `raw_content` are NULL on every row; `is_deleted` is false on every
row.

**Comments—personal data.** 9,241 comments in the discussion groups of 55 channels,
written by 2,644 distinct Telegram accounts (`commenter_id`, every row); 5,618
rows carry a `commenter_username` (1,562 distinct); 8,399 have text. Comment
timestamps run from 2025-06-16 to 2026-06-06; they were collected on 2026-06-05
and 2026-06-06. None of these accounts is a channel of the corpus, and no
commenter id appears as a forward origin. These are **private individuals**:
even without the username, the channel, the comment's message id and its timestamp locate it in the
public thread, so the table cannot be considered pseudonymous.

The project's own pipeline republishes part of this table. Its
`build_commenters` stage (`scripts/build_commenters.py`) writes, for each
channel, the commenter id, commenter username and comment count of its most
frequent commenters, without comment text, into the analyst bundle file
`commenters.json`, and the analyst interface lists them in the channel drawer.
The stage reads the whole table whatever the mission, so every mission's
bundle carries the commenters of every channel. Any bundle generated from this
release therefore carries commenter usernames.

**Derived tables.** `edges`, `channel_scores` and `scores_run_meta` are the
output of the pipeline run that produced the snapshot (`gan` scored on
2026-06-09, `russosphere` on 2026-06-10). Edge types: `FORWARD` 6,889,
`CITES_DOMAIN` 2,832, `CO_HASHTAG` 1,701, `MENTIONS` 1,606, `MEDIA_REUSE`
1,330, `CO_FORWARD` 1,062, `CO_URL` 564, `CO_URL_EXACT` 291. Scores: 3,699 for
`russosphere`, 3,614 for `gan`. They are machine-generated, were never human
reviewed, and are **not** labels: running the pipeline overwrites them, and
results must be cited from a fresh run, not from these tables.

**Annotation archive** (`idefix-annotations-v1.0.0.tar.gz`, extracted into
`data/`), 9 files:

- `annotations/batch-20260604.jsonl`—200 posts sampled for message-level
  labelling, each with its channel, a candidate fact-checked claim and a
  proximity score; `annotations/batch-20260604__needs_manual_screening.jsonl`—211 posts set aside (claim link too weak);
- `annotations/judgments/batch-20260604__claude.jsonl`—200 verdicts by one
  LLM judge (Claude), with atomic claims, sources and rationale; no human
  adjudication was recorded;
- `annotations/channel_digests.jsonl` and `.md`—23 channel-level digests
  (sample posts, forward neighbours, a provisional label and rationale);
- `annotations/PROTOCOLE_LABELLISATION.md`, `annotations/README.md`—the
  labelling protocol (in French), `annotations/.gitkeep`;
- `claims/claims_fr.jsonl`—15 seed claims from French fact-checkers.

The protocol and README name the maintainer ('Micky') as the human arbiter.
Post texts in the archive are copies of posts of the database.

**Is it a sample?** Yes, and not a random one: see the biases under
[Collection process](#collection-process). It is not representative of
Telegram, of French-language Telegram, or of any channel's full history.

**Labels.** No ground truth. The scores and LLM verdicts are model outputs.

**Missing data.** Posts deleted before collection are absent; deletion after
collection is not reflected (`is_deleted` is never set). Views and forwards
are values at collection time. Private channels, channels under a French legal
block, and comments of groups that were not accessible are invisible.

**Confidential or sensitive content.** Channel posts are public broadcast
content but include propaganda, disinformation and possibly hateful or violent
material. Comments are personal data (above) and may reveal political
opinions—a special category under GDPR Art. 9. A read-only scan found none of
the collector account's secrets (Telegram session, phone, API hash, LLM key) in
any table or archived file.

## Collection process

**How was the data acquired?** Through Telegram's MTProto API (Hydrogram), with
one dedicated account, read-only, serialized requests and `FLOOD_WAIT`
discipline; public channels only (governance:
[`docs/method/07-tiers-and-governance.md`](../docs/method/07-tiers-and-governance.md)).

1. **Seeds (hop 0).** `scripts/backfill_seeds.py` backfilled a hand-picked set
   (its default: six French news and aggregator hubs and one documented
   pro-Kremlin channel).
2. **Snowball.** Every forward reveals its origin channel, recorded as
   `discovered` (catalogue source `forward_origin`). `scripts/snowball_crawl.py`
   then backfilled bounded waves of the most promising frontier channels,
   ranked by their proximity to France-relevant channels already collected
   (a lexical `fr_score` of at least 0.15 marks a 'France seed'). The data
   does not record which crawl added which channel: `catalogue_source` only
   marks forward origins.
3. **Enrichment.** `scripts/enrich_recrawl.py` re-read collected channels to add
   media ids, channel bios and comments of public linked discussion groups (up
   to 500 per group).

**Biases this creates.**

- *Seed bias*: collection starts from channels chosen by hand; communities
  not connected to them by forwards are absent.
- *Snowball bias*: discovery follows forwards, so channels that forward or get
  forwarded a lot are over-represented and quiet or isolated ones missed; the
  frontier was deliberately steered towards France-relevant channels.
- *Lexical steering*: France relevance was a keyword score, which favours
  French-language channels; this bias is documented in
  [`docs/limitations.md`](../docs/limitations.md).
- *Truncation*: per-channel caps keep the most recent posts, so the corpus is
  dominated by May–June 2026 and older dates come from low-volume channels.
- *Single platform*: diffusion outside Telegram is not observed.
- *Comment coverage*: only 55 channels with an accessible public linked group.

**Who collected it, when, under what basis?** The maintainer, between
2026-06-03 and 2026-06-10. The collection of commenters was decided on
2026-06-05 under a public-interest basis (GDPR Art. 6.1.e); the record is in
`alembic/versions/0003_enrich_media_description_comments.py`. Publishing
their data is a further processing; see
[Open decisions](#open-decisions-for-the-maintainer).

## Preprocessing, cleaning, labelling

**At collection.** Post text, media id (`file_unique_id`, no media downloaded),
forward origin, counters. `raw_content`, `language` and `urls` were not filled
by this collector version.

**For the release: none.** The release is the complete snapshot. The steps,
each verified by the release script and listed in `manifest.json`
(`sanitization`):

- no row deleted, no table emptied, no column nulled—including `comments`,
  the derived tables and every `channels.extra` key;
- lossless restore proved per table: row count and content MD5 of the 8 source
  tables identical before and after the upgrade (`alembic_version` excepted);
- additive migrations `0006` → `0008` only: new empty table
  `channel_llm_scores`, new column `channel_scores.gate_families` (NULL on
  every row);
- owners and privileges stripped (`pg_dump --no-owner --no-privileges`);
- hosting residue kept unchanged: row-level-security flag on 9 tables (no
  policy), function `public.rls_auto_enable()`;
- annotation files archived byte-for-byte, nothing excluded.

**Is the raw data available?** The database dump *is* the raw collected data.

**Software.** [`scripts/release_dataset.py`](../scripts/release_dataset.py)
builds and verifies the release; the pipeline that derives the scores is in
the repository.

## Uses

**Intended uses.**

- Reproducing, auditing or refuting Idéfix's method and published results by
  rerunning the offline pipeline (`scripts/bootstrap.py`).
- Research on diffusion structures between *channels*: forward networks, media
  and link reuse, timing.
- Methodological work on detection of coordinated behaviour, at the channel
  level, with the tiered vocabulary of the project.

**Out of scope—do not use the dataset to:**

- identify, profile, contact, track or harass any commenter, or link a
  Telegram account to a real person (deanonymization is excluded by the
  project's governance);
- republish commenter identifiers, usernames or comment text, or redistribute
  the `comments` table outside the terms you received it under—this
  includes deploying an analyst bundle where others can reach it, since its
  `commenters.json` carries commenter identifiers and usernames;
- claim a real-world attribution (state sponsorship, who operates a channel):
  that is tier T3, out of scope and a reportable defect;
- present the shipped `channel_scores`, `edges` or LLM verdicts as facts, as
  ground truth, or as a list of disinformation actors: they are stale,
  machine-generated and unreviewed;
- target candidates, press or platforms with the outputs—the project's
  outputs are reserved for designated institutional recipients ([repository README](../README.md#11-governance) §11,
  'Arm-only');
- train models whose purpose is to recognize or score individuals.

**Possible harms.** Exposure of commenters; reputational harm to channels from
uncalibrated scores; amplification of disinformation by redistributing it.

## Distribution

- **How:** two assets of the GitHub release `dataset-v1.0.0`, each pinned by
  size and SHA-256 in `dataset/manifest.json`; `scripts/bootstrap.py fetch`
  downloads and verifies them. Mirrors are allowed when hashes match.
- **When:** first release `v1.0.0`; publication is a manual maintainer step.

### Licence (pending maintainer decision)

> **Decision pending.** The terms below are a proposed default, not yet
> adopted. Until the maintainer replaces this section, no licence is granted
> beyond what applicable law allows.

Proposed default:

- **Content** (post text, channel titles and bios, comment text): copyright
  stays with the respective authors; no licence is granted on it. It is made
  available for research and reproducibility only, under the uses above.
- **Annotations and metadata** created by the project (annotation files,
  claim registry, schema, derived tables, manifest, this datasheet):
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Code** of the repository: Apache-2.0 (`LICENSE`), unchanged.
- **Personal data** in `comments`: processed under GDPR; whoever downloads it
  becomes responsible for their own processing of it.

## Maintenance

- **Maintainer:** the repository owner. Use the issue tracker for errors in
  the data or the documentation, and the private channel of
  [`SECURITY.md`](../SECURITY.md) for anything involving personal data.
- **Removal requests:** a person can ask for their data to be removed through
  that private channel. A removal means a new release; the old assets would
  have to be withdrawn.
- **Versioning:** semantic. A patch changes documentation only, a minor adds
  data, a major changes or removes data or the schema. Every version has its
  own tag, files and manifest; a published version is never modified in place.
- **Rebuild:** [`README.md`](./README.md) § Rebuild it. The dump is not
  bit-reproducible (it records its own creation time), its per-table
  fingerprints are; the annotation archive is byte-reproducible.

## Open decisions for the maintainer

1. **Licence and terms of use**: adopt, amend or replace the proposed default
   above.
2. **Legal basis for publishing `comments`.** Collection was justified by a
   public-interest mission; a public release is a different processing. The
   collection record (`alembic/versions/0003_enrich_media_description_comments.py`)
   names retention bounds (13/36 months), an access journal and deletion
   propagation, which cannot hold once the table is public. A data-protection
   impact assessment and a contact/removal process should precede publication.
3. **Shipping the derived scores publicly** conflicts with the 'Arm-only'
   output rule of the governance ([repository README](../README.md#11-governance) §11 records the exception).
