# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Each
release opens with two headings that sort its changes by their effect on the
method, before the usual categories:

- **Normative**: a change to what the pipeline computes. It can move a ranking.
- **Editorial**: a change to the documentation only. It never moves a ranking.

The methodology's own version history, with the reasoning behind each
withdrawn claim, is in [`METHODOLOGY.md`](./METHODOLOGY.md#version-history).
Defect numbers (D1, D19, …) refer to [`docs/limitations.md`](./docs/limitations.md).

## [Unreleased]

### Normative

None. No change here alters what the pipeline computes.

### Editorial

- **`ONBOARDING.md`**: a single tutorial for new contributors. It covers the
  one-command setup, then the database in depth: schema, read-only
  exploration, Alembic migrations with a worked example, corpus enrichment,
  and dataset releases. It ends with an improvement backlog and good first
  issues. It is linked from `README.md`.
- `scripts/check_docs.py` no longer reads a footnote definition (`[^id]: text`)
  as a link reference definition.

## [0.4.1] — 2026-10-26

### Normative

None. No change in this release alters what the pipeline computes, and no
ranking moves.

### Editorial

A documentation pass that rewrote every claim the code does not support into
what the code does today, and registered each gap as a defect instead of
changing the code. The code fixes are separate, later, versioned changes.

- **`METHODOLOGY.md` 0.4.1.** One full rewrite. Its methodology hash, the first
  eight hexadecimal characters of the SHA-256 of the file's LF bytes as
  `src/shared/dossier.py::get_methodology_version_hash` computes them, is now
  <!-- fact:methodology.hash -->**cd38fde0**<!-- /fact -->. A checkout with CRLF line endings computes a different value
  ([D27](./docs/limitations.md#d27)).
- **Privacy.** The README now opens with a caution: the `comments` table holds
  the Telegram user ID, username and text of private commenters, and dataset
  `v1.0.0` publishes it. The `build_commenters` pipeline stage copies the IDs
  and usernames of each channel's most frequent commenters into the analyst
  bundle, and the interface displays them; the README, the product page, the
  governance chapter and the datasheet now say so. `docs/product/product.md`
  had said that member identifiers are never collected.
- **Withdrawn as false**, each rewritten to the present-tense truth:
  - family (f) is active and helps a channel cross the gate. It is computed,
    not scored ([D19](./docs/limitations.md#d19));
  - every export carries the hash of `METHODOLOGY.md`. Bundles carry a static
    methodology version string, and no output carries the hash
    ([D20](./docs/limitations.md#d20)), which would ignore `docs/method/` in
    any case ([D23](./docs/limitations.md#d23));
  - no escalated severity without at least two triggered families. Severity
    modulation is not gated ([D21](./docs/limitations.md#d21));
  - deletions are detected by polling. Deletion detection is not implemented
    ([D22](./docs/limitations.md#d22));
  - the coverage callout is permanently visible in the analyst interface. It
    is in every bundle manifest, but the interface no longer displays it
    ([D31](./docs/limitations.md#d31));
  - the published snapshot predates schema revisions `0007` and `0008`. The
    source snapshot was at `0006`; the published dump is at `0008`, the
    current Alembic head;
  - `src/scorer/base.py::ScoreSummary` is live code. Its only consumer has no
    caller in the pipeline, and the pipeline's dossier hard-codes its
    attribution tier ([D16](./docs/limitations.md#d16));
  - families (b) and (d) share their bootstrap draws. They share the null
    ensemble only ([D3](./docs/limitations.md#d3)).
- **Terminology.** 'Flagged' now has one meaning, the Benjamini–Hochberg
  rejection set, defined in the glossary. A channel that crosses the
  multi-source gate is said to 'meet the gate'.
- **`docs/limitations.md`.** Defects D19 to D31 registered; a status table at
  the top; an explicit anchor on every entry; the five fixed defects moved to a
  closed part, Part V, so that Part III keeps its number.
- **Stale facts corrected**: the README stage order (now taken from
  `scripts/pipeline.py::STAGES`), the taxonomy count (27 themes, not 28), the
  `gan` family count (seven of nine combined p-values are not p-values, not
  eight of ten), the bundle file list, the experiment statuses for Experiments
  2 and f (their script defects were fixed in 0.4.0), the documented
  invocations of evaluation scripts that take no arguments
  ([D24](./docs/limitations.md#d24)), and the artefact paths those scripts
  actually write ([D25](./docs/limitations.md#d25)).
- **Code references** in the documentation now name a path and a symbol, such
  as `src/scorer/rigor.py::compute_family_significance`, instead of a line. Commit `cc258e4` had broken 23 of them.
- **Language.** This changelog and `CITATION.cff` are now in British English.

### Added

- **Public dataset `v1.0.0`** (`dataset/`): the complete database snapshot,
  with channels, channel posts, and comments from public linked discussion
  groups (commenter identifiers, usernames and text included), plus the
  derived tables of an earlier pipeline run, as a GitHub Release asset pinned
  by SHA-256 in `dataset/manifest.json`, with a datasheet
  (`dataset/DATASHEET.md`).
- `scripts/bootstrap.py` (`make setup`): check prerequisites, fetch and verify
  the dataset, start a local PostgreSQL 17 with Docker Compose
  (`docker-compose.yml`), restore and migrate an empty database (a database
  that holds data is left untouched), run the pipeline, and start the webapp.
  It never reads `.env` and never deletes data. Make targets `setup`, `data`,
  `db-up`, `db-down`, `pipeline` and `webapp`.
- `scripts/pipeline.py`: runs every offline stage in order for one mission or
  all of them, with per-stage timings and `--list`, `--only`, `--from` and
  `--skip-embeddings`.
- `scripts/release_dataset.py`: builds the release artefacts and the manifest
  (maintainers).
- `docs/limitations.md` D18: the snapshot's derived tables come from an earlier
  pipeline run and are recomputed by `scripts/pipeline.py`; only regenerated
  numbers may be cited, and they are not expected to match the archive.

### Changed

- `README.md`, `docs/ops/quickstart.md` and `docs/ops/install.md`: the default
  path is the bootstrap on the public corpus, and Telegram collection moved to
  an optional section. The manual `docker run` instructions gave way to the
  Compose database (`idefix`/`idefix`, `127.0.0.1:5433`, `IDEFIX_DB_PORT`).
- Reproducibility status (`README.md`, `docs/limitations.md`,
  `docs/experiments/README.md`): the corpus is public and rebuildable;
  `docs/experiments/results/` stays empty until figures are regenerated from
  it; the archive stays quarantined.
- `docs/limitations.md` D12 narrowed (the database is now rebuildable, the
  evaluation inputs still are not), and D17 marked partly fixed (families (b)
  and (d) have test files; `rigor.py` has none).
- `docs/method/07-tiers-and-governance.md` and the README governance section
  state that `scripts/enrich_recrawl.py` collects the commenters of public
  linked discussion groups, and that the public dataset includes them. They
  had said that member identifiers were not collected, which was true of
  channel member lists only.

### Fixed

- Stale references: `scripts/crawl.py` (absent from the repository and its
  history; the real collection entry points are now listed in the README),
  `scripts/init_db.py` (removed), environment variable names given only in
  their `TG_*` form, sequential `uv sync --extra` commands that undid each
  other, and statements that D1 and D11 were still open.

### Security

- Dependency updates folded from the open Dependabot pull requests (`6d58bba`).
  Python: aiohttp 3.14.5, anyio 4.14.2, filelock 4.2.4, GitPython 3.2.1,
  opentelemetry-api 1.45.1, Pillow 13.0.0, urllib3 2.8.0 and virtualenv
  21.14.13. Webapp: react-router-dom 7.18.4, Vite 8.3.5, brace-expansion
  5.0.12, source-map-js 1.2.2, and zod 4.6.7 for advisory GHSA-mrhx-c7xc-m3w5
  (a development-only dependency); `npm audit` reported no vulnerabilities
  afterwards.

## [0.4.0] — 2026-09-10

### Normative

Commit `cc258e4` changed the ranking without a methodology version bump at the
time; `METHODOLOGY.md` 0.4.1 is the first cover page that describes it. The
size of the ranking change has not been measured
([`exp-language-prior-ablation.md`](./docs/experiments/exp-language-prior-ablation.md)).

- **D1 fixed: the credibility prior is no longer a language partition.** A
  channel used to be `suspect` if and only if `fr_score < 0.15`, and that prior
  drives the largest severity modulator. It is now `suspect` when it cites
  documented adversary infrastructure (`CITES_DOMAIN` edges into the
  catalogue) or is itself catalogued. `ScoringProfile.suspect_threshold`, a
  language threshold, became `credibility_prior_enabled`, a switch, so `gan`
  keeps its neutral prior.
- **D4 fixed: no discontinuity at zero in the combiner.** Families were dropped
  on the exact equality `p >= 1.0`; they are now dropped in a band,
  `NO_SIGNAL_PVALUE = 0.99`.
- **D7 fixed:** `n_bootstrap` raised from 100 to 1,000. The p-values come from
  `n_null`, so this changes confidence bands, not the ranking.
- **D15b fixed: a channel with no edges no longer scores the maximum in family
  (b).** A degenerate-centrality guard scores it 0.0. The main scoring path had
  masked the bug, but the dossier builder and the archetype classifier were
  exposed to it.

### Editorial

An adversarial pass compared every documented claim against the code. Details
are in the [`METHODOLOGY.md`](./METHODOLOGY.md#version-history) version history
and in [`docs/limitations.md`](./docs/limitations.md).

- **Withdrawn: claims the code contradicted.** Chief among them, the assertion
  that `fr_score` was never used as an anchor: it set
  `credibility_prior = "suspect"` below a threshold, and that prior drives the
  largest severity modulator. Also withdrawn: the weighted-sum description of
  the combiner (the code uses Stouffer with Benjamini–Hochberg), the claim that
  confidence bands propagate from real intervals for every family, and the
  description of family (d) as cross-episode.
- **Withdrawn: every numeric result.** The corpus behind them had been
  decommissioned, so none could be regenerated or falsified. The artefacts
  moved to `archive/2026-06-russosphere/`, which may not be cited.
- **D9 corrected, not fixed.** The audit had the direction of the effect
  backwards: the eigenvector term is not negligible at scale, it dominates
  large corpora. The register now carries the measurements and a test that
  reproduces the crossover.
- `docs/` restructured as a paper: `method/`, `experiments/`, `limitations.md`,
  `reference/`, `ops/` and `product/`. `METHODOLOGY.md` became a versioned
  cover page, and the methodology moved to `docs/method/`.
- `docs/limitations.md`: one register of the permanent limits and the verified
  defects.
- Six falsification protocols under `docs/experiments/`, each with a
  falsification criterion fixed before the run. Two were new: a language-prior
  ablation and a parameter-sensitivity sweep.
- `docs/reference/references.bib`, and a bibliography in which every entry was
  resolved against Crossref or arXiv. Unverifiable entries and references that
  grounded no implemented method were dropped.
- The documentation moved to English, except that
  `docs/reference/glossary.md` keeps French institutional terms in their
  official form.
- Dangling `CLAUDE.md` references across sources, tests and migrations were
  remapped to the documents that now carry that content.

### Added

- `scripts/check_docs.py`, a blocking CI job: no dead links, no number in
  experiment prose without a backing artefact, no citation of the quarantined
  archive.
- Test files for families (b) and (d) (`tests/scorer/test_cascade_role.py`,
  `tests/scorer/test_recidivism.py`), including regression tests for D8 and
  D15b.
- Open-source community health files: `CONTRIBUTING`, `CODE_OF_CONDUCT`,
  `SECURITY`, `CITATION`, and issue and pull-request templates.
- GitHub Actions CI: lint, mypy, and tests with coverage.
- A `pre-commit` configuration (Ruff, file hygiene, `detect-private-key`).
- Badges and a licence notice in the README.

### Changed

- Python 3.14 is the only supported interpreter; the 3.11 and 3.12 matrix was
  dropped.
- Root clean-up: personal scripts and notes moved to `scripts/` and `docs/`.
- `.gitignore` widened (`.env.*`, `_bmad-output/`, `webapp/.vercel/`).
- The Alembic documentation now gives the real head, `0008`.

### Fixed

- D11, both evaluation scripts. `scripts/eval_episode_recovery.py` reported an
  expected hit count as `random_control_recall@k`; the control is now `k/n`,
  the count keeps an honest name, and an underpowered run reports
  `NON CONCLUANT` (inconclusive). `scripts/eval_embedding_discrimination.py`
  embedded channel handles rather than message content; it now calls
  `compute_channel_embeddings`, the function the scorer uses.

### Removed

- **Six modules documented as part of the method but imported only by
  tests:** `pockets`, `registry`, `readiness`, `coordination_fabric`,
  `dossier/v1` and `analytical_contract`, with their documentation.
- **The webapp's science section**: about 160 KB of hand-written TSX that
  duplicated the Markdown and had already drifted from it, with its routes and
  i18n keys.
- **Analyst bundles from version control** (`webapp/public/data/`). They are
  corpus-specific, and publishing them shipped unreproducible numbers. They are
  generated locally by `scripts/export_static.py`.

### Security

- `.env.supabase`, which held a service-role key, removed from version control;
  the key was rotated and purged from the history.
- Dependency floors raised to close Dependabot alerts (`0c1b004`, `d8a567b`):
  GitPython `>=3.1.58` (remote code execution and injection advisories),
  Pillow `>=12.3.0` (heap out-of-bounds reads and decompression bombs),
  aiohttp 3.14.3 (HTTP response parser and WebSocket advisories), setuptools
  `>=83.0.0` (a `MANIFEST.in` exclusion bypass), and the npm overrides PostCSS
  `>=8.5.28`, browserslist `>=4.28.9` and brace-expansion `>=5.0.9` (build
  toolchain only).

## [0.3.0-poc] — 2026-06-29

See the 0.2.0-poc → 0.3.0-poc entry in the
[`METHODOLOGY.md`](./METHODOLOGY.md#version-history) version history: the
semantic score family (f) added to the pipeline (it was described at the time
as wired into the score; it never was, [D19](./docs/limitations.md#d19)),
automatic episode discovery, a traceable multi-source gate (`gate_families`),
a non-circular validation track, and a review of the community snapshots.

## [0.2.0-poc]

An earlier version of the methodology; see
[`METHODOLOGY.md`](./METHODOLOGY.md#version-history).
