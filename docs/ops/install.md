# Install guide

Full installation on a development machine: database, Python environment,
Telegram credentials, and the analyst interface.

For the fastest useful path, see [`quickstart.md`](./quickstart.md).

## Prerequisites

| Tool | Version | Role |
|---|---|---|
| Python | >= 3.11 | Analytical pipeline |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| Node.js | >= 20 | Analyst interface |
| Docker | >= 20 | PostgreSQL database |
| Telegram account | — | MTProto collection (read-only) |

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
uv sync --extra embed    # base + local embedding model (recommended)
uv sync --extra llm      # optional LLM classification pipeline
uv sync --extra dev      # development tooling
```

`.venv/` is created at the repository root.

> **Windows:** prefix Python commands with `$env:PYTHONUTF8="1"` (PowerShell) or
> `set PYTHONUTF8=1` (cmd) so that channel titles and accented characters print
> correctly.

## 3. Database — PostgreSQL via Docker

Idéfix targets PostgreSQL 17. Docker is the recommended development setup.

```bash
docker run -d \
  --name idefix-db \
  --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=disinfo \
  -e POSTGRES_PASSWORD=<a-local-password> \
  -e POSTGRES_DB=disinfo_trace \
  postgres:17-alpine

docker exec idefix-db pg_isready -U disinfo -d disinfo_trace
```

> **Managed alternative:** create a project on
> [supabase.com](https://supabase.com), take the connection string from
> *Dashboard → Connect → Session pooler*, and use it as `DATABASE_URL`.

### Apply migrations

```bash
uv run alembic upgrade head
uv run alembic current      # must print: 0008 (head)
```

This creates `channels`, `messages`, `edges`, `channel_scores` and the rest,
through migration `0008`.

## 4. Environment variables

```bash
cp .env.example .env
```

### Database

```dotenv
DATABASE_URL=postgresql+asyncpg://disinfo:<password>@localhost:5432/disinfo_trace
```

### Telegram

```dotenv
TELEGRAM_API_ID=<your-api-id>
TELEGRAM_API_HASH=<your-api-hash>
TELEGRAM_SESSION_STRING=<generated in step 5>
TELEGRAM_PHONE_NUMBER=+33XXXXXXXXX
```

### Optional

```dotenv
MISTRAL_API_KEY=<mistral-key>   # only with uv sync --extra llm
LOG_LEVEL=INFO
```

## 5. Telegram API credentials

Collection uses **MTProto**, read-only, public channels only.

> **Use a dedicated account**, separate from your personal one. It must never be
> used concurrently from elsewhere — that risks `FLOOD_WAIT` and account bans.

### Step 1 — API_ID and API_HASH

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

### Step 2 — Session string

A persistent token that avoids re-authenticating on every restart.

```bash
uv sync --extra session
uv run streamlit run scripts/session_web.py --server.port 8502
```

Open [http://localhost:8502](http://localhost:8502):

1. Enter the phone number in international format (`+33...`)
2. Enter the code received by SMS or in the Telegram app
3. If 2FA is enabled, enter the password
4. Copy the displayed session string into `TELEGRAM_SESSION_STRING`

> The session string is a secret. Treat it as a password — it grants read access
> to the account. It is scrubbed from every export by key and by value.

## 6. Analyst interface

```bash
cd webapp
npm install
npm run dev        # http://localhost:5173

npm run build      # static build -> webapp/dist/
npm run preview    # preview the production build
```

The webapp reads JSON bundles from `webapp/public/data/`. **Those bundles are
not in the repository** — they are corpus-specific and are generated locally by
`scripts/export_static.py` (step 8). Until you generate one, the interface has
nothing to display.

## 7. Verify the installation

```bash
uv run python -m pytest                     # 447 tests
cd webapp && npx tsc --noEmit && cd ..      # strict typecheck
uv run python scripts/check_docs.py         # documentation integrity
uv run python scripts/test_supabase_connection.py   # database connectivity
```

## 8. First pipeline run

```bash
uv run alembic upgrade head

uv run python scripts/backfill.py --channel @France24_fr --limit 500
uv run python scripts/build_edges.py
uv run python scripts/build_scores.py        --mission russosphere
uv run python scripts/analyze_communities.py --mission russosphere
uv run python scripts/export_static.py       --mission russosphere
uv run python scripts/build_stories.py       --mission russosphere

cd webapp && npm run dev
```

Full walkthrough: [`demo-runbook.md`](./demo-runbook.md).

Before interpreting any output, read
[`../limitations.md`](../limitations.md) — several defects materially affect how
the ranking should be read.

## Common problems

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` on port 5432 | Docker container stopped | `docker start idefix-db` |
| `FLOOD_WAIT` during crawl | Too many Telegram requests | Wait out the stated delay; never parallelize sessions |
| `ModuleNotFoundError: sentence_transformers` | `embed` extra not installed | `uv sync --extra embed` |
| `alembic current` shows an old revision | Migrations incomplete | `uv run alembic upgrade head` |
| Blank page in the webapp | No JSON bundle generated yet | Run `export_static.py` and `build_stories.py` |
| Broken UTF-8 output on Windows | Missing env var | `$env:PYTHONUTF8="1"` before each command |
