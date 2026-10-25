# Contribuer à Idéfix

Merci de votre intérêt. Ce document décrit comment configurer l'environnement, valider vos
changements et proposer une contribution.

## Prérequis

- **Python ≥ 3.14** (version unique, testée en CI)
- **[uv](https://docs.astral.sh/uv/)** — gestionnaire de paquets et d'environnement Python
- **Node.js 20.19+ ou 22.12+** avec npm — pour la webapp (`webapp/`)
- **Docker avec Compose v2** — uniquement pour faire tourner le système complet sur le corpus
  public (base PostgreSQL 17 locale) ; inutile pour les tests

## Mise en route

```bash
uv sync --extra dev --extra llm --extra embed   # environnement + dépendances (dont extras de test)
make test                                        # doit être vert avant de commencer
```

Les tests tournent **hors-ligne** : aucune base Postgres, Redis ou Supabase live n'est requise
(les accès réseau/DB sont mockés).

`uv sync` retire les extras qu'on ne lui nomme pas : nommez-les tous dans la même commande.

### Faire tourner le système complet

Pour voir l'effet d'un changement de bout en bout, sur le corpus public (dataset `v1.0.0`),
sans identifiants Telegram :

```bash
uv run --extra embed python scripts/bootstrap.py   # ou : make setup
```

Une seule commande : téléchargement vérifié du dataset, PostgreSQL 17 local via Docker Compose,
restauration, migrations, pipeline hors-ligne (`scripts/pipeline.py`), webapp sur
<http://localhost:5173>. La relancer est sans risque. Pour rejouer seulement le pipeline après
une modification : `make pipeline` (ou `bootstrap.py pipeline`), qui l'exécute toujours.
Détails et dépannage : [`docs/ops/quickstart.md`](./docs/ops/quickstart.md).

Le bootstrap ne lit jamais `.env`. Pour lancer un script à la main contre la base locale,
copiez `.env.example` en `.env` (sa valeur par défaut est la base locale) ou exportez
`DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix`.

La collecte Telegram est **optionnelle** et réservée à qui veut étendre le corpus : voir
[`docs/ops/install.md`](./docs/ops/install.md). Ni les tests ni le système complet sur le
corpus public n'en ont besoin.

## Workflow

1. Créez une branche depuis `main` (`feat/…`, `fix/…`, `docs/…`, `chore/…`).
2. Faites vos changements ; ajoutez un test qui échoue sans votre correctif.
3. Vérifiez localement :
   ```bash
   make fmt     # ruff format + autofix
   make lint    # ruff check + mypy
   make test    # pytest
   ```
4. Ouvrez une PR. La **CI doit être verte** (lint + mypy + tests sur 3.14).

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
[`docs/README.md`](./docs/README.md)) ; [`dataset/DATASHEET.md`](./dataset/DATASHEET.md) décrit
le corpus public. Mettez-les à jour si votre changement les concerne.

`uv run python scripts/check_docs.py` est un contrôle bloquant en CI : aucun lien mort, aucun
chiffre dans la prose des expériences sans artefact sous `docs/experiments/results/`, aucune
citation de l'archive en quarantaine.

## Données

- **Ne committez jamais de données collectées** ni de bundles d'analyse
  (`webapp/public/data/`) : ils sont propres à un corpus et à une exécution. Le corpus de
  référence est publié comme release versionnée, épinglée par SHA-256 dans
  [`dataset/manifest.json`](./dataset/manifest.json).
- **Données personnelles.** Le dataset public contient la table `comments` : identifiants,
  pseudonymes et textes de commentateurs, personnes physiques. N'en copiez rien dans le dépôt
  (fixtures, tests, captures, issues) ; utilisez des données synthétiques
  (`scripts/make_fixture_bundle.py`). Conditions d'utilisation :
  [`dataset/DATASHEET.md`](./dataset/DATASHEET.md).
- **Chiffres.** Les tables dérivées restaurées avec l'instantané viennent d'une exécution
  antérieure du pipeline : ne citez que des chiffres régénérés par `scripts/pipeline.py`
  ([`docs/limitations.md`](./docs/limitations.md), D18).
