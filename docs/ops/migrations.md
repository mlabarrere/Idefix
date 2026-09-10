# Database migrations — Alembic

Operational reference for the PostgreSQL schema. Alembic is the **source of
truth**; `scripts/init_db.py` is retained only as a historical record of the
original schema and is frozen.

Scope: data layer only. No Telegram or MTProto contact.

## 1. Conventions

- `DATABASE_URL` lives in `.env` with the `+asyncpg` suffix. On Windows, prefix
  commands with `$env:PYTHONUTF8="1"` (PowerShell) or `PYTHONUTF8=1` (bash).
- **Alembic runs in async mode** (`alembic init -t async`). This is forced: no
  synchronous driver is installed — neither `psycopg2` nor `psycopg` v3, only
  `asyncpg`. SQLAlchemy's async engine consumes the `+asyncpg` URL directly, so
  no suffix stripping is needed.
- `alembic/env.py` loads `DATABASE_URL` from `.env` via `python-dotenv` and
  injects it into `sqlalchemy.url`. The URL is **never** written to
  `alembic.ini` — no credentials in version control.
- Migrations are **hand-written** (`op.execute`). There is no ORM model in this
  project, so there is no autogenerate (`target_metadata = None`).

> **asyncpg constraint (load-bearing).** SQLAlchemy's asyncpg dialect uses the
> prepared-statement protocol, which **refuses multiple SQL commands in a single
> `execute`** (`cannot insert multiple commands into a prepared statement`).
> Every migration therefore issues **one statement per `op.execute` call** — DDL
> is a list of statements, never a multi-statement block. `init_db.py` escaped
> this because it used raw `asyncpg` with the simple-query protocol.

## 2. Revisions

| Rev. | Name | Content |
|---|---|---|
| `0001` | baseline | Recreates the four historical tables (`channels`, `messages`, `episodes`, `evidence_dossiers`) plus indexes. Idempotent (`IF NOT EXISTS`). |
| `0002` | edges | Creates `edges`, materializing the channel-centric multiplex graph. Additive. |
| `0003` | enrich | Ingestion enrichment: `messages.media_hash` (Telegram `file_unique_id`, indexed), `channels.description`, and a `comments` table for commenters in linked public groups — legal basis documented in the migration file. Additive. |
| `0004` | perf | Score materialization: `channel_scores` (one row per channel, `suspicion` indexed DESC, `archetype`, `payload`), a single-row `scores_run_meta` envelope (`coverage_callout`, `symmetric_ratio`), and two hot-path indexes on `messages`. Additive. |
| `0005` | mission_scoped_scores | Scores scoped per mission. Additive. |
| `0006` | mission_composite_pk | Composite primary key including the mission. |
| `0007` | channel_llm_scores | Per-channel LLM scores (semantic track). Additive. |
| `0008` | add_gate_families | Materializes the triggered-family set per channel (`gate_families`), making the multi-source gate auditable. Additive. |

`alembic heads` returns `0008 (head)` — a single head, linear history.

> **Why scores are materialized (rev. 0004).** After each crawl the order is
> `build_edges.py → build_scores.py → analyze_communities.py`. `build_scores.py`
> computes once, off the query path, what was previously recomputed on every
> request — thematic targeting over all messages, the forward projection,
> eigenvector centrality, coordination and recidivism — and writes it to
> `channel_scores` / `scores_run_meta`. Consumers only **read** the precomputed
> result. This is why the analyst interface can be a static bundle with no
> backend at all.

## 3. Fresh database

```bash
uv run alembic upgrade head
```

Creates the baseline tables and every subsequent revision.

## 4. Existing database with no `alembic_version` table

If the schema was created historically by `init_db.py`, do **not** re-run
`0001` — it would attempt to recreate populated tables. Stamp it instead:

```bash
uv run alembic stamp 0001    # marks the baseline applied; executes no DDL
uv run alembic upgrade head  # applies everything after it
```

Then `alembic current` reports `0008 (head)` with populated tables intact.

## 5. Creating a migration

```bash
uv run alembic revision --rev-id 0009 -m "my_migration"
```

Edit `alembic/versions/0009_*.py` and fill `upgrade()` / `downgrade()` with
`op.execute(...)` calls — **one SQL statement per call** (see the asyncpg note
in §1). Always provide a working `downgrade()`.

## 6. The `edges` table (rev. 0002)

Persistent projection of the channel-centric multiplex graph. An edge targets
**either** another channel (`dst_channel_id`) **or** a web domain
(`dst_domain`) — never both, never neither, enforced by
`ck_edges_exactly_one_dst`.

Edge families are documented in
[`../method/02-graph-model.md`](../method/02-graph-model.md) §2.2.

Notable attributes: `count` and `weight` for the aggregated edge;
`delay_seconds` for `FORWARD`; `text_sim` for text-similarity families;
`window_delta_seconds` with `window_start` / `window_end` for the coordination
window; and an `attrs` JSONB catch-all (shared domain for a `CO_URL`, perceptual
hash for a `MEDIA_REUSE`, count of shared origins for a `CO_FORWARD`).

**Upsert key.** Unique index `uq_edges_src_dst_type` on
`(src_channel_id, COALESCE(dst_channel_id, -1), COALESCE(dst_domain, ''), edge_type)`.

The `COALESCE` is required: PostgreSQL treats `NULL`s as **distinct** in a
conventional UNIQUE constraint, so without it two identical channel→domain
edges — both with `dst_channel_id` NULL — would each be inserted. A Telegram
`channel_id` is never `-1` and `''` is never a real domain, so both sentinels
are safe.
