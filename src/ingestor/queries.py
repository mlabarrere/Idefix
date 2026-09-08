"""PostgreSQL queries for the ingestor service."""

import asyncpg
import structlog

log = structlog.get_logger(__name__)


async def upsert_channel(conn: asyncpg.Connection, channel_id: int, data: dict) -> None:
    # description (channel bio, chat.description) added in migration 0003.
    # COALESCE on update so a later poll that lacks the bio (e.g. a forward-origin
    # upsert) does NOT wipe a description captured by an earlier full backfill.
    await conn.execute(
        """
        INSERT INTO channels (channel_id, username, title, member_count, description, tier,
                              is_in_catalogue, catalogue_source, first_seen_at, extra)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
        ON CONFLICT (channel_id) DO UPDATE SET
            username       = EXCLUDED.username,
            title          = EXCLUDED.title,
            member_count   = EXCLUDED.member_count,
            description    = COALESCE(EXCLUDED.description, channels.description),
            extra          = COALESCE(channels.extra, '{}'::jsonb)
                             || COALESCE(EXCLUDED.extra, '{}'::jsonb),
            last_polled_at = NOW()
        """,
        channel_id,
        data.get("username"),
        data.get("title"),
        data.get("member_count"),
        data.get("description"),
        data.get("tier", "cold"),
        data.get("is_in_catalogue", False),
        data.get("catalogue_source"),
        data.get("first_seen_at"),
        data.get("extra"),
    )


async def insert_message(conn: asyncpg.Connection, msg: dict) -> bool:
    try:
        result = await conn.execute(
            """
            INSERT INTO messages (
                message_id, channel_id, timestamp, text, language,
                forward_from_channel_id, forward_from_message_id, forward_delay_seconds,
                views, forwards, media_type, media_hash, urls, raw_content
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14::jsonb)
            ON CONFLICT (channel_id, message_id) DO NOTHING
            """,
            msg["message_id"], msg["channel_id"],
            msg["timestamp"], msg.get("text"), msg.get("language"),
            msg.get("forward_from_channel_id"), msg.get("forward_from_message_id"),
            msg.get("forward_delay_seconds"),
            msg.get("views"), msg.get("forwards"),
            msg.get("media_type"), msg.get("media_hash"),
            None, None,
        )
        return isinstance(result, str) and result.endswith("1")
    except asyncpg.UniqueViolationError:
        return False


async def insert_comment(conn: asyncpg.Connection, row: dict) -> bool:
    """Insert a public-group commenter row (idempotent).

    RGPD: persists an individual commenter (id + username) of a PUBLIC linked
    discussion group — public-interest legal basis, see migration 0003 header.
    ON CONFLICT DO NOTHING on (channel_id, message_id, commenter_id, timestamp)
    makes re-crawls safe. Returns True if a new row was inserted.
    """
    try:
        result = await conn.execute(
            """
            INSERT INTO comments (
                channel_id, message_id, commenter_id, commenter_username, text, timestamp
            ) VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (channel_id, message_id, commenter_id, timestamp) DO NOTHING
            """,
            row.get("channel_id"),
            row.get("message_id"),
            row.get("commenter_id"),
            row.get("commenter_username"),
            row.get("text"),
            row.get("timestamp"),
        )
        # asyncpg returns the command tag, e.g. "INSERT 0 1" / "INSERT 0 0".
        return isinstance(result, str) and result.endswith("1")
    except asyncpg.UniqueViolationError:
        return False


async def get_latest_message_id(conn: asyncpg.Connection, channel_id: int) -> int:
    row = await conn.fetchrow(
        "SELECT MAX(message_id) AS max_id FROM messages WHERE channel_id = $1", channel_id
    )
    return row["max_id"] or 0
