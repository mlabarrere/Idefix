# Contribuer à Idéfix

Merci de votre intérêt. Ce document décrit comment configurer l'environnement, valider vos
changements et proposer une contribution.

## Prérequis

- **Python ≥ 3.11** (CI testée sur 3.11 et 3.12)
- **[uv](https://docs.astral.sh/uv/)** — gestionnaire de paquets et d'environnement Python
- **Node.js ≥ 20** — uniquement pour la webapp (`webapp/`)

## Mise en route

```bash
uv sync --extra dev --extra llm --extra embed   # environnement + dépendances (dont extras de test)
make test                                        # doit être vert avant de commencer
```

Les tests tournent **hors-ligne** : aucune base Postgres, Redis ou Supabase live n'est requise
(les accès réseau/DB sont mockés).

## Workflow

1. Créez une branche depuis `main` (`feat/…`, `fix/…`, `docs/…`, `chore/…`).
2. Faites vos changements ; ajoutez un test qui échoue sans votre correctif.
3. Vérifiez localement :
   ```bash
   make fmt     # ruff format + autofix
   make lint    # ruff check + mypy
   make test    # pytest
   ```
4. Ouvrez une PR. La **CI doit être verte** (lint + mypy + tests sur 3.11 & 3.12).

Installez les hooks pour attraper les erreurs avant le commit :
```bash
uv run pre-commit install
```

## Conventions

- **Commits** : [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`…) — c'est déjà la convention de l'historique.
- **Style** : ruff (format + lint) et mypy, configurés dans [`pyproject.toml`](./pyproject.toml).
- **⚠️ Email de commit** : vos commits doivent utiliser l'email associé à votre compte GitHub,
  sinon le déploiement Vercel est bloqué.

## Ne jamais committer de secrets

Aucune clé, token ou session ne doit entrer dans le dépôt. `.env*` est gitignoré (sauf
`.env.example`), un hook `detect-private-key` est actif, et l'export scrube les secrets
(cf. `tests/test_export_secret_scrub.py`). Voir [SECURITY.md](./SECURITY.md) pour signaler
une fuite.

## Documentation

Le README est le guide d'ingénierie ; [`METHODOLOGY.md`](./METHODOLOGY.md) est la spécification
scientifique versionnée ; [`docs/`](./docs/) contient la doc détaillée (indexée par
[`docs/README.md`](./docs/README.md)). Mettez-les à jour si votre changement les concerne.
