# 4. Thematic relevance and targeting

**Status:** implemented. `src/normalizer/targeting.py`,
`src/normalizer/france_targeting.py`, `scripts/tag_france.py`.

This chapter exists because two different quantities in this system are easy to
confuse, and confusing them has already produced a false claim in an earlier
version of the methodology. They are computed by different code, mean different
things, and have different consequences.

<a id="s4-1"></a>

## 4.1 Two quantities, not one

| Property | `targeting_score` | `fr_score` |
|---|---|---|
| Computed by | `src/normalizer/targeting.py::score_targeting` | `scripts/tag_france.py::main` |
| Definition | Weighted composite of lexicon breadth, depth and adversary-domain citation | `matching_messages / total_messages` for one French-keyword regex |
| Range | [0,1], per channel, max over sampled messages | [0,1], a raw density |
| Used for | Bounded severity modulation ([`03-suspicion-score.md` §3.8](./03-suspicion-score.md#s3-8)) | Not the score. It decides the side of each episode and which channels can enter episodes (`scripts/mine_episodes.py`), drives the porosity view (`scripts/analyze_porosity.py`), and ranks the snowball frontier (`scripts/snowball_crawl.py`). The mission profile names these signals (`porosity_side_signal` and `snowball_anchor_signal` in `src/missions/spec.py`), but both scripts read `fr_score` directly |
| Status | Uncalibrated but principled | Fed the credibility prior until 2026-09—[D1](../limitations.md#d1), fixed |

The 'Used for' row is the important one. `fr_score` was documented for a long
time as 'a display field only, never used as a filter or anchor', while in fact
being the threshold that decided whether a channel was labelled `suspect`—a
label feeding the largest severity modulator. The claim was false when written.
The code was changed in September 2026: `credibility_prior` is now derived from
documented adversary linkage, and language is no longer an input anywhere in
the score. `fr_score` is still not a display field, though: outside the score,
it filters and orients episodes, the porosity view, and the snowball crawl, as
the table says.

<a id="s4-2"></a>

## 4.2 The targeting engine

A mission supplies a `TargetingProfile`: an anchor lexicon grouped into
categories, a set of contextual terms, and a list of adversary domains. The
engine is generic; only the data is thematic.

```text
breadth       = distinct_categories_matched / n_categories
depth         = total_hits / (total_hits + depth_saturation)
domain_signal = 1.0 if any adversary domain is cited else 0.0

score = breadth_weight*breadth + depth_weight*depth + domain_weight*domain_signal
```

For the `russosphere` mission (`src/normalizer/france_targeting.py::_FRANCE_WEIGHTS`): 5
categories, `breadth_weight = 0.55`, `depth_weight = 0.30`,
`domain_weight = 0.15`, `depth_saturation = 4.0`. The `gan` mission uses
`0.40 / 0.45 / 0.15`, and `france_ukraine` and `dircom_minarm` carry their own
`TargetingProfile` too. None of these sets has a recorded calibration: each is
three weights and one saturation, **four free parameters per mission**.

Matching is **regex keyword counting**, not semantics: accent folding, plus a
bounded Cyrillic inflectional suffix so that Russian declensions of a keyword
match its stem. Contextual terms are counted only when an anchor term also
matched in the same message. A channel's score is the **maximum** over its most
recent sampled messages (up to 500), so one strongly on-topic message is enough
to score the channel.

There is no model here. Read `targeting_score` as 'how densely and how broadly
this channel's text hits a hand-written word list'.

<a id="s4-3"></a>

## 4.3 The claim-proximity seam is dead code

`src/normalizer/targeting.py::score_targeting` implements a soft-OR that would raise the score
when a claim-proximity value is supplied:

```text
score = score + (1 - score) * claim_proximity
```

Nothing ever supplies one. The evidence record contains the literal string
`"N/A — episodes registry empty (v0)"`. This branch has never executed in
production and should not be described as part of the method.

<a id="s4-4"></a>

## 4.4 The property that does hold

Thematic relevance enters the score only through the bounded multiplicative
modulator of [`03-suspicion-score.md` §3.8](./03-suspicion-score.md#s3-8). A channel with zero base suspicion
stays at zero regardless of how strongly it is on-theme, so legitimate press
writing about France is not promoted by relevance alone. That guarantee is
structural, and it held even while the defect of [§4.1](#s4-1) was open: that defect
distorted *which* channels were boosted, not *whether* an unsuspicious channel
could be boosted from zero.
