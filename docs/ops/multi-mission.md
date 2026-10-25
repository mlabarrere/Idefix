# Multi-mission platform — contributor guide

Canonical scope:
[`../method/01-problem-and-scope.md`](../method/01-problem-and-scope.md) §1.5.

Idéfix is a **theme-agnostic Telegram engine** plus **N analytical missions**.
A mission is a **configuration** — six profiles and a relevance scorer — never a
code fork.

## Missions (`src/missions/`)

| Mission | `implemented` | Object |
|---|---|---|
| `russosphere` | `True` (default) | Coordinated disinformation targeting the image, integrity or sovereignty of France |
| `france_ukraine` | `True` | Narratives targeting France in the Ukraine conflict |
| `gan` | `True` | Telegram-observable informational footprint of the Carrier Strike Group — OPSEC objective |
| `dircom_minarm` | `False` | Reuse and distortion of official MoD communication. Appears in the switcher, refuses live selection |

Each `src/missions/<name>/__init__.py` exports
`MISSION: MissionDefinition` (see `src/missions/spec.py`), composed of a
`SourceUniverse`, `LexiconProfile`, `TargetingProfile`, `ScoringProfile`,
`DashboardProfile`, `ExportProfile`, and a `relevance_scorer`.
`src/missions/registry.py` discovers them by convention;
`resolve_mission(name | None)` defaults to `russosphere`.

**Adding a mission = creating a package and its `MISSION`.** No engine change.

## Per-mission pipeline

```
raw data (public dataset restore, or your own crawl/backfill)
  -> build_edges -> tag_<mission> -> build_scores --mission <m>
  -> analyze_*   -> export_static --mission <m> -> build_stories --mission <m>
```

`scripts/pipeline.py --mission <m>` runs the offline part in order
(`--mission all` for every implemented mission; `--list` prints the stages). A
new mission's stages must be registered there to be part of a reproducible run.

`export_static` and `build_stories` default to
`webapp/public/data/<mission>/`; an explicit `--out` is not required. Those
bundles are gitignored by design — see [`../limitations.md`](../limitations.md)
Part III.

Omitting `--mission` selects `russosphere` and reproduces the historical
behaviour byte-for-byte, which the golden tests enforce.

For `gan`, `scripts/tag_gan.py` writes `channels.extra.gan_targeting` as a
merge, so it does not clobber `fr_score`. `build_scores --mission gan`
materializes the `telegram_*` families (visibility, velocity, source diversity,
disclosure precision, propagation, adverse attention), mission-scoped via
`channel_scores.mission` (Alembic `0005` / `0006`).

> **Calibration warning.** The `gan` gate has never been reconciled with
> `russosphere`, and the two missions have produced T2 volumes differing by more
> than an order of magnitude. Treat `gan` T2 counts as uninterpretable —
> [`../limitations.md`](../limitations.md) D15.

## Scope and secrets

- **Telegram-only.** Every `gan` score is named `telegram_*` as a deliberate
  perimeter lock: what is measured is the Telegram-observable footprint, never
  the total footprint. Permanent caveat in the UI and in every report.
- **The Telegram account and session** are execution dependencies
  (`src/ingestor/session.py`: `TELEGRAM_*` env vars with `TG_*` aliases, plus
  `session_preflight`). They are **never exported** — `export_static` scrubs
  secrets by key and by value.
- **Arm-only**, tiers **T1/T2** only, T3 out of scope.

## Scoring (`src/scorer/`)

- `channel_suspicion.compute_channel_queue(..., profile, extra_families)` is
  parameterized by a `ScoringProfile`. The structural families — (b) cascade,
  (c) coordination, (d) forward influence — are theme-agnostic.
- `telegram_footprint.py` holds the `telegram_*` families. `eefi_rubric.py`
  holds the graded EEFI rubric behind `telegram_disclosure_precision`; its
  severities are a **business decision**, currently a v0 seed pending
  calibration by the sponsor.
- `loader.make_prior_policy(enabled)`, fed from
  `ScoringProfile.credibility_prior_enabled`, makes `credibility_prior`
  mission-aware — `gan` disables it (neutral prior), since
  discussing a friendly asset carries no presumption of suspicion.

  **Note:** until September 2026 this prior was derived from French-keyword
  density — a language partition. It is now derived from documented adversary
  linkage; the effect of that change on the ranking is unmeasured —
  [`../limitations.md`](../limitations.md) D1.

Full treatment:
[`../method/03-suspicion-score.md`](../method/03-suspicion-score.md).

## Analyst interface

`webapp/` — React, Vite, TypeScript, Tailwind, Radix. Static build, no backend.
Mission switcher, permanent Telegram-only banner, overview and channel views.
See [`../../webapp/README.md`](../../webapp/README.md) and
[`../product/frontend.md`](../product/frontend.md).

## Validation

```bash
uv run python -m pytest                  # golden tests pin the default path
cd webapp && npm run build && npx tsc --noEmit
```

`scripts/pipeline.py --mission gan` runs on the public corpus. Widening the
`gan` source universe (more naval and defence seeds) requires your own
collection — see the [install guide](./install.md#optional-collect-your-own-data-from-telegram).
