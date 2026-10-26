.PHONY: help setup data db-up db-down pipeline install migrate session backfill crawl webapp test lint fmt

# Reproducible setup on the public corpus (scripts/bootstrap.py, docker-compose.yml).
# No Telegram credentials and no .env needed. The database port defaults to 5433;
# override with the IDEFIX_DB_PORT environment variable. No target deletes data:
# the restore only ever happens into an empty database.
BOOTSTRAP := uv run python scripts/bootstrap.py
# The pipeline's embedding stages need the optional "embed" extra.
BOOTSTRAP_EMBED := uv run --extra embed python scripts/bootstrap.py
# Development tooling (pytest, ruff, mypy) is the "dev" extra.
DEV := uv run --extra dev
# Telegram collection (hydrogram + tgcrypto) is the optional "collect" extra.
# tgcrypto has no Python 3.14 wheels: installing it needs a C compiler.
COLLECT := uv run --extra collect
MISSION ?= all
# Keep Compose away from .env (secrets): only the process environment configures it.
ifeq ($(OS),Windows_NT)
NULL_DEVICE := nul
else
NULL_DEVICE := /dev/null
endif
COMPOSE := docker compose --env-file $(NULL_DEVICE)

help:
	@echo "Idéfix — available commands:"
	@echo "  Reproduce on the public corpus (Docker + Node 20.19+, no credentials):"
	@echo "  make setup         Everything: check, fetch dataset, restore DB, pipeline, webapp"
	@echo "  make data          Download + verify the pinned dataset (dataset/manifest.json)"
	@echo "  make db-up         Start the local PostgreSQL 17; restore the dataset if the DB is empty"
	@echo "  make db-down       Stop the local PostgreSQL (container and data are kept)"
	@echo "  make pipeline [MISSION=russosphere]  Run the offline pipeline on the local DB"
	@echo "  make webapp        Serve the analyst webapp (npm ci if needed, Vite dev server)"
	@echo "  Development:"
	@echo "  make install       Install Python deps with uv (uv sync --extra dev --extra embed)"
	@echo "  make migrate       Run Alembic migrations (upgrade head, DATABASE_URL from env/.env)"
	@echo "  Telegram collection (the collect extra; tgcrypto needs a C compiler on Python 3.14):"
	@echo "  make session       Generate Telegram session string (Streamlit, port 8502, run once)"
	@echo "  make backfill CH=@channelname  Backfill a channel"
	@echo "  make crawl         Run the paced single-account backfill crawler"
	@echo "  make test          Run pytest (offline; no llm/embed/collect extra needed)"
	@echo "  make lint          Run ruff + mypy"
	@echo "  make fmt           Auto-format with ruff"

setup:
	$(BOOTSTRAP_EMBED) all

data:
	$(BOOTSTRAP) fetch

db-up:
	$(BOOTSTRAP) db

# Stop only: nothing here ever removes the container, the volume or any data.
db-down:
	$(COMPOSE) stop

pipeline:
	$(BOOTSTRAP_EMBED) pipeline --mission $(MISSION)

# The public-corpus path: development tooling + the pipeline's embedding stages.
# `uv sync` removes the extras it is not given; collection adds `--extra collect`.
install:
	uv sync --extra dev --extra embed

migrate:
	uv run alembic upgrade head

# Generate Telegram session string (interactive web UI on port 8502, run once).
# streamlit lives in the optional "session" extra, hydrogram in "collect".
session:
	uv run --extra session --extra collect streamlit run scripts/session_web.py --server.port 8502

# Backfill a single channel: make backfill CH=@Vbachir
backfill:
	$(COLLECT) python scripts/backfill.py --channel $(CH) --limit 500

# Paced crawler — serialized single +33 account, read-only (see docs/method/07-tiers-and-governance.md §7.3)
crawl:
	$(COLLECT) python scripts/paced_backfill.py

# Static analyst webapp (React+Vite, no backend — reads the precomputed JSON bundle).
# Runs `npm ci` first when webapp/node_modules is missing or older than the lockfile.
webapp:
	$(BOOTSTRAP) webapp

test:
	$(DEV) python -m pytest

lint:
	$(DEV) ruff check src/ tests/
	$(DEV) mypy src/ --ignore-missing-imports

fmt:
	$(DEV) ruff format src/ tests/
	$(DEV) ruff check --fix src/ tests/
