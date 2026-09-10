# 4 — Thematic relevance and targeting

**Status:** implemented. `src/normalizer/targeting.py`,
`src/normalizer/france_targeting.py`, `scripts/tag_france.py`.

This chapter exists because two different quantities in this system are easy to
confuse, and confusing them has already produced a false claim in an earlier
version of the methodology. They are computed by different code, mean different
things, and have different consequences.

## 4.1 Two quantities, not one

| | `targeting_score` | `fr_score` |
|---|---|---|
| Computed by | `src/normalizer/targeting.py:183-193` | `scripts/tag_france.py:35` |
| Definition | Weighted composite of lexicon breadth, depth and adversary-domain citation | `matching_messages / total_messages` for one French-keyword regex |
| Range | [0,1], per channel, max over sampled messages | [0,1], a raw density |
| Used for | Bounded severity modulation (`03-suspicion-score.md` §3.8) | Display only |
| Status | Uncalibrated but principled | Was a defect until 2026-09 — `docs/limitations.md` D1 |

The second row is the important one. `fr_score` was documented for a long time
as "a display field only, never used as a filter or anchor", while in fact being
the threshold that decided whether a channel was labelled `suspect` — a label
feeding the largest severity modulator. The claim was false when written. The
code was changed in September 2026 so that it is now true: `credibility_prior`
is derived from documented adversary linkage, and language is no longer an
input anywhere in the score.

## 4.2 The targeting engine

A mission supplies a `TargetingProfile`: an anchor lexicon grouped into
categories, a set of contextual terms, and a list of adversary domains. The
engine is generic; only the data is thematic.

```
breadth       = distinct_categories_matched / n_categories
depth         = total_hits / (total_hits + depth_saturation)
domain_signal = 1.0 if any adversary domain is cited else 0.0

score = breadth_weight*breadth + depth_weight*depth + domain_weight*domain_signal
```

For the `russosphere` mission (`france_targeting.py:136-141`): 5 categories,
`breadth_weight = 0.55`, `depth_weight = 0.30`, `domain_weight = 0.15`,
`depth_saturation = 4.0`. The `gan` mission uses `0.40 / 0.45 / 0.15` with no
recorded calibration for either set. **These are six free parameters.**

Matching is **regex keyword counting**, not semantics: accent folding, plus a
bounded Cyrillic inflectional suffix so that Russian declensions of a keyword
match its stem. Contextual terms are counted only when an anchor term also
matched in the same message. A channel's score is the **maximum** over its most
recent sampled messages (up to 500), so one strongly on-topic message is enough
to score the channel.

There is no model here. Read `targeting_score` as "how densely and how broadly
this channel's text hits a hand-written word list".

## 4.3 The claim-proximity seam is dead code

`targeting.py:199` implements a soft-OR that would raise the score when a
claim-proximity value is supplied:

```
score = score + (1 - score) * claim_proximity
```

Nothing ever supplies one. The evidence record contains the literal string
`"N/A — episodes registry empty (v0)"`. This branch has never executed in
production and should not be described as part of the method.

## 4.4 The property that does hold

Thematic relevance enters the score only through the bounded multiplicative
modulator of `03-suspicion-score.md` §3.8. A channel with zero base suspicion
stays at zero regardless of how strongly it is on-theme, so legitimate press
writing about France is not promoted by relevance alone. That guarantee is
structural, and it survives the defect of §4.1 — which distorts *which* channels
are boosted, not *whether* an unsuspicious channel can be boosted from zero.
