# Quickstart: from a fresh clone to the analyst interface

This tutorial takes you from an empty machine to the Idéfix analyst interface
running on the public corpus (dataset `v1.0.0`). You install the tools, restore
the corpus into a local PostgreSQL database, run the offline pipeline, and open
the interface in your browser. You need **no Telegram account, no credentials,
and no `.env` file**.

It describes Idéfix version 0.4.1. Each step shows the command, the output you
should expect, and what to check before you move on. When a step fails, the
links under it lead to the fix in [Troubleshooting](./troubleshooting.md).

> [!TIP]
> Once the prerequisites are installed (steps 1 and 2), one command runs
> steps 3 to 7 in a row: `uv run python scripts/bootstrap.py`. This tutorial
> runs them one at a time so that you can check each result.

## Contents

- [Before you begin](#before-you-begin)
- [Install the prerequisites](#install-the-prerequisites)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Windows Subsystem for Linux](#windows-subsystem-for-linux)
  - [Proxy and corporate TLS](#proxy-and-corporate-tls)
  - [Synchronized folders (OneDrive, Dropbox, iCloud)](#synchronized-folders-onedrive-dropbox-icloud)
- [Step 1: Clone the repository](#step-1)
- [Step 2: Install the Python environment](#step-2)
- [Step 3: Check the prerequisites](#step-3)
- [Step 4: Download the dataset](#step-4)
- [Step 5: Start and restore the database](#step-5)
- [Step 6: Run the pipeline](#step-6)
- [Step 7: Open the analyst interface](#step-7)
- [Step 8: Verify the checkout](#step-8)
- [Stop, restart, and update](#stop-restart-and-update)
- [Start over](#start-over)
- [Bootstrap reference](#bootstrap-reference)
- [Next](#next)

## Before you begin

- [ ] A Windows 10 or 11, macOS, or Linux computer on which you may install
      software (Docker Desktop needs administrator rights).
- [ ] About 5 GB of free disk space on Windows, or 8 GB on Linux (see the table
      below).
- [ ] 60 to 90 minutes. Most of it is the pipeline, which runs unattended.
- [ ] Internet access to GitHub, PyPI, the npm registry, Docker Hub, and the
      Hugging Face Hub, directly or through a proxy.
- [ ] A working folder outside OneDrive, Dropbox, or iCloud Drive (see
      [Synchronized folders](#synchronized-folders-onedrive-dropbox-icloud)).

What the setup writes to disk:

| What | Where | Size |
|---|---|---|
| Python environment | `.venv/` | about 1 GB on Windows; about 3 GB on Linux, where PyTorch brings NVIDIA's CUDA libraries for graphics cards |
| `uv` download cache | your user cache folder | up to the size of `.venv/` again; `uv cache clean` frees it |
| PostgreSQL 17 image | Docker | about 424 MB (a 118 MB download) |
| Database | Docker volume `idefix_pgdata` | about 360 MB |
| Embedding model | Hugging Face cache (`~/.cache/huggingface/`) | about 458 MB |
| Webapp dependencies | `webapp/node_modules/` | about 240 MB |
| Analyst bundles | `webapp/public/data/` | about 120 MB |
| Dataset files | `dataset/downloads/` | 45.5 MB |

How long it takes, measured on a GitHub-hosted Ubuntu runner (4 virtual CPUs,
16 GB of memory): installing the Python environment about 2 minutes; `check`,
`fetch`, and `db` under 30 seconds together; the pipeline about 55 minutes. On
the Windows 11 machine used to write this tutorial, the Python environment took
about 10 minutes to install and `npm ci` about 2 minutes.

> [!NOTE]
> The expected outputs below were captured on Windows 11 for steps 2, 3, 7,
> and 8, and on the GitHub-hosted Ubuntu runner for steps 4 to 6. Your paths,
> versions, speeds, and timings will differ; the structure and the row counts
> will not.

Where a command is the same in every shell, the tutorial shows it once, in a
`bash` block; it runs unchanged in PowerShell 7. Where the shells differ, it
shows a `bash` block and a `powershell` block.

## Install the prerequisites

You need four tools. Follow the section for your system, then go to
[Step 1](#step-1).

| Tool | Version | Why |
|---|---|---|
| [Git](https://git-scm.com/) | any recent | Clone the repository |
| [uv](https://docs.astral.sh/uv/) | any recent | Python environment; it installs Python 3.14 itself |
| [Node.js](https://nodejs.org/) with npm | 22.12 or later (20.19 is accepted, but Node.js 20 is past its end of life) | Analyst interface (Vite 8) |
| [Docker](https://docs.docker.com/get-docker/) with Compose | Compose 2.17 or later, engine **running** | Local PostgreSQL 17 |

A C compiler is **not** needed. Only Telegram collection (the `collect` extra)
needs one; see the [install guide](./install.md#optional-collect-your-own-data-from-telegram).

### Windows

Use **PowerShell 7**, not the Windows PowerShell 5.1 that ships with Windows.
Install it first, from any terminal:

```powershell
winget install --id Microsoft.PowerShell --source winget
```

Open **PowerShell 7** from the Start menu, then install the other tools:

```powershell
winget install --id Git.Git --source winget
winget install --id astral-sh.uv --source winget
winget install --id OpenJS.NodeJS.LTS --source winget
winget install --id Docker.DockerDesktop --source winget
```

Restart Windows if the Docker Desktop installer asks you to (it enables the
Windows Subsystem for Linux, WSL 2). Start **Docker Desktop**, accept its terms,
and wait until it reports **Engine running**. Then close PowerShell and open a
new PowerShell 7 window so that it sees the new `PATH`, and check the tools:

```powershell
git --version
uv --version
node --version
docker compose version
```

```text
git version 2.55.0.windows.5
uv 0.13.0 (4ecd0eff2 2026-10-09 x86_64-pc-windows-msvc)
v26.11.0
Docker Compose version v5.6.1
```

You should now see four version lines and no error. Your versions may be newer.

Finally, make Python print non-English text correctly in this terminal (add the
line to your profile, `notepad $PROFILE`, to keep it):

```powershell
$env:PYTHONUTF8 = "1"
```

> [!WARNING]
> **Windows PowerShell 5.1 pitfalls.** If `$PSVersionTable.PSVersion` prints
> `5.1`, you are in the wrong shell. In 5.1:
>
> - `&&` and `||` are parse errors ([details](./troubleshooting.md#ps51-ampersand)).
> - `>` and `Out-File` write UTF-16, which breaks a `.env` file
>   ([details](./troubleshooting.md#env-utf16)). Create `.env` with
>   `Copy-Item .env.example .env` instead.
> - `curl` is an alias of `Invoke-WebRequest`, not the real curl; type
>   `curl.exe` if you need curl.
>
> In both versions, a `Restricted` execution policy blocks `npm`
> ([fix](./troubleshooting.md#execution-policy)).

### macOS

Install the Xcode Command Line Tools (they provide Git), then
[Homebrew](https://brew.sh/) if you do not have it, then `uv` and Node.js:

```bash
xcode-select --install
brew install uv node
```

Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
(choose Apple silicon or Intel), start it, and wait until it reports
**Engine running**. Any other Docker engine with the Compose plugin 2.17 or
later also works. Check the tools:

```bash
git --version
uv --version
node --version
docker compose version
```

You should now see four version lines and no error.

### Linux

These commands are for Debian and Ubuntu; adapt the package manager for other
distributions. Install Git and Docker Engine with its Compose plugin, then let
your user run Docker:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker "$USER"
```

Log out and back in, so that the group change applies. Install `uv`, and
Node.js through [fnm](https://github.com/Schniz/fnm) (distribution packages of
Node.js are often too old):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://fnm.vercel.app/install | bash
source ~/.bashrc
fnm install --lts
```

Check the tools:

```bash
git --version
uv --version
node --version
docker compose version
```

You should now see four version lines and no error. If `docker` reports
`permission denied`, see [Docker socket](./troubleshooting.md#check-docker-permission).

### Windows Subsystem for Linux

You can run everything inside WSL 2 instead of Windows. Install a distribution
from PowerShell (as administrator), then restart:

```powershell
wsl --install -d Ubuntu-24.04
```

Inside WSL:

- Either install Docker Desktop on Windows and turn on **Settings → Resources →
  WSL integration** for your distribution, or install Docker Engine inside WSL
  as in [Linux](#linux).
- Install Git, `uv`, and Node.js as in [Linux](#linux).
- Clone into the Linux file system (for example `~/src/Idefix`), **not** under
  `/mnt/c/`. Files under `/mnt/c/` are slow to read from WSL and do not trigger
  Vite's file watching.

Your Windows browser reaches the interface at <http://localhost:5173>, because
WSL 2 forwards `localhost`.


### Proxy and corporate TLS

Many corporate networks send traffic through a proxy that inspects Transport
Layer Security (TLS) connections and re-signs them with the organization's own
root certificate. Behind such a proxy, set these variables in the terminal
before step 1.
Replace the example proxy address and certificate path with your
organization's.

```powershell
$env:HTTPS_PROXY = "http://proxy.example.com:8080"
$env:HTTP_PROXY = "http://proxy.example.com:8080"
$env:UV_NATIVE_TLS = "true"
$env:NODE_EXTRA_CA_CERTS = "C:\certs\corporate-root.pem"
git config --global http.sslBackend schannel
```

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export HTTP_PROXY=http://proxy.example.com:8080
export UV_NATIVE_TLS=true
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/corporate-root.pem
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

What each one does:

| Tool | Setting | Effect |
|---|---|---|
| All | `HTTPS_PROXY`, `HTTP_PROXY` | `uv`, `npm`, the dataset download, and the model download go through the proxy |
| `uv` | `UV_NATIVE_TLS` | Trusts the operating system's certificate store, which usually holds the corporate root |
| Node.js and `npm` | `NODE_EXTRA_CA_CERTS` | Adds the corporate root, as a PEM (Base64 text) certificate file, to Node.js's own list |
| Python (dataset and model downloads) | `SSL_CERT_FILE` | Linux and macOS: a bundle that includes the corporate root. Windows Python already trusts the Windows store |
| Git | `http.sslBackend schannel` | Windows: Git trusts the Windows store |
| Docker | Docker Desktop **Settings → Resources → Proxies** | Lets Docker pull `postgres:17-alpine` |

If GitHub release downloads stay blocked, download the two files listed in
[`dataset/manifest.json`](../../dataset/manifest.json) another way and use
`--dataset-dir` in step 4. Symptoms of a missing setting:
[`uv`](./troubleshooting.md#tls-uv), [`npm`](./troubleshooting.md#tls-npm),
[`fetch`](./troubleshooting.md#tls-python), [Git](./troubleshooting.md#tls-git),
[Docker](./troubleshooting.md#tls-docker),
[Hugging Face](./troubleshooting.md#hf-offline).


### Synchronized folders (OneDrive, Dropbox, iCloud)

Clone the repository outside any synchronized folder: for example
`C:\dev\Idefix` on Windows or `~/src/Idefix` elsewhere. Windows often puts
`Documents` and `Desktop` inside OneDrive without asking.

The setup writes hundreds of thousands of small files into `.venv/` and
`webapp/node_modules/`. A sync client uploads them all and locks files while it
does, which interrupts installs ([`os error 396`](./troubleshooting.md#onedrive-uv)).
If you must keep the clone in a synchronized folder, move the Python
environment out of it before step 2:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "C:\dev\venvs\idefix"
```

<a id="step-1"></a>

## Step 1: Clone the repository

Create a working folder outside any synchronized folder, and clone into it:

```powershell
New-Item -ItemType Directory -Force C:\dev | Out-Null
Set-Location C:\dev
git clone https://github.com/mlabarrere/Idefix.git
Set-Location Idefix
```

```bash
mkdir -p ~/src && cd ~/src
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
```

```text
Cloning into 'Idefix'...
remote: Enumerating objects: [...]
Receiving objects: 100% [...]
Resolving deltas: 100% [...]
```

You should now be in the `Idefix` folder, which contains `pyproject.toml`,
`docker-compose.yml`, and `dataset/manifest.json`. Every later command runs
from this folder.

If it fails: [certificate error](./troubleshooting.md#tls-git).

<a id="step-2"></a>

## Step 2: Install the Python environment

```bash
uv sync --extra embed --extra dev
```

```text
Using CPython 3.14.8 interpreter at: C:\Python314\python3.exe
Creating virtual environment at: .venv
Resolved 155 packages in 2ms
[...]
Installed 92 packages in 6m 14s
 + aiosqlite==0.22.1
 + alembic==1.18.4
[...]
```

`uv` creates `.venv/` and installs the base dependencies plus two extras:
`embed` (sentence-transformers and PyTorch, for the embedding stages) and `dev`
(tests and linters). If Python 3.14 is missing, `uv` first prints
`Downloading cpython-3.14...` and installs it. The package counts and the time
vary with the platform and the lock file.

Check the interpreter:

```bash
uv run python --version
```

```text
Python 3.14.8
```

You should now see `Python 3.14` followed by a patch number.

> [!TIP]
> Short of disk space? `uv sync --extra dev` leaves out PyTorch (several GB on
> Linux). Then add `--skip-embeddings` to the bootstrap commands in steps 3
> and 6: the pipeline drops its embedding stage, runs `mine_episodes` without
> embeddings, and never downloads the model.

If it fails: [`uv` not found](./troubleshooting.md#uv-not-found),
[certificate error](./troubleshooting.md#tls-uv),
[`os error 396` or access denied](./troubleshooting.md#onedrive-uv),
[`tgcrypto` build](./troubleshooting.md#tgcrypto-build) (only if you added
`--extra collect`).

<a id="step-3"></a>

## Step 3: Check the prerequisites

```bash
uv run --extra embed python scripts/bootstrap.py check
```

```text
== check ==
  [ ok ] python      3.14.8
  [ ok ] docker      daemon 29.9.2
  [ ok ] compose     5.6.1
  [ ok ] db port     127.0.0.1:5433 free
  [ ok ] node        v26.11.0, npm 12.2.0
  [ ok ] embeddings  sentence-transformers installed
  [ ok ] pipeline    scripts/pipeline.py present
  [ ok ] manifest    idefix-telegram-public-corpus 1.0.0 (2 files, 43.4 MB)
```

You should now see `[ ok ]` on every line. The bootstrap reports sizes in
binary units: 43.4 MB here is 45.5 million bytes. If an Idéfix database already
runs on this machine, the port line reads
`127.0.0.1:5433 (idefix database running)`, which is fine.

If a line says `[FAIL]`, the line under it names the fix:
[Docker missing](./troubleshooting.md#check-docker-missing),
[Docker not running](./troubleshooting.md#check-docker-daemon),
[Compose](./troubleshooting.md#check-compose),
[port in use](./troubleshooting.md#check-port),
[Node.js](./troubleshooting.md#check-node),
[`embed` extra](./troubleshooting.md#check-embed),
[Python](./troubleshooting.md#python-version).

<a id="step-4"></a>

## Step 4: Download the dataset

```bash
uv run python scripts/bootstrap.py fetch
```

```text
== fetch: idefix-telegram-public-corpus 1.0.0 ==
  idefix-corpus-v1.0.0.dump: downloading https://github.com/mlabarrere/Idefix/releases/download/dataset-v1.0.0/idefix-corpus-v1.0.0.dump
  idefix-corpus-v1.0.0.dump: 43.3 MB / 43.3 MB (100.0%) 51.6 MB/s
  idefix-corpus-v1.0.0.dump: ok (43.3 MB, SHA-256 verified)
  idefix-annotations-v1.0.0.tar.gz: downloading https://github.com/mlabarrere/Idefix/releases/download/dataset-v1.0.0/idefix-annotations-v1.0.0.tar.gz
  idefix-annotations-v1.0.0.tar.gz: 169.3 KB / 169.3 KB (100.0%) 6.5 MB/s
  idefix-annotations-v1.0.0.tar.gz: ok (169.3 KB, SHA-256 verified)
  idefix-annotations-v1.0.0.tar.gz: extracted 7 new file(s) into data/
warning: kept 1 local file(s) that differ from the release (delete them to take the release version): claims/claims_fr.jsonl
```

The bootstrap downloads the two files pinned in
[`dataset/manifest.json`](../../dataset/manifest.json) into
`dataset/downloads/`, checks their size and SHA-256, and unpacks the
annotations into `data/`. The final warning is expected: the repository tracks
its own copy of `data/claims/claims_fr.jsonl`, and the bootstrap never
overwrites a local file ([details](./troubleshooting.md#fetch-kept)).

Check the files:

```powershell
Get-ChildItem dataset\downloads -Name
```

```bash
ls -1 dataset/downloads
```

```text
idefix-annotations-v1.0.0.tar.gz
idefix-corpus-v1.0.0.dump
```

You should now see both files. Running `fetch` again prints
`ok (cached, SHA-256 verified)` and downloads nothing.

If it fails: [cannot download](./troubleshooting.md#fetch-download),
[certificate error](./troubleshooting.md#tls-python),
[interrupted](./troubleshooting.md#fetch-interrupted),
[hash mismatch](./troubleshooting.md#fetch-hash). Offline, copy the two files
from another machine and pass their folder:
`uv run python scripts/bootstrap.py fetch --dataset-dir D:\idefix-dataset`.

<a id="step-5"></a>

## Step 5: Start and restore the database

```bash
uv run python scripts/bootstrap.py db
```

```text
== db: PostgreSQL 17 on 127.0.0.1:5433 (compose project idefix) ==
[...]
 Volume "idefix_pgdata"  Created
 Container idefix-db-1  Created
 Container idefix-db-1  Started
 Container idefix-db-1  Waiting
 Container idefix-db-1  Healthy
  restoring idefix-corpus-v1.0.0.dump with pg_restore inside the container ...
  restored in 4.1 s
  alembic upgrade head ...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
  schema at alembic revision 0008; rows: channel_llm_scores 0, channel_scores 7313, channels 3699, comments 9241, edges 16275, episodes 0, evidence_dossiers 0, messages 166188, scores_run_meta 2
  DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

The bootstrap starts PostgreSQL 17 in Docker (port 5433, loopback only, user
and password `idefix`), restores the corpus into the empty database, and runs
`alembic upgrade head`. The corpus is already at revision 0008, the latest, so
there is nothing to migrate. The first run also pulls the `postgres:17-alpine`
image; Docker prints its progress where the output shows `[...]`, and in an
interactive terminal it redraws those lines in place.

**Checkpoint.** The `rows:` line must match the counts pinned in the manifest:

| Table | Rows |
|---|---|
| `channels` | <!-- fact:manifest.row_counts.channels -->3,699<!-- /fact --> |
| `messages` | <!-- fact:manifest.row_counts.messages -->166,188<!-- /fact --> |
| `comments` | <!-- fact:manifest.row_counts.comments -->9,241<!-- /fact --> |
| `edges` | <!-- fact:manifest.row_counts.edges -->16,275<!-- /fact --> |
| `channel_scores` | <!-- fact:manifest.row_counts.channel_scores -->7,313<!-- /fact --> |
| `scores_run_meta` | <!-- fact:manifest.row_counts.scores_run_meta -->2<!-- /fact --> |
| `channel_llm_scores`, `episodes`, `evidence_dossiers` | 0 |

To count the three source tables yourself at any time:

```bash
docker compose -p idefix exec -T db psql -U idefix -d idefix -c "SELECT (SELECT count(*) FROM channels) AS channels, (SELECT count(*) FROM messages) AS messages, (SELECT count(*) FROM comments) AS comments;"
```

```text
 channels | messages | comments
----------+----------+----------
     3699 |   166188 |     9241
(1 row)
```

You should now see those three counts. The pipeline in step 6 recomputes
`edges`, `channel_scores`, and `scores_run_meta`, so their counts can change
after it; `channels`, `messages`, and `comments` do not.

> [!CAUTION]
> The database now holds personal data. The `comments` table contains the
> identifiers, usernames, and messages of private individuals who commented in
> public Telegram groups. Read the terms of use in the
> [datasheet](../../dataset/DATASHEET.md) before you share, export, or publish
> anything from it.

If it fails: [port in use](./troubleshooting.md#check-port),
[could not start](./troubleshooting.md#db-start),
[not healthy](./troubleshooting.md#db-unhealthy),
[Docker certificate error](./troubleshooting.md#tls-docker),
[dump missing](./troubleshooting.md#db-not-fetched),
[row counts differ](./troubleshooting.md#db-row-counts),
[restore failed](./troubleshooting.md#db-restore-failed). If the output says
`the database already holds data ... left untouched`, a database from an
earlier run exists; the bootstrap never overwrites it
([details](./troubleshooting.md#db-left-untouched),
[shared by every clone](./troubleshooting.md#shared-database)).

<a id="step-6"></a>

## Step 6: Run the pipeline

The pipeline recomputes every derived table and writes the JavaScript Object Notation (JSON) bundles
that the interface reads. It contacts neither Telegram nor any paid application
programming interface (API). First, list its
stages:

```bash
uv run python scripts/pipeline.py --list
```

```text
Stages, in run order:
   1. build_edges                db-wide
                                 multiplex graph: table edges (upsert)
   2. tag_france                 db-wide
                                 channels.extra.fr_score (French keyword density)
   3. tag_gan                    db-wide
                                 channels.extra.gan_targeting (GAN lexicon)
   4. build_scores               russosphere, france_ukraine, gan
                                 channel_scores + scores_run_meta for the mission
   5. build_dossier              russosphere
                                 dugin_cluster.json, the scoring dossier of the registry episode
   6. analyze_communities        russosphere, france_ukraine, gan
                                 russosphere_snapshot.json (Leiden communities + bridges)
   7. analyze_communities_embed  russosphere, france_ukraine, gan [embeddings]
                                 <mission>_embed_snapshot.json (communities with embedding edges)
   8. precompute_galaxy_layout   russosphere, france_ukraine, gan
                                 x/y coordinates written into the galaxy snapshots
   9. analyze_porosity           russosphere
                                 porosity_snapshot.json (RU -> FR traces)
  10. mine_episodes              russosphere
                                 episodes_discovered.json (RU -> FR episodes)
  11. build_gan_footprint        russosphere
                                 gan_footprint.json (GAN theme readout)
  12. build_commenters           russosphere, france_ukraine, gan
                                 commenters.json (per-channel aggregate of the comments table)
  13. export_static              russosphere, france_ukraine, gan
                                 manifest, channels_index, channels/, graph, themes, episodes/
  14. build_stories              russosphere, france_ukraine, gan
                                 stories.json (narrative selector)
```

This list is the authoritative stage order. Each stage runs for every mission
it applies to before the next stage starts. Now run it (about an hour; leave
the terminal open):

```bash
uv run python scripts/bootstrap.py pipeline
```

```text
== pipeline: --mission all ==
 Container idefix-db-1  Running
 Container idefix-db-1  Waiting
 Container idefix-db-1  Healthy

=== [1/28] build_edges
    $ /home/runner/work/Idefix/Idefix/scripts/build_edges.py
[...]
--- ok: build_edges in 5.2s

=== [2/28] tag_france
[...]
=== [28/28] build_stories [gan]
    $ /home/runner/work/Idefix/Idefix/scripts/build_stories.py --mission gan
[...]
--- ok: build_stories [gan] in 0.7s

Stage timings:
  build_edges                                     5.2s
[...]
  total                                         54m05s
```

Each stage prints its own progress between the `===` and `--- ok` lines. The
first embedding stage downloads the sentence-transformers model (about 458 MB)
and may print `You are sending unauthenticated requests to the HF Hub`, which
is harmless ([details](./troubleshooting.md#hf-unauthenticated)).
`build_scores` and `export_static` take several minutes per mission and print
little while they work.

Check that the bundles exist:

```powershell
Get-ChildItem webapp\public\data -Name
```

```bash
ls -1 webapp/public/data
```

```text
france_ukraine
gan
russosphere
```

You should now see one folder per mission, and the run should have ended with
`Stage timings` and a `total` line, not with `FAILED`.

If it fails: the runner stops at the failing stage and tells you how to resume
with `--from` ([details](./troubleshooting.md#pipeline-failed)). See also
[model download blocked](./troubleshooting.md#hf-offline),
[`sentence_transformers` missing](./troubleshooting.md#module-sentence-transformers),
[`skipped`](./troubleshooting.md#pipeline-skipped).

> [!IMPORTANT]
> The restored corpus also carries derived tables from an earlier pipeline run.
> Cite only numbers that this pipeline regenerated, and do not expect them to
> match anything in the archive ([D18](../limitations.md#d18)).

<a id="step-7"></a>

## Step 7: Open the analyst interface

```bash
uv run python scripts/bootstrap.py webapp
```

```text
== webapp ==
  npm ci ...
[...]
added 282 packages, and audited 283 packages in 2m
[...]

Serving the analyst webapp: Vite prints the URL (default http://localhost:5173/). Ctrl+C stops it.
[...]

  VITE v8.3.5  ready in 8244 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

The bootstrap runs `npm ci` in `webapp/` when `node_modules/` is missing or
older than the lock file, then starts the Vite dev server. `npm` may print
warnings about blocked install scripts or deprecations; they are harmless
([details](./troubleshooting.md#webapp-install-scripts)).

Open <http://localhost:5173> in your browser.

You should now see the galaxy of the `russosphere` mission: the address bar
ends in `#/m/russosphere`, and the sidebar on the left holds the mission
switcher and the **Galaxy** and **Analysis** views (the labels follow the
language picked in the interface). The browser reads only the bundles under
`webapp/public/data/`; it never contacts the database or Telegram.

To stop the dev server, press <kbd>Ctrl</kbd>+<kbd>C</kbd> in its terminal. The
database keeps running.

If it fails: [blank page or empty states](./troubleshooting.md#blank-page),
[port 5173 in use](./troubleshooting.md#webapp-port),
[Node.js too old](./troubleshooting.md#webapp-ebadengine),
[`npm` certificate error](./troubleshooting.md#tls-npm),
[`npm.ps1` blocked](./troubleshooting.md#execution-policy).

<a id="step-8"></a>

## Step 8: Verify the checkout

These checks need neither Docker nor the network. Run the test suite:

```bash
uv run --extra dev python -m pytest
```

```text
........................................................................ [ 11%]
[...]
........................................................................ [ 94%]
[...]
613 passed, 3 warnings in 236.52s (0:03:56)
```

You should now see a last line that reports only `passed` (and possibly
`skipped` or `warnings`), with no `failed` or `error`. The count grows as tests
are added.

Type-check the interface:

```bash
cd webapp
npx tsc --noEmit
cd ..
```

```text
npm notice run idefix-webapp@0.1.0 npx
npm notice run tsc --noEmit
```

You should now see no TypeScript error. (npm 12 prints the two `npm notice`
lines; older versions print nothing.)

Check the documentation's links:

```bash
uv run --no-project python scripts/check_docs.py
```

```text
ok   - dead links
ok   - unbacked numbers
ok   - archive citations

All documentation checks passed.
```

You should now see `All documentation checks passed.`

If the tests fail with `No module named 'mistralai'`, your checkout predates
version 0.4.1 ([details](./troubleshooting.md#module-mistralai)).

## Stop, restart, and update

**Stop the database** and keep its data:

```bash
docker compose -p idefix stop
```

**Start again later.** `db` starts the stopped container and leaves the data as
it is; then serve the interface:

```bash
uv run python scripts/bootstrap.py db
uv run python scripts/bootstrap.py webapp
```

```text
== db: PostgreSQL 17 on 127.0.0.1:5433 (compose project idefix) ==
[...]
  the database already holds data (restored from idefix-corpus-v1.0.0.dump on 2026-10-26T10:20:24+00:00): left untouched (no restore, no migration; the bootstrap never deletes or replaces data)
  schema at alembic revision 0008; rows: [...]
  DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

**After `git pull`**, bring each part up to date. Every command is safe to
re-run:

```bash
uv sync --extra embed --extra dev
uv run python scripts/bootstrap.py db
uv run python scripts/bootstrap.py pipeline
uv run python scripts/bootstrap.py webapp
```

If `db` warns that the schema is behind, it prints the
`alembic upgrade head` command to run ([details](./troubleshooting.md#db-schema-behind)).
The `webapp` step reinstalls the Node.js dependencies when the lock file
changed.


## Start over

Use this only to discard the local database, for example after a failed
restore.

> [!CAUTION]
> This permanently deletes the local Idéfix database: the restored corpus,
> every pipeline result, and anything you collected into it. **Every clone and
> worktree on this machine uses the same database** (the Compose project is
> always `idefix`), so this deletes it for all of them. There is no undo.

First, if the database holds anything you want to keep, back it up to a file in
the current folder (the backup contains the personal data described in step 5):

```bash
docker compose -p idefix exec -T db pg_dump -U idefix -d idefix -Fc -f /tmp/idefix-backup.dump
docker cp idefix-db-1:/tmp/idefix-backup.dump ./idefix-backup.dump
```

Then remove the container and the volume that holds the data:

```bash
docker compose -p idefix down
docker volume rm idefix_pgdata
```

Run [step 5](#step-5) and [step 6](#step-6) again. The verified files in
`dataset/downloads/` are reused, so there is nothing to download. The pipeline
overwrites the old bundles in `webapp/public/data/`.

## Bootstrap reference

`scripts/bootstrap.py` runs the steps of this tutorial. With no step name it
runs `all`: steps 3 to 7 in order, then prints the time each took.

```bash
uv run python scripts/bootstrap.py --help
```

| Step | What it does | Safe to re-run |
|---|---|---|
| `check` | Python 3.14, Docker and Compose, a free database port, Node.js and npm, the `embed` extra, a valid manifest | Yes |
| `fetch` | Downloads and verifies the files in `dataset/manifest.json`; unpacks the annotations | Yes: verified files are kept |
| `db` | Starts the Compose service `db`; restores the corpus and migrates **only if the database is empty** | Yes: never touches a database that holds data |
| `pipeline` | `scripts/pipeline.py --mission all` against the local database | Yes: stages rewrite their own outputs |
| `webapp` | `npm ci` when needed, then `npm run dev` | Yes |
| `all` | All of the above. Runs the pipeline only on a database it restored itself, and only until one run has completed | Yes |

| Option | Effect |
|---|---|
| `--mission russosphere` | Run the pipeline for one mission (`russosphere`, `france_ukraine`, or `gan`) instead of `all` |
| `--skip-embeddings` | Skip the embedding stage: no `embed` extra, no model download |
| `--no-webapp` | `all` stops after the pipeline (headless machines, continuous integration) |
| `--dataset-dir D:\idefix-dataset` | Copy the release files from a local folder instead of downloading them |
| `--manifest dataset/manifest.json` | Use another manifest |

| Environment variable | Effect |
|---|---|
| `IDEFIX_DB_PORT` | Host port of the local database (default `5433`). Compose and the injected `DATABASE_URL` both follow it |
| `IDEFIX_DATASET_BASE_URL` | Download each file from this mirror instead of GitHub; sizes and hashes are still verified |
| `IDEFIX_EMBED_MODEL` | Another sentence-transformers model, or the path of a local copy |

The bootstrap never reads or writes `.env`. It passes the local
`DATABASE_URL` to each step itself, and gives Docker Compose an empty env file,
so that Compose ignores `.env` too. To run a script yourself, set the variable
in the terminal:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
```

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

Where `make` is available, the `Makefile` wraps the same commands:

| Target | Runs |
|---|---|
| `make setup` | `all`, with the `embed` extra |
| `make data` | `fetch` |
| `make db-up` | `db` |
| `make db-down` | `docker compose stop`: stops the database, keeps its data |
| `make pipeline MISSION=russosphere` | `pipeline`, with the `embed` extra |
| `make webapp` | `webapp` |

## Next

- [Install guide](./install.md): manual setup, a managed PostgreSQL, the
  Python extras, and Telegram collection.
- [Troubleshooting](./troubleshooting.md): every error message, its cause, and
  its fix.
- [Limitations](../limitations.md): read this before you interpret any score.
- [What the corpus contains](../../dataset/DATASHEET.md).
- [What Idéfix is and is not](../product/product.md).
- [Method](../method/01-problem-and-scope.md).
