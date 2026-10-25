# Install guide

Full installation on a development machine: Python environment, database,
pipeline, analyst interface — and, optionally, Telegram collection.

For the one-command path, see [`quickstart.md`](./quickstart.md). This page
describes the same steps by hand, plus the alternatives.

## Prerequisites

| Tool | Version | Role |
|---|---|---|
| Python | >= 3.14 | Analytical pipeline (uv can install it) |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| Node.js | 20.19+ or 22.12+ | Analyst interface (Vite) |
| Docker with Compose v2 | Compose 2.17+ | Local PostgreSQL 17 |
| Telegram account | — | **Optional.** Only to collect your own data |

### Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install Node.js

From [nodejs.org](https://nodejs.org/) (LTS recommended) or via a version
manager (`nvm`, `fnm`, `volta`).

## 1. Clone

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
```

## 2. Python environment

```bash
uv sync --extra embed --extra dev    # embedding stages + development tooling
```

`.venv/` is created at the repository root. Name every extra you want in one
command: `uv sync` removes the extras it is not given. Available extras:

| Extra | For |
|---|---|
| `embed` | Embedding-based pipeline stages (sentence-transformers, PyTorch) |
| `dev` | Tests, lint, type checks, pre-commit |
| `session` | Generating a Telegram session string (collection only) |
| `llm` | Optional LLM classification track (paid Mistral API) |

`uv run --extra embed ...`, as the bootstrap examples use, installs the extra on
the fly.

> **Windows:** prefix Python commands with `$env:PYTHONUTF8="1"` (PowerShell) or
> `set PYTHONUTF8=1` (cmd) so that channel titles and accented characters print
> correctly.

## 3. Database — local PostgreSQL via Docker Compose (default)

Idéfix targets PostgreSQL 17. The repository ships a Compose file for a local
instance: [`../../docker-compose.yml`](../../docker-compose.yml), project
`idefix`, service `db`, image `postgres:17-alpine`.

| Setting | Value |
|---|---|
| User / password / database | `idefix` / `idefix` / `idefix` — local only |
| Port | `127.0.0.1:5433` (loopback only); override with `IDEFIX_DB_PORT` |
| Data | named Docker volume |
| Dataset files | `./dataset/downloads` mounted read-only at `/dataset` |
| `DATABASE_URL` | `postgresql+asyncpg://idefix:idefix@localhost:5433/idefix` |

The bootstrap drives it:

```bash
uv run python scripts/bootstrap.py fetch   # download + verify the public corpus
uv run python scripts/bootstrap.py db      # start; restore + migrate an empty database
```

`db` starts the Compose service and waits for the healthcheck. If the
database is empty, it restores the database file from `dataset/downloads/` and
then runs `alembic upgrade head`, which applies the additive migrations that
postdate the snapshot (it predates `0007` and `0008`). It migrates only right
after its own restore: a database that already holds data is left untouched —
no restore, no migration — and if its schema is behind, `db` prints the
`alembic upgrade head` command for you to run. The bootstrap never deletes
data. Make equivalents: `make data`, `make db-up`, `make db-down`
(`docker compose stop`: stops the container, keeps its data).

The bootstrap passes `DATABASE_URL` to its own child processes and never reads
`.env`. To run a script or Alembic yourself, either copy `.env.example` to
`.env` (its default is the local database) or set the variable in the
environment — an explicit environment variable wins over `.env`:

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
# PowerShell: $env:DATABASE_URL="postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"

uv run alembic current      # must print: 0008 (head)
```

What the restored database contains is described in
[`../../dataset/DATASHEET.md`](../../dataset/DATASHEET.md). In short, the
complete snapshot: channels, channel posts, and the `comments` table with
commenter identifiers, usernames and text — personal data, see the datasheet's
terms of use — plus the derived tables of an earlier pipeline run. Those
derived values are not results: the pipeline (§4) recomputes them, and only
regenerated numbers may be cited ([`../limitations.md`](../limitations.md)
D18).

> **Managed alternative.** Any PostgreSQL 17 works. With
> [Supabase](https://supabase.com), take the connection string from
> *Dashboard → Connect → Session pooler*, keep the `+asyncpg` driver suffix, and
> use it as `DATABASE_URL`. Restore the corpus yourself
> (`pg_restore --no-owner --no-privileges` into an empty database, from the file
> the `fetch` step verified), then `uv run alembic upgrade head`. Do not run the
> bootstrap's `db` step against it — that step manages the local Compose
> database only.

### Empty database instead of the corpus

To start from an empty schema (for example before collecting your own data),
start the database without the bootstrap, so that nothing is restored, and
apply the migrations only:

```bash
docker compose --env-file /dev/null up -d db    # PowerShell / cmd: --env-file nul
uv run alembic upgrade head                     # with DATABASE_URL set as above
```

`--env-file` keeps Compose away from `.env`, as the bootstrap and the Makefile
do. A later `bootstrap.py db` keeps this database as it is, since it is not
empty.

This creates `channels`, `messages`, `edges`, `channel_scores` and the rest,
through migration `0008`. Migration reference: [`migrations.md`](./migrations.md).

## 4. Pipeline

```bash
uv run --extra embed python scripts/bootstrap.py pipeline   # all missions, local DB injected
make pipeline MISSION=russosphere                          # same, one mission
# or directly, with DATABASE_URL set:
uv run --extra embed python scripts/pipeline.py --mission russosphere --list
uv run --extra embed python scripts/pipeline.py --mission russosphere
```

`scripts/pipeline.py` runs every offline stage in order — no Telegram, no paid
API — and stops at the first failure. `--only STAGE` and `--from STAGE` select
stages; `--skip-embeddings` skips the stages that need the `embed` extra. The
embedding stages download a sentence-transformers model from the Hugging Face
hub on first use.

The pipeline overwrites the derived tables restored from the snapshot, with two
caveats recorded in [`../limitations.md`](../limitations.md) D18: scores are
rewritten only for the missions it runs, and `build_edges` upserts without
deleting edges the earlier run alone produced.

The stages themselves are documented one by one in
[`../../scripts/README.md`](../../scripts/README.md).

## 5. Analyst interface

```bash
cd webapp
npm ci
npm run dev        # http://localhost:5173

npm run build      # static build -> webapp/dist/
npm run preview    # preview the production build
```

The webapp reads JSON bundles from `webapp/public/data/<mission>/`. **Those
bundles are not in the repository** — they are corpus- and run-specific and are
generated by the pipeline (`export_static` and `build_stories` stages). Until
the pipeline has run, the interface has nothing to display.

`uv run python scripts/bootstrap.py webapp` does the same as `npm ci` (when
needed) followed by `npm run dev`.

## 6. Verify the installation

```bash
uv run --extra dev python -m pytest         # offline test suite
cd webapp && npx tsc --noEmit && cd ..      # strict typecheck
uv run python scripts/check_docs.py         # documentation integrity
uv run alembic current                      # database connectivity (DATABASE_URL set)
```

Before interpreting any output, read
[`../limitations.md`](../limitations.md) — several defects materially affect how
the ranking should be read.

## Optional: collect your own data from Telegram

Nothing above needs this. Collection is the only part of the system that
contacts Telegram. Data you collect is added to whatever database
`DATABASE_URL` points at; once you collect into the restored corpus, the
database is no longer dataset `v1.0.0` and its results are not comparable with
results computed from the public corpus.

Collection uses **MTProto**, read-only, public channels only.

> **Use a dedicated account**, separate from your personal one. It must never be
> used concurrently from elsewhere — that risks `FLOOD_WAIT` and account bans.
> Run one collection script at a time.

### Environment variables

Collection scripts read `.env` (via `python-dotenv`). Create it from the
template:

```bash
cp .env.example .env
```

```dotenv
TELEGRAM_API_ID=<your-api-id>
TELEGRAM_API_HASH=<your-api-hash>
TELEGRAM_SESSION_STRING=<generated below>
TELEGRAM_PHONE_NUMBER=+33XXXXXXXXX
```

The legacy names `TG_API_ID`, `TG_API_HASH`, `TG_SESSION_STRING`, `TG_PHONE` are
still honoured; the `TELEGRAM_*` names take precedence
(`src/ingestor/session.py`).

`DATABASE_URL` decides where collected data lands. The `.env.example` default
is the local Compose database; an explicit environment variable wins over
`.env`.

Optional:

```dotenv
MISTRAL_API_KEY=<mistral-key>   # only with uv sync --extra llm (paid API)
LOG_LEVEL=INFO
```

### API_ID and API_HASH

1. Go to **[my.telegram.org](https://my.telegram.org)**
2. Sign in with the dedicated account's phone number
3. Open **API development tools**
4. Fill the form — *App title*: `Idefix`, *Short name*: `idefix`,
   *Platform*: `Other`
5. **Create application**
6. Copy `App api_id` into `TELEGRAM_API_ID`
7. Copy `App api_hash` into `TELEGRAM_API_HASH`

These credentials are tied to your Telegram account. **Never commit them.**
`.env` is gitignored.

### Session string

A persistent token that avoids re-authenticating on every restart.

```bash
make session
# equivalent: uv run --extra session streamlit run scripts/session_web.py --server.port 8502
```

Open [http://localhost:8502](http://localhost:8502):

1. Enter the phone number in international format (`+33...`)
2. Enter the code received by SMS or in the Telegram app
3. If 2FA is enabled, enter the password
4. Copy the displayed session string into `TELEGRAM_SESSION_STRING`

> The session string is a secret. Treat it as a password — it grants read access
> to the account. It is scrubbed from every export by key and by value.

### Collect, then recompute

```bash
uv run python scripts/backfill.py --channel @France24_fr --limit 500   # one channel
make pipeline MISSION=russosphere                                      # recompute
# without make: uv run --extra embed python scripts/bootstrap.py pipeline --mission russosphere
```

`make pipeline` and `bootstrap.py pipeline` target the local Compose database.
If you collected into another database, run `scripts/pipeline.py` directly with
that `DATABASE_URL` in the environment.

The other entry points — seed set, bounded snowball crawl, France–Ukraine
campaign, paced long-running backfill, enrichment re-crawl — are listed in the
[README](../../README.md#8-collect-your-own-data-optional-advanced) and
documented in [`../../scripts/README.md`](../../scripts/README.md).

`scripts/enrich_recrawl.py` also collects **commenters** of public linked
discussion groups (`comments` table): identifiers and text of private
individuals. That is personal data, subject to the governance rules of
[`../method/07-tiers-and-governance.md`](../method/07-tiers-and-governance.md)
§7.3.

## Common problems

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` on port 5433 | Compose database stopped | `make db-up`, or `uv run python scripts/bootstrap.py db` |
| Port 5433 already in use | Another service holds it | `IDEFIX_DB_PORT=<port>` for both the bootstrap and your `DATABASE_URL` |
| A script writes to the wrong database | `.env` holds another `DATABASE_URL` | Set `DATABASE_URL` explicitly in the environment; it wins over `.env` |
| `FLOOD_WAIT` during collection | Too many Telegram requests | Wait out the stated delay; never parallelize sessions |
| `ModuleNotFoundError: sentence_transformers` | `embed` extra not installed | `uv sync --extra embed`, or `--skip-embeddings` |
| `alembic current` shows an old revision | Migrations incomplete | `uv run alembic upgrade head` |
| Blank page in the webapp | No JSON bundle generated yet | Run the pipeline (§4) |
| Broken UTF-8 output on Windows | Missing env var | `$env:PYTHONUTF8="1"` before each command |

More, for the one-command path: [`quickstart.md`](./quickstart.md#troubleshooting).
