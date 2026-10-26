# Contributing to Idéfix

Thank you for your interest. This guide covers how to propose a change: the
workflow, the rules for branches and pull requests, the checks that
continuous integration (CI) runs, and the conventions the project follows.

- [🚀 Set up](#-set-up)
- [🤝 Workflow](#-workflow)
- [🧪 Checks](#checks)
- [📝 Conventions](#-conventions)
- [🔒 Never commit secrets](#-never-commit-secrets)
- [🔒 Data and personal data](#data-and-personal-data)
- [📚 Documentation](#-documentation)

## 🚀 Set up

Follow [`docs/ops/quickstart.md`](./docs/ops/quickstart.md), the one canonical
setup tutorial. It covers the prerequisites, the Python environment, and running
the whole system on the public corpus. When something fails, see
[`docs/ops/troubleshooting.md`](./docs/ops/troubleshooting.md).

You do not need Docker, a database, or Telegram credentials to work on most of
the code: the tests run offline, with network and database access mocked.
Telegram collection is optional and only for extending the corpus; see
[`docs/ops/install.md`](./docs/ops/install.md).

## 🤝 Workflow

1. **Find or open an issue** for anything larger than a small fix, so the
   approach can be agreed before you write the code. Use the issue templates.
2. **Create a branch from `main`.** Name it after the change type:
   `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `chore/…`, `ci/…`, or `build/…`.
3. **Make the change, with a test.** A fix comes with a test that fails without
   it. Keep a pull request to one logical change.
4. **Run the checks locally** (see [Checks](#checks)).
5. **Open a pull request against `main`.** Fill in the template, and link the
   issue it closes.
6. **Get CI green and a review.** The maintainer reviews and merges; nothing is
   pushed to `main` directly.

Install the pre-commit hooks once, so that the most common problems are caught
before each commit:

```bash
uv run --extra dev pre-commit install
```

The hooks run ruff (lint with fixes, then format), fix trailing whitespace and
missing final newlines, and reject large files, private keys, and unresolved
merge-conflict markers. Their configuration is in
[`.pre-commit-config.yaml`](./.pre-commit-config.yaml).

<a id="checks"></a>

## 🧪 Checks

The checks in `ci.yml` run on every pull request, and those in `ui-gate.yml`
when the web app changes. All of them are blocking; reproduce them locally
before you push.

### Python and documentation (`ci.yml`)

CI installs the full environment, with every extra the tests touch:

```bash
uv sync --extra dev --extra llm --extra embed
```

| CI job | What it checks | Local command |
|---|---|---|
| `test`, lint step | ruff lint on `src/` and `tests/` | `uv run ruff check src/ tests/` |
| `test`, type-check step | mypy on `src/` | `uv run mypy src/ --ignore-missing-imports` |
| `test`, tests step | pytest with coverage on Python 3.14 | `uv run --extra dev python -m pytest` |
| `docs` | documentation integrity (links, anchors, unbacked numbers, archive citations, and the rules in its docstring) | `uv run --no-project python scripts/check_docs.py` |

The test suite passes without the `llm` extra, so `uv sync --extra dev` is
enough to run it. To format the code, run:

```bash
uv run ruff format src/ tests/
```

Where Make is available, `make fmt`, `make lint`, and `make test` wrap these
commands.

### Web app (`ui-gate.yml`)

These jobs run only when a pull request changes `webapp/` or the workflow file
itself. Run them from `webapp/`; the commands are described in
[`webapp/README.md`](./webapp/README.md).

| CI job | What it checks | Local command |
|---|---|---|
| `typecheck` | TypeScript, no emit | `npm run typecheck` |
| `i18n-parity` | every locale has every key, and no value is empty, marked `__MISSING__`, or has drifted placeholders | `npm run i18n:parity` |
| `lint` | ESLint | `npm run lint` |
| `ui-contract` | design-system ratchet: violation counts may only go down from `webapp/ui-contract-baseline.json` | `npm run ui:contract` |
| `e2e` | Playwright smoke tests in Chromium, on a synthetic bundle | `npm run test:e2e` |

The `e2e` job first generates the synthetic bundle with
`uv run --no-project python scripts/make_fixture_bundle.py`. A `visual` job is
a placeholder that always passes.

### End-to-end reproduction (`reproduce.yml`)

A heavier workflow runs every Monday and on demand, not on pull requests: on a
clean machine, it fetches the pinned dataset, restores it, runs every offline
pipeline stage, and builds the web app on the regenerated bundle. A change to
the bootstrap, the pipeline, or the migrations should keep it green; the
maintainer can run it from the Actions tab.

## 📝 Conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `ci:`, `build:`, and so on,
  as in the existing history.
- **Commit email.** Commit with the email address linked to your GitHub
  account; otherwise the Vercel deployment is blocked.
- **Python style** is ruff (format and lint, line length 100) and mypy,
  configured in [`pyproject.toml`](./pyproject.toml).
- **Documentation style** is set out in [`docs/STYLE.md`](./docs/STYLE.md):
  Oxford British English, code cited by path and symbol (as in
  `src/missions/loader.py::add_mission_arg`) rather than by line number, and
  known defects recorded in [`docs/limitations.md`](./docs/limitations.md).
- **Scripts.** Every script has a section in
  [`scripts/README.md`](./scripts/README.md). Add one when you add a script,
  and update it when you change a script's flags.

## 🔒 Never commit secrets

No key, token, or session string may enter the repository. `.env*` files are
ignored by git, except `.env.example`; the `detect-private-key` hook runs on
every commit; and the static export scrubs secrets
(`tests/test_export_secret_scrub.py`). If a secret is committed by mistake,
follow [`SECURITY.md`](./SECURITY.md).

<a id="data-and-personal-data"></a>

## 🔒 Data and personal data

- **Never commit collected data or analyst bundles** (`webapp/public/data/`).
  They are specific to one corpus and one run. The reference corpus is
  published as a versioned GitHub Release, pinned by SHA-256 in
  [`dataset/manifest.json`](./dataset/manifest.json).
- **Quote only numbers you regenerated.** The derived tables restored with the
  snapshot come from an earlier pipeline run; cite figures only after running
  `scripts/pipeline.py` yourself
  ([`docs/limitations.md`](./docs/limitations.md#d18)).

> [!CAUTION]
> The public dataset contains the `comments` table: the Telegram identifier,
> username, and text of private individuals who commented in public discussion
> groups. Never copy any of it into the repository, a test fixture, a
> screenshot, an issue, or a pull request. Use synthetic data instead
> (`scripts/make_fixture_bundle.py`). The terms of use are in
> [`dataset/DATASHEET.md`](./dataset/DATASHEET.md).

## 📚 Documentation

[`README.md`](./README.md) is the engineering guide;
[`METHODOLOGY.md`](./METHODOLOGY.md) is the versioned scientific
specification; [`docs/`](./docs/README.md) holds the detailed documentation;
and [`dataset/DATASHEET.md`](./dataset/DATASHEET.md) describes the public
corpus. Update them when your change affects them.

By taking part, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).
