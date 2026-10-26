# Scripts

Every script in this directory, what it does, what it needs, and how to run
it. The flags listed here are read from each script's `argparse`
`add_argument` calls; a script without a parser says so.

To set up a machine, follow [`docs/ops/quickstart.md`](../docs/ops/quickstart.md),
the one canonical setup tutorial. When something fails, see
[`docs/ops/troubleshooting.md`](../docs/ops/troubleshooting.md).

## Where the scripts fit

The deliverable is the static analyst web app in [`webapp/`](../webapp/README.md):
it reads precomputed JSON bundles under `webapp/public/data/<mission>/` and has
no backend. Python is an offline chain only:

```text
corpus in PostgreSQL ──► build_edges ──► tag_france / tag_gan ──► build_scores
   ▲                                                                   │
   │ optional: Telegram collection                                     ▼
   │ (backfill*, crawlers)                    analysis snapshots, export_static,
   │                                          build_stories ──► webapp/public/data/
   └── default: the public corpus, restored by bootstrap.py
```

- **Default path.** [`bootstrap.py`](#bootstrappy) downloads and verifies the
  public dataset `v1.0.0`, restores it into a local PostgreSQL 17 started by
  Docker Compose, applies the migrations, and runs [`pipeline.py`](#pipelinepy).
  It needs no Telegram credentials and no `.env`.
- **Optional collection.** The Telegram scripts extend the corpus. They need
  the `collect` extra and Telegram credentials, and they must never run in
  parallel (see [Telegram rules](#telegram-rules)).
- **Everything else** reads the database or the bundles: labelling, the
  parallel classification tracks, evaluation, and inspection tools.

## Conventions

### Running a script

Run every script from the repository root: the scripts import `src/` relative
to it, and some write paths relative to the current directory.

```bash
uv run python scripts/pipeline.py --list
```

A script that needs an optional extra names it on the command line, as in the
examples below. `uv run` adds the extra to the environment for that run.

| Extra | Provides | Needed by |
|---|---|---|
| `collect` | Hydrogram and TgCrypto, the Telegram MTProto client | every script that opens a Telegram session |
| `session` | Streamlit, plus the `collect` extra | [`session_web.py`](#session_webpy) |
| `embed` | sentence-transformers, run locally | the embedding stages and the embedding track |
| `llm` | the Mistral SDK | the paid Mistral classification track |
| `dev` | pytest, ruff, mypy, pre-commit | tests and checks, not the scripts |

> [!NOTE]
> TgCrypto ships no wheel for Python 3.14, so installing the `collect` extra
> builds it from source and needs a C compiler. See
> [`docs/ops/troubleshooting.md`](../docs/ops/troubleshooting.md).

On Windows, set `PYTHONUTF8=1` before running a script by hand: the scripts
print characters that the default console code page cannot encode.
`pipeline.py` sets it for its own child processes.

```powershell
$env:PYTHONUTF8 = "1"
```

### Configuration

Scripts load `.env` through `python-dotenv` without overriding the process
environment, so a variable you set explicitly wins. `bootstrap.py` never reads
`.env`: it injects the local `DATABASE_URL` into every child process itself.

| Variable | Read by | Meaning |
|---|---|---|
| `DATABASE_URL` | every script that uses PostgreSQL | Connection string. A `+asyncpg` suffix is stripped before connecting. The local database is `postgresql+asyncpg://idefix:idefix@localhost:5433/idefix`, the default in `.env.example`. |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | the collection scripts | Telegram API credentials. Fallbacks: `TG_API_ID`, `TG_API_HASH`. |
| `TELEGRAM_SESSION_STRING` | the collection scripts | Persistent MTProto session. `TELEGRAM_SESSION_NAME` is also accepted. Fallback: `TG_SESSION_STRING`. |
| `TELEGRAM_PHONE_NUMBER` | the collection scripts | Phone number for the first sign-in. Fallback: `TG_PHONE`. |
| `MISTRAL_API_KEY`, `MISTRAL_MODEL`, `MISTRAL_API_BASE` | the Mistral track | API key, model (default `mistral-large-latest`), and endpoint override. |
| `IDEFIX_EMBED_MODEL` | the embedding stages | sentence-transformers model (default `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). |
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | the Supabase utilities, `--push` | The hosted Supabase deployment, reached over its REST API. |
| `IDEFIX_DB_PORT`, `IDEFIX_DATASET_BASE_URL` | `bootstrap.py` | Host port of the local database (default `5433`) and a dataset mirror. |

The `TELEGRAM_*` names take precedence over the `TG_*` fallbacks
(`src/ingestor/session.py::resolve_session_env`). Two exceptions read the
`TG_*` names only: [`session_web.py`](#session_webpy) and the
[`_tg.py`](#_tgpy) module.

### Missions

Scripts that accept `--mission` get it from
`src/missions/loader.py::add_mission_arg`. The default is `russosphere`; the
missions are the packages under `src/missions/` (`russosphere`,
`france_ukraine`, `gan`, and the planned `dircom_minarm`).

### Telegram rules

> [!WARNING]
> Every collection script opens a read-only MTProto session on a single
> personal account. Run one at a time, never in parallel, and never two copies
> of the same script: parallel sessions risk a ban. A PostgreSQL collector lock
> (`src/ingestor/run_lock.py::try_acquire_collector_lock`) refuses a second
> collector, and the client handles `FLOOD_WAIT`. Account hygiene is set out in
> [`docs/method/07-tiers-and-governance.md`](../docs/method/07-tiers-and-governance.md).

## Script index

| Script | Section | Extras | Opens Telegram |
|---|---|---|---|
| [`bootstrap.py`](#bootstrappy) | Reproducibility | `embed` (unless `--skip-embeddings`) | no |
| [`pipeline.py`](#pipelinepy) | Reproducibility | `embed` (unless `--skip-embeddings`) | no |
| [`release_dataset.py`](#release_datasetpy) | Reproducibility | none | no |
| [`make_fixture_bundle.py`](#make_fixture_bundlepy) | Reproducibility | none | no |
| [`check_docs.py`](#check_docspy) | Reproducibility | none | no |
| [`session_web.py`](#session_webpy) | Collection | `session` | yes |
| [`backfill.py`](#backfillpy) | Collection | `collect` | yes |
| [`backfill_seeds.py`](#backfill_seedspy) | Collection | `collect` | yes |
| [`snowball_crawl.py`](#snowball_crawlpy) | Collection | `collect` (not for `--dry-run`) | yes |
| [`crawl_france_ukraine.py`](#crawl_france_ukrainepy) | Collection | `collect` (not for `--dry-run`) | yes |
| [`paced_backfill.py`](#paced_backfillpy) | Collection | `collect` | yes |
| [`enrich_recrawl.py`](#enrich_recrawlpy) | Collection | `collect` | yes |
| [`_tg.py`](#_tgpy) | Collection (module) | `collect` | yes |
| [`build_edges.py`](#build_edgespy) | Pipeline | none (`embed` with `--embed`) | no |
| [`tag_france.py`](#tag_francepy) | Pipeline | none | no |
| [`tag_gan.py`](#tag_ganpy) | Pipeline | none | no |
| [`build_scores.py`](#build_scorespy) | Pipeline | none (`embed` with `--embeddings`) | no |
| [`build_dossier.py`](#build_dossierpy) | Pipeline | none | no |
| [`analyze_communities.py`](#analyze_communitiespy) | Pipeline | none | no |
| [`analyze_communities_embed.py`](#analyze_communities_embedpy) | Pipeline | `embed` | no |
| [`precompute_galaxy_layout.py`](#precompute_galaxy_layoutpy) | Pipeline | none | no |
| [`analyze_porosity.py`](#analyze_porositypy) | Pipeline | none | no |
| [`mine_episodes.py`](#mine_episodespy) | Pipeline | `embed` (unless `--no-embeddings`) | no |
| [`build_gan_footprint.py`](#build_gan_footprintpy) | Pipeline | none | no |
| [`build_commenters.py`](#build_commenterspy) | Pipeline | none | no |
| [`export_static.py`](#export_staticpy) | Pipeline | none | no |
| [`build_stories.py`](#build_storiespy) | Pipeline | none | no |
| [`classify_channels_llm.py`](#classify_channels_llmpy) | Classification tracks | `llm` (not for `--dry-run`) | no |
| [`label_communities_llm.py`](#label_communities_llmpy) | Classification tracks | `llm` (not for `--dry-run`) | no |
| [`classify_channels_embed.py`](#classify_channels_embedpy) | Classification tracks | `embed` | no |
| [`calibrate_text_sim.py`](#calibrate_text_simpy) | Classification tracks | `embed` | no |
| [`build_label_batch.py`](#build_label_batchpy) | Labelling | none | no |
| [`aggregate_labels.py`](#aggregate_labelspy) | Labelling | none | no |
| [`finalize_gold.py`](#finalize_goldpy) | Labelling | none | no |
| [`build_channel_digests.py`](#build_channel_digestspy) | Labelling | none | no |
| [`derive_channel_gold.py`](#derive_channel_goldpy) | Labelling | none | no |
| [`bootstrap_baseline.py`](#bootstrap_baselinepy) | Labelling | none | no |
| [`_eval_common.py`](#_eval_commonpy) | Evaluation (module) | none | no |
| [`prep_eval_inputs.py`](#prep_eval_inputspy) | Evaluation | none | no |
| [`eval_ablation_centrality.py`](#eval_ablation_centralitypy) | Evaluation | none | no |
| [`eval_discriminant_organic.py`](#eval_discriminant_organicpy) | Evaluation | none | no |
| [`eval_episode_recovery.py`](#eval_episode_recoverypy) | Evaluation | none | no |
| [`eval_organic_control.py`](#eval_organic_controlpy) | Evaluation | none | no |
| [`eval_france_targeting_audit.py`](#eval_france_targeting_auditpy) | Evaluation | none | no |
| [`eval_scoring_significance.py`](#eval_scoring_significancepy) | Evaluation | none | no |
| [`eval_embedding_discrimination.py`](#eval_embedding_discriminationpy) | Evaluation | `embed` | no |
| [`eval_mistral_classification.py`](#eval_mistral_classificationpy) | Evaluation | none | no |
| [`eval_embeddings_classification.py`](#eval_embeddings_classificationpy) | Evaluation | none | no |
| [`detect_clusters.py`](#detect_clusterspy) | Inspection | none | no |
| [`compare_snapshots.py`](#compare_snapshotspy) | Inspection | none | no |
| [`export_via_rest_api.py`](#export_via_rest_apipy) | Supabase utilities | none | no |
| [`test_supabase_connection.py`](#test_supabase_connectionpy) | Supabase utilities | none | no |
| [`bench.py`](#benchpy) | Supabase utilities | `embed` | no |
| [`EXPORT_AND_DEPLOY.ps1`](#export_and_deployps1) | Supabase utilities | none | no |

## Reproducibility and orchestration

None of these scripts contacts Telegram or a paid API.

### `bootstrap.py`

From a fresh clone to the web app on the public corpus, in one command. It runs
these steps in order; each is also a subcommand:

1. `check`: Python 3.14, the Docker daemon and Compose v2, Node.js and npm, a
   free database port, the `embed` extra, and a valid manifest.
2. `fetch`: downloads every file listed in `dataset/manifest.json` into
   `dataset/downloads/`, verifies its size and SHA-256, and extracts the
   archives safely.
3. `db`: starts the local PostgreSQL 17 (service `db` in `docker-compose.yml`).
   On an **empty** database only, it restores the dataset and runs
   `alembic upgrade head`. A database that already holds data is left as it is:
   no restore, no migration; if the schema is behind, it prints the
   `alembic upgrade head` command for you to run.
4. `pipeline`: runs `pipeline.py` against that database. Under `all`, this step
   runs automatically only on a database the bootstrap itself restored, until
   one complete run; `bootstrap.py pipeline` always runs it.
5. `webapp`: runs `npm ci` when `webapp/node_modules` is missing or older than
   the lockfile, then `npm run dev`.

It never deletes data, never reads `.env`, and is safe to re-run. It uses the
standard library only.

- **Extras:** `embed`, unless you pass `--skip-embeddings`.
- **Reads:** `dataset/manifest.json`, `docker-compose.yml`; environment
  `IDEFIX_DB_PORT`, `IDEFIX_DATASET_BASE_URL`.
- **Writes:** `dataset/downloads/`, the local database, and the bundles under
  `webapp/public/data/<mission>/`.

```bash
uv run --extra embed python scripts/bootstrap.py
```

```bash
uv run --extra embed python scripts/bootstrap.py pipeline --mission russosphere
```

`make setup` runs `bootstrap.py all`; `make pipeline` runs its `pipeline` step.

| Argument | Default | Effect |
|---|---|---|
| `step` (positional) | `all` | One of `check`, `fetch`, `db`, `pipeline`, `webapp`, `all`. |
| `--dataset-dir` | none | Copy the release files from this local folder instead of downloading them. |
| `--manifest` | `dataset/manifest.json` | Use another dataset manifest. |
| `--mission` | `all` | Mission or missions for the pipeline step. |
| `--skip-embeddings` | off | Forwarded to `pipeline.py`; removes the need for the `embed` extra. |
| `--no-webapp` | off | `all` stops after the pipeline (CI, headless machines). |

### `pipeline.py`

Runs every offline stage, in order, for one mission or all of them. Each stage
is a script in this directory run as a subprocess; the runner prints each
stage's duration and stops at the first failure. Stages that write shared
database state (`edges`, `channels.extra`) run once, whatever the mission
selection. The only network access is the one-time download of the public
sentence-transformers model by the embedding stages. Run it with `--list` to
print the authoritative stage order.

- **Extras:** `embed`, unless you pass `--skip-embeddings`.
- **Reads:** PostgreSQL through `DATABASE_URL` (or `.env`).
- **Writes:** the derived tables and the bundles under
  `webapp/public/data/<mission>/`, through its stages.
- **Exit status:** `0` on success, the failing stage's exit code on the first
  failure, `2` on a usage error.

```bash
uv run --extra embed python scripts/pipeline.py --mission russosphere
```

```bash
uv run python scripts/pipeline.py --mission all --skip-embeddings --from export_static
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `all` | One of `russosphere`, `france_ukraine`, `gan`, `all`. |
| `--list` | off | Print the stages that would run, in order, and exit. |
| `--only` | none | Run this stage only. |
| `--from` | none | Run from this stage to the end (resume). |
| `--skip-embeddings` | off | Drop the embedding stages; sentence-transformers is never imported. |

`--only` and `--from` take a stage name: `build_edges`, `tag_france`,
`tag_gan`, `build_scores`, `build_dossier`, `analyze_communities`,
`analyze_communities_embed`, `precompute_galaxy_layout`, `analyze_porosity`,
`mine_episodes`, `build_gan_footprint`, `build_commenters`, `export_static`,
`build_stories`.

### `release_dataset.py`

**For the maintainer.** Builds, or verifies, the public dataset release from a
PostgreSQL snapshot. The release is a complete `pg_dump` of the source
snapshot, migrated additively to the Alembic head, and a deterministic archive
of `data/annotations/` and `data/claims/`, both pinned by SHA-256 in
`dataset/manifest.json`. Nothing is deleted or stripped: the dump includes the
`comments` table (commenters' identifiers, usernames, and texts) and every
derived table of the run that produced the snapshot. Each table's row count
and content fingerprint are compared before and after the migration, and again
after a second restore. A read-only secret scan prints counts only and refuses
to write the manifest when it finds a secret.

Everything runs in a throw-away `postgres:17-alpine` container bound to
`127.0.0.1`. See [`dataset/README.md`](../dataset/README.md) and
[`dataset/DATASHEET.md`](../dataset/DATASHEET.md).

- **Extras:** none; needs Docker.
- **Reads:** the source dump (read-only), `data/annotations/`, `data/claims/`,
  and `.env` for the secret values to scan for.
- **Writes:** the release files in `--out` and `dataset/manifest.json`.

```bash
uv run python scripts/release_dataset.py --version 1.0.0 --out dataset/downloads
```

```bash
uv run python scripts/release_dataset.py --verify-only --out dataset/downloads
```

<details>
<summary>All flags of <code>release_dataset.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--source` | `backups/idefix-supabase-post-cutover-20260618-132009.dump` | Source snapshot in `pg_dump` custom format, mounted read-only. |
| `--version` | `1.0.0` | Dataset version, `MAJOR.MINOR.PATCH` (not the software version). |
| `--out` | `dataset/downloads` | Artefact directory. |
| `--manifest` | `dataset/manifest.json` | Manifest to write, or to verify against. |
| `--data-dir` | `data` | Directory holding `annotations/` and `claims/`. |
| `--base-url` | `https://github.com/mlabarrere/Idefix/releases/download` | Release download URL prefix recorded in the manifest. |
| `--container` | `idefix-release` | Name of the scratch container. |
| `--port` | `55434` | Host port of the scratch container, on `127.0.0.1`. |
| `--keep-db` | off | Leave the scratch container running. |
| `--no-dotenv` | off | Do not load `.env` before resolving the secrets to scan for. |
| `--allow-secret-hits` | off | Write the manifest even if the secret scan finds occurrences. |
| `--verify-only` | off | Verify the artefacts in `--out` against `--manifest` in a fresh container. |

</details>

### `make_fixture_bundle.py`

Generates a small, obviously synthetic analyst bundle with a fixed seed:
invented channels and a planted coordination cluster. It lets the browser tests
run in CI and lets a reader see the interface without a database. Nothing it
produces says anything about Telegram, and none of it may be cited.

- **Extras:** none; standard library only.
- **Reads:** nothing.
- **Writes:** the bundle in `--out`.

```bash
uv run --no-project python scripts/make_fixture_bundle.py
```

| Flag | Default | Effect |
|---|---|---|
| `--out` | `webapp/public/data/russosphere` | Bundle directory. |

### `check_docs.py`

Documentation integrity checks, run by the `docs` CI job; it fails the build on
a violation. The rules it applies, and any options, are described in its module
docstring.

- **Extras:** none; standard library only.
- **Reads:** the repository's Markdown files and the artefacts under
  `docs/experiments/results/`.
- **Writes:** nothing; findings go to the console.

```bash
uv run --no-project python scripts/check_docs.py
```

## Telegram collection

These scripts open a Telegram session and write to the database selected by
`DATABASE_URL`. They need the `collect` extra and the `TELEGRAM_*` variables
(see [Configuration](#configuration)), and they follow the
[Telegram rules](#telegram-rules). Setting up credentials is covered in
[`docs/ops/install.md`](../docs/ops/install.md).

### `session_web.py`

A Streamlit page that generates a persistent MTProto session string: enter the
phone number, receive the code, sign in (two-factor authentication is handled),
and the page writes `TG_SESSION_STRING` and `TG_PHONE` into `.env`. Run it once.
It has no `argparse` parser; the flags below belong to Streamlit.

- **Extras:** `session` (which includes `collect`).
- **Reads:** `TG_API_ID`, `TG_API_HASH`, and optionally `TG_PHONE`. It does not
  read the `TELEGRAM_*` names.
- **Writes:** `TG_SESSION_STRING` and `TG_PHONE` in `.env`.

```bash
uv run --extra session streamlit run scripts/session_web.py --server.port 8502
```

Then open <http://localhost:8502>. `make session` runs the same command.

### `backfill.py`

Backfills one channel into PostgreSQL through the production client
(`src/ingestor/client.py::TelegramClient.from_env`), under the collector lock.

- **Reads:** the channel's history on Telegram.
- **Writes:** `channels` and `messages`.

```bash
uv run --extra collect python scripts/backfill.py --channel @Vbachir --limit 500
```

`make backfill CH=@Vbachir` runs the same command.

| Flag | Default | Effect |
|---|---|---|
| `--channel` | required | Channel username, for example `@Vbachir`. |
| `--limit` | `500` | Maximum number of messages to fetch. |

### `backfill_seeds.py`

Backfills the accessible seed set in a single Telegram session, for account
hygiene: hop 0 of the snowball, French news hubs plus one documented adversary
anchor. Pass channel usernames to backfill those instead. It has no `argparse`
parser: every argument is taken as a channel. It fetches 300 messages per
channel.

- **Reads:** the channels' history on Telegram.
- **Writes:** `channels` and `messages`.

```bash
uv run --extra collect python scripts/backfill_seeds.py
```

```bash
uv run --extra collect python scripts/backfill_seeds.py @RFI_fr @Geopolitika_fr
```

### `snowball_crawl.py`

Bounded, multi-wave crawl of the snowball frontier. Each wave takes the
channels that have a username and no messages yet, ranks them by inferred
relevance to France, and backfills them (capped, jittered). Ranking is anchored
on French seed channels already in the database, so that the frontier does not
drift towards the much larger non-French apparatus. Between waves the frontier
is queried again, so channels discovered by one wave can be crawled by the
next. At the end it re-tags every channel's France-relevance score.

- **Extras:** `collect`; `--dry-run` does not need it and opens no session.
- **Reads:** the frontier in `channels` and `messages`, then Telegram.
- **Writes:** `channels`, `messages`, and `channels.extra.fr_score`.

```bash
uv run --extra collect python scripts/snowball_crawl.py --waves 3 --cap 20
```

```bash
uv run python scripts/snowball_crawl.py --dry-run --anchor-threshold 0.2
```

| Flag | Default | Effect |
|---|---|---|
| `--cap` | `12` | Channels backfilled per wave. |
| `--waves` | `1` | Number of sequential waves. |
| `--limit` | `150` | Messages per channel. |
| `--anchor-threshold` | `0.15` | France anchor threshold θ: keep only candidates relayed by at least one French seed (`fr_score` ≥ θ). `0` disables anchoring. |
| `--dry-run` | off | Print the anchored frontier ranking without backfilling or opening a Telegram session. |

### `crawl_france_ukraine.py`

Bounded France–Ukraine acquisition campaign in Russian-language networks: it
refreshes the relevant channels it already knows and discovers origins through
Cyrillic forwards. It is an acquisition lens over the shared graph, not a
classifier and not a scoring mission. A live run takes the collector lock,
checks the session first, and paces channels 90 to 150 seconds apart.

The script enforces its own safety limits: `--refresh-cap` plus
`--discovery-cap` must not exceed 20, and `--min-gap` must be at least 90
seconds. To stop a live run cleanly, create `scripts/.stop_france_ukraine`; a
live run deletes a stale stop file when it starts.

- **Extras:** `collect`; `--dry-run` does not need it and makes no Telegram
  call and no write.
- **Reads:** `channels` and `messages`, then Telegram.
- **Writes:** `channels` and `messages`.

```bash
uv run python scripts/crawl_france_ukraine.py --dry-run
```

```bash
uv run --extra collect python scripts/crawl_france_ukraine.py --refresh-cap 5 --discovery-cap 12
```

<details>
<summary>All flags of <code>crawl_france_ukraine.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--dry-run` | off | Print the refresh and discovery queues, then exit: no Telegram call, no write. |
| `--refresh-cap` | `5` | Known channels to refresh. |
| `--discovery-cap` | `12` | New origin channels to discover. |
| `--stale-hours` | `10` | A known channel is refreshed when its data is older than this. |
| `--message-limit` | `300` | Messages per channel. |
| `--min-gap` | `90.0` | Minimum pause between channels, in seconds (at least 90). |
| `--max-gap` | `150.0` | Maximum pause between channels, in seconds. |

</details>

### `paced_backfill.py`

A paced backfill daemon that fills channels that are catalogued but have no
messages yet, well below Telegram's tolerated rate: jittered pauses of several
minutes, slowing down further when a channel takes longer than expected (a
sign the client slept on a `FLOOD_WAIT`). It is resumable, since each cycle
queries the remaining channels again and inserts deduplicate. It stops at the
time cap, when the list is exhausted, or when `scripts/.stop_backfill` exists.
It does not delete the stop file: remove it before the next run.

- **Reads:** `channels`, then Telegram.
- **Writes:** `channels` and `messages`.

```bash
uv run --extra collect python scripts/paced_backfill.py --max-hours 48
```

`make crawl` runs it with the defaults. To stop it at the next channel:

```bash
touch scripts/.stop_backfill
```

```powershell
New-Item scripts\.stop_backfill
```

<details>
<summary>All flags of <code>paced_backfill.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--limit` | `300` | Messages per channel. |
| `--min-gap` | `90.0` | Minimum pause between channels, in seconds. |
| `--max-gap` | `150.0` | Maximum pause between channels, in seconds. |
| `--max-hours` | `48.0` | Time cap, in hours. |
| `--max-channels` | none | Channel cap, for tests. |
| `--batch` | `50` | Channels fetched from the database per cycle. |

</details>

### `enrich_recrawl.py`

Enrichment re-crawl of channels already in the database, in one serialized
session. For each channel it re-backfills the history to capture the media
`file_unique_id` (no download) and the channel bio, then collects the
commenters of the channel's public linked discussion group. Without arguments
it uses the same seed set as `backfill_seeds.py`; every argument is taken as a
channel. It has no `argparse` parser. It fetches 300 messages and 500 comments
per channel.

> [!CAUTION]
> This script collects personal data of private individuals: each commenter's
> Telegram identifier, username, comment text, and timestamp. The `comments`
> table is published in dataset `v1.0.0`. The legal basis and retention terms
> are recorded in `alembic/versions/0003_enrich_media_description_comments.py`
> and discussed in [`dataset/DATASHEET.md`](../dataset/DATASHEET.md).

- **Reads:** the channels and their linked groups on Telegram.
- **Writes:** `messages.media_hash`, `channels.description`, and `comments`.

```bash
uv run --extra collect python scripts/enrich_recrawl.py @RFI_fr @Geopolitika_fr
```

### `_tg.py`

A shared module, not a script: `tg_client(name)` builds a read-only Hydrogram
client from `TG_API_ID`, `TG_API_HASH`, and `TG_SESSION_STRING` (the `TG_*`
names only), and loads `.env` on import. It is for ad hoc diagnostic probes.
Pipeline code goes through `src/ingestor/client.py::TelegramClient`, which
handles `FLOOD_WAIT` and account hygiene. No script in this directory imports
it today.

```python
from _tg import tg_client

async with tg_client("probe") as client:
    ...
```

## Offline pipeline stages

The stages `pipeline.py` runs, in its order. They read PostgreSQL through
`DATABASE_URL` and never contact Telegram. Run them through `pipeline.py`
unless you are debugging one stage.

### `build_edges.py`

Fills the `edges` table, the channel-centred multiplex graph: it derives every
edge family (`FORWARD`, `MENTIONS`, `CITES_DOMAIN`, `CO_FORWARD`, `CO_URL`,
`CO_URL_EXACT`, `CO_HASHTAG`, `MEDIA_REUSE`) from the stored messages and text,
and upserts them idempotently. `MEDIA_REUSE` produces nothing while
`messages.media_hash` is empty. The logic lives in `src/graph/edges.py`.

- **Extras:** none; `--embed` needs `embed`.
- **Reads:** `messages` and `channels`.
- **Writes:** `edges` (upsert only; see
  [`docs/limitations.md`](../docs/limitations.md#d18)).

```bash
uv run python scripts/build_edges.py --window-hours 48
```

| Flag | Default | Effect |
|---|---|---|
| `--window-hours` | `72` | Coordination window Δt, in hours, for `CO_FORWARD` and `CO_URL`. |
| `--embed` | off | Also derive the semantic `TEXT_SIM` and `TRANSLATION` edges from local embeddings. |
| `--model` | `IDEFIX_EMBED_MODEL` or the encoder default | sentence-transformers model, with `--embed`. |

### `tag_france.py`

Tags every backfilled channel with a crude France-relevance score, the density
of French keywords matched with PostgreSQL regular expressions. Axiom 1: tag,
do not filter. It has no `argparse` parser and takes no arguments.

- **Reads:** `messages.text`.
- **Writes:** `channels.extra.fr_score` and `channels.extra.msg_sampled`,
  merged into `channels.extra` without touching other keys.

```bash
uv run python scripts/tag_france.py
```

### `tag_gan.py`

Tags channels with the GAN mission's thematic-targeting score, computed by the
mission's relevance scorer on its multilingual lexicon. It always uses the
`gan` mission, has no `argparse` parser, and takes no arguments.

- **Reads:** `messages` and `channels`.
- **Writes:** `channels.extra.gan_targeting`, merged without overwriting
  `fr_score`.

```bash
uv run python scripts/tag_gan.py
```

### `build_scores.py`

Materializes the per-channel suspicion scores of one mission, once, outside the
request path: France targeting, the forward projection, eigenvector
centrality, coordination, and recidivism. Run it after `build_edges.py`. It is
idempotent: each run deletes the mission's rows and rewrites them in one
transaction, leaving other missions' rows alone.

- **Extras:** none; `--embeddings` needs `embed`.
- **Reads:** `channels`, `messages`, and `edges`.
- **Writes:** `channel_scores` and `scores_run_meta`.

```bash
uv run python scripts/build_scores.py --mission gan
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to score. |
| `--embeddings` | off | Also compute the semantic family (f) from embeddings. |

### `build_dossier.py`

Builds the dossier of the Eurasianist Dugin–Geopolitika cluster from
PostgreSQL, in the web app's contract. Families (b) cascade role, (c)
coordination, and (d) recidivism are computed; families (a) proximity and (e)
AI origin are explicit stubs. It has no `argparse` parser and takes no
arguments.

- **Reads:** `channels` and `messages`.
- **Writes:** `webapp/public/data/russosphere/dugin_cluster.json`.

```bash
uv run python scripts/build_dossier.py
```

### `analyze_communities.py`

Community snapshot: builds the multiplex graph, detects communities with
Leiden (igraph, weighted modularity), finds the bridges between communities
with betweenness on the channel projection, labels each community
automatically, and builds the meta-graph (one node per community). The
snapshot is computed on the whole graph; `--mission` only chooses the bundle
directory. If the database is unreachable it falls back to a graph read from
the static bundle.

- **Reads:** `channels` and `edges`.
- **Writes:** `webapp/public/data/<mission>/russosphere_snapshot.json`; with
  `--push`, also the Supabase table `community_snapshots`.

```bash
uv run python scripts/analyze_communities.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose bundle directory receives the snapshot. |
| `--push` | off | Push the scrubbed snapshot to Supabase `community_snapshots` (needs `SUPABASE_URL` and `SUPABASE_KEY`). |

### `analyze_communities_embed.py`

The embedding counterpart of `analyze_communities.py`, with the same output
shape: Leiden runs on the graph enriched with embedding-similarity edges, so
semantically close channels are pulled together. It adds a `stats.comparison`
block (intra-community cohesion, modularity, number of communities) that feeds
the galaxy's comparison callout. The default snapshot is never touched.

- **Extras:** `embed`.
- **Reads:** `channels`, `edges`, and message text; if the database is
  unreachable, the static bundle, plus message text over Supabase REST when
  `SUPABASE_URL` and `SUPABASE_KEY` are set.
- **Writes:** `webapp/public/data/<mission>/<mission>_embed_snapshot.json`;
  with `--push`, also Supabase.

```bash
uv run --extra embed python scripts/analyze_communities_embed.py --mission russosphere
```

<details>
<summary>All flags of <code>analyze_communities_embed.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to analyse. |
| `--sample-size` | `15` | Messages per channel used for the embedding. |
| `--model` | `IDEFIX_EMBED_MODEL` or the encoder default | sentence-transformers model. |
| `--k` | `5` | Semantic neighbours per channel. |
| `--threshold` | `0.5` | Minimum cosine similarity of an `EMB_SIM` edge. |
| `--weight-scale` | `3.0` | Weight of the embedding edges. |
| `--push` | off | Push the scrubbed snapshot to Supabase `community_snapshots`. |

</details>

### `precompute_galaxy_layout.py`

A post-pass that needs no database: it writes deterministic `x` and `y`
coordinates into the galaxy snapshots, so the web app renders a preset layout
instead of running a force layout in the browser. Communities are placed with
a seeded `networkx.spring_layout` on the meta-graph; channels sit on a
phyllotaxis disc around their community. Two runs produce byte-identical files,
which the browser tests rely on. Only `x` and `y` are added or overwritten.

- **Reads and writes:** the snapshot files, in place. A missing file is reported
  and skipped.

```bash
uv run python scripts/precompute_galaxy_layout.py
```

```bash
uv run python scripts/precompute_galaxy_layout.py webapp/public/data/russosphere/russosphere_snapshot.json
```

| Argument | Default | Effect |
|---|---|---|
| `snapshots` (positional, any number) | `russosphere/russosphere_snapshot.json`, `gan/russosphere_snapshot.json`, `russosphere/russosphere_embed_snapshot.json` under `webapp/public/data/` | Snapshot files to process. |

### `analyze_porosity.py`

Extracts the traces of porosity from the Russian-language sphere to the French
far right: media reuse (a media hash seen first on the Russian side, then on
the French side, with the delay), the `france_targeting` theme carried in both
languages, and adversary domains cited on both sides. It publishes a handful
of named, verifiable traces, never an inflated volume; tiers T1 and T2 only.
Its parser takes no options beyond `--help`.

- **Reads:** `channels`, `messages`, and `channel_scores`.
- **Writes:** `webapp/public/data/russosphere/porosity_snapshot.json`.

```bash
uv run python scripts/analyze_porosity.py
```

### `mine_episodes.py`

Generalizes `analyze_porosity.py` to several cross-side pivots without a
curated list. An episode is a pivot shared between a Russian-side origin
channel and a French-side channel, with timestamps: the same media hash, the
same exact URL, or a forward. Each episode is named by its salient TF-IDF
terms, and corroborated when several pivot types link the same pair.

- **Extras:** `embed`, unless you pass `--no-embeddings`.
- **Reads:** `channels` and `messages`.
- **Writes:** `webapp/public/data/<mission>/episodes_discovered.json`.

```bash
uv run --extra embed python scripts/mine_episodes.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose bundle receives the file. |
| `--min-corroboration` | `1` | Keep only episodes corroborated by at least this many pivot types. |
| `--no-embeddings` | off | Do not load the embedding model (`pourquoi_embedding` stays `null`). |

### `build_gan_footprint.py`

GAN footprint readout, an OPSEC self-assessment for the GAN mission: which
non-adversary channels originate talk about the carrier strike group, which
adversary channels amplify it, how it circulates between those channels, and
how often the carrier is mentioned, by month. It crawls nothing, has no
`argparse` parser, and takes no arguments.

- **Reads:** channels tagged by `tag_gan.py`, `messages`, `edges`, and
  `webapp/public/data/russosphere/russosphere_snapshot.json`.
- **Writes:** `webapp/public/data/russosphere/gan_footprint.json`.

```bash
uv run python scripts/build_gan_footprint.py
```

### `build_commenters.py`

Aggregates the `comments` table per channel for the channel drawer: discussion
engagement and recurring commenters. Comment text is not exported.

> [!CAUTION]
> The output carries each recurring commenter's Telegram identifier and
> username, the personal data of private individuals, into the web app bundle.

- **Reads:** `comments`.
- **Writes:** `webapp/public/data/<mission>/commenters.json`.

```bash
uv run python scripts/build_commenters.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose bundle receives the file. |

### `export_static.py`

The static exporter: it materializes the web app's bundle with the same
functions as the pipeline, without reimplementing any logic, and scrubs
secrets by key and by value. It is idempotent.

- **Reads:** `channel_scores`, `channels`, `edges`, `episodes`, and the
  analysis snapshots already in the mission directory.
- **Writes:** in `webapp/public/data/<mission>/`: `channels.json`,
  `channels_index.json`, `channels/`, `graph.json`, `themes.json`,
  `tasking.json`, `episodes/`, and `manifest.json`.

```bash
uv run python scripts/export_static.py --mission gan
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to export. |
| `--out` | `webapp/public/data/<mission>/` | Output directory. |
| `--public` | off | Reduced bundle, aggregates only. |
| `--no-snapshots` | off | Do not relocate the community and porosity snapshots. |
| `--js-twins` | off | Also emit the legacy `.js` twins (a `file://` fallback). |

### `build_stories.py`

The final stage. Builds `stories.json` for the narrative selector: each story
is a set of named, dated phases, and selecting a phase filters the galaxy. It
merges a story derived from the data (the porosity story, rebuilt from
`porosity_snapshot.json`) with the editorial stories in
`src/missions/<mission>/stories.py`. Handles are resolved against the bundle;
a story with missing channels is marked `data_status: "partial"`. It uses no
database.

- **Reads:** `channels_index.json` and `porosity_snapshot.json` in the bundle.
- **Writes:** `stories.json` in the bundle.

```bash
uv run python scripts/build_stories.py --mission gan
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to build. |
| `--out` | `webapp/public/data/<mission>/` | Bundle directory. |

## Parallel classification tracks

Two parallel tracks classify channels and label communities: the paid Mistral
track and a free local embedding track. Both write to their own table or
snapshot, never to `channels` or `channel_scores`, so the explainable score
and the default bundle stay intact. Neither contacts Telegram.

### `classify_channels_llm.py`

Samples each channel's text messages and asks Mistral for a high-level
classification (`is_gan_footprint`, `is_france_ukraine`, `actor_type`,
`themes`, `confidence`, `rationale`). Results are cached offline, so re-runs
are free.

- **Extras:** `llm` and `MISTRAL_API_KEY`; `--dry-run` needs neither.
- **Reads:** `channels` and `messages`.
- **Writes:** `channel_llm_scores` (upsert).

```bash
uv run python scripts/classify_channels_llm.py --mission gan --limit 50 --dry-run
```

```bash
uv run --extra llm python scripts/classify_channels_llm.py --mission gan --limit 50 --budget-usd 2.0
```

<details>
<summary>All flags of <code>classify_channels_llm.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose channels to classify. |
| `--limit` | `50` | Number of channels. |
| `--sample-size` | `40` | Messages per channel. |
| `--min-relevance` | `0.0` | Cost filter: classify only channels whose relevance signal in `channels.extra` reaches this value. |
| `--model` | `MISTRAL_MODEL` or `mistral-large-latest` | Mistral model. |
| `--dry-run` | off | No network; print the prompts. |
| `--budget-usd` | `0.0` | Estimated cost cap in US dollars (`0` = no cap). |

</details>

### `label_communities_llm.py`

Reads the lexical community snapshot and, for each community, sends its most
representative channels and their per-channel classifications to Mistral for
one high-level label. It writes a parallel snapshot with the same shape as the
lexical one, for a field-by-field comparison; the lexical snapshot is never
modified. Labels and rationales pass through
`src/labeling/aggregate.py::_redact_providers`, so no provider name reaches an
export.

- **Extras:** `llm` and `MISTRAL_API_KEY`; `--dry-run` needs neither.
- **Reads:** `webapp/public/data/<mission>/<mission>_snapshot.json` and
  `channel_llm_scores`. `analyze_communities.py` names its snapshot
  `russosphere_snapshot.json` in every mission directory, so the input exists
  only for `russosphere`.
- **Writes:** `webapp/public/data/<mission>/<mission>_llm_snapshot.json`.

```bash
uv run python scripts/label_communities_llm.py --mission russosphere --top-n 6 --dry-run
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to label. |
| `--top-n` | `6` | Representative channels per community. |
| `--model` | `MISTRAL_MODEL` or `mistral-large-latest` | Mistral model. |
| `--dry-run` | off | No network; print the prompts. |
| `--budget-usd` | `0.0` | Estimated cost cap in US dollars (`0` = no cap). |

### `classify_channels_embed.py`

The local mirror of `classify_channels_llm.py`: same channel selection, same
sampling, same output table, but the classification comes from a local
sentence-transformers embedding, at no cost and deterministically. Rows are
written under the model's name, so the two tracks compare directly.

- **Extras:** `embed`.
- **Reads:** `channels` and `messages`.
- **Writes:** `channel_llm_scores`, unless `--dry-run`.

```bash
uv run --extra embed python scripts/classify_channels_embed.py --mission gan --limit 50 --dry-run
```

<details>
<summary>All flags of <code>classify_channels_embed.py</code></summary>

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose channels to classify. |
| `--limit` | `50` | Number of channels. |
| `--sample-size` | `40` | Messages per channel. |
| `--min-relevance` | `0.0` | Classify only channels whose relevance signal in `channels.extra` reaches this value. |
| `--model` | `IDEFIX_EMBED_MODEL` or the encoder default | sentence-transformers model. |
| `--theme-threshold` | `0.2` | Minimum cosine similarity to keep a theme (to be calibrated). |
| `--flag-threshold` | `0.3` | Minimum cosine similarity for the mission's target flag (to be calibrated). |
| `--dry-run` | off | No database write; print the results. |

</details>

### `calibrate_text_sim.py`

Helps calibrate the `TEXT_SIM` and `TRANSLATION` thresholds for the local
embedding model. The default thresholds were set for another model and do not
transfer. It samples messages, computes the distribution of cosine
similarities between pairs from distinct channels, and prints percentiles and
example pairs around candidate thresholds, so the analyst can choose the cuts
on real data.

- **Extras:** `embed`.
- **Reads:** `messages`.
- **Writes:** nothing; results go to the console.

```bash
uv run --extra embed python scripts/calibrate_text_sim.py --limit 800 --thresholds 0.6 0.7 0.8 0.9
```

| Flag | Default | Effect |
|---|---|---|
| `--limit` | `800` | Number of messages sampled. |
| `--model` | `IDEFIX_EMBED_MODEL` or the encoder default | sentence-transformers model. |
| `--thresholds` | `0.6 0.7 0.8 0.85 0.9` | Candidate thresholds to inspect. |

## Labelling and gold

Building ground truth: a stratified batch, aggregation of several judges, a
validated gold file, and the channel-level gold derived from external sources.
None of these scripts contacts Telegram or the network.

### `build_label_batch.py`

Builds a reproducible, stratified batch of messages to label. Two France
gates apply: a channel pre-filter on `channels.extra.fr_score`, then at least
one France keyword in the message itself. A TF-IDF cosine link to a claim is
computed; items whose link falls below `--min-claim-proximity` go to a manual
screening file instead of the batch.

- **Reads:** `messages`, `episodes`, and `channels`.
- **Writes:** `data/annotations/batch-20260604.jsonl` (named after the batch
  identifier) and `data/annotations/batch-20260604__needs_manual_screening.jsonl`.

```bash
uv run python scripts/build_label_batch.py --n 300 --batch-id batch-20260604
```

| Flag | Default | Effect |
|---|---|---|
| `--n` | `300` | Batch size. |
| `--batch-id` | `batch-` followed by today's date (`YYYYMMDD`) | Batch identifier. |
| `--min-fr-score` | `0.0` | Channel `fr_score` floor (`0.0` turns it off; the France filter applies per message). |
| `--min-claim-proximity` | `0.04` | Claim-proximity threshold below which an item goes to screening. |
| `--seed` | `42` | Random seed. |

### `aggregate_labels.py`

Aggregates the judges' files for a batch, computes agreement (Cohen's or
Fleiss' kappa), and splits the items into gold candidates and an arbitration
queue, with the judges anonymized. It also writes a template for human
arbitration: copy it to `__arbitration_resolved.jsonl`, fill in each verdict,
rationale, and sources, then run `finalize_gold.py`.

- **Reads:** `data/annotations/judgments/batch-001__*.jsonl` (one file per
  judge).
- **Writes:** in `data/annotations/`: `batch-001__agreement.json`,
  `batch-001__gold_candidates.jsonl`, `batch-001__arbitration_queue.jsonl`, and
  `batch-001__arbitration_resolved.template.jsonl`.

```bash
uv run python scripts/aggregate_labels.py --batch-id batch-001
```

| Flag | Default | Effect |
|---|---|---|
| `--batch-id` | required | Batch identifier, for example `batch-001`. |
| `--min-judges` | `2` | Minimum number of judges for an item to be gold-eligible; below it, the item goes to arbitration. |
| `--allow-partial` | off | Proceed even if a judge file has validation errors. |

### `finalize_gold.py`

Merges the gold candidates and the human arbitration decisions into
`gold.jsonl`. Only labels that pass Pydantic validation are kept. A human
decision supersedes an automatic candidate for the same item; a changed verdict
for an item already finalized at the same authority is reported as a conflict
and the existing label is kept. Re-runs are idempotent; the final count is
printed.

- **Reads:** in `data/annotations/`: `batch-001__gold_candidates.jsonl`,
  `batch-001__agreement.json`, `batch-001__arbitration_resolved.jsonl` (if
  present), and the batch file.
- **Writes:** `data/annotations/gold.jsonl`.

```bash
uv run python scripts/finalize_gold.py --batch-id batch-001
```

| Flag | Default | Effect |
|---|---|---|
| `--batch-id` | required | Batch identifier. |
| `--batch-file` | `data/annotations/` followed by the batch identifier and `.jsonl` | Path to the batch file. |

### `build_channel_digests.py`

Builds one digest per active channel, for labelling at channel level
(propagator, legitimate, or mixed) rather than message level: volume, time
window, share of anti-France messages, prior credibility, who the channel
forwards and who forwards it, and representative anti-France samples.

- **Reads:** `channels` and `messages`.
- **Writes:** `data/annotations/channel_digests.jsonl` (for an LLM judge) and
  `data/annotations/channel_digests.md` (for a human reader).

```bash
uv run python scripts/build_channel_digests.py --min-msgs 50 --samples 5
```

| Flag | Default | Effect |
|---|---|---|
| `--min-msgs` | `50` | Message threshold for an active channel. |
| `--samples` | `5` | Anti-France samples per channel. |

### `derive_channel_gold.py`

Derives the channel-level gold (suspect or benign) from external gold files.
It reads neither `channels.json` nor any scorer output, so the gold is not
circular. The external files it needs do not exist yet (see
[`docs/limitations.md`](../docs/limitations.md#d12)).

- **Reads:** `data/eval/gold_episode_*.json` and
  `data/eval/organic_control_*.json`, or the files you pass.
- **Writes:** `data/eval/channel_gold.json` only.

```bash
uv run python scripts/derive_channel_gold.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission. |
| `--episodes` | the `gold_episode_*.json` files | Paths of the gold episode files. |
| `--organic` | the `organic_control_*.json` files | Paths of the organic control corpora. |

### `bootstrap_baseline.py`

Writes a baseline of legitimate French channels across media, institutions,
academia, and culture, from a list held in the script. The channels are
external to the scorer's inputs and serve as a control group for false
positives. It has no `argparse` parser and takes no arguments.

- **Reads:** nothing.
- **Writes:** `data/eval/baseline_organic_fr.json`.

```bash
uv run python scripts/bootstrap_baseline.py
```

## Evaluation and falsification

The falsification programme asks whether the suspicion score measures
manipulation or only a structural position in the graph. Most of these scripts
read a static snapshot, `data/channels.json` and `data/graph.json`, and write
their reports under `data/eval/`, which is not tracked.

> [!IMPORTANT]
> The harness does not yet run from a clean clone: only
> `prep_eval_inputs.py` writes the snapshot files, and it reads Supabase over
> REST rather than the local database. See
> [`docs/limitations.md`](../docs/limitations.md#d12) and, for two scripts that
> were mis-specified, [`docs/limitations.md`](../docs/limitations.md#d11).

### `_eval_common.py`

A shared module, not a script: loaders for `data/channels.json` and
`data/graph.json`, rank and set helpers (Spearman, Jaccard, top-k), and
`write_report`, which writes a JSON report under `data/eval/`.

### `prep_eval_inputs.py`

Rebuilds the evaluation snapshot from Supabase over REST: the scored channel
payloads from `channel_scores` and the graph from `edges`. Credentials come
from the environment, never from the code. It is idempotent.

- **Reads:** Supabase REST, with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
  (or `SUPABASE_KEY`).
- **Writes:** `data/channels.json` and `data/graph.json`.

```bash
uv run python scripts/prep_eval_inputs.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission whose scores to fetch. |

### `eval_ablation_centrality.py`

Experiment 1, the null-baseline ablation: is the suspicion score more than
graph centrality or activity? The score is falsified if, for raw in-degree or
eigenvector centrality, Spearman's ρ exceeds 0.90 or the top-50 Jaccard index
exceeds 0.80. It prints `PASS` or `FALSIFIED`. It has no `argparse` parser.

- **Reads:** `data/channels.json` and `data/graph.json`.
- **Writes:** `data/eval/ablation_centrality.json`.

```bash
uv run python scripts/eval_ablation_centrality.py
```

### `eval_discriminant_organic.py`

Experiment 3: can the system tell hostile coordination from organic
co-posting (activism, virality, a media outlet reposting itself)? Family (c)
fires identically for both; only the severity boosts discriminate. The script
measures how much of the suspicion gap among highly coordinated channels the
boosts explain, and lists organic candidates for a human to check. It has no
`argparse` parser.

- **Reads:** `data/channels.json`.
- **Writes:** `data/eval/discriminant_organic.json`.

```bash
uv run python scripts/eval_discriminant_organic.py
```

### `eval_episode_recovery.py`

Experiment 2: does the top-k of suspicion recover a documented operation? The
test episode is the Dugin cluster, using its membership only and ignoring the
dossier's own scores. Because that membership comes partly from the same
pipeline, the test is indicative only. A non-circular test needs an external
seed list in `data/eval/gold_episode_*.json`, which the script uses when
present. It has no `argparse` parser.

- **Reads:** `webapp/public/data/russosphere/dugin_cluster.json`,
  `data/channels.json`, and `data/eval/gold_episode_*.json`.
- **Writes:** `data/eval/episode_recovery.json`.

```bash
uv run python scripts/eval_episode_recovery.py
```

### `eval_organic_control.py`

Experiment 3b, a false-positive check: are documented, non-hostile
coordination groups surfaced as high-suspicion pockets? Templates under
`data/eval/templates/` are ignored. It has no `argparse` parser.

- **Reads:** `data/eval/organic_control_*.json` and `data/channels.json`,
  falling back to `webapp/public/data/russosphere/channels.json`.
- **Writes:** `data/eval/organic_control.json`.

```bash
uv run python scripts/eval_organic_control.py
```

### `eval_france_targeting_audit.py`

Experiment 4, a precision audit of the France perimeter: `france_targeting` is
a lexicon, not a classifier. The script samples channels by score band,
re-scores their most France-targeting messages, and lists the matched terms
with the text, so a human can judge substantial targeting against incidental
mention. It has no `argparse` parser.

- **Reads:** `data/channels.json` and message text from PostgreSQL.
- **Writes:** `data/eval/france_targeting_audit.json`, material to label.

```bash
uv run python scripts/eval_france_targeting_audit.py
```

### `eval_scoring_significance.py`

Tests whether the rigorous suspicion score (one minus the combined p-value,
modulated) separates suspect from benign channels better than plain
centrality, with Wilson intervals, ROC-AUC, a permutation test of the ranking,
and a calibration curve. It exits at once without the channel gold.

- **Reads:** `data/channels.json`, `data/graph.json`, and
  `data/eval/channel_gold.json` (from `derive_channel_gold.py`).
- **Writes:** `data/eval/scoring_significance.json`.

```bash
uv run python scripts/eval_scoring_significance.py --k 20 50 100
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission recorded in the report. |
| `--k` | `20 50 100` | Values of k for the top-k metrics. |
| `--permutations` | `2000` | Number of permutations for the significance test. |

### `eval_embedding_discrimination.py`

Experiment f: does the embedding space separate organic French channels from
the scored population? It reports ROC-AUC, the silhouette score, and a t-SNE
projection. It calls the scorer's own function
(`src/scorer/embedding_signals.py::compute_channel_embeddings`), so the
experiment and the deployed family share one code path. It refuses to report
when the mission's anchors did not resolve, and reports the result as
inconclusive with fewer than ten channels in a class. The plot is skipped when
`matplotlib`, which no extra installs, is absent.

- **Extras:** `embed`.
- **Reads:** `data/eval/baseline_organic_fr.json`, `data/channels.json`, and
  message text from PostgreSQL.
- **Writes:** `data/eval/embedding_discrimination_russosphere.json` (named
  after the mission) and, with `matplotlib`, the matching `.png`.

```bash
uv run --extra embed python scripts/eval_embedding_discrimination.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission ID. |

### `eval_mistral_classification.py`

Evaluates the Mistral classification against an independent human gold
(precision, recall, F1, overall and at k, and an `actor_type` confusion matrix)
and against the lexical baseline (top-k Jaccard, Spearman between Mistral
confidence and lexical relevance), with the total estimated cost. With
`--model` naming a sentence-transformers model, it evaluates the embedding
track instead.

- **Reads:** `channel_llm_scores` and `channels`, and the human gold
  `data/eval/gold_gan_footprint.json` for `gan` or
  `data/eval/gold_france_ukraine.json` for the other missions.
- **Writes:** `data/eval/mistral_classification_gan.json`, or
  `embed_classification_gan.json` for the embedding track (named after the
  mission).

```bash
uv run python scripts/eval_mistral_classification.py --mission gan --k 10 20 50
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to evaluate. |
| `--target` | `gan_footprint` for `gan`, otherwise `france_ukraine` | Gold slug. |
| `--k` | `10 20 50` | Values of k. |
| `--model` | none | Filter on `channel_llm_scores.model`. |

### `eval_embeddings_classification.py`

An alias of `eval_mistral_classification.py` with `--model` preset to the
sentence-transformers model, so it evaluates only the rows written by
`classify_channels_embed.py`. The human gold is shared with the Mistral track,
for a direct comparison of quality and cost.

- **Reads and writes:** as `eval_mistral_classification.py`.

```bash
uv run python scripts/eval_embeddings_classification.py --mission gan
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | Mission to evaluate. |
| `--target` | `gan_footprint` for `gan`, otherwise `france_ukraine` | Gold slug. |
| `--k` | `10 20 50` | Values of k. |
| `--model` | `IDEFIX_EMBED_MODEL` or the encoder default | sentence-transformers model to filter on. |

## Inspection

### `detect_clusters.py`

Detects coordinated clusters on the forward graph: loads the weighted
forward graph (origin to relay), optionally restricts it to the k-hop
neighbourhood of a seed channel, detects communities (igraph multilevel,
weighted Louvain), scores each on coordination patterns, and prints the ranked
clusters with the reasons.

- **Reads:** `messages` (the forward edges).
- **Writes:** nothing; results go to the console.

```bash
uv run python scripts/detect_clusters.py --seed @Dugin_Aleksandr --hops 5
```

| Flag | Default | Effect |
|---|---|---|
| `--seed` | none (whole graph) | Seed channel, as `@handle`. |
| `--hops` | `5` | Neighbourhood radius around the seed. |

### `compare_snapshots.py`

Temporal diff of the community snapshots, to detect network reconfigurations:
it pulls the analytics and embedding snapshots stored in Supabase, if present,
and compares channels, communities, and embeddings.

- **Reads:** Supabase `community_snapshots`, with `SUPABASE_URL` and
  `SUPABASE_KEY`.
- **Writes:** `data/russosphere/snapshot_diff.json`; the directory is
  `data/gan/` for `gan` and `data/dircom/` for `france_ukraine`.

```bash
uv run python scripts/compare_snapshots.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | `russosphere` | One of `russosphere`, `gan`, `france_ukraine`. |

## Supabase utilities

Tools for the hosted Supabase deployment, reached over REST because the
PostgreSQL port can be blocked on the deployment network. The default path,
the local database, does not need them.

### `export_via_rest_api.py`

Rebuilds the scored part of the bundle directly from Supabase
`channel_scores`, without re-scoring and without the graph. Community
snapshots and episodes are out of its scope. It writes relative to the current
directory, so run it from the repository root.

- **Reads:** Supabase REST, with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
  (or `SUPABASE_KEY`).
- **Writes:** in `webapp/public/data/<mission>/`: `channels_index.json`,
  `channels/`, and `manifest.json`.

```bash
uv run python scripts/export_via_rest_api.py --mission russosphere
```

| Flag | Default | Effect |
|---|---|---|
| `--mission` | every mission with scores | A single mission. |

### `test_supabase_connection.py`

Connects to the database in `DATABASE_URL`, prints the server version, checks
that the expected tables exist, and prints row counts for `channels`,
`messages`, and `edges`. It is read-only and, despite its name, works
with any PostgreSQL database. It has no `argparse` parser and takes no
arguments.

- **Reads:** `DATABASE_URL`.
- **Writes:** nothing.

```bash
uv run python scripts/test_supabase_connection.py
```

### `bench.py`

A minimal runtime benchmark: corpus size counted over Supabase REST, the
embedding cache hit rate, and encoding throughput with and without the cache.
It needs `SUPABASE_URL` and a key at import, has no `argparse` parser, and
takes no arguments.

- **Extras:** `embed`.
- **Reads:** Supabase REST and `data/embed_cache/`.
- **Writes:** `docs/metrics/perf.json`.

```bash
uv run --extra embed python scripts/bench.py
```

### `EXPORT_AND_DEPLOY.ps1`

A PowerShell script from the hosted deployment: it activates `.venv`, loads
`.env` if `DATABASE_URL` is unset, runs `export_static.py` for `russosphere`
and `gan`, then stages, commits, and pushes `webapp/public/data/` for Vercel to
redeploy.

> [!CAUTION]
> Do not run it. It commits and pushes the analyst bundles, which this
> repository no longer tracks, and they can carry commenters' personal data
> (see [`build_commenters.py`](#build_commenterspy)). A push cannot be taken
> back. See [`CONTRIBUTING.md`](../CONTRIBUTING.md#data-and-personal-data).
