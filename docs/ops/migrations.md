# Database migrations with Alembic

Operational reference for the PostgreSQL schema. Alembic is the **source of
truth** for it. The script that created the original schema, `init_db.py`, is
no longer in the repository; it appears below only because databases it created
need stamping ([below](#stamp-existing-database)).

The latest revision is `0008`, and the public corpus (dataset `v1.0.0`) is
already at `0008`: the release process took a snapshot at `0006`, applied the
additive revisions `0007` and `0008`, and only then dumped it
([`dataset/manifest.json`](../../dataset/manifest.json) records
`"alembic_revision": "0008"`). Right after restoring it into an empty database,
the bootstrap still runs `alembic upgrade head`, which has nothing to do until a
later revision exists. On a database that already holds data the bootstrap
migrates nothing; it prints the `alembic upgrade head` command if the schema is
behind.

Scope: the data layer only. Nothing here contacts Telegram.

Which command to run depends on the state of the database:

```mermaid
flowchart TD
    start{Does the database hold tables?}
    start -- "No: fresh database" --> upgrade["alembic upgrade head"]
    start -- Yes --> version{Is there an alembic_version table?}
    version -- "No: created by init_db.py" --> stamp["alembic stamp 0001"] --> upgrade
    version -- "Yes: restored corpus or earlier run" --> upgrade
    upgrade --> head["alembic current reports the head"]
```

## 🧭 Contents

- [Conventions](#conventions)
- [Revisions](#-revisions)
- [Fresh database](#-fresh-database)
- [Existing database with no `alembic_version` table](#stamp-existing-database)
- [Creating a migration](#-creating-a-migration)
- [The `edges` table](#-the-edges-table-revision-0002)

<a id="conventions"></a>

## 📝 Conventions

- `DATABASE_URL` carries the `+asyncpg` suffix, for example
  `postgresql+asyncpg://idefix:idefix@localhost:5433/idefix` for the local
  Docker database. It comes from the environment or from `.env`; a variable set
  in the environment wins, because `python-dotenv` never overrides one.
- **Alembic runs in asynchronous mode** (`alembic init -t async`). This is
  forced: no synchronous driver is installed (neither `psycopg2` nor
  `psycopg` 3), only `asyncpg`. SQLAlchemy's asynchronous engine takes the
  `+asyncpg` URL as it is.
- `alembic/env.py` loads `.env`, then injects `DATABASE_URL` into
  `sqlalchemy.url`, and stops with
  `RuntimeError: DATABASE_URL is not set` when there is none. The URL is
  **never** written to `alembic.ini`, so no credentials reach version control.
- Migrations are **hand-written** (`op.execute`). There is no
  object-relational mapping (ORM) model in this project, so there is no
  autogenerate (`target_metadata = None`).

> [!IMPORTANT]
> **One SQL statement per `op.execute` call.** SQLAlchemy's asyncpg dialect uses
> the prepared-statement protocol, which refuses several commands in one
> `execute` (`cannot insert multiple commands into a prepared statement`).
> Data definition language (DDL) is therefore a list of statements, never a
> multi-statement block.
> `init_db.py` escaped this because it used raw `asyncpg` with the simple-query
> protocol.

Set the variable before any command below:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
```

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

## 🧩 Revisions

| Rev. | Name | Content |
|---|---|---|
| `0001` | baseline | Recreates the four historical tables (`channels`, `messages`, `episodes`, `evidence_dossiers`) and their indexes, copied from `init_db.py`. Idempotent (`IF NOT EXISTS`) |
| `0002` | edges | Creates `edges`, which materializes the channel-centric multiplex graph. Additive |
| `0003` | enrich | Ingestion enrichment: `messages.media_hash` carries the Telegram `file_unique_id` (indexed), `channels.description`, and a `comments` table for commenters in linked public groups, with its legal basis documented in the migration file. Additive |
| `0004` | perf | Score materialization: `channel_scores` (one row per channel, `suspicion` indexed in descending order, `archetype`, `payload`), a single-row `scores_run_meta` envelope (`coverage_callout`, `symmetric_ratio`), and two hot-path indexes on `messages`. Additive |
| `0005` | mission_scoped_scores | Adds a `mission` column, defaulting to `russosphere`, to `channel_scores` and `scores_run_meta`. Additive |
| `0006` | mission_composite_pk | Switches the primary keys so that missions coexist: `channel_scores` to `(mission, channel_id)`, `scores_run_meta` to `(mission)` |
| `0007` | channel_llm_scores | Creates `channel_llm_scores` for the optional Mistral classification track, keyed by `(mission, channel_id, model, prompt_version)`. Additive |
| `0008` | add_gate_families | Adds `channel_scores.gate_families`, the families that triggered the multi-source gate, so that the gate is auditable. Additive and nullable |

The history is linear, with a single head:

```bash
uv run alembic heads
```

```text
0008 (head)
```

> [!NOTE]
> **Why scores are materialized (revision `0004`).** `build_scores` computes once,
> off the query path, what used to be recomputed on every request: thematic
> targeting over all messages, the forward projection, eigenvector centrality,
> coordination, and recidivism. It writes the result to `channel_scores` and
> `scores_run_meta`, and every consumer only reads it. In the pipeline it runs
> after `build_edges` and the tagging stages, and before the analyses and the
> export. This is why the analyst interface can be a static bundle with no
> backend at all.

## 🚀 Fresh database

```bash
uv run alembic upgrade head
```

This creates the baseline tables and applies every later revision. Check the
result:

```bash
uv run alembic current
```

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
0008 (head)
```

<a id="stamp-existing-database"></a>

## 🔧 Existing database with no `alembic_version` table

If `init_db.py` created the schema, do **not** let Alembic run `0001`, which
would try to recreate populated tables. Stamp the baseline instead, then apply
the rest:

```bash
uv run alembic stamp 0001
uv run alembic upgrade head
```

`alembic stamp 0001` marks the baseline as applied without executing any DDL.
Afterwards, `alembic current` reports `0008 (head)` and the populated tables are
intact.

## 🔧 Creating a migration

```bash
uv run alembic revision --rev-id 0009 -m "my_migration"
```

Edit the new `alembic/versions/0009_my_migration.py`, and fill `upgrade()` and
`downgrade()` with `op.execute(...)` calls, **one SQL statement per call** (see
[Conventions](#conventions)). Always provide a working `downgrade()`. Keep it
additive where you can: the bootstrap runs `alembic upgrade head` after every
restore, so a new revision is applied to a freshly restored corpus
automatically.

## 🧩 The `edges` table (revision `0002`)

The persistent projection of the channel-centric multiplex graph. An edge
targets **either** another channel (`dst_channel_id`) **or** a web domain
(`dst_domain`), never both and never neither; the constraint
`ck_edges_exactly_one_dst` enforces this.

The edge families are documented in
[`../method/02-graph-model.md`](../method/02-graph-model.md) §2.2.

Notable attributes: `count` and `weight` for the aggregated edge;
`delay_seconds` for `FORWARD`; `text_sim` for the text-similarity families;
`window_delta_seconds`, with `window_start` and `window_end`, for the
coordination window; and an `attrs` JSONB catch-all (the shared domain of a
`CO_URL`, the perceptual hash of a `MEDIA_REUSE`, the count of shared origins
of a `CO_FORWARD`).

**Upsert key.** The unique index `uq_edges_src_dst_type` covers
`(src_channel_id, COALESCE(dst_channel_id, -1), COALESCE(dst_domain, ''), edge_type)`.

The `COALESCE` is required. PostgreSQL treats `NULL` values as **distinct** in
a conventional unique constraint, so without it two identical channel-to-domain
edges, both with a `NULL` `dst_channel_id`, would both be inserted. A Telegram
`channel_id` is never `-1` and `''` is never a real domain, so both sentinels
are safe.
