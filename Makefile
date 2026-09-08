.PHONY: help install install-ml migrate session backfill crawl webapp test lint fmt

help:
	@echo "Idéfix — available commands:"
	@echo "  make install       Install Python deps with uv (uv sync)"
	@echo "  make install-ml    Install PyTorch + PyG (CPU, run once, special index)"
	@echo "  make migrate       Run Alembic migrations (upgrade head)"
	@echo "  make session       Generate Telegram session string (Streamlit, port 8502, run once)"
	@echo "  make backfill CH=@channelname  Backfill a channel"
	@echo "  make crawl         Run the paced single-account backfill crawler"
	@echo "  make webapp        Serve the static analyst webapp (Vite dev server)"
	@echo "  make test          Run pytest"
	@echo "  make lint          Run ruff + mypy"
	@echo "  make fmt           Auto-format with ruff"

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

# Paced crawler — serialized single +33 account, read-only (see docs/ops-runbook.md §7)
crawl:
	uv run python scripts/paced_backfill.py

# Static analyst webapp (React+Vite, no backend — reads the precomputed JSON bundle)
webapp:
	cd webapp && npm run dev

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run mypy src/ --ignore-missing-imports

fmt:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/
