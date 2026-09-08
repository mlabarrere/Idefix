"""
Hydrogram MTProto client — read-only Telegram ingestion.

Usage:
    client = TelegramClient.from_env()
    async with client:
        messages = await client.get_history("@Vbachir", limit=100)
"""

import asyncio
import random
from pathlib import Path

import structlog
from hydrogram import Client
from hydrogram.errors import AuthKeyUnregistered, FloodWait, UserDeactivated

log = structlog.get_logger(__name__)

MAX_RETRIES = 5


async def with_flood_wait(coro, context: str = ""):
    """
    Wrap any Hydrogram API call with FLOOD_WAIT handling + jitter.
    NEVER retry infinitely. NEVER sleep without jitter.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return await coro
        except FloodWait as e:
            wait = e.value + random.uniform(1, 5)
            log.warning(
                "flood_wait",
                event="flood_wait",
                context=context,
                seconds=round(wait, 1),
                attempt=attempt + 1,
                max_retries=MAX_RETRIES,
            )
            await asyncio.sleep(wait)
        except (UserDeactivated, AuthKeyUnregistered) as e:
            log.error("auth_error", event="auth_error", error=str(e))
            raise
    raise RuntimeError(f"Max retries ({MAX_RETRIES}) exceeded for {context}")


class TelegramClient:
    """Thin wrapper around Hydrogram Client for Idéfix."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_string: str | None = None,
        session_file: str | None = None,
        phone: str | None = None,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.phone = phone

        # Prefer session string (for Docker), fall back to session file (local dev)
        if session_string:
            self._client = Client(
                name="disinfo_trace",
                api_id=api_id,
                api_hash=api_hash,
                session_string=session_string,
            )
        elif session_file:
            self._client = Client(
                name=session_file,
                api_id=api_id,
                api_hash=api_hash,
                phone_number=phone,
            )
        else:
            raise ValueError("Either session_string or session_file must be provided")

    @classmethod
    def from_env(cls) -> "TelegramClient":
        """Build client from environment variables.

        Resolves the canonical ``TELEGRAM_*`` names with backward-compatible
        ``TG_*`` aliases (preferring the new names) via
        ``src.ingestor.session.resolve_session_env``. Lazy import avoids an
        import cycle (session.py imports this client only inside its live check).
        """
        from src.ingestor.session import resolve_session_env

        env = resolve_session_env()
        api_id, api_hash = env["api_id"], env["api_hash"]
        if not api_id or not api_hash:
            raise EnvironmentError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH (aliases TG_API_ID / "
                "TG_API_HASH) must be set. "
                "Get them at https://my.telegram.org → API development tools"
            )
        return cls(
            api_id=int(api_id),
            api_hash=api_hash,
            session_string=env["session"] or None,
            session_file=str(Path.home() / ".disinfo_trace_session"),
            phone=env["phone"],
        )

    async def __aenter__(self):
        await self._client.start()
        log.info("telegram_client_started")
        return self

    async def __aexit__(self, *args):
        await self._client.stop()
        log.info("telegram_client_stopped")

    async def get_history(
        self,
        channel: str | int,
        limit: int = 100,
        offset_id: int = 0,
    ) -> list:
        """
        Fetch up to `limit` messages from a channel.
        Returns list of Hydrogram Message objects.
        """
        messages = []
        # get_chat_history is an async generator — iterate directly, handle FloodWait per-item
        async for msg in self._client.get_chat_history(channel, limit=limit, offset_id=offset_id):
            messages.append(msg)
        log.info(
            "history_fetched",
            event="history_fetched",
            channel=str(channel),
            count=len(messages),
        )
        return messages

    async def get_channel_info(self, channel: str | int):
        """Fetch channel metadata (coroutine — can be awaited)."""
        for attempt in range(MAX_RETRIES):
            try:
                return await self._client.get_chat(channel)
            except FloodWait as e:
                wait = e.value + random.uniform(1, 5)
                log.warning(
                    "flood_wait",
                    context=f"get_chat:{channel}",
                    seconds=round(wait, 1),
                    attempt=attempt + 1,
                )
                await asyncio.sleep(wait)
        raise RuntimeError(f"Max retries exceeded for get_chat:{channel}")

    async def iter_history(self, channel: str | int, limit: int = 1000):
        """
        Async generator: yield messages one by one for large backfills.
        FloodWait is handled inside with a sleep; the generator pauses and resumes.
        Usage: async for msg in client.iter_history("@Vbachir", limit=5000):
        """
        count = 0
        retries = 0
        # We can't wrap an async generator in with_flood_wait, so we handle FloodWait here.
        # Hydrogram raises FloodWait at the iterator level between API pages.
        while True:
            try:
                async for msg in self._client.get_chat_history(channel, limit=limit):
                    yield msg
                    count += 1
                break  # completed without flood
            except FloodWait as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    raise
                wait = e.value + random.uniform(1, 5)
                log.warning(
                    "flood_wait_in_iter", seconds=round(wait, 1), count=count, retries=retries
                )
                await asyncio.sleep(wait)
                # Re-enter the generator from scratch is not ideal, but Hydrogram does not
                # support resuming — we rely on ON CONFLICT DO NOTHING in insert_message to
                # deduplicate. For large backfills this doubles work; acceptable for PoC.

        log.info("iter_history_complete", channel=str(channel), total=count)
