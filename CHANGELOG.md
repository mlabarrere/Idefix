# Changelog

Toutes les évolutions notables de ce projet sont consignées ici.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet suit
[Semantic Versioning](https://semver.org/lang/fr/). La spécification scientifique et ses
« change records » détaillés vivent dans [`METHODOLOGY.md`](./METHODOLOGY.md).

## [Unreleased]

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
- CI GitHub Actions (lint + mypy + tests sur Python 3.11 & 3.12, avec couverture).
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
