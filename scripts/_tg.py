"""Shared Hydrogram client factory for the diagnostic/probe scripts.

Centralizes the boilerplate that was duplicated across every diagnostic script:
loading the ``.env`` file and building a read-only MTProto ``hydrogram.Client``
from the environment.

The variables are resolved like the production client: the canonical
``TELEGRAM_API_ID`` / ``TELEGRAM_API_HASH`` / ``TELEGRAM_SESSION_STRING`` first,
then the legacy ``TG_API_ID`` / ``TG_API_HASH`` / ``TG_SESSION_STRING`` aliases
(``src.ingestor.session.resolve_session_env``).

This helper is intentionally for the *ad hoc diagnostic scripts only*. The
production ingestion path lives in ``src/ingestor/client.py``
(``TelegramClient.from_env``), with FLOOD_WAIT handling and account hygiene;
do not route pipeline code through this module.

Hydrogram is in the optional ``collect`` extra: run the probes with
``uv run --extra collect python scripts/<probe>.py``.

Usage::

    from _tg import tg_client

    async with tg_client("my_probe") as c:
        ...

``load_dotenv()`` is called at import time, mirroring the original scripts which
each called it at module top level.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from hydrogram import Client  # noqa: E402

from src.ingestor.session import resolve_session_env  # noqa: E402

load_dotenv()


def make_client(name: str) -> Client:
    """Build a read-only Hydrogram ``Client`` from the environment.

    Parameters
    ----------
    name:
        Hydrogram session name (kept per-script, as in the original boilerplate).

    Returns
    -------
    hydrogram.Client
        An un-started client. Use it as an async context manager
        (``async with``) exactly like the original inline ``Client(...)``.
    """
    env = resolve_session_env()
    api_id, api_hash, session = env["api_id"], env["api_hash"], env["session"]
    if not (api_id and api_hash and session):
        raise RuntimeError(
            "TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING must be set "
            "(legacy aliases TG_API_ID / TG_API_HASH / TG_SESSION_STRING are also "
            "accepted), e.g. in .env; `make session` generates the session string."
        )
    return Client(
        name,
        api_id=int(api_id),
        api_hash=api_hash,
        session_string=session,
    )


# Convenience alias: ``make_client`` returns a Client, which is itself an async
# context manager — so ``async with tg_client("x") as c:`` reads naturally.
tg_client = make_client
