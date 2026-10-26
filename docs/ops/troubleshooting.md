# Troubleshooting

Find the message you saw, then follow its fix. Every entry quotes the error as
the tool prints it, names the cause, and gives the fix. The
[quickstart](./quickstart.md) links here from each step.

To search: copy a distinctive fragment of your error (for example
`daemon not reachable` or `os error 396`) and use your browser's find
(<kbd>Ctrl</kbd>+<kbd>F</kbd>, or <kbd>Cmd</kbd>+<kbd>F</kbd> on macOS).

> [!NOTE]
> The bootstrap (`scripts/bootstrap.py`) prints its own errors after
> `error:` and its warnings after `warning:`. Each one names the fix in the same
> line. When it does, that line is the authoritative fix; this page adds the
> background.

## Contents

- [Shells and operating systems](#shells-and-operating-systems)
- [Python environment](#python-environment)
- [Network, proxies, and corporate TLS](#network-proxies-and-corporate-tls)
- [Step `check`](#step-check)
- [Step `fetch`](#step-fetch)
- [Step `db`](#step-db)
- [Step `pipeline`](#step-pipeline)
- [Analyst interface](#analyst-interface)
- [Telegram collection](#telegram-collection)
- [Symptoms without an error message](#symptoms-without-an-error-message)

## Shells and operating systems

<a id="ps51-ampersand"></a>

### Windows PowerShell 5.1 rejects `&&`

```text
The token '&&' is not a valid statement separator in this version.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : InvalidEndOfLine
```

**Cause.** You are in Windows PowerShell 5.1, the version built into Windows. It
does not support the `&&` and `||` pipeline-chain operators.

**Fix.** Use PowerShell 7 (`pwsh`), which every PowerShell block in these
guides targets. Install it once, then open **PowerShell 7** from the Start menu:

```powershell
winget install --id Microsoft.PowerShell --source winget
```

Check which one you are in: `$PSVersionTable.PSVersion` prints `7.x` in
PowerShell 7 and `5.1.x` in Windows PowerShell.

<a id="make-not-found"></a>

### `make` is not recognized

```text
make : The term 'make' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

```text
bash: make: command not found
```

**Cause.** `make` is not installed. Windows does not ship it.

**Fix.** You never need `make`: every target in the `Makefile` wraps a `uv`
command, and the guides give that command. For example, `make setup` is
`uv run --extra embed python scripts/bootstrap.py`.

<a id="execution-policy"></a>

### `npm.ps1 cannot be loaded because running scripts is disabled`

```text
npm : File C:\Program Files\nodejs\npm.ps1 cannot be loaded because running scripts is disabled on this system. For
more information, see about_Execution_Policies at https:/go.microsoft.com/fwlink/?LinkID=135170.
```

**Cause.** The PowerShell execution policy is `Restricted`, so PowerShell
refuses the `npm.ps1` shim that Node.js installs. The same policy blocks other
`.ps1` launchers.

**Fix.** Allow local scripts for your user only (no administrator rights
needed):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

If your organization's policy forbids that, call the `.cmd` shim instead:
`npm.cmd ci`, `npx.cmd tsc --noEmit`.

<a id="unicode-encode"></a>

### `UnicodeEncodeError: 'charmap' codec can't encode character`

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 0: character maps to <undefined>
```

**Cause.** On Windows, Python writes redirected or piped output in the legacy
code page (cp1252), which has no arrows, Cyrillic, or many accented characters.
The bootstrap and `scripts/pipeline.py` set `PYTHONUTF8=1` for the scripts they
start, so this only happens when you run a script yourself.

**Fix.** Turn on Python's UTF-8 mode for the session:

```powershell
$env:PYTHONUTF8 = "1"
```

To make it permanent, add that line to your PowerShell profile
(`notepad $PROFILE`).

<a id="env-utf16"></a>

### `UnicodeDecodeError` on byte `0xff` when reading `.env`

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
```

**Cause.** The `.env` file is UTF-16. Windows PowerShell 5.1 writes UTF-16 by
default when you create a file with `>` or `Out-File` (for example
`"DATABASE_URL=…" > .env`). `python-dotenv` reads UTF-8 only.

**Fix.** Recreate the file from the template, then edit it in a text editor:

```powershell
Copy-Item .env.example .env -Force
```

PowerShell 7 writes UTF-8 without a byte-order mark, so this does not recur
there.

## Python environment

<a id="uv-not-found"></a>

### `uv` is not recognized after installing it

```text
uv : The term 'uv' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

```text
bash: uv: command not found
```

**Cause.** The installer added `uv` to `PATH`, but the open terminal still has
the old `PATH`.

**Fix.** Close the terminal and open a new one. On Linux and macOS you can
instead reload the variables the installer wrote:

```bash
source "$HOME/.local/bin/env"
```

<a id="python-version"></a>

### `[FAIL] python  3.12.x (needs 3.14+)`

```text
  [FAIL] python      3.12.10 (needs 3.14+)
                     -> run through uv: `uv run python scripts/bootstrap.py`
```

**Cause.** You ran the bootstrap with a system Python instead of through `uv`.

**Fix.** Prefix the command with `uv run`. `uv` reads `.python-version`
(`3.14`) and downloads Python 3.14 itself if it is missing.

<a id="tgcrypto-build"></a>

### `Failed to build tgcrypto` or `Microsoft Visual C++ 14.0 or greater is required`

```text
  × Failed to build `tgcrypto==1.2.5`
```

```text
error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Cause.** `tgcrypto` speeds up the Telegram client and publishes no wheel for
Python 3.14, so `uv` compiles it from source. That needs a C compiler. Only the
`collect` extra installs it; the public-corpus path does not.

**Fix.** If you do not collect from Telegram, drop `--extra collect` (and
`--extra session`) from your command. To collect, install a compiler, open a new
terminal, and re-run the same `uv sync`:

- **Windows:** [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/),
  workload **Desktop development with C++**. From PowerShell:

  ```powershell
  winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
  ```

- **macOS:** `xcode-select --install`.
- **Debian and Ubuntu:** `sudo apt-get install build-essential`.

<a id="onedrive-uv"></a>

### `os error 396` or `Access is denied. (os error 5)` during `uv sync`

```text
error: Failed to install: ... (os error 396)
```

```text
error: Failed to install: ... Access is denied. (os error 5)
```

**Cause.** The repository sits in a folder synchronized by OneDrive (or another
sync client, or watched by an antivirus scanner), which locks files while `uv`
writes them. `pyproject.toml` already sets `link-mode = "copy"` to avoid the
hard-link failure (`os error 396`), but locks can still interrupt an install.

**Fix.** Clone the repository outside any synchronized folder, for example
`C:\dev\Idefix` or `~/src/Idefix`, and run the install there. If you must keep
the clone where it is, put the environment outside the synchronized folder:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "C:\dev\venvs\idefix"
```

See [Synchronized folders](./quickstart.md#synchronized-folders-onedrive-dropbox-icloud).

<a id="module-sentence-transformers"></a>

### `ModuleNotFoundError: No module named 'sentence_transformers'`

```text
ModuleNotFoundError: No module named 'sentence_transformers'
```

**Cause.** An embedding stage ran without the `embed` extra.

**Fix.** Add `--extra embed` to the command, or skip the embedding stages with
`--skip-embeddings`:

```bash
uv run --extra embed python scripts/pipeline.py --mission russosphere
```

<a id="module-hydrogram"></a>

### `ModuleNotFoundError: No module named 'hydrogram'`

```text
ModuleNotFoundError: No module named 'hydrogram'
```

**Cause.** A Telegram collection script ran without the `collect` extra. Since
version 0.4.1 the Telegram client is not part of the base install.

**Fix.** Add `--extra collect` (it needs a C compiler, see
[`tgcrypto`](#tgcrypto-build)):

```bash
uv run --extra collect python scripts/backfill.py --channel @France24_fr --limit 500
```

<a id="module-mistralai"></a>

### `ModuleNotFoundError: No module named 'mistralai'` or `'httpx'`

```text
E       ModuleNotFoundError: No module named 'mistralai'
FAILED tests/test_mistral_client.py::test_cache_miss_then_hit - ModuleNotFoun...
```

```text
E   ModuleNotFoundError: No module named 'httpx'
ERROR tests/test_mistral_client.py
```

**Cause.** Before version 0.4.1, `tests/test_mistral_client.py` needed the
optional `llm` extra. From 0.4.1 the suite passes without it.

**Fix.** Update your checkout. On an older checkout, add the extra:

```bash
uv run --extra dev --extra llm python -m pytest
```

<a id="module-streamlit"></a>

### `Failed to spawn: streamlit`

```text
error: Failed to spawn: `streamlit`
  Caused by: program not found
```

**Cause.** The session generator ran without the `session` extra.

**Fix.** Use `make session`, or the command it wraps, which installs the extra:

```bash
uv run --extra session streamlit run scripts/session_web.py --server.port 8502
```

## Network, proxies, and corporate TLS

Many corporate networks send traffic through a proxy that inspects Transport
Layer Security (TLS) connections and re-signs them with the organization's own
root certificate. Behind such a proxy, set the proxy and trust that root
certificate once per terminal, as [Proxy and corporate TLS](./quickstart.md#proxy-and-corporate-tls)
describes. The entries below are the symptoms when one of those settings is
missing.

<a id="tls-uv"></a>

### `uv`: `invalid peer certificate: UnknownIssuer`

```text
error: Failed to fetch: `https://pypi.org/simple/alembic/`
  Caused by: Request failed after 3 retries
  [...]
  Caused by: invalid peer certificate: UnknownIssuer
```

**Cause.** A proxy re-signs HTTPS traffic with your organization's certificate,
which `uv`'s bundled certificate list does not contain.

**Fix.** Make `uv` use the operating system's certificate store, which usually
already trusts the corporate root:

```powershell
$env:UV_NATIVE_TLS = "true"
```

```bash
export UV_NATIVE_TLS=true
```

If the root is not in the system store, point `SSL_CERT_FILE` at a PEM (Base64 text) certificate bundle
that contains it.

<a id="tls-npm"></a>

### `npm`: `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` or `SELF_SIGNED_CERT_IN_CHAIN`

```text
npm error code UNABLE_TO_GET_ISSUER_CERT_LOCALLY
npm error errno UNABLE_TO_GET_ISSUER_CERT_LOCALLY
```

```text
npm error code SELF_SIGNED_CERT_IN_CHAIN
```

**Cause.** Node.js does not use the operating system's certificate store, so it
rejects the proxy's re-signed certificate.

**Fix.** Give Node.js the corporate root as a PEM file, then re-run `npm ci`:

```powershell
$env:NODE_EXTRA_CA_CERTS = "C:\certs\corporate-root.pem"
```

```bash
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/corporate-root.pem
```

Do not set `strict-ssl=false`: it turns off certificate checks for every
package you install.

<a id="tls-python"></a>

### `fetch`: `CERTIFICATE_VERIFY_FAILED`

```text
error: cannot download https://github.com/mlabarrere/Idefix/releases/download/dataset-v1.0.0/idefix-corpus-v1.0.0.dump: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032). Check the connection, set IDEFIX_DATASET_BASE_URL to a mirror, or pass --dataset-dir with local copies.
```

**Cause.** The bootstrap downloads with Python's standard library. On Windows it
trusts the Windows certificate store; on Linux and macOS it trusts the OpenSSL
bundle shipped with Python, which lacks your corporate root.

**Fix.** Point Python at a bundle that contains the corporate root, then re-run
`fetch`:

```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

On Windows, ask your IT team to install the root in the Windows store, or
download the two release files in a browser and pass the folder:

```powershell
uv run python scripts/bootstrap.py fetch --dataset-dir "$HOME\Downloads"
```

The bootstrap verifies the size and SHA-256 of copied files exactly as it does
for downloads.

<a id="tls-git"></a>

### `git clone`: `SSL certificate problem: unable to get local issuer certificate`

```text
fatal: unable to access 'https://github.com/mlabarrere/Idefix.git/': SSL certificate problem: unable to get local issuer certificate
```

**Cause.** Git for Windows defaults to its own OpenSSL bundle, which does not
contain the corporate root.

**Fix.** On Windows, make Git use the Windows certificate store:

```powershell
git config --global http.sslBackend schannel
```

On Linux and macOS, point Git at a bundle that contains the root:

```bash
git config --global http.sslCAInfo /etc/ssl/certs/ca-certificates.crt
```

<a id="tls-docker"></a>

### Docker: `x509: certificate signed by unknown authority`

```text
Error response from daemon: Get "https://registry-1.docker.io/v2/": tls: failed to verify certificate: x509: certificate signed by unknown authority
```

**Cause.** Docker cannot pull `postgres:17-alpine` through a proxy that
re-signs TLS.

**Fix.** In Docker Desktop, set the proxy under **Settings → Resources →
Proxies**; Docker Desktop trusts the certificates in the Windows store or the
macOS keychain, so install the corporate root there and restart Docker Desktop.
With Docker Engine on Linux, add the root to the system store
(`/usr/local/share/ca-certificates/`, then `sudo update-ca-certificates`) and
restart the daemon (`sudo systemctl restart docker`).

<a id="hf-offline"></a>

### `We couldn't connect to 'https://huggingface.co'`

```text
OSError: We couldn't connect to 'https://huggingface.co' to load this file, couldn't find it in the cached files and it looks like sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 is not the path to a directory containing a file named config.json.
```

**Cause.** The first embedding stage (`analyze_communities_embed`) downloads the
sentence-transformers model (about 458 MB) from the Hugging Face Hub, and the
download was blocked.

**Fix.** Pick one:

- Set `HTTPS_PROXY` and `SSL_CERT_FILE` as in
  [Proxy and corporate TLS](./quickstart.md#proxy-and-corporate-tls), then
  resume with `--from analyze_communities_embed`.
- Copy the model folder from a machine that has it, and point the pipeline at
  it. `IDEFIX_EMBED_MODEL` accepts a local directory:

  ```powershell
  $env:IDEFIX_EMBED_MODEL = "C:\models\paraphrase-multilingual-MiniLM-L12-v2"
  ```

- Skip the embedding stages: `--skip-embeddings`.

<a id="hf-unauthenticated"></a>

### `You are sending unauthenticated requests to the HF Hub`

```text
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
```

**Cause.** The model download runs without a Hugging Face account token.

**Fix.** None needed: the model is public and the download succeeds. A token
(`HF_TOKEN`) only raises the rate limit.

## Step `check`

`check` prints one line per prerequisite: `[ ok ]`, `[FAIL]` (stops the run), or
`[warn]` (reported, does not stop it). A failing line is followed by its fix
after `->`.

<a id="check-docker-missing"></a>

### `[FAIL] docker  not installed`

```text
  [FAIL] docker      not installed (no `docker` on PATH)
```

**Cause.** No `docker` command on `PATH`.

**Fix.** Install Docker as the [quickstart](./quickstart.md#install-the-prerequisites)
describes for your system, open a new terminal, and re-run `check`.

<a id="check-docker-daemon"></a>

### `[FAIL] docker  daemon not reachable`

```text
  [FAIL] docker      daemon not reachable
                     -> Docker is installed but not running: start Docker Desktop (Windows/macOS) or the service (Linux: `sudo systemctl start docker`), wait until it is ready, re-run.
```

**Cause.** Docker is installed but its engine is not running. On Windows,
`docker info` reports
`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`

**Fix.** Start Docker Desktop and wait until its status reads **Engine
running**, or on Linux run `sudo systemctl start docker`. Then re-run `check`.

<a id="check-docker-permission"></a>

### `[FAIL] docker` with `permission denied` on the Docker socket (Linux)

```text
  [FAIL] docker      daemon not reachable
                     -> your user cannot reach the Docker socket: `sudo usermod -aG docker $USER`, log out and back in (or use Docker Desktop).
```

**Cause.** Your user is not in the `docker` group, so it cannot open
`/var/run/docker.sock`.

**Fix.** Add yourself to the group, then log out and back in (a new terminal is
not enough):

```bash
sudo usermod -aG docker "$USER"
```

<a id="check-compose"></a>

### `[FAIL] compose`

```text
  [FAIL] compose     Docker Compose v2 not available
                     -> install the Compose v2 plugin (bundled with Docker Desktop): https://docs.docker.com/compose/install/
```

**Cause.** The `docker compose` plugin is missing (the old standalone
`docker-compose` does not count), or it is older than 2.17.

**Fix.** Docker Desktop bundles the plugin. On Linux, install
`docker-compose-plugin` from Docker's package repository:

```bash
sudo apt-get install docker-compose-plugin
```

<a id="check-port"></a>

### `[FAIL] db port  127.0.0.1:5433 already in use`

```text
  [FAIL] db port     127.0.0.1:5433 already in use
                     -> 127.0.0.1:5433 is taken: pick another port and re-run, e.g. `export IDEFIX_DB_PORT=55432` (bash/zsh) or `$env:IDEFIX_DB_PORT=55432` (PowerShell). On Windows, Hyper-V may also reserve it: `netsh interface ipv4 show excludedportrange protocol=tcp`.
```

**Cause.** Another program listens on port 5433, or (on Windows) Hyper-V or the Windows Subsystem for Linux (WSL)
reserved a port range that includes it.

**Fix.** Choose another port for this terminal and re-run. Every bootstrap step
and the `DATABASE_URL` it prints follow the variable:

```powershell
$env:IDEFIX_DB_PORT = "55432"
```

```bash
export IDEFIX_DB_PORT=55432
```

To see the reserved ranges on Windows:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

If you set `DATABASE_URL` yourself (in `.env` or the environment), change its
port too.

<a id="check-node"></a>

### `[FAIL] node`

```text
  [FAIL] node        v18.20.4 is too old
                     -> install Node.js 20.19+ or 22.12+ (Vite 8): https://nodejs.org/
```

**Cause.** Node.js is missing, older than Vite 8 accepts, or installed without
`npm`.

**Fix.** Install the current long-term support (LTS) release of Node.js, open a new terminal, and
re-run. With `--no-webapp` the line becomes a `[warn]` and does not stop
the run.

<a id="check-embed"></a>

### `[FAIL] embeddings  the embed extra is not installed`

```text
  [FAIL] embeddings  the `embed` extra is not installed
                     -> run `uv run --extra embed python scripts/bootstrap.py ...` (installs sentence-transformers + torch, about 1 GB), or pass --skip-embeddings
```

**Cause.** The environment lacks sentence-transformers, which the embedding
stages need. Plain `uv run python scripts/bootstrap.py check` on a fresh clone
fails this way by design.

**Fix.** Install the extra once (`uv sync --extra embed --extra dev`, as the
quickstart does), or run with `--extra embed`, or skip those stages with
`--skip-embeddings`.

<a id="check-manifest"></a>

### `[FAIL] manifest`

```text
  [FAIL] manifest    dataset manifest not found: C:\dev\Idefix\dataset\manifest.json. It pins the public dataset release (dataset/manifest.json); restore it with `git checkout -- dataset/` or pass --manifest PATH.
```

**Cause.** `dataset/manifest.json` was deleted or edited.

**Fix.** Restore it from your checkout:

```bash
git restore dataset/manifest.json
```

## Step `fetch`

<a id="fetch-download"></a>

### `cannot download`

```text
error: cannot download https://github.com/mlabarrere/Idefix/releases/download/dataset-v1.0.0/idefix-corpus-v1.0.0.dump: [Errno 11001] getaddrinfo failed. Check the connection, set IDEFIX_DATASET_BASE_URL to a mirror, or pass --dataset-dir with local copies.
```

**Cause.** No route to GitHub: offline, a proxy that is not configured, or a
firewall. A certificate error has [its own entry](#tls-python).

**Fix.** Set `HTTPS_PROXY` if you are behind a proxy, then re-run. Otherwise use
a mirror or local copies:

```bash
export IDEFIX_DATASET_BASE_URL=https://mirror.example.org/idefix/dataset-v1.0.0
```

```bash
uv run python scripts/bootstrap.py fetch --dataset-dir /media/usb/idefix-dataset
```

A mirror must serve each file under its manifest name
(`https://mirror.example.org/idefix/dataset-v1.0.0/idefix-corpus-v1.0.0.dump`).
Sizes and hashes are verified either way.

<a id="fetch-interrupted"></a>

### `download ... interrupted; re-run to resume`

```text
error: download of https://github.com/mlabarrere/Idefix/releases/download/dataset-v1.0.0/idefix-corpus-v1.0.0.dump interrupted (ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None)); re-run to resume.
```

**Cause.** The connection dropped mid-download.

**Fix.** Re-run `fetch`. It resumes from the partial `.part` file when the
server allows it, and verifies the whole file at the end.

<a id="fetch-hash"></a>

### `SHA-256 mismatch` or `size mismatch`

```text
error: SHA-256 mismatch for idefix-corpus-v1.0.0.dump: expected c2da11bbcce3f055b7f8e687e5febbbdf47bab22e82761b25abc1497c34db825, got 4f0c...
```

**Cause.** The downloaded or copied file is not the published release: a
truncated copy, a proxy that rewrote the response, or a mirror serving another
version.

**Fix.** Re-run `fetch`: the bootstrap deletes a file that fails verification
and fetches it again. If it fails again, check your mirror or
`--dataset-dir` copy against [`dataset/manifest.json`](../../dataset/manifest.json).

<a id="fetch-kept"></a>

### `kept 1 local file(s) that differ from the release`

```text
warning: kept 1 local file(s) that differ from the release (delete them to take the release version): claims/claims_fr.jsonl
```

**Cause.** Expected on every fresh clone. The repository tracks
`data/claims/claims_fr.jsonl` (the tests need it), and its copy differs from the
one in the release archive. The bootstrap never overwrites a local file.

**Fix.** None. Keep the tracked file.

<a id="fetch-dataset-dir"></a>

### `not found in --dataset-dir`

```text
error: idefix-corpus-v1.0.0.dump not found in --dataset-dir C:\Users\ada\Downloads.
```

**Cause.** The folder you passed lacks one of the release files, or a browser
renamed it (for example `idefix-corpus-v1.0.0 (1).dump`).

**Fix.** Put both files listed in `dataset/manifest.json` in the folder under
their exact names, then re-run.

## Step `db`

<a id="db-unhealthy"></a>

### `the database container started but did not become healthy`

```text
error: the database container started but did not become healthy. Logs: `docker compose -p idefix logs db`.
```

**Cause.** PostgreSQL did not pass its health check within 180 seconds: a slow
first start, too little disk space, or a damaged data volume.

**Fix.** Read the container's log, which names the problem:

```bash
docker compose -p idefix logs db
```

Free disk space if the log says `No space left on device`, then re-run `db`.

<a id="db-start"></a>

### `could not start the database`

```text
error: could not start the database (see the Docker output above). Logs: `docker compose -p idefix logs db`.
```

**Cause.** `docker compose up` failed. The Docker output just above names the
reason, for example a failed pull of `postgres:17-alpine` (see
[Docker TLS](#tls-docker)) or a port conflict (see [port in use](#check-port)).

**Fix.** Fix that reason, then re-run `db`.

<a id="db-not-fetched"></a>

### `is not in ... dataset/downloads: run ... fetch first`

```text
error: idefix-corpus-v1.0.0.dump is not in C:\dev\Idefix\dataset\downloads: run `uv run python scripts/bootstrap.py fetch` first.
```

**Cause.** `db` found an empty database but no verified dump to restore.

**Fix.** Run `fetch`, then `db`:

```bash
uv run python scripts/bootstrap.py fetch
```

<a id="db-left-untouched"></a>

### `the database already holds data ... left untouched`

```text
  the database already holds data (restored from idefix-corpus-v1.0.0.dump on 2026-10-26T10:20:24+00:00): left untouched (no restore, no migration; the bootstrap never deletes or replaces data)
```

**Cause.** Not an error. The database was restored earlier; `db` restores only
into an empty database. If the parentheses say
`tables, not restored by this bootstrap`, the data did not come from the
bootstrap (your own collection, or an interrupted restore).

**Fix.** None. To start from scratch, see
[Start over](./quickstart.md#start-over).

<a id="db-schema-behind"></a>

### `its schema is at revision ..., the code expects 0008`

```text
warning: its schema is at revision 0006, the code expects 0008. To migrate it yourself: DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix uv run alembic upgrade head
```

**Cause.** The database holds data, so `db` did not migrate it, and its schema
predates the code.

**Fix.** Apply the migrations (they are additive and keep your data):

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
uv run alembic upgrade head
```

```bash
DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix uv run alembic upgrade head
```

See [Migrations](./migrations.md).

<a id="alembic-database-url"></a>

### `RuntimeError: DATABASE_URL is not set` from Alembic

```text
RuntimeError: DATABASE_URL is not set. Alembic loads it from the environment / .env. Set it (e.g. postgresql+asyncpg://user:pass@host/db) before running migrations.
```

**Cause.** You ran `uv run alembic ...` in a terminal without `DATABASE_URL` and
without a `.env` file.

**Fix.** Set the variable in the terminal, then re-run the command:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
```

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

<a id="db-restore-failed"></a>

### `pg_restore failed`

```text
error: pg_restore failed (exit 1):
pg_restore: error: could not read from input file: end of file
The database is probably partially restored. The bootstrap never deletes data, so later runs will leave it as it is. To start over, remove the `idefix_pgdata` Docker volume yourself (this deletes the local database), then re-run.
```

**Cause.** The restore stopped part-way (a damaged file, or no disk space).

**Fix.** Follow [Start over](./quickstart.md#start-over), which removes the
partial database, then re-run `fetch` and `db`.

<a id="db-row-counts"></a>

### `restored row counts differ from the manifest`

```text
warning: restored row counts differ from the manifest (expected, got): {'messages': (166188, 120000)}
```

**Cause.** The restore completed without an error but did not load every row,
usually because it was interrupted.

**Fix.** Do not use this database for results. [Start over](./quickstart.md#start-over)
and restore again. If the warning persists, report it with the full output.

<a id="db-connection-refused"></a>

### `Connect call failed ('127.0.0.1', 5433)`

```text
OSError: Multiple exceptions: [Errno 10061] Connect call failed ('::1', 5433, 0, 0), [Errno 10061] Connect call failed ('127.0.0.1', 5433)
```

**Cause.** A script or Alembic reached for the database while its container was
stopped (on Linux the error number is 111).

**Fix.** Start it. This only starts the container; it never restores over
existing data:

```bash
uv run python scripts/bootstrap.py db
```

<a id="db-shm"></a>

### `could not resize shared memory segment`

```text
ERROR:  could not resize shared memory segment "/PostgreSQL.1234567890" to 8388608 bytes: No space left on device
```

**Cause.** The analytics queries use parallel hash joins, which need more than
Docker's default 64 MB of `/dev/shm`. The repository's `docker-compose.yml`
sets `shm_size: 256mb`; a PostgreSQL container you started yourself does not.

**Fix.** Use the repository's Compose service, or give your own container
`--shm-size=256m`.

## Step `pipeline`

<a id="pipeline-empty-db"></a>

### `the database is empty: run ... db first`

```text
error: the database is empty: run `uv run python scripts/bootstrap.py db` first.
```

**Cause.** The pipeline needs the restored corpus.

**Fix.** Run `fetch` and `db` first.

<a id="pipeline-skipped"></a>

### `skipped: already completed on this database`

```text
  skipped: already completed on this database (`uv run python scripts/bootstrap.py pipeline` runs it explicitly)
```

```text
  skipped: this database was not restored by the bootstrap (`uv run python scripts/bootstrap.py pipeline` runs it explicitly)
```

**Cause.** Not an error. Within `all`, the bootstrap runs the pipeline only on a
database it restored itself, and only until one run has completed.

**Fix.** To run it anyway, call the step explicitly:

```bash
uv run --extra embed python scripts/bootstrap.py pipeline
```

<a id="pipeline-failed"></a>

### `FAILED: ... Fix it, then resume with --from`

```text
FAILED: build_scores [gan] (exit 1) after 7m52s. Fix it, then resume with --from build_scores.
```

```text
error: the pipeline failed (exit 1). Stages: `uv run python scripts/pipeline.py --list`; resume with `--from STAGE`, with DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix in the environment.
```

**Cause.** One stage failed; the runner stops at the first failure. The stage's
own error is printed above these lines.

**Fix.** Fix the stage's error, then resume from that stage instead of starting
again:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
uv run --extra embed python scripts/pipeline.py --mission all --from build_scores
```

```bash
DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix uv run --extra embed python scripts/pipeline.py --mission all --from build_scores
```

<a id="pipeline-database-url"></a>

### `DATABASE_URL is not set (and there is no .env)`

```text
DATABASE_URL is not set (and there is no .env). Example: DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
```

**Cause.** You ran `scripts/pipeline.py` directly. Unlike the bootstrap, it does
not inject the local database URL.

**Fix.** Set the variable as in the previous entry, or run the pipeline through
the bootstrap, which sets it for you.

## Analyst interface

<a id="webapp-no-bundle"></a>

### `no analyst bundle under webapp/public/data/ yet`

```text
warning: no analyst bundle under webapp/public/data/ yet: run `uv run python scripts/bootstrap.py pipeline` (or, for a synthetic demo, `uv run python scripts/make_fixture_bundle.py`).
```

**Cause.** The interface reads JavaScript Object Notation (JSON) bundles that only the pipeline writes; they
are not in the repository. Without them every page shows empty states.

**Fix.** Run the pipeline (step 6 of the quickstart). For a quick look at the
interface with synthetic data instead, run
`uv run python scripts/make_fixture_bundle.py`.

<a id="webapp-install-scripts"></a>

### `install scripts blocked because they are not covered by allowScripts`

```text
npm warn install-scripts 1 package had install scripts blocked because they are not covered by allowScripts:
npm warn install-scripts   esbuild@0.28.1 (postinstall: node install.js)
```

**Cause.** Recent versions of `npm` do not run dependencies' install scripts
unless they are approved.

**Fix.** None needed. `esbuild` installs its platform binary as a separate
package, so the interface builds and starts without the script.

<a id="webapp-ebadengine"></a>

### `npm warn EBADENGINE Unsupported engine`

```text
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: 'vite@8.3.5',
npm warn EBADENGINE   required: { node: '^20.19.0 || >=22.12.0' },
npm warn EBADENGINE   current: { node: 'v20.11.1', npm: '10.2.4' }
npm warn EBADENGINE }
```

**Cause.** Your Node.js is older than Vite 8 supports.

**Fix.** Install the current Node.js LTS release, delete `webapp/node_modules`,
and run `npm ci` again.

<a id="webapp-port"></a>

### `Port 5173 is in use, trying another one...`

```text
Port 5173 is in use, trying another one...
```

**Cause.** Another dev server (often an earlier Vite you did not stop) holds the
port.

**Fix.** None needed: open the `Local:` URL that Vite prints next. To free 5173,
stop the other server with <kbd>Ctrl</kbd>+<kbd>C</kbd> in its terminal.

<a id="webapp-dep0205"></a>

### `DeprecationWarning: module.register() is deprecated`

```text
(node:15124) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
```

**Cause.** A development dependency uses an application programming interface (API) that Node.js 26 deprecates.

**Fix.** None needed. The dev server starts normally.

## Telegram collection

<a id="tg-credentials"></a>

### `SessionError` naming `TELEGRAM_API_ID` or `TELEGRAM_SESSION_STRING`

```text
src.ingestor.session.SessionError
```

**Cause.** A collection script started without Telegram credentials. The
message names the missing variables.

**Fix.** Fill `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and
`TELEGRAM_SESSION_STRING` in `.env`, as
[the install guide](./install.md#optional-collect-your-own-data-from-telegram)
describes. The legacy names `TG_API_ID`, `TG_API_HASH`, and `TG_SESSION_STRING`
still work; the `TELEGRAM_*` names win when both are set.

<a id="tg-flood-wait"></a>

### `FLOOD_WAIT`

```text
Telegram says: [420 FLOOD_WAIT_X] - A wait of 1832 seconds is required
```

**Cause.** Telegram rate-limits the account because it sent too many requests,
often because two clients used the same session at once. The message gives the
wait in seconds.

**Fix.** Wait out the delay. Run one collection script at a time, and never use
the collection account from anywhere else while a script runs.

## Symptoms without an error message

<a id="blank-page"></a>

### The interface shows a blank page or only empty states

The pipeline has not written the bundles yet, or it failed before
`export_static`. See [no analyst bundle](#webapp-no-bundle).

<a id="wrong-database"></a>

### A script writes to the wrong database

`.env` holds another `DATABASE_URL`, for example a hosted one. Scripts read
`.env`; a variable set in the environment wins over it. Set `DATABASE_URL`
explicitly in the terminal before running the script. The bootstrap is not
affected: it never reads `.env`.

<a id="shared-database"></a>

### A second clone shows the first clone's data

Every clone on a machine uses the same database. `docker-compose.yml` names the
Compose project `idefix`, so every clone, worktree, and copy shares the
container `idefix-db-1` and the volume `idefix_pgdata`, whatever folder it
lives in. `IDEFIX_DB_PORT` changes only the port. Bear this in mind before you
[start over](./quickstart.md#start-over): removing the volume from any clone
deletes the database for all of them.

<a id="pipeline-slow"></a>

### The pipeline seems stuck on `build_scores` or `export_static`

It is working. On a GitHub-hosted Ubuntu runner (4 virtual CPUs), `build_scores` and
`export_static` each take about 8 minutes per mission, and the whole pipeline
takes about 55 minutes. Both stages print little while they work.

<a id="alembic-old"></a>

### `alembic current` shows an old revision

The schema is behind the code. Run `uv run alembic upgrade head` with
`DATABASE_URL` set, as in [schema behind](#db-schema-behind).

<a id="crlf-hash"></a>

### The dossier's methodology hash differs between Windows and Linux

The hash is computed over the bytes of `METHODOLOGY.md`, and Git on Windows
checks it out with CRLF line endings
([defect D27](../limitations.md#d27)). From version 0.4.1, `.gitattributes`
pins the line endings. In a clone made before that, delete the file and restore
it so that Git rewrites it with the pinned endings:

```powershell
Remove-Item METHODOLOGY.md
git restore METHODOLOGY.md
```

```bash
rm METHODOLOGY.md && git restore METHODOLOGY.md
```
