# Install guide: manual setup

This guide is for setups that the [quickstart](./quickstart.md) does not cover:
choosing Python extras, using a managed or external PostgreSQL instead of the
local Docker database, starting from an empty schema, running each part by
hand, and collecting your own data from Telegram.

It describes Idéfix version 0.4.1. For a first installation, follow the
quickstart: it is the tested path, and this guide links to it for every step
the two share.

## Contents

- [Prerequisites](#prerequisites)
- [Python environment and extras](#python-environment-and-extras)
- [Database](#database)
  - [Local PostgreSQL in Docker (default)](#local-postgresql-in-docker-default)
  - [Managed or external PostgreSQL](#managed-or-external-postgresql)
  - [Empty schema instead of the corpus](#empty-schema-instead-of-the-corpus)
- [Pipeline](#pipeline)
- [Analyst interface](#analyst-interface)
- [Verify the installation](#verify-the-installation)
- [Optional: collect your own data from Telegram](#optional-collect-your-own-data-from-telegram)
- [Problems](#problems)

## Prerequisites

The same tools as the quickstart: Git, `uv`, Node.js, and Docker. Install them
as [Install the prerequisites](./quickstart.md#install-the-prerequisites)
describes for your system, including the proxy and synchronized-folder notes.
Docker is optional if you use a [managed database](#managed-or-external-postgresql).

## Python environment and extras

The base install covers the offline pipeline, the database migrations, and the
export. Optional extras add the rest:

| Extra | Installs | Needed for | Notes |
|---|---|---|---|
| `embed` | sentence-transformers, PyTorch | The pipeline's embedding stage | About 1 GB on Windows, 3 GB on Linux; downloads a 458 MB model on first use |
| `dev` | pytest, Ruff, mypy, pre-commit | Tests, linting, type checks | |
| `llm` | Mistral client, HTTPX | The optional Mistral classification scripts, which the pipeline does not run | Paid application programming interface (API); needs `MISTRAL_API_KEY` |
| `collect` | Hydrogram, TgCrypto | [Telegram collection](#optional-collect-your-own-data-from-telegram) | Needs a C compiler: TgCrypto has no wheel for Python 3.14 |
| `session` | Streamlit | The session-string generator (`make session`) | Use with `collect` |

Common combinations:

| Purpose | Command |
|---|---|
| Development (tests, lint) | `uv sync --extra dev` |
| The quickstart's public-corpus path | `uv sync --extra embed --extra dev` |
| Everything continuous integration (CI) installs | `uv sync --extra dev --extra llm --extra embed` |
| Telegram collection | `uv sync --extra dev --extra embed --extra collect --extra session` |

`uv sync` installs exactly what you name and **removes** extras you leave out,
so name every extra you want in one command. `uv run --extra embed ...`, by
contrast, adds an extra for that command without removing the others.

`.venv/` is created at the repository root. To keep it elsewhere (for example
outside a synchronized folder), set `UV_PROJECT_ENVIRONMENT` before
`uv sync`.

Run the tests with:

```bash
uv run --extra dev python -m pytest
```

They pass without the `llm` extra.

## Database

Idéfix targets PostgreSQL 17. All scripts read the connection string from
`DATABASE_URL`, which must keep the `+asyncpg` driver suffix (Alembic and the
scripts use the asynchronous driver only).

Scripts read `DATABASE_URL` from the environment or from a `.env` file at the
repository root; a variable set in the environment wins. The bootstrap is the
exception: it never reads `.env` and always uses the local Docker database.

### Local PostgreSQL in Docker (default)

[`docker-compose.yml`](../../docker-compose.yml) defines one service, `db`:

| Setting | Value |
|---|---|
| Compose project | `idefix`, whatever folder the clone is in |
| Image | `postgres:17-alpine` |
| User, password, and database | `idefix`, `idefix`, `idefix` (local only) |
| Port | `127.0.0.1:5433` (loopback only); change it with `IDEFIX_DB_PORT` |
| Data | Docker volume `idefix_pgdata` |
| Dataset files | `./dataset/downloads`, mounted read-only at `/dataset` |
| `DATABASE_URL` | `postgresql+asyncpg://idefix:idefix@localhost:5433/idefix` |

Because the project name is fixed, every clone on a machine shares this one
database ([details](./troubleshooting.md#shared-database)).

To fetch, start, and restore it, follow quickstart
[step 4](./quickstart.md#step-4) and [step 5](./quickstart.md#step-5). The `db`
step restores the corpus and runs `alembic upgrade head` only when the database
is empty. A database that already holds data is left as it is, with no restore
and no migration; if its schema is behind, `db` prints the
`alembic upgrade head` command for you to run. The corpus dump is already at
the latest revision, `0008`.

To run Alembic or a script yourself against this database, set the variable in
the terminal:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
uv run alembic current
```

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
uv run alembic current
```

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
0008 (head)
```

Alternatively, copy `.env.example` to `.env`; its default is the same local URL.

### Managed or external PostgreSQL

Any PostgreSQL 17 server works: a managed service such as
[Supabase](https://supabase.com), or a server you run. The bootstrap's `db` and
`pipeline` steps manage the local Docker database only, so with an external
server you restore, migrate, and run the pipeline yourself.

> [!CAUTION]
> The corpus contains personal data: the `comments` table holds the
> identifiers, usernames, and messages of private individuals. Restoring it on
> a hosted server makes you responsible for that copy. Read the terms of use
> in the [datasheet](../../dataset/DATASHEET.md) first.

You need:

- an **empty** database and a role that may create tables in it;
- the dump, downloaded and verified by
  `uv run python scripts/bootstrap.py fetch` (quickstart [step 4](./quickstart.md#step-4));
- `pg_restore` 17 or later. If you do not have it, run it from the
  `postgres:17-alpine` image as below.

The examples use a server at `db.example.org`, a database `idefix`, and a
role `idefix_owner` with the password `S3cret-Example`; use your own values.

**1. Restore the dump.** `pg_restore` takes a plain libpq URL, without
`+asyncpg`:

```powershell
docker run --rm -v "${PWD}/dataset/downloads:/dataset:ro" postgres:17-alpine pg_restore --no-owner --no-privileges --dbname "postgresql://idefix_owner:S3cret-Example@db.example.org:5432/idefix?sslmode=require" /dataset/idefix-corpus-v1.0.0.dump
```

```bash
docker run --rm -v "$PWD/dataset/downloads:/dataset:ro" postgres:17-alpine pg_restore --no-owner --no-privileges --dbname "postgresql://idefix_owner:S3cret-Example@db.example.org:5432/idefix?sslmode=require" /dataset/idefix-corpus-v1.0.0.dump
```

The only error you may see is `schema "public" already exists`, which is
harmless: the dump re-creates a schema that every new database already has.

**2. Point Idéfix at the server and check the schema.** For the asynchronous
driver, the URL keeps `+asyncpg` and asks for Transport Layer Security (TLS) with `ssl=require`:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix_owner:S3cret-Example@db.example.org:5432/idefix?ssl=require"
uv run alembic upgrade head
uv run alembic current
```

```bash
export DATABASE_URL="postgresql+asyncpg://idefix_owner:S3cret-Example@db.example.org:5432/idefix?ssl=require"
uv run alembic upgrade head
uv run alembic current
```

`alembic current` should print `0008 (head)`.

**3. Run the pipeline** directly, as in [Pipeline](#pipeline), with that
`DATABASE_URL` set.

**Supabase.** Take the connection string from **Dashboard → Connect → Session
pooler** (port 5432). Do not use the transaction pooler: the asynchronous
driver relies on prepared statements, which it does not support. Use a
dedicated role rather than the `postgres` superuser, and never commit the URL.
`.env.example` shows the expected form.

### Empty schema instead of the corpus

To start from an empty schema, for example before collecting your own data,
start the database without the bootstrap, so that nothing is restored, then
apply the migrations:

```powershell
docker compose --env-file nul up -d db
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
uv run alembic upgrade head
```

```bash
docker compose --env-file /dev/null up -d db
DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix uv run alembic upgrade head
```

`--env-file` keeps Compose away from `.env`, as the bootstrap does. This
creates every table up to revision `0008`. A later `bootstrap.py db` leaves this
database as it is, because it is no longer empty; and because every clone
shares the database, do this only on a machine with no corpus you want to keep.
Migration reference: [`migrations.md`](./migrations.md).

## Pipeline

`scripts/pipeline.py` runs every offline stage in order, stops at the first
failure, and prints per-stage timings. It contacts neither Telegram nor any
paid API; the only download is the embedding model, on first use. Quickstart
[step 6](./quickstart.md#step-6) lists the stages.

Through the bootstrap, against the local Docker database:

```bash
uv run python scripts/bootstrap.py pipeline --mission russosphere
```

Directly, against whatever `DATABASE_URL` points at:

```bash
uv run python scripts/pipeline.py --mission russosphere --list
uv run python scripts/pipeline.py --mission russosphere
uv run python scripts/pipeline.py --mission all --from export_static
uv run python scripts/pipeline.py --mission all --skip-embeddings
```

| Option | Effect |
|---|---|
| `--mission` | `russosphere`, `france_ukraine`, `gan`, or `all` (the default) |
| `--list` | Print the stages that would run, in order, and exit |
| `--only build_scores` | Run one stage |
| `--from export_static` | Run from this stage to the end (to resume after a failure) |
| `--skip-embeddings` | Drop the embedding stage; sentence-transformers is never imported |

The pipeline overwrites the derived tables restored from the snapshot, with two
caveats recorded in [D18](../limitations.md#d18): scores are rewritten only for
the missions it runs, and `build_edges` adds and updates edges without deleting
those that only the earlier run produced. Each stage is documented in
[`scripts/README.md`](../../scripts/README.md).

## Analyst interface

```bash
cd webapp
npm ci
npm run dev
```

`npm run dev` serves the interface at <http://localhost:5173> until you press
<kbd>Ctrl</kbd>+<kbd>C</kbd>. To build a static copy instead:

```bash
npm run build
npm run preview
```

`npm run build` writes `webapp/dist/`. It first runs two pre-build scripts that
pull data from Supabase, but only when `SUPABASE_URL` and `SUPABASE_KEY` are
set; without them, they print a warning and keep the local bundle.

The interface reads the JavaScript Object Notation (JSON) bundles under
`webapp/public/data/`, which only the pipeline writes; they are not in the
repository. Until the pipeline has
run, every page shows empty states.

## Verify the installation

Run the offline checks in quickstart [step 8](./quickstart.md#step-8), then
confirm that the database answers (with `DATABASE_URL` set):

```bash
uv run alembic current
```

```text
0008 (head)
```

Before you interpret any output, read [the limitations](../limitations.md):
several defects materially affect how the ranking should be read.


## Optional: collect your own data from Telegram

Nothing above needs Telegram. Collection is the only part of Idéfix that
contacts it: read-only, over MTProto (Telegram's client protocol), from public channels only.

<details>
<summary>Telegram collection: account, credentials, session string, and collection</summary>

### What changes when you collect

Collected data goes into whatever database `DATABASE_URL` points at. Once you
collect into the restored corpus, the database is no longer dataset `v1.0.0`,
and its results are no longer comparable with results computed from the
public corpus.

> [!CAUTION]
> `scripts/enrich_recrawl.py` collects the **commenters** of public linked
> discussion groups into the `comments` table: identifiers, usernames, and
> messages of private individuals. That is personal data, governed by
> [§7.3 of the governance chapter](../method/07-tiers-and-governance.md).

### 1. Install the collection extras

`collect` builds TgCrypto from source, so install a C compiler first
([how](./troubleshooting.md#tgcrypto-build)). Then:

```bash
uv sync --extra dev --extra embed --extra collect --extra session
```

### 2. Use a dedicated Telegram account

Create a Telegram account for collection only, separate from your personal
one. Never use it from anywhere else while a script runs, and run one
collection script at a time: concurrent use triggers `FLOOD_WAIT` errors and
can get the account banned.

### 3. Get an API ID and hash

1. Go to [my.telegram.org](https://my.telegram.org) and sign in with the
   dedicated account's phone number.
2. Open **API development tools**.
3. Fill in the form: **App title** `Idefix`, **Short name** `idefix`,
   **Platform** `Other`.
4. Select **Create application**.
5. Keep the page open: you need **App api_id** and **App api_hash** next.

These credentials belong to your account. Never commit them.

### 4. Create `.env`

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Open `.env` in a text editor and fill in the Telegram block, for example:

```dotenv
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_PHONE_NUMBER=+33612345678
```

`.env` is ignored by Git. The legacy names `TG_API_ID`, `TG_API_HASH`,
`TG_SESSION_STRING`, and `TG_PHONE` still work; when both are set, the
`TELEGRAM_*` names win (`src/ingestor/session.py::resolve_session_env`).

### 5. Generate a session string

The session string saves you from signing in again on every run. Start the
generator:

```bash
make session
```

Without `make`, run the command it wraps:

```bash
uv run --extra collect --extra session streamlit run scripts/session_web.py --server.port 8502
```

Open <http://localhost:8502>, then:

1. Enter the phone number in international format (`+33612345678`).
2. Enter the code Telegram sends to the app or by SMS.
3. If the account has two-step verification, enter its password.
4. Copy the session string it displays into `.env`:

   ```dotenv
   TELEGRAM_SESSION_STRING=1BVtsOKABu0example
   ```

Stop the generator with <kbd>Ctrl</kbd>+<kbd>C</kbd>.

> [!WARNING]
> The session string grants access to the account. Treat it as a password.
> Exports scrub it by key and by value, but never paste it anywhere else.

### 6. Collect, then recompute

```bash
uv run --extra collect python scripts/backfill.py --channel @France24_fr --limit 500
uv run python scripts/bootstrap.py pipeline --mission russosphere
```

`bootstrap.py pipeline` targets the local Docker database. If you collected
into another database, run `scripts/pipeline.py` directly with that
`DATABASE_URL` set.

The other entry points (seed set, bounded snowball crawl, France–Ukraine
campaign, paced long-running backfill, and enrichment re-crawl) are listed in
the [README](../../README.md#8-collect-your-own-data-optional-advanced) and
documented in [`scripts/README.md`](../../scripts/README.md).

</details>

## Problems

Every error message with its cause and fix is in
[Troubleshooting](./troubleshooting.md). The ones specific to this guide:
[schema behind](./troubleshooting.md#db-schema-behind),
[wrong database](./troubleshooting.md#wrong-database),
[connection refused](./troubleshooting.md#db-connection-refused),
[`DATABASE_URL` not set](./troubleshooting.md#pipeline-database-url),
[`tgcrypto` build](./troubleshooting.md#tgcrypto-build),
[missing credentials](./troubleshooting.md#tg-credentials), and
[`FLOOD_WAIT`](./troubleshooting.md#tg-flood-wait).
