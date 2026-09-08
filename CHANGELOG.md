# Changelog

Toutes les évolutions notables de ce projet sont consignées ici.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet suit
[Semantic Versioning](https://semver.org/lang/fr/). La spécification scientifique et ses
« change records » détaillés vivent dans [`METHODOLOGY.md`](./METHODOLOGY.md).

## [Unreleased]

### Added
- Fichiers de santé communautaire OSS : `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `CITATION`,
  templates d'issues/PR.
- CI GitHub Actions (lint + mypy + tests sur Python 3.11 & 3.12, avec couverture).
- Configuration `pre-commit` (ruff, hygiène de fichiers, `detect-private-key`).
- Badges et mention de licence dans le README ; manifeste des skills (`docs/agent-skills.md`).

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
