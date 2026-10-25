.PHONY: help setup data db-up db-down pipeline install install-ml migrate session backfill crawl webapp test lint fmt

# Reproducible setup on the public corpus (scripts/bootstrap.py, docker-compose.yml).
# No Telegram credentials and no .env needed. The database port defaults to 5433;
# override with the IDEFIX_DB_PORT environment variable. No target deletes data:
# the restore only ever happens into an empty database.
BOOTSTRAP := uv run python scripts/bootstrap.py
# The pipeline's embedding stages need the optional "embed" extra.
BOOTSTRAP_EMBED := uv run --extra embed python scripts/bootstrap.py
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
	@echo "  Development and collection:"
	@echo "  make install       Install Python deps with uv (uv sync)"
	@echo "  make install-ml    Install PyTorch + PyG (CPU, run once, special index)"
	@echo "  make migrate       Run Alembic migrations (upgrade head, DATABASE_URL from env/.env)"
	@echo "  make session       Generate Telegram session string (Streamlit, port 8502, run once)"
	@echo "  make backfill CH=@channelname  Backfill a channel"
	@echo "  make crawl         Run the paced single-account backfill crawler"
	@echo "  make test          Run pytest"
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

install:
	uv sync

# PyTorch + PyG (CPU) — run once separately due to special index
install-ml:
	uv pip install torch --index-url https://download.pytorch.org/whl/cpu
	uv pip install torch-geometric --find-links https://data.pyg.org/whl/torch-2.3.0+cpu.html

migrate:
	uv run alembic upgrade head

# Generate Telegram session string (interactive web UI on port 8502, run once).
# streamlit lives in the optional "session" extra, not the base env.
session:
	uv run --extra session streamlit run scripts/session_web.py --server.port 8502

# Backfill a single channel: make backfill CH=@Vbachir
backfill:
	uv run python scripts/backfill.py --channel $(CH) --limit 500

# Paced crawler — serialized single +33 account, read-only (see docs/method/07-tiers-and-governance.md §7.3)
crawl:
	uv run python scripts/paced_backfill.py

# Static analyst webapp (React+Vite, no backend — reads the precomputed JSON bundle).
# Runs `npm ci` first when webapp/node_modules is missing or older than the lockfile.
webapp:
	$(BOOTSTRAP) webapp

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run mypy src/ --ignore-missing-imports

fmt:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/
