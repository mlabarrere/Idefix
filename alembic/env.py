import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load DATABASE_URL from .env and inject it into the Alembic config so the URL
# is NOT hard-coded in alembic.ini (single source of truth = .env).
# DATABASE_URL already carries the "+asyncpg" suffix, which is exactly what the
# async engine below expects — no stripping needed (no sync driver is installed:
# neither psycopg2 nor psycopg3 is available in this venv, so the async path is
# the only viable one).
load_dotenv()
_db_url = os.environ.get("DATABASE_URL")
if not _db_url:
    # Fail FAST and CLEAR. Without this guard a missing DATABASE_URL leaves
    # sqlalchemy.url unset (commented out in alembic.ini), producing an opaque
    # downstream error: a None URL in offline mode, a "no URL" engine error online.
    raise RuntimeError(
        "DATABASE_URL is not set. Alembic loads it from the environment / .env. "
        "Set it (e.g. postgresql+asyncpg://user:pass@host/db) before running migrations."
    )
# escape '%' for ConfigParser interpolation safety (URLs rarely contain it,
# but credentials might be percent-encoded).
config.set_main_option("sqlalchemy.url", _db_url.replace("%", "%%"))

# No ORM models in this project — migrations are written BY HAND
# (op.execute / op.create_table). Autogenerate is intentionally disabled.
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
