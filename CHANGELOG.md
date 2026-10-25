# Changelog

Toutes les évolutions notables de ce projet sont consignées ici.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet suit
[Semantic Versioning](https://semver.org/lang/fr/). La spécification scientifique et ses
« change records » détaillés vivent dans [`METHODOLOGY.md`](./METHODOLOGY.md).

## [Unreleased]

### Reproducible setup on the public corpus (2026-10)

A third party can now clone the repository and, with one command and no
Telegram credentials, get the previously collected corpus in a local database,
the full offline pipeline recomputed from it, and the analyst interface
running. Collection becomes an optional, advanced path.

#### Added
- **Public dataset `v1.0.0`** (`dataset/`): the complete database snapshot —
  channels, channel posts, and comments from public linked discussion groups
  (commenter identifiers, usernames and text included), plus the derived
  tables of an earlier pipeline run — as a GitHub Release asset, pinned by
  SHA-256 in `dataset/manifest.json`, with a datasheet
  (`dataset/DATASHEET.md`).
- `scripts/bootstrap.py` (`make setup`): check prerequisites, fetch and verify
  the dataset, start a local PostgreSQL 17 with Docker Compose
  (`docker-compose.yml`), restore and migrate an empty database (a database
  that holds data is left untouched), run the pipeline, start the webapp.
  Never reads `.env`, never deletes data. Make targets `setup`, `data`, `db-up`, `db-down`,
  `pipeline`, `webapp`.
- `scripts/pipeline.py`: runs every offline stage in order for one mission or
  all of them, with per-stage timings and `--list` / `--only` / `--from` /
  `--skip-embeddings`.
- `scripts/release_dataset.py`: builds the release artefacts and the manifest
  (maintainers).
- `docs/limitations.md` **D18**: the snapshot's derived tables come from an
  earlier pipeline run and are recomputed by `scripts/pipeline.py`; only
  regenerated numbers may be cited, and they are not expected to match the
  archive.

#### Changed
- `README.md`, `docs/ops/quickstart.md`, `docs/ops/install.md`: the default
  path is the bootstrap on the public corpus; Telegram collection moved to an
  optional section. Manual `docker run` instructions removed in favour of the
  Compose database (`idefix`/`idefix`, `127.0.0.1:5433`, `IDEFIX_DB_PORT`).
- Reproducibility status (`README.md`, `docs/limitations.md` Part III,
  `docs/experiments/README.md`): the corpus is public and rebuildable;
  `docs/experiments/results/` stays empty until figures are regenerated from
  it; the archive stays quarantined.
- `docs/limitations.md` D12 narrowed (the database is now rebuildable, the
  evaluation inputs still are not) and D17 marked partly fixed (families (b)
  and (d) have test files; `rigor.py` has none).
- `docs/method/07-tiers-and-governance.md` and the README governance section
  now state that commenters of public linked discussion groups are collected
  by `scripts/enrich_recrawl.py`, and that the public dataset includes them.
  They previously said member identifiers were not collected, which was true
  of channel member lists only.

#### Fixed
- Stale references: `scripts/crawl.py` (absent from the repository and its
  history; the real collection entry points are now listed in the README),
  `scripts/init_db.py` (removed), the `TG_*`-only variable names, sequential `uv sync --extra` commands that undo
  each other, and statements that D1 and D11 were still open.

### Documentation audit (2026-09-10)

An adversarial pass compared every documented claim against the code. Details in
[`METHODOLOGY.md`](./METHODOLOGY.md) version history and
[`docs/limitations.md`](./docs/limitations.md).

#### Removed
- **Claims the code contradicts.** Chief among them the assertion that `fr_score`
  was never used as an anchor: it sets `credibility_prior = "suspect"` below a
  threshold, and that prior drives the largest severity modulator. Also withdrawn:
  the weighted-sum description of the combiner (the code uses Stouffer + BH),
  the claim that confidence bands propagate from real intervals for all families,
  and the description of family (d) as cross-episode.
- **Every numeric result.** The corpus behind them was decommissioned, so none can
  be regenerated or falsified. Artefacts moved to `archive/2026-06-russosphere/`
  with an explicit prohibition on citing them.
- **The webapp science section** (~160 KB of hand-written TSX duplicating the
  Markdown, already drifted from it) and its routes and i18n keys.
- **Six modules documented as part of the method but imported only by tests:**
  `pockets`, `registry`, `readiness`, `coordination_fabric`, `dossier/v1`,
  `analytical_contract` — with their documentation.
- **Analyst bundles from version control** (`webapp/public/data/`). They are
  corpus-specific; publishing them shipped unreproducible numbers. Files remain
  on disk and are generated locally by `scripts/export_static.py`.

#### Added
- `docs/` restructured as a paper: `method/`, `experiments/`, `limitations.md`,
  `reference/`, `ops/`, `product/`.
- `docs/limitations.md` — one register of 6 permanent limits and 17 verified
  defects, each with a `file:line` reference.
- Six falsification protocols under `docs/experiments/`, each with a
  falsification criterion fixed before the run. Two are new: a language-prior
  ablation and a parameter-sensitivity sweep.
- `docs/reference/references.bib`, and a bibliography in which every entry was
  resolved against Crossref or arXiv. Unverifiable entries and references
  grounding no implemented method were dropped.
- `scripts/check_docs.py`, wired into CI as a blocking job: no dead links, no
  number in experiment prose without a backing artefact, no citation of the
  quarantined archive.

#### Changed
- Documentation is now in English, except that `docs/reference/glossary.md`
  preserves French institutional terms in their official form.
- `METHODOLOGY.md` is a versioned cover page; the methodology lives in
  `docs/method/`.
- Dangling `CLAUDE.md` references across sources, tests and migrations remapped
  to the documents that now carry that content.

### Added
- Fichiers de santé communautaire OSS : `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `CITATION`,
  templates d'issues/PR.
- CI GitHub Actions (lint + mypy + tests avec couverture ; Python 3.14 seul depuis l'abandon de
  la matrice 3.11/3.12).
- Configuration `pre-commit` (ruff, hygiène de fichiers, `detect-private-key`).
- Badges et mention de licence dans le README.

### Changed
- Nettoyage de la racine : scripts/notes personnels déplacés vers `scripts/` et `docs/`.
- `.gitignore` élargi (`.env.*`, `_bmad-output/`, `webapp/.vercel/`).
- Documentation Alembic mise à jour (head réel `0008`).

### Security
- Retrait du fichier `.env.supabase` (clé service-role) du suivi ; clé rotée et purgée de
  l'historique.

## [0.3.0-poc] — 2026-06-29

Voir le *change record* 0.2.0 → 0.3.0 dans [`METHODOLOGY.md`](./METHODOLOGY.md) : famille de score
sémantique (f) branchée au scoring, découverte automatique d'épisodes, gate multi-sources traçable
(`gate_families`), piste de validation non-circulaire, relecture des snapshots communautaires.

## [0.2.0-poc]

Version antérieure de la méthodologie (voir `METHODOLOGY.md`).
