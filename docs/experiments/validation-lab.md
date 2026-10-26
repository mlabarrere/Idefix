# Validation lab — external gold and organic corpora

The validation lab is the set of data contracts that would close the two gaps
blocking Experiments 2 and 3:

1. the **circularity** of known-episode recovery, and
2. the **absence of an organic French corpus** against which to measure false
   positives.

Both gaps require human annotation. This document specifies the shape of the
data; producing it is the work. See [L4](../limitations.md#l4) and
[L5](../limitations.md#l5).

Executable schemas: `src/validation_lab/schema.py`.

> [!NOTE]
> The templates named below are not in the repository: `data/eval/` is
> gitignored, so a fresh clone has no `data/eval/templates/`
> ([D26](../limitations.md#d26)). Build a file from the schema instead.

## External gold episode

A JSON file conforming to `ExternalGoldEpisode`. It must document:

- an **external provenance**;
- an **independence statement** explaining that the list derives neither from
  Idéfix scores nor from the scorer's allowlists;
- at least one `seed` channel;
- channels identified by `username` or `channel_id`;
- a confidence level and a source reference per channel.

Template: `data/eval/templates/gold_episode.example.json`.

Files consumable by `scripts/eval_episode_recovery.py` go under `data/eval/`
as `gold_episode_<name>.json`. Templates stay in `data/eval/templates/` so they
are never mistaken for real gold.

**The independence statement is the point of the contract.** A gold list built
from the same priors as the scorer cannot falsify it. The only gold assembled so
far was hypothetical, which is why Experiment 2 is blocked rather than weak.

## Organic control corpus

A JSON file conforming to `OrganicControlCorpus`, containing **non-hostile
coordinated groups**: newsrooms, institutions, activist networks, sports
fandoms, civic events, or any other documented category.

Template: `data/eval/templates/organic_control_corpus.example.json`.

Each group needs at least two channels and a rationale explaining why
coordination is expected and legitimate there.

Files consumable by `scripts/eval_organic_control.py` go under `data/eval/`
as `organic_control_<name>.json`. The script counts how many documented organic
channels surface near the top of the suspicion ranking and raises a
false-positive alarm when:

- at least three organic channels appear in the top 50, **or**
- at least two channels from the same organic group appear in the top 50.

With no real corpus present the script writes an inconclusive report rather than
inventing a verdict. That is the correct behaviour and the reason Experiment 3
is reported as blocked rather than passing.

## Validity guards

- A gold episode with `excluded_from_scorer_inputs = false` is invalid.
- A gold episode with no `seed` channel is invalid.
- A channel with neither `username` nor `channel_id` is invalid.
- An organic corpus with no group is invalid.
- An organic group with a single channel is invalid.

## Current wiring

- `scripts/eval_episode_recovery.py` reads `gold_episode_*.json` in
  `ExternalGoldEpisode` v1 format. When a file fails that validation, for any
  reason, the script re-reads it in the legacy `{episode, seeds, relays}`
  shape, so the validity guards above do not protect legacy files; and its
  conversion drops gold channels identified by `channel_id` alone
  (`src/validation_lab/schema.py::ExternalGoldEpisode.legacy_eval_payload`). See
  [`exp2-episode-recovery.md`](./exp2-episode-recovery.md).
- `scripts/eval_organic_control.py` reads `organic_control_*.json` in
  `OrganicControlCorpus` v1 format.

`scripts/eval_episode_recovery.py` also depends on evaluation inputs that are
absent from a clean clone ([D12](../limitations.md#d12)). Both write their
reports under `data/eval/` ([D25](../limitations.md#d25)).

## Next increment

1. Produce at least one **real** organic control corpus. This unblocks
   Experiment 3 and, with it, every global performance figure.
2. Obtain a **real** external gold episode, replacing the hypothetical one.
3. Re-run the battery and publish artefacts under `results/`.
