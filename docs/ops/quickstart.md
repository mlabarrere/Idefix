# Quickstart

Clone, run one command, open the interface. This path uses the public corpus
(dataset `v1.0.0`) and needs **no Telegram account, no credentials and no
`.env`**.

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) with Compose v2, **running** | Compose 2.17+ | Local PostgreSQL 17 |
| [uv](https://docs.astral.sh/uv/) | recent | Python environment; it can install Python 3.14 itself |
| [Node.js](https://nodejs.org/) with npm | 20.19+ or 22.12+ | Analyst interface (Vite) |
| git | — | Clone |

Disk space: the downloaded files plus the database volume, plus PyTorch if you
keep the embedding stages. File sizes are listed in
[`../../dataset/manifest.json`](../../dataset/manifest.json).

## 1. Clone

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
```

## 2. One command

```bash
uv run --extra embed python scripts/bootstrap.py   # macOS, Linux, Windows
make setup                                         # same thing, where make is available
```

It runs five steps in order. Each is also a subcommand, so you can run or
re-run one alone (`uv run python scripts/bootstrap.py db`, for instance):

| Step | Subcommand | What it does |
|---|---|---|
| 1 | `check` | Python 3.14, Docker daemon and Compose v2, Node and npm, a free database port, the `embed` extra, a valid manifest. Prints a fix for each failure |
| 2 | `fetch` | Reads `dataset/manifest.json`, downloads each file into `dataset/downloads/`, verifies size and SHA-256, unpacks the archives it lists |
| 3 | `db` | Starts the Compose service `db` and waits until healthy. **If the database is empty**: restores the snapshot, then runs `alembic upgrade head` (the additive migrations after the snapshot's revision). A database that already holds data is left untouched — no restore, no migration |
| 4 | `pipeline` | `scripts/pipeline.py --mission all` against that database: every offline stage, no Telegram, no paid API. Recomputes the derived tables the snapshot carries from an earlier run. Within `all`, it runs only on a database the bootstrap restored itself, until one run has completed |
| 5 | `webapp` | `npm ci` when `node_modules` is missing or stale, then `npm run dev` |

At the end it prints how long each step took and the `DATABASE_URL` it used.

The bootstrap never reads or writes `.env`, and never deletes data. It hands
each step the local `DATABASE_URL` itself, and gives Docker Compose an empty
env file, so Compose does not read `.env` either:

```
postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

These credentials are local-only; the port is bound to `127.0.0.1`.

## 3. Open the interface

<http://localhost:5173> — Vite prints the exact URL when it is ready. `Ctrl+C`
stops the dev server; the database keeps running.

The browser reads only the JSON bundles the pipeline wrote under
`webapp/public/data/<mission>/`. It never contacts the database and never calls
Telegram.

## Options

```
uv run --extra embed python scripts/bootstrap.py [check|fetch|db|pipeline|webapp|all]
       [--dataset-dir PATH] [--manifest PATH] [--mission M]
       [--skip-embeddings] [--no-webapp]
```

| Option | Effect |
|---|---|
| `--mission M` | Run the pipeline for one mission (`russosphere`, `france_ukraine`, `gan`) instead of `all` |
| `--skip-embeddings` | Skip the embedding-based stages: no `embed` extra needed (drop `--extra embed`), no model download |
| `--no-webapp` | `all` stops after the pipeline (headless machines, CI) |
| `--dataset-dir PATH` | Copy the release files from a local folder instead of downloading them |
| `--manifest PATH` | Use another manifest than `dataset/manifest.json` |

| Environment variable | Effect |
|---|---|
| `IDEFIX_DB_PORT` | Host port of the local database (default `5433`). Compose and the injected `DATABASE_URL` both follow it |
| `IDEFIX_DATASET_BASE_URL` | Mirror: fetch `<base>/<file name>` instead of the URLs pinned in the manifest. Hashes are still verified |

Make targets wrap the subcommands:

| Target | Runs |
|---|---|
| `make setup` | `all`, with the `embed` extra |
| `make data` | `fetch` |
| `make db-up` | `db` — start; restore and migrate only an empty database |
| `make db-down` | `docker compose stop` — stops the database container, keeps its data |
| `make pipeline [MISSION=russosphere]` | `pipeline`, with the `embed` extra |
| `make webapp` | `webapp` |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `check`: db port already in use | Something already listens on `5433` | Pick another port and re-run: `export IDEFIX_DB_PORT=55432` (bash/zsh) or `$env:IDEFIX_DB_PORT=55432` (PowerShell). On Windows, Hyper-V may reserve ports: `netsh interface ipv4 show excludedportrange protocol=tcp` |
| `check`: Docker daemon not reachable | Docker is installed but not running | Start Docker Desktop (Windows/macOS) or the service (Linux: `sudo systemctl start docker`), wait until it is ready, re-run |
| `check`: permission denied on the Docker socket (Linux) | Your user is not in the `docker` group | `sudo usermod -aG docker $USER`, log out and back in |
| `check`: the `embed` extra is not installed | Launched with plain `uv run` | Re-run with `uv run --extra embed ...`, or pass `--skip-embeddings` |
| Garbled accented characters or `UnicodeEncodeError` on Windows | Console code page is not UTF-8 | `$env:PYTHONUTF8="1"` (PowerShell) or `set PYTHONUTF8=1` (cmd) before the command |
| A step failed half-way | — | Fix the cause and re-run the same command. Verified downloads are kept, a non-empty database is not restored again, and the pipeline runs again until one run has completed |
| You want the pipeline to run again | `all` runs it automatically only until one run has completed, and only on a database it restored itself | `uv run --extra embed python scripts/bootstrap.py pipeline` (or `make pipeline`) always runs it |
| `db` reports the schema is behind | The database already held data, so `db` did not migrate it | Run the printed command: `uv run alembic upgrade head`, with the `DATABASE_URL` above in the environment |
| The pipeline failed at one stage | — | `uv run python scripts/pipeline.py --list` shows the stages; resume with `--from STAGE`, with the `DATABASE_URL` above in the environment |
| `db` says the database was not restored by the bootstrap | An interrupted restore, or a database you filled yourself | It is left untouched: the bootstrap restores only into an empty database, and `all` will not run the pipeline on it automatically (`bootstrap.py pipeline` does) |
| No internet access to GitHub | Downloads fail | Use a mirror (`IDEFIX_DATASET_BASE_URL`) or copy the files and pass `--dataset-dir /path/to/files`. Hashes are verified either way |
| Blank page or empty states in the webapp | No bundle yet: the pipeline did not run or did not finish | `uv run --extra embed python scripts/bootstrap.py pipeline`, and read the failing stage |

## Verify a checkout without Docker

Nothing here touches Docker, the network or Telegram.

```bash
uv run --extra dev python -m pytest -x -q    # offline test suite
cd webapp && npx tsc --noEmit && cd ..       # strict typecheck
uv run python scripts/check_docs.py          # documentation integrity
```

## Before you interpret anything

Read [`../limitations.md`](../limitations.md). Several defects materially affect
how the ranking should be read. One concerns the public corpus directly
(**D18**): the snapshot carries derived tables from an earlier pipeline run.
The bootstrap recomputes them; cite only regenerated numbers, and do not expect
them to match anything in the archive.

## Next

- [Full install guide](./install.md) — manual setup, managed database, Telegram
  collection
- [What the corpus contains](../../dataset/DATASHEET.md)
- [What Idéfix is and is not](../product/product.md)
- [Method](../method/01-problem-and-scope.md)
