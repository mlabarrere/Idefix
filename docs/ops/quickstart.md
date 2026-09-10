# Quickstart

The fastest path to a running system.

> **There is no bundled sample data.** Analyst bundles are corpus- and
> run-specific, so publishing them would ship numbers nobody could regenerate.
> They are not tracked in this repository — you generate them locally. See
> [`../limitations.md`](../limitations.md) Part III.
>
> This means the shortest useful path still requires a database. Budget about 20
> minutes.

## Prerequisites

- [Node.js 20+](https://nodejs.org/)
- [Python 3.14+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/)
- Docker, or any reachable PostgreSQL 17 instance
- Telegram API credentials, **only** if you intend to collect (step 4)

## 1. Clone and install

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix

uv sync                       # Python pipeline
cd webapp && npm install && cd ..
```

## 2. Database

```bash
docker run -d --name idefix-db --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=disinfo -e POSTGRES_PASSWORD=<password> \
  -e POSTGRES_DB=disinfo_trace postgres:17-alpine

cp .env.example .env          # then set DATABASE_URL
uv run alembic upgrade head
```

## 3. Verify the install without collecting

Nothing here touches Telegram or the network.

```bash
uv run python -m pytest -x -q              # 478 tests
cd webapp && npx tsc --noEmit && cd ..     # strict typecheck
uv run python scripts/check_docs.py        # documentation integrity
```

If those three pass, the checkout is sound.

## 4. Collect and build a bundle

Requires Telegram API credentials in `.env` — see
[`install.md`](./install.md) for obtaining them and for the session-string
procedure.

```bash
uv run python scripts/crawl.py               --mission russosphere
uv run python scripts/build_edges.py
uv run python scripts/build_scores.py        --mission russosphere
uv run python scripts/mine_episodes.py       --mission russosphere
uv run python scripts/analyze_communities.py --mission russosphere
uv run python scripts/export_static.py       --mission russosphere
```

This writes `webapp/public/data/russosphere/`, which is gitignored by design.

## 5. Run the interface

```bash
cd webapp
npm run dev     # http://localhost:5173
```

The browser reads only the local JSON bundle. It never contacts the database and
never calls Telegram.

## Before you interpret anything

Read [`../limitations.md`](../limitations.md). Several defects materially affect
how the ranking should be read — in particular **D1**, a language bias in the
credibility prior that substantially shapes the output.

## Next

- [Full install guide](./install.md) — Telegram credentials, session string, production
- [What Idéfix is and is not](../product/product.md)
- [Method](../method/01-problem-and-scope.md)
