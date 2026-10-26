# 🐾 Idéfix: the onboarding guide

[![CI](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml/badge.svg)](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/badge/licence-Apache--2.0-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)](./docker-compose.yml)
[![Node](https://img.shields.io/badge/node-20.19%2B%20%7C%2022.12%2B-339933?logo=node.js&logoColor=white)](./webapp/package.json)
[![Dataset](https://img.shields.io/badge/dataset-v1.0.0-8A2BE2)](./dataset/DATASHEET.md)

> **TL;DR** 🏁 Clone the repository and run **one command**: you get the public
> corpus in a local PostgreSQL, every derived table recomputed, and the analyst
> interface open at <http://localhost:5173>. No Telegram account, no secrets,
> and no paid API are needed. Then read
> [§6](#database) before you touch the database: it is the heart of the
> project, and the part most worth improving.

> [!IMPORTANT]
> **Idéfix is not a fake-news detector**, and it is **not a validated
> manipulation detector** either. It describes observable structures of
> diffusion and coordination on public Telegram channels and produces a
> ranked, explainable *examination queue* for human analysts — never a verdict.
> Read [`docs/limitations.md`](./docs/limitations.md) before drawing any
> conclusion from an output.

---

## 📑 Contents

| # | Chapter | You will learn… |
|:-:|---|---|
| 1 | [🧭 What Idéfix is — and is not](#what) | the principle, in two minutes |
| 2 | [🗺️ The lie of the land](#land) | how the pieces fit together |
| 3 | [🧰 Before you begin](#prereq) | what to install, and the Windows quirks |
| 4 | [🚀 Up and running in one command](#setup) | the bootstrap, step by step |
| 5 | [🛠️ Your development environment](#devenv) | tests, linters, CI |
| 6 | [🗄️ **The database, in depth**](#database) | schema, safe exploration, migrations, enrichment, releases |
| 7 | [🧩 Improving the rest of the project](#improve) | missions, method roadmap, good first issues |
| 8 | [🤝 Contributing like a native](#contrib) | branches, commits, pull requests |
| 9 | [📚 Cheat sheet and further reading](#cheatsheet) | everything on one page |

<details>
<summary>📖 <b>Conventions used in this guide</b></summary>

- `code spans` are literal names: files, commands, columns.
- `path:line` references point at the code as of the commit this guide was
  written against; line numbers drift, names do not.
- Shell blocks give the **bash** form (Linux, macOS, Git Bash). Where
  PowerShell differs in substance — environment variables, `nul` — a second
  block follows. For bash commands split with a trailing `\`, PowerShell
  wants a single line or a trailing backtick instead.
- 🧱 marks *raw* data, ⚙️ *derived* data, 💤 *dormant* schema.
- Impact and effort in the backlogs use 🟢 low, 🟡 medium, 🔴 high.

</details>

---

<a id="what"></a>

## 🧭 1. What Idéfix is — and is not

Idéfix analyses **propagation and coordination** across public Telegram
channels. It builds a channel-centric multiplex graph (forwards, mentions,
shared URLs, reused media, and so on), scores each channel with several
independent *families* of structural signals, combines them statistically, and
exports a static bundle that a React interface displays.

Its organizing principle is **one engine, N missions**. A mission
(`russosphere`, `france_ukraine`, `gan`, and the planned `dircom_minarm`) is a
*configuration*, never a code fork: seeds, lexicon, weights, and export
settings. Thematic relevance modulates **severity**, never **inclusion**.

> [!NOTE]
> The authoritative descriptions live elsewhere and this guide does not
> replace them: [`README.md`](./README.md) for the overview,
> [`METHODOLOGY.md`](./METHODOLOGY.md) for the versioned method cover page,
> [`docs/`](./docs/README.md) for the method chapters and experiments, and
> [`docs/limitations.md`](./docs/limitations.md) for what bounds every claim.

---

<a id="land"></a>

## 🗺️ 2. The lie of the land

Two strictly disjoint halves: an **offline Python pipeline** that reads
PostgreSQL and writes JSON, and a **fully static interface** that reads only
that JSON. The browser never touches the database.

```mermaid
flowchart LR
    subgraph RAW["🧱 Raw data (one of)"]
        DS["Public dataset v1.0.0<br/>pg_dump + SHA-256 manifest"]
        TG["Your own collection<br/>MTProto, optional"]
    end
    DB[("PostgreSQL 17<br/>channels · messages · comments")]
    subgraph PIPE["⚙️ Offline pipeline — scripts/pipeline.py"]
        E["build_edges"] --> S["build_scores"] --> C["analyze_communities"] --> X["export_static"]
    end
    B["📦 webapp/public/data/#lt;mission#gt;/<br/>JSON bundles"]
    UI["🖥️ React + Vite<br/>static site"]
    DS -- "pg_restore" --> DB
    TG -- "upserts" --> DB
    DB --> E
    S -- "channel_scores" --> DB
    X --> B --> UI
```

```text
Idefix/
├── ONBOARDING.md       ← you are here
├── METHODOLOGY.md      versioned cover page (its hash ships in every export)
├── alembic/            PostgreSQL migrations, hand-written (head: 0008)
├── dataset/            public corpus: manifest, datasheet, README
├── docker-compose.yml  local PostgreSQL 17, loopback only
├── docs/               method · experiments · limitations · ops · product
├── scripts/            bootstrap, pipeline runner, collectors, release tooling
├── src/                the engine (see the table below)
├── supabase/           hosting overlay for a managed database (not Alembic)
├── tests/              offline pytest suite: no database, no network
└── webapp/             React 18 + Vite + TypeScript analyst interface
```

| Package | Role | Start reading at |
|---|---|---|
| `src/ingestor` | Read-only MTProto collection, `FLOOD_WAIT` discipline | `queries.py`, `handlers.py`, `run_lock.py` |
| `src/normalizer` | Text extraction, lexicon-driven thematic targeting | `targeting.py` |
| `src/graph` | The multiplex graph: derivation, persistence, in-memory rebuild | `edges.py`, `loader.py` |
| `src/scorer` | Score families, null model, Stouffer and Benjamini–Hochberg | `channel_suspicion.py`, `rigor.py` |
| `src/embed` | Local sentence-transformers track, lazily imported | `encoder.py` |
| `src/dossier` | Evidence-first episode dossiers | `builder.py`, `evidence.py` |
| `src/missions` | One package per mission, auto-discovered | `spec.py`, `registry.py` |
| `src/validation_lab` | Schemas for non-circular external validation | `schema.py` |
| `src/shared` | Database pool, secret scrubbing, snapshot store | `db.py`, `scrub.py` |

---

<a id="prereq"></a>

## 🧰 3. Before you begin

| Tool | Version | Why | Check with |
|---|---|---|---|
| 🐍 [uv](https://docs.astral.sh/uv/) | recent | Installs Python 3.14 for you and manages every dependency | `uv --version` |
| 🐍 Python | **3.14** exactly | Pinned in `.python-version` and `pyproject.toml` | `uv run python --version` |
| 🐳 [Docker](https://docs.docker.com/get-docker/) | Compose v2 **≥ 2.17**, daemon running | Local PostgreSQL 17 | `docker compose version` |
| 🟩 [Node.js](https://nodejs.org/) + npm | **20.19+** or **22.12+** (21.x is refused) | Vite 8 for the interface | `node --version` |
| 🧶 make | optional | Shortcuts; everything also works without it | `make --version` |

A short pre-flight checklist:

- [ ] Docker Desktop (or the Docker service) is running.
- [ ] Port `5433` is free, or you have chosen another one (`IDEFIX_DB_PORT`).
- [ ] A few gigabytes of free disk space: the dataset and the database volume
      are modest, but PyTorch and the embedding model of the `embed` extra are
      not.
- [ ] You have read the governance section of [`README.md`](./README.md): the
      corpus includes **personal data** of commenters in public discussion
      groups.

<details>
<summary>🪟 <b>Windows and OneDrive notes</b> (read this if you are on Windows)</summary>

- **UTF-8 everywhere.** Accented French and Cyrillic text comes out garbled
  in a `cp1252` console, or raises `UnicodeEncodeError`. Set `$env:PYTHONUTF8="1"` (PowerShell) or
  `set PYTHONUTF8=1` (cmd) before running scripts by hand. The bootstrap sets
  it for its own children.
- **OneDrive.** `pyproject.toml` sets `[tool.uv] link-mode = "copy"` because
  hard links fail inside OneDrive folders (os error 396). Leave it alone.
- **Compose and `.env`.** Docker Compose would otherwise read `.env`, which
  may hold secrets. The project always passes an empty env file:
  `--env-file nul` in PowerShell and cmd, `--env-file /dev/null` in bash.
- **Reserved ports.** Hyper-V sometimes reserves port ranges. If `5433` is
  refused although nothing listens on it, run
  `netsh interface ipv4 show excludedportrange protocol=tcp` and pick a port
  outside the ranges listed.
- **Git Bash and container paths.** Git Bash rewrites arguments that look
  like Unix paths (`/tmp/…`) into Windows paths. Prefix such commands with
  `MSYS_NO_PATHCONV=1`, or use PowerShell.

</details>

---

<a id="setup"></a>

## 🚀 4. Up and running in one command

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
uv run --extra embed python scripts/bootstrap.py    # any OS
# or, where make is available:
make setup
```

When the Vite dev server reports that it is ready, open
<http://localhost:5173>. Stop it with <kbd>Ctrl</kbd>+<kbd>C</kbd>.

### What the bootstrap actually does

[`scripts/bootstrap.py`](./scripts/bootstrap.py) uses the standard library
only, never reads `.env`, and **never deletes data**. Each of its five steps is
also a subcommand you can run on its own.

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant BS as bootstrap.py
    participant GH as GitHub Release
    participant PG as PostgreSQL 17 (Docker)
    participant PL as pipeline.py
    participant V as Vite
    You->>BS: uv run --extra embed python scripts/bootstrap.py
    BS->>BS: check — Python, Docker, Compose, Node, port, manifest
    BS->>GH: fetch — download the files listed in dataset/manifest.json
    GH-->>BS: dump + annotations archive
    BS->>BS: verify size and SHA-256, unpack the archive into data/
    BS->>PG: db — docker compose up --wait
    alt the public schema is empty
        BS->>PG: pg_restore --no-owner --no-privileges
        BS->>PG: alembic upgrade head
    else the database already holds data
        BS-->>You: left untouched — prints the migrate command if behind
    end
    BS->>PL: pipeline — every stage, every mission
    PL->>PG: read raw tables, write derived tables
    PL-->>BS: JSON bundles in webapp/public/data/
    BS->>V: webapp — npm ci if needed, then npm run dev
    V-->>You: http://localhost:5173
```

| Step | Subcommand | In one line |
|:-:|---|---|
| 1 | `check` | Stops with a `-> fix` hint for each missing prerequisite |
| 2 | `fetch` | Resumable download, size and SHA-256 verified; cached files are kept |
| 3 | `db` | Starts Compose; restores **only into an empty database**; writes a JSON marker as the database comment |
| 4 | `pipeline` | Runs `scripts/pipeline.py`; inside `all`, only on a database the bootstrap restored, until one run has completed |
| 5 | `webapp` | Installs the frontend dependencies when the lockfile is newer, then starts Vite |

### Options and environment variables

| Flag or variable | Effect |
|---|---|
| `--skip-embeddings` | Skips the embedding stage: no PyTorch, no model download (`uv run python scripts/bootstrap.py --skip-embeddings`) |
| `--no-webapp` | `all` stops after the pipeline; Node becomes optional |
| `--mission M` | One mission instead of `all` |
| `--dataset-dir PATH` | Copies the release files from a local folder instead of downloading them |
| `IDEFIX_DB_PORT` | Host port of the database (default `5433`); read by both Compose and the bootstrap |
| `IDEFIX_DATASET_BASE_URL` | A mirror for the release files; hashes are still verified |

### ✅ Did it work?

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
uv run alembic current        # expected: 0008 (head)
```

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
uv run alembic current        # expected: 0008 (head)
```

> [!TIP]
> Want to look at the interface with **no database at all**?
> `uv run python scripts/make_fixture_bundle.py` writes an obviously synthetic
> bundle (invented channels, fixed seed) into `webapp/public/data/russosphere/`.
> It **replaces** whatever bundle is there, so rerun the pipeline afterwards if
> you had a real one.

<details>
<summary>🩺 <b>Troubleshooting the bootstrap</b></summary>

| Symptom | Fix |
|---|---|
| `check`: database port already in use | `export IDEFIX_DB_PORT=55432` (bash) or `$env:IDEFIX_DB_PORT=55432` (PowerShell), then rerun |
| `check`: Docker daemon not reachable | Start Docker Desktop or `sudo systemctl start docker`, wait, rerun |
| `check`: permission denied on the Docker socket (Linux) | `sudo usermod -aG docker $USER`, then log out and back in |
| `check`: the `embed` extra is not installed | Rerun with `uv run --extra embed …`, or pass `--skip-embeddings` |
| Garbled accents or `UnicodeEncodeError` (Windows) | `$env:PYTHONUTF8="1"` before the command |
| A step failed half-way | Fix the cause and rerun the same command: verified downloads are kept, and a non-empty database is never restored again |
| You want the pipeline to run again | `uv run --extra embed python scripts/bootstrap.py pipeline` always runs it |
| `db` says the schema is behind | Run the printed `uv run alembic upgrade head` with `DATABASE_URL` set |
| One pipeline stage failed | `uv run python scripts/pipeline.py --list`, then resume with `--from STAGE` |
| No access to GitHub | `IDEFIX_DATASET_BASE_URL` or `--dataset-dir` |
| Blank page or empty states in the interface | The pipeline has not finished: run the `pipeline` step and read the failing stage |

The full table lives in [`docs/ops/quickstart.md`](./docs/ops/quickstart.md);
the manual route, including a managed database, in
[`docs/ops/install.md`](./docs/ops/install.md).

</details>

---

<a id="devenv"></a>

## 🛠️ 5. Your development environment

### Python

```bash
uv sync --extra dev --extra llm --extra embed   # name every extra you need, in one command
uv run pre-commit install                       # ruff, whitespace, private-key detection
```

> [!WARNING]
> `uv sync` **removes** the extras you do not name. Running `uv sync --extra dev`
> after the line above silently uninstalls `llm` and `embed`, and the tests
> that import them then fail. Always sync with the full list, as CI does.

| Task | With make | Without make |
|---|---|---|
| Format | `make fmt` | `uv run ruff format src/ tests/` and `uv run ruff check --fix src/ tests/` |
| Lint and type-check | `make lint` | `uv run ruff check src/ tests/` and `uv run mypy src/ --ignore-missing-imports` |
| Test | `make test` | `uv run pytest tests/` |
| Documentation integrity | — | `uv run python scripts/check_docs.py` |

The test suite is **entirely offline**: no PostgreSQL, no network, no model
download. Database access is replaced by fake connections, embeddings by an
injected encoder, and the Mistral client by `httpx.MockTransport`.

### The interface

```bash
cd webapp
npm ci
npm run typecheck      # strict TypeScript
npm run lint           # ESLint
npm run i18n:parity    # six locales must carry the same keys
npm run ui:contract    # a ratchet: design-contract violations may only go down
npm run test:e2e       # Playwright smoke tests (needs a bundle, see the tip in §4)
```

### What CI runs

| Workflow | Trigger | What blocks a merge |
|---|---|---|
| [`ci.yml`](./.github/workflows/ci.yml) | every push to `main`, every pull request | ruff, mypy, pytest with coverage on Python 3.14; `check_docs.py` |
| [`ui-gate.yml`](./.github/workflows/ui-gate.yml) | changes under `webapp/` or to the workflow itself | typecheck, i18n parity, ESLint, the UI contract, and Playwright on a synthetic bundle |
| [`reproduce.yml`](./.github/workflows/reproduce.yml) | weekly (Monday, 04:23 UTC) and on demand | the whole bootstrap on a real PostgreSQL, then `npm run build` |

> [!NOTE]
> `reproduce.yml` is the **only** place where code meets a real database in
> CI. Everything else is offline by design, which is why a broken SQL string
> can pass the test suite — see the backlog in [§6.7](#db-backlog).

---

<a id="database"></a>

## 🗄️ 6. The database, in depth

Everything Idéfix collects lives in one PostgreSQL 17 database. There is **no
ORM**: the schema is the eight hand-written Alembic revisions under
[`alembic/versions/`](./alembic/versions/), and all runtime access is raw
`asyncpg` SQL (pool in [`src/shared/db.py`](./src/shared/db.py), writers in
[`src/ingestor/queries.py`](./src/ingestor/queries.py)).

<a id="db-anatomy"></a>

### 6.1 🔬 Anatomy

```mermaid
erDiagram
    channels ||--o{ messages : "publishes"
    channels |o..o{ messages : "forwarded from (no FK)"
    channels |o..o{ comments : "discussion of (no FK)"
    channels ||--o{ edges : "source"
    channels |o--o{ edges : "destination channel"
    channels ||--o{ channel_scores : "scored per mission"
    channels ||--o{ channel_llm_scores : "classified (LLM track)"
    episodes ||--o{ evidence_dossiers : "documents"

    channels {
        BIGINT channel_id PK "Telegram id"
        TEXT username
        TEXT title
        TEXT description
        INT member_count
        TEXT tier
        JSONB extra "fr_score, gan_targeting, msg_sampled"
    }
    messages {
        BIGSERIAL id PK
        BIGINT channel_id FK
        BIGINT message_id "unique with channel_id"
        TIMESTAMPTZ timestamp
        TEXT text
        BIGINT forward_from_channel_id
        INT views
        INT forwards
        TEXT media_hash "Telegram file_unique_id"
        JSONB urls "never filled"
        BOOLEAN is_deleted "never set"
    }
    comments {
        BIGSERIAL id PK
        BIGINT channel_id
        BIGINT message_id
        BIGINT commenter_id "personal data"
        TEXT commenter_username "personal data"
        TEXT text
        TIMESTAMPTZ timestamp
    }
    edges {
        BIGSERIAL id PK
        BIGINT src_channel_id FK
        BIGINT dst_channel_id FK "or dst_domain, never both"
        TEXT dst_domain
        TEXT edge_type
        INT count
        REAL weight
        JSONB attrs
    }
    channel_scores {
        TEXT mission PK
        BIGINT channel_id PK
        REAL suspicion
        TEXT tier
        BOOLEAN gate_met
        TEXT_ARRAY gate_families "since 0008"
        JSONB payload
    }
    scores_run_meta {
        TEXT mission PK
        JSONB envelope
    }
    channel_llm_scores {
        TEXT mission PK
        BIGINT channel_id PK
        TEXT model PK
        TEXT prompt_version PK
        TEXT actor_type
        REAL confidence
    }
    episodes {
        TEXT episode_id PK
        TEXT title
        JSONB claim_variants
    }
    evidence_dossiers {
        TEXT dossier_id PK
        TEXT episode_id FK
        JSONB scores
    }
```

Dotted lines are *logical* links that no foreign key enforces.

| Table | Kind | Written by | Read by | Rows in `v1.0.0` |
|---|:-:|---|---|--:|
| `channels` | 🧱 | `upsert_channel` (collectors); `tag_france` / `tag_gan` merge into `extra`; `build_edges` inserts placeholder rows for edge targets | almost every stage | 3,699 |
| `messages` | 🧱 | `insert_message` (collectors) only | graph, scorer, targeting, episodes, export | 166,188 |
| `comments` | 🧱 | `insert_comment`, via `scripts/enrich_recrawl.py` | `build_commenters` (ids and usernames, never text) | 9,241 |
| `edges` | ⚙️ | `build_edges` (upsert only) | graph loader, porosity, GAN footprint, export | 16,275 |
| `channel_scores` | ⚙️ | `build_scores` (per mission) | `export_static`, `analyze_porosity`, `mine_episodes` | 7,313 |
| `scores_run_meta` | ⚙️ | `build_scores` | REST exporters | 2 |
| `channel_llm_scores` | ⚙️ | `classify_channels_llm` / `classify_channels_embed` (paid, outside the pipeline) | LLM evaluation scripts | 0 |
| `episodes` | 💤 | nothing | nothing (episodes are JSON files) | 0 |
| `evidence_dossiers` | 💤 | nothing | nothing | 0 |

Row counts are those of [`dataset/manifest.json`](./dataset/manifest.json),
which also pins a per-table content MD5 so that a restore can be proved
lossless.

<details>
<summary>🔑 <b>Keys and indexes worth knowing by heart</b></summary>

- `messages`: `UNIQUE (channel_id, message_id)` is the collectors' idempotency
  key (`ON CONFLICT … DO NOTHING`).
- `edges`: the upsert key is the **expression** index `uq_edges_src_dst_type`
  on `(src_channel_id, COALESCE(dst_channel_id, -1), COALESCE(dst_domain, ''), edge_type)`.
  The `COALESCE` exists because PostgreSQL treats `NULL`s as distinct in an
  ordinary unique constraint. A `CHECK` (`ck_edges_exactly_one_dst`) enforces
  exactly one destination.
- `channel_scores`: primary key `(mission, channel_id)` since `0006`; hot read
  path `idx_channel_scores_mission_suspicion (mission, suspicion DESC, channel_id)`.
- `comments`: `UNIQUE (channel_id, message_id, commenter_id, timestamp)`; note
  that both `commenter_id` and `timestamp` are nullable.

</details>

> [!NOTE]
> **Supabase is a separate overlay, not a second schema.** The SQL files under
> [`supabase/migrations/`](./supabase/migrations/) secure a hosted copy
> (an `idefix_owner` role, row-level security on every table, and no access for
> `anon` or `authenticated`) and add one table, `community_snapshots`, that
> exists **only** there and is reached over REST by
> [`src/shared/snapshot_store.py`](./src/shared/snapshot_store.py). Alembic
> remains the source of truth for the business schema.

<a id="db-raw-derived"></a>

### 6.2 🧱 Raw versus ⚙️ derived

The distinction governs what you may change, what you may cite, and what the
pipeline rewrites behind your back.

| Data | Rewritten by the pipeline? | How |
|---|:-:|---|
| `channels` (except `extra`), `messages`, `comments` | ❌ | Only collectors add to them — save that `build_edges` inserts a bare `channels` row (`ON CONFLICT DO NOTHING`) for any edge endpoint not yet catalogued |
| `channels.extra` keys `fr_score`, `gan_targeting` | ✅ | `tag_france`, `tag_gan` merge with `\|\|` |
| `edges` | ✅ | `build_edges` upserts; it never retires an edge that is no longer derived |
| `channel_scores`, `scores_run_meta` | ✅ | `build_scores` replaces **its own mission's** rows inside one transaction (`DELETE … WHERE mission = $1`, never `TRUNCATE`) |
| JSON bundles under `webapp/public/data/` | ✅ | `export_static`, `build_stories`, and friends; gitignored |

> [!IMPORTANT]
> **Cite only numbers you have regenerated.** The published snapshot carries
> the derived tables of an *earlier* pipeline run. They are recomputed by the
> bootstrap, and only freshly regenerated numbers may be quoted (defect D18 in
> [`docs/limitations.md`](./docs/limitations.md)).

The pipeline's authoritative stage order is printed by
`uv run python scripts/pipeline.py --mission all --list`. Each stage runs for
every applicable mission before the next one starts:

| # | Stage | Scope | Writes |
|--:|---|---|---|
| 1 | `build_edges` | whole database | `edges` (upsert) |
| 2 | `tag_france` | whole database | `channels.extra.fr_score` |
| 3 | `tag_gan` | whole database | `channels.extra.gan_targeting` |
| 4 | `build_scores` | every mission | `channel_scores`, `scores_run_meta` |
| 5 | `build_dossier` | `russosphere` | a scoring dossier (JSON) |
| 6 | `analyze_communities` | every mission | Leiden communities (JSON) |
| 7 | `analyze_communities_embed` | every mission, embeddings only | communities with embedding edges (JSON) |
| 8 | `precompute_galaxy_layout` | every mission | layout coordinates (JSON) |
| 9 | `analyze_porosity` | `russosphere` | porosity traces (JSON) |
| 10 | `mine_episodes` | `russosphere` | discovered episodes (JSON) |
| 11 | `build_gan_footprint` | `russosphere` | the GAN theme readout (JSON) |
| 12 | `build_commenters` | every mission | per-channel commenter aggregate (JSON) |
| 13 | `export_static` | every mission | the bundle: manifest, index, channels, graph |
| 14 | `build_stories` | every mission | the narrative selector (JSON) |

<a id="db-explore"></a>

### 6.3 🔦 Poking around safely

Open `psql` inside the container in a **read-only session**: the server then
refuses any write, whatever you type.

```bash
docker compose --env-file /dev/null exec \
  -e PGOPTIONS="-c default_transaction_read_only=on" \
  db psql -U idefix -d idefix
```

```powershell
docker compose --env-file nul exec -e PGOPTIONS="-c default_transaction_read_only=on" db psql -U idefix -d idefix
```

Then try these, one at a time. Every one of them is a plain `SELECT`.

```sql
-- 1. Which schema revision, and how was this database created?
SELECT version_num FROM alembic_version;
SELECT shobj_description(oid, 'pg_database') AS bootstrap_marker
FROM pg_database WHERE datname = current_database();

-- 2. Row counts, to compare with dataset/manifest.json
SELECT 'channels' AS table_name, count(*) AS row_count FROM channels
UNION ALL SELECT 'messages', count(*) FROM messages
UNION ALL SELECT 'comments', count(*) FROM comments
UNION ALL SELECT 'edges', count(*) FROM edges
UNION ALL SELECT 'channel_scores', count(*) FROM channel_scores
ORDER BY row_count DESC;

-- 3. The collection window
SELECT min(timestamp) AS first_post, max(timestamp) AS last_post FROM messages;

-- 4. The edge families of the multiplex graph
SELECT edge_type, count(*) AS edges, sum(count) AS observations
FROM edges GROUP BY edge_type ORDER BY edges DESC;

-- 5. Scores per mission (derived data: check computed_at before trusting it)
SELECT mission, count(*) AS channels,
       count(*) FILTER (WHERE gate_met) AS gate_met,
       max(computed_at) AS computed_at
FROM channel_scores GROUP BY mission ORDER BY mission;

-- 6. The most-forwarded sources, collected or not
SELECT m.forward_from_channel_id AS source_id,
       COALESCE(c.username, c.title, '(not collected)') AS source,
       count(*) AS forwards_observed
FROM messages m
LEFT JOIN channels c ON c.channel_id = m.forward_from_channel_id
WHERE m.forward_from_channel_id IS NOT NULL
GROUP BY 1, 2 ORDER BY forwards_observed DESC LIMIT 10;

-- 7. Catalogue coverage: channels known but never collected
SELECT count(*) AS channels,
       count(*) FILTER (WHERE m.channel_id IS NULL) AS without_messages
FROM channels c
LEFT JOIN (SELECT DISTINCT channel_id FROM messages) m USING (channel_id);

-- 8. A data-quality profile of messages (see §6.6 for why some are zero)
SELECT count(*) AS messages,
       count(language) AS with_language,
       count(urls) AS with_urls,
       count(media_hash) AS with_media_hash,
       count(*) FILTER (WHERE is_deleted) AS marked_deleted
FROM messages;

-- 9. Which indexes are used, and what they cost
SELECT relname AS table_name, indexrelname AS index_name, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes ORDER BY relname, indexrelname;

-- 10. Comment rows that would collide if NULLs counted as equal
--     (GROUP BY treats NULLs as equal; the unique constraint does not)
SELECT channel_id, message_id, commenter_id, timestamp, count(*) AS copies
FROM comments
GROUP BY channel_id, message_id, commenter_id, timestamp
HAVING count(*) > 1;
```

To understand *why* a query is slow, ask the planner. `EXPLAIN ANALYZE` runs
the query, so keep it to `SELECT`s:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM messages WHERE text ~* 'porte-avions';
```

On the public corpus this reads every page of `messages` (`Parallel Seq Scan
… Filter: (text ~* …)`). Hold that thought: [§6.5](#db-migrations) turns it
into an index scan.

<a id="db-rules"></a>

### 6.4 🛡️ The golden rules

> [!CAUTION]
> **The corpus is preserved whole.** Not one row, table, or column of the
> collected data is ever deleted, emptied, or stripped — not locally, not in a
> release.
>
> - Restore only into an **empty** database; the bootstrap refuses anything
>   else, and so should you.
> - No `TRUNCATE`, no `DROP`, no hand-written `DELETE` on corpus tables. The
>   only deletion the pipeline performs is `build_scores` replacing its own
>   mission's derived rows inside a transaction.
> - Never `docker compose down -v`, never remove the `idefix_pgdata` volume,
>   never delete anything under `backups/`. `make db-down` only *stops* the
>   container.
> - Run **one Telegram collector at a time**. They all take the same
>   PostgreSQL advisory lock
>   ([`src/ingestor/run_lock.py`](./src/ingestor/run_lock.py)) and a second
>   one exits immediately.

> [!WARNING]
> **Do not check out old commits while generated files exist.** Commits from
> before the bundles became gitignored[^bundles] still track `webapp/public/data/`.
> Switching to one overwrites your local bundles, and switching back deletes
> them — mid-pipeline, that costs you the run. Before checking out an older
> commit, compare with
> `git diff --name-status --diff-filter=D <old> <new> -- webapp/public/data`.

> [!NOTE]
> **Personal data.** `comments` holds the identifiers, usernames, and text of
> private individuals who commented in public discussion groups. It ships in
> full in the public dataset (see [`dataset/DATASHEET.md`](./dataset/DATASHEET.md)).
> Never paste rows from it into an issue, a commit, a test fixture, or a log;
> use synthetic data (`scripts/make_fixture_bundle.py` shows the style).

<a id="db-migrations"></a>

### 6.5 🧬 Evolving the schema with Alembic

#### The house rules

| Rule | Why |
|---|---|
| Migrations are **hand-written** with `op.execute(...)` | There is no ORM, hence no autogenerate (`target_metadata = None`) |
| **One SQL statement per `op.execute` call** | SQLAlchemy's asyncpg dialect uses prepared statements, which refuse multi-statement strings |
| Alembic runs in **async** mode; `DATABASE_URL` keeps `+asyncpg` | No synchronous driver is installed |
| The URL never goes into `alembic.ini` | No credentials in version control; it comes from the environment or `.env`, and the environment wins |
| Prefer **additive** changes with `IF NOT EXISTS` | A fresh clone restores a dump and then runs `alembic upgrade head`: your migration must apply cleanly on top of real data |
| Always write a working `downgrade()` | …and test it, on a throwaway database only |

> [!NOTE]
> The public dump is **already at `0008`** (`alembic_revision` in
> [`dataset/manifest.json`](./dataset/manifest.json)), so the bootstrap's
> `alembic upgrade head` after a restore is a no-op today. The moment you add
> `0009`, that same call applies it to every fresh clone — which is precisely
> why it must be additive and idempotent.

#### A worked example: a trigram index for regex scans

Several stages scan `messages.text` with case-insensitive regular expressions
(`~*` in `scripts/build_gan_footprint.py` and `scripts/snowball_crawl.py`). A
GIN index over `pg_trgm` trigrams lets PostgreSQL answer such predicates with a
bitmap index scan. It is a good first migration: additive, touches no row, and
measurable. Treat it as an illustration — measure before you merge.

**Step 1 — generate the file.**

```bash
uv run alembic revision --rev-id 0009 -m "messages_text_trgm"
```

**Step 2 — write it in the house style**, modelled on
[`0008_add_gate_families.py`](./alembic/versions/0008_add_gate_families.py):

```python
"""messages.text — trigram index for case-insensitive regex scans

Stages that filter messages.text with ``~*`` read the whole table. A GIN index
over pg_trgm trigrams lets PostgreSQL use a bitmap index scan instead.
Additive: creates the extension if absent and one index; no row is touched.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS idx_messages_text_trgm "
    "ON messages USING gin (text gin_trgm_ops)",
]

DOWNGRADE_STATEMENTS = [
    # The extension stays: other objects may come to depend on it.
    "DROP INDEX IF EXISTS idx_messages_text_trgm",
]


def upgrade() -> None:
    """Create the trigram index on ``messages.text``."""
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    """Drop the trigram index."""
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
```

**Step 3 — add an offline smoke test**, after
[`tests/ingestor/test_migration_0006.py`](./tests/ingestor/test_migration_0006.py).
It records the statements instead of running them, so it needs no database:

```python
"""Smoke test for alembic/versions/0009 — OFFLINE (no DB, no alembic run)."""
import importlib.util
from pathlib import Path

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0009_messages_text_trgm.py"
)


def _load_migration(monkeypatch):
    recorded: list[str] = []
    import alembic.op as op_mod

    monkeypatch.setattr(op_mod, "execute", lambda stmt: recorded.append(str(stmt)))
    spec = importlib.util.spec_from_file_location("mig_0009", _MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, recorded


def test_revision_chain(monkeypatch):
    mod, _ = _load_migration(monkeypatch)
    assert (mod.revision, mod.down_revision) == ("0009", "0008")


def test_one_statement_per_execute(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    mod.upgrade()
    mod.downgrade()
    assert recorded and all(";" not in stmt for stmt in recorded)
```

**Step 4 — run the full cycle on a throwaway database**, never on the corpus
volume:

```bash
docker run --rm -d --name idefix-scratch \
  -e POSTGRES_USER=idefix -e POSTGRES_PASSWORD=idefix -e POSTGRES_DB=idefix \
  -p 127.0.0.1:55435:5432 postgres:17-alpine
docker exec idefix-scratch pg_isready -h 127.0.0.1 -U idefix   # repeat until "accepting connections"

export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:55435/idefix
uv run alembic upgrade head      # 0001 → 0009 on an empty schema
uv run alembic downgrade -1      # 0009 → 0008
uv run alembic upgrade head      # and back
uv run alembic current           # expected: 0009 (head)
docker stop idefix-scratch       # --rm disposes of the container
```

```powershell
docker run --rm -d --name idefix-scratch -e POSTGRES_USER=idefix -e POSTGRES_PASSWORD=idefix -e POSTGRES_DB=idefix -p 127.0.0.1:55435:5432 postgres:17-alpine
docker exec idefix-scratch pg_isready -h 127.0.0.1 -U idefix

$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:55435/idefix"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run alembic current
docker stop idefix-scratch
```

> [!CAUTION]
> `DATABASE_URL` in the environment **overrides** `.env`. Before any
> `downgrade`, run `echo $DATABASE_URL` (`$env:DATABASE_URL` in PowerShell)
> and make sure it names port `55435`, the scratch database. Downgrading the
> corpus database is how data gets lost.

**Step 5 — measure, then upgrade your real database.** Point `DATABASE_URL`
back at port `5433`, run the `EXPLAIN` of §6.3, apply the migration with
`uv run alembic upgrade head`, and run the `EXPLAIN` again. The plan should now
read `Bitmap Index Scan on idx_messages_text_trgm`; if it does not, the index
is not earning its keep, and the pull request should say so.

**Step 6 — the head-bump checklist.** A new head ripples through files that no
test ties together:

- [ ] `scripts/release_dataset.py` — `ALEMBIC_HEAD = "0008"` becomes `"0009"`
      (a release refuses to build otherwise, and no test catches a stale value)
- [ ] [`docs/ops/migrations.md`](./docs/ops/migrations.md) — the revision
      table of §2 and every `0008 (head)`
- [ ] [`docs/ops/install.md`](./docs/ops/install.md) — the expected output of
      `alembic current`
- [ ] [`README.md`](./README.md) — the repository tree (`head: 0008`)
- [ ] `tests/ingestor/test_migration_0009.py` — the smoke test above
- [ ] [`CHANGELOG.md`](./CHANGELOG.md) — under `[Unreleased]`

<details>
<summary>🪤 <b>Pitfalls that have bitten before</b></summary>

- **`CREATE INDEX CONCURRENTLY`** cannot run inside a transaction, and Alembic
  wraps each migration in one. On a large hosted database, build such an index
  by hand outside Alembic, then ship a migration whose `IF NOT EXISTS` makes it
  a no-op.
- **Downgrades are not all safe.** `0006`'s downgrade cannot run on the
  `v1.0.0` data (two missions share channel ids, so the old single-column
  primary keys would collide). The downgrades of `0001` and `0003` drop tables
  that hold corpus data.
- **Databases from the pre-Alembic era** were created by a deleted
  `init_db.py`. Stamp them (`uv run alembic stamp 0001`) instead of running
  `0001` against populated tables.
- **A new `NOT NULL` column** on a populated table needs a default, or the
  restore-then-upgrade path of every fresh clone breaks.
- **A `CHECK` on existing data** is safest added `NOT VALID` first, then
  validated in a second statement once you have proved no row violates it.

</details>

<a id="db-enrich"></a>

### 6.6 🌱 Enriching the corpus

Collection is optional, advanced, and the **only** part of Idéfix that contacts
Telegram: public channels only, one dedicated read-only account, terms of
service respected, and `FLOOD_WAIT` honoured.

**1. Credentials.** Copy `.env.example` to `.env` (gitignored) and fill
`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` (from <https://my.telegram.org>, *API
development tools*) and `TELEGRAM_PHONE_NUMBER`. Generate the session string
once:

```bash
make session    # = uv run --extra session streamlit run scripts/session_web.py --server.port 8502
```

Paste the result into `TELEGRAM_SESSION_STRING`. These values are secrets:
[`src/shared/scrub.py`](./src/shared/scrub.py) strips them from every export,
by key *and* by value.

**2. Collect.** Collectors write wherever `DATABASE_URL` points — by default,
the local Compose database.

| Script | Collects | Shortcut or cautious first run |
|---|---|---|
| `scripts/backfill.py --channel @name --limit 500` | One channel's history | `make backfill CH=@name` |
| `scripts/backfill_seeds.py [@channel …]` | The hop-0 seed set, in one session | — |
| `scripts/snowball_crawl.py --waves 1` | The most-forwarded channels not yet collected | `--dry-run` |
| `scripts/crawl_france_ukraine.py` | A bounded France–Ukraine campaign | `--dry-run` |
| `scripts/paced_backfill.py` | Paced, long-running backfill of catalogued but empty channels | `--max-channels 5` |
| `scripts/enrich_recrawl.py` | Media hashes, channel bios, and **commenters** (personal data) | — |

**3. Recompute** every derived table: `make pipeline`, or
`uv run --extra embed python scripts/bootstrap.py pipeline`.

> [!IMPORTANT]
> A database you have collected into **is no longer dataset `v1.0.0`**.
> Results from it are not comparable with results from the public corpus until
> you publish it as a new version ([§6.8](#db-release)).

<details>
<summary>🧪 <b>Data-quality caveats you will meet</b></summary>

| Observation | Cause | Consequence |
|---|---|---|
| `views`, `forwards`, `media_hash` frozen at first sight | `insert_message` uses `ON CONFLICT (channel_id, message_id) DO NOTHING` (`src/ingestor/queries.py:49`) | A re-crawl never refreshes a message it already has |
| `urls`, `raw_content` always `NULL` | Hard-coded `None, None` in `insert_message` (`queries.py:57`) | URL pivots are re-derived from text instead |
| `language` always `NULL` | `_parse_message` sets `"language": None` (`src/ingestor/handlers.py:61`) | The `TRANSLATION` edge family never fires |
| `is_deleted` always `false` | No code detects deletions | Deleted posts look alive |
| `channels.extra` loses keys | `snowball_crawl.py` replaces the whole object (`SET extra = $2::jsonb`) where everything else merges with `\|\|` | `gan_targeting` can vanish until `tag_gan` runs again |
| Duplicate comments possible | The unique key includes nullable `commenter_id` and `timestamp`, and `NULL`s are distinct | A comment with a `NULL` timestamp is never deduplicated |

Query 8 of §6.3 shows most of these at a glance.

</details>

<a id="db-backlog"></a>

### 6.7 🧭 The database improvement backlog

Ranked by what each item unlocks. Every one of them is lossless by
construction: none deletes corpus data.

| # | Improvement | Impact | Effort | Where |
|:-:|---|:-:|:-:|---|
| 1 | Refresh counters on re-crawl: `ON CONFLICT … DO UPDATE SET views = EXCLUDED.views, forwards = EXCLUDED.forwards, media_hash = COALESCE(EXCLUDED.media_hash, messages.media_hash)` | 🔴 | 🟢 | `src/ingestor/queries.py` |
| 2 | Fill `language` and `urls` at collection time, which unblocks `TRANSLATION` and the URL pivot (D25) | 🔴 | 🟡 | `src/ingestor/handlers.py`, `queries.py` |
| 3 | A CI job with a PostgreSQL service that restores a small synthetic dump and runs `upgrade → downgrade → upgrade` plus a pipeline smoke test | 🔴 | 🟡 | `.github/workflows/ci.yml` |
| 4 | Merge rather than overwrite `channels.extra` in the snowball crawler | 🟡 | 🟢 | `scripts/snowball_crawl.py` |
| 5 | Retire stale edges **without deleting them**: stamp each upsert with a run identifier and let readers filter on the latest run | 🟡 | 🟡 | `src/graph/edges.py`, new column |
| 6 | Deletion detection: set `is_deleted` / `deleted_at` when a re-crawl no longer finds a post (D22) — a flag, never a row removal | 🟡 | 🟡 | `src/ingestor/` |
| 7 | Make the `comments` unique key treat `NULL`s as equal (`UNIQUE NULLS NOT DISTINCT`, PostgreSQL 15+), once query 10 of §6.3 returns no row | 🟡 | 🟢 | new migration |
| 8 | A test that `ALEMBIC_HEAD` equals the newest file in `alembic/versions/` | 🟡 | 🟢 | `tests/` |
| 9 | Offline smoke tests for `0001`, `0002`, `0007`, `0008` (only `0003`–`0006` have one) | 🟢 | 🟢 | `tests/ingestor/` |
| 10 | Prune overlapping indexes after measuring with query 9: `idx_messages_channel_id`, `idx_edges_src`, `idx_channel_llm_scores_mission` duplicate the leading columns of another index; `idx_channel_scores_suspicion` is not mission-scoped | 🟢 | 🟢 | new migration |
| 11 | Push work into SQL: `build_edges` and the targeting scorer load whole tables into Python (`src/graph/edges.py`, `src/normalizer/targeting.py`) | 🟡 | 🔴 | engine |
| 12 | A `CHECK` (or enum) on `edges.edge_type`, added `NOT VALID` then validated | 🟢 | 🟢 | new migration |
| 13 | Foreign keys for `messages.forward_from_channel_id` and `comments.channel_id`, added `NOT VALID` — or a written decision not to | 🟢 | 🟡 | new migration |
| 14 | Decide the fate of the dormant `episodes` and `evidence_dossiers` tables (episodes currently live as JSON) | 🟢 | 🟡 | design note first |

Pick one, open an issue saying so, and copy this into the pull request:

- [ ] The change is additive, or its data impact is set out in the PR
- [ ] Tested on a throwaway database, including `downgrade`
- [ ] Offline test added; `make test` and `make lint` green
- [ ] Head-bump checklist of §6.5 done, if a migration was added
- [ ] `CHANGELOG.md` updated

<a id="db-release"></a>

### 6.8 📦 Publishing a dataset version

A release is two files pinned by SHA-256 in `dataset/manifest.json`: a
`pg_dump` custom-format dump of the **complete** database, and a deterministic
`tar.gz` of `data/annotations/` and `data/claims/`.
[`scripts/release_dataset.py`](./scripts/release_dataset.py) builds both and
*proves* the result lossless rather than asserting it.

```mermaid
flowchart TD
    A["Source dump<br/>backups/*.dump (read-only mount)"] --> B["Restore into a scratch container<br/>idefix-release · 127.0.0.1:55434"]
    B --> C["Fingerprint every table<br/>row count + content MD5"]
    C --> D["alembic upgrade head"]
    D --> E{"Lossless?<br/>same fingerprints on source columns,<br/>new columns NULL, new tables empty"}
    E -- no --> X["❌ abort, no manifest"]
    E -- yes --> F{"Secret scan<br/>counts only, never values"}
    F -- hits --> X
    F -- none --> G["pg_dump -Fc --no-owner --no-privileges"]
    G --> H["Restore the new dump into idefix_verify<br/>and compare fingerprints again"]
    H --> I["Write dataset/manifest.json ✅"]
```

**Versioning** is semantic, and a published version is **never modified in
place** ([`dataset/DATASHEET.md`](./dataset/DATASHEET.md)):

| Bump | When |
|---|---|
| Patch `1.0.x` | Documentation only |
| Minor `1.x.0` | Data added (a new collection, say) |
| Major `x.0.0` | Data changed or removed, or the schema changed |

**The procedure, for a maintainer.**

1. **Snapshot your local database** to a file. Dump inside the container and
   copy the file out, which keeps binary output safe from shell redirection:

   ```bash
   MSYS_NO_PATHCONV=1 docker compose --env-file /dev/null exec -T db \
     pg_dump -Fc --no-owner --no-privileges -U idefix -d idefix -f /tmp/idefix-local.dump
   docker compose --env-file /dev/null cp db:/tmp/idefix-local.dump backups/idefix-local-20261026.dump
   ```

   ```powershell
   docker compose --env-file nul exec -T db pg_dump -Fc --no-owner --no-privileges -U idefix -d idefix -f /tmp/idefix-local.dump
   docker compose --env-file nul cp db:/tmp/idefix-local.dump backups/idefix-local-20261026.dump
   ```

2. **Build the release** (Docker required; nothing is uploaded):

   ```bash
   uv run python scripts/release_dataset.py \
     --source backups/idefix-local-20261026.dump \
     --version 1.1.0 --out dataset/downloads
   ```

3. **Verify** the artefacts against the manifest it wrote; this restores the
   dump into a scratch container and checks every fingerprint:

   ```bash
   uv run python scripts/release_dataset.py --verify-only
   ```

4. **Document**: `dataset/DATASHEET.md` (contents, collection window, and what
   changed), `dataset/README.md` (file table), `CITATION.cff` (dataset
   version), and `CHANGELOG.md`.
5. **Publish by hand.** No script uploads anything; the tag follows the
   `dataset-vX.Y.Z` pattern:

   ```bash
   gh release create dataset-v1.1.0 \
     dataset/downloads/idefix-corpus-v1.1.0.dump \
     dataset/downloads/idefix-annotations-v1.1.0.tar.gz \
     --title "Dataset v1.1.0" --notes-file <your-notes.md>
   ```

6. **Commit the new manifest** in the same pull request as the documentation.

> [!CAUTION]
> A release is **public and permanent**: once uploaded, assets may be copied
> and cached even if withdrawn later. It ships the complete `comments` table,
> commenter identifiers included, and the datasheet lists the legal basis for
> publishing it as an open maintainer decision. Read *Open decisions for the
> maintainer* in [`dataset/DATASHEET.md`](./dataset/DATASHEET.md) before every
> release.

> [!TIP]
> The annotation archive is byte-reproducible; the dump is not, because
> `pg_dump` records its own timestamp. Two builds of the same data therefore
> have different SHA-256s but **identical per-table fingerprints** — compare
> those, not the hashes.

---

<a id="improve"></a>

## 🧩 7. Improving the rest of the project

### 7.1 Adding a mission

A mission is a package, not a fork. The recipe, derived from the code:

1. **Create** `src/missions/<name>/__init__.py`. The registry discovers it
   automatically (any name except `spec`, `registry`, and `loader`).
2. **Write a lexicon** in `src/missions/<name>/lexicon.py`, modelled on
   [`src/missions/dircom_minarm/lexicon.py`](./src/missions/dircom_minarm/lexicon.py):
   categories, contextual terms, adversary domains, a `LexiconProfile`, and a
   `TargetingProfile`.
3. **Export** `MISSION = MissionDefinition(...)` (fields in
   [`src/missions/spec.py`](./src/missions/spec.py)): a `SourceUniverse`, a
   `ScoringProfile` whose `active_families` are a subset of its
   `family_weights`, `ExportProfile(out_subdir="<name>")`, and a relevance
   scorer. Leave `implemented=False` while it is only planned.
4. **Optionally** add `stories.py` with `EDITORIAL_STORIES`, picked up by
   `scripts/build_stories.py`.
5. **Register it in the runner**: append the name to `MISSIONS` in
   `scripts/pipeline.py` and update `EXPECTED_ALL` in
   `tests/test_pipeline_runner.py`, or the test that pins the plan fails.
6. **Optionally** write a `tag_<name>.py` stage, modelled on
   `scripts/tag_gan.py`, if the relevance signal should be stored in
   `channels.extra`.
7. **Wire the interface**: an entry in
   [`webapp/src/data/missions.ts`](./webapp/src/data/missions.ts), and the
   keys `mission.<name>.label`, `.description`, and `.caveat` in all six
   locales ([`docs/product/i18n.md`](./docs/product/i18n.md)).
8. **Test**: registry and lexicon tests on the pattern of
   `tests/missions/`, then `uv run python scripts/pipeline.py --mission <name> --list`.
9. **Document** it in [`docs/ops/multi-mission.md`](./docs/ops/multi-mission.md).

### 7.2 The method roadmap

Each structural family yields a one-sided $p$-value. Families with no signal
(`NO_SIGNAL_PVALUE`) are set aside, the rest are combined by weighted
Stouffer, and Benjamini–Hochberg then controls the false discovery rate across
channels:

```math
Z = \frac{\sum_i w_i \, z_i}{\sqrt{\sum_i w_i^{2}}}, \qquad z_i = \Phi^{-1}\!\left(1 - p_i\right)
```

The open defects[^ids], in the priority order of
[`docs/limitations.md`](./docs/limitations.md) (Part IV):

| Rank | ID | Problem | What a fix looks like |
|:-:|---|---|---|
| 1 | L4 | No organic negative class | Human annotation of an organic-coordination corpus |
| 2 | D2 🚨 | Family (c) has no null model | A degree-preserving or edge-swap null on the coordination graph |
| 3 | L5 | No real external gold | Externally sourced, independently labelled episodes |
| 4 | D5 | `CO_HASHTAG` manufactures coordination | Drop it, demand a stronger co-pivot, or weight edge types by surprise |
| 5 | D6 | Confidence bands outside (b) and (d) are constants | Genuine interval estimates |
| 6 | D9 | Bridge Score terms scale differently with corpus size | Standardize or rank the components first |
| 7 | D3 | Stouffer's independence assumption is violated | Account for the shared forward graph of (b) and (d) |
| 8 | D14 | Free parameters without sensitivity analysis | Start with `EMB_SIM` and the Leiden resolution |
| 9 | D16 | Two contradictory gate definitions | One gate, imported by both paths |

> [!NOTE]
> **No experiment has a current result.** The protocols in
> [`docs/experiments/`](./docs/experiments/README.md) define their
> falsification criteria in advance; running one against the public corpus,
> with its artefact committed under `docs/experiments/results/`, is among the
> most valuable contributions there is. CI rejects any figure in experiment
> prose that no artefact backs.

### 7.3 🌟 Good first issues

Small, verifiable, and genuinely useful:

- [ ] The method chapters and `METHODOLOGY.md` cite defects D19–D26, which
      `docs/limitations.md` does not define yet.
- [ ] `check_docs.py` strips `#anchors` before checking links, so dangling
      anchors such as `limitations.md#d19` pass. Teach it to check them.
- [ ] `france_ukraine` is missing from `webapp/src/data/missions.ts` and from
      the locales, so its bundle cannot be reached in the interface.
- [ ] `scripts/` is neither linted nor type-checked in CI.

---

<a id="contrib"></a>

## 🤝 8. Contributing like a native

```mermaid
flowchart LR
    A["🌿 branch from main<br/>feat/ · fix/ · docs/ · chore/"] --> B["✍️ change + a test<br/>that fails without it"]
    B --> C["🧹 make fmt · make lint · make test"]
    C --> D["📬 pull request<br/>template checklist"]
    D --> E{"🚦 CI green?"}
    E -- no --> B
    E -- yes --> F["👀 review"] --> G["✅ merge into main"]
```

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `ci:`, `build(deps):`.
  Subjects are imperative and lower-case, for example
  `docs: correct the false 'member identifiers are never collected' claim`.
- **Commit email**: use the address attached to your GitHub account, or the
  Vercel deployment is blocked.
- **Pull requests** use [the template](./.github/PULL_REQUEST_TEMPLATE.md):
  tests pass, lint passes, a test was added, docs were updated, no secret was
  committed.
- **The changelog** follows [Keep a Changelog](https://keepachangelog.com/):
  add your entry under `[Unreleased]`.
- **Never commit** `.env`, collected data, or `webapp/public/data/`.
- **Security issues**, and anything touching personal data, go through the
  private channel of [`SECURITY.md`](./SECURITY.md) — never a public issue.

The full reference is [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

<a id="cheatsheet"></a>

## 📚 9. Cheat sheet and further reading

| I want to… | Command |
|---|---|
| Set everything up | `uv run --extra embed python scripts/bootstrap.py` |
| Start or stop the database | `make db-up` · `make db-down` (stop only) |
| Rerun the pipeline | `make pipeline MISSION=russosphere` |
| Resume a failed stage | `uv run python scripts/pipeline.py --mission gan --from <stage>` |
| Open a read-only SQL session | `docker compose --env-file /dev/null exec -e PGOPTIONS="-c default_transaction_read_only=on" db psql -U idefix -d idefix` |
| Check the schema revision | `uv run alembic current` |
| Create a migration | `uv run alembic revision --rev-id 0009 -m "name"` |
| Verify the dataset files | `uv run python scripts/release_dataset.py --verify-only` |
| Format, then run every check | `make fmt && make lint && make test && uv run python scripts/check_docs.py` |
| Serve the interface | `make webapp`, then <kbd>Ctrl</kbd>+<kbd>C</kbd> to stop |

**A pocket glossary.** The full one is
[`docs/reference/glossary.md`](./docs/reference/glossary.md).

| Term | Meaning here |
|---|---|
| Mission | A configuration of the engine: seeds, lexicon, weights, export |
| Family | One independent structural signal, (a) to (f), yielding a $p$-value |
| Gate | A channel is escalated only when at least two distinct families trigger |
| Bundle | The static JSON the interface reads; produced, never committed |
| Raw / derived | Collected data versus data the pipeline recomputes |
| T1 / T2 / T3 | Tiers of claim; T3 (real-world attribution) is out of scope |

**Where to go next:**

- 📐 Method: [`docs/method/`](./docs/README.md) and [`METHODOLOGY.md`](./METHODOLOGY.md)
- 🧪 Experiments: [`docs/experiments/README.md`](./docs/experiments/README.md)
- ⚠️ Limits: [`docs/limitations.md`](./docs/limitations.md)
- 🗄️ Migrations: [`docs/ops/migrations.md`](./docs/ops/migrations.md)
- 📦 Dataset: [`dataset/README.md`](./dataset/README.md) and [`dataset/DATASHEET.md`](./dataset/DATASHEET.md)
- 🧭 Missions: [`docs/ops/multi-mission.md`](./docs/ops/multi-mission.md)
- 🖥️ Interface: [`docs/product/frontend.md`](./docs/product/frontend.md)

[^bundles]: Commit `c47f838` (‘remove unwired modules, the embedded science UI,
    and published bundles’) stopped tracking the generated bundles. Any commit
    before it still contains them.

[^ids]: `L` identifiers are permanent limits of the approach and `D`
    identifiers are defects; both are defined in
    [`docs/limitations.md`](./docs/limitations.md). Defects D1, D4, D7, D11,
    and D15b are fixed.

---

<sub>This guide describes the code as of schema revision `0008` and dataset
`v1.0.0`. Wherever it disagrees with the code or with
[`dataset/manifest.json`](./dataset/manifest.json), they win: please fix the
guide in the same pull request.</sub>
