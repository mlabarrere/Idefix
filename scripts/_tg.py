"""Shared Hydrogram client factory for the diagnostic/probe scripts.

Centralizes the boilerplate that was duplicated across every diagnostic script:
loading the ``.env`` file and building a read-only MTProto ``hydrogram.Client``
from the ``TG_API_ID`` / ``TG_API_HASH`` / ``TG_SESSION_STRING`` environment
variables.

This helper is intentionally for the *ad hoc diagnostic scripts only*. The
production ingestion path lives in ``src/ingestor/client.py``
(``TelegramClient.from_env``), with FLOOD_WAIT handling and account hygiene;
do not route pipeline code through this module.

Behaviour is identical to the previous inline construction::

    from hydrogram import Client
    Client(name,
           api_id=int(os.environ["TG_API_ID"]),
           api_hash=os.environ["TG_API_HASH"],
           session_string=os.environ["TG_SESSION_STRING"])

Usage::

    from _tg import tg_client

    async with tg_client("my_probe") as c:
        ...

``load_dotenv()`` is called at import time, mirroring the original scripts which
each called it at module top level.
"""

import os

from dotenv import load_dotenv
from hydrogram import Client

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
    return Client(
        name,
        api_id=int(os.environ["TG_API_ID"]),
        api_hash=os.environ["TG_API_HASH"],
        session_string=os.environ["TG_SESSION_STRING"],
    )


# Convenience alias: ``make_client`` returns a Client, which is itself an async
# context manager — so ``async with tg_client("x") as c:`` reads naturally.
tg_client = make_client
