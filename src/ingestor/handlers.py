"""Ingestor handlers — backfill, live polling, channel upsert."""

from datetime import datetime, timezone

import asyncpg
import structlog

from src.ingestor import queries
from src.ingestor.client import TelegramClient

log = structlog.get_logger(__name__)


def _parse_message(msg, channel_id: int) -> dict:
    """Convert a Hydrogram Message to a flat dict for PostgreSQL."""
    # Hydrogram exposes channel forwards via forward_from_chat / forward_from_message_id
    # / forward_date (Pyrogram-style). Fall back to the newer forward_origin API if present.
    fwd_channel_id = fwd_message_id = fwd_delay = None
    fwd_chat = getattr(msg, "forward_from_chat", None)
    fwd_date = getattr(msg, "forward_date", None)
    if fwd_chat is not None:
        fwd_channel_id = fwd_chat.id
        fwd_message_id = getattr(msg, "forward_from_message_id", None)
    else:
        fo = getattr(msg, "forward_origin", None)
        fo_chat = getattr(fo, "chat", None) if fo else None
        if fo_chat is not None:
            fwd_channel_id = fo_chat.id
            fwd_message_id = getattr(fo, "message_id", None)
            fwd_date = fwd_date or getattr(fo, "date", None)
    if fwd_channel_id is not None and fwd_date and msg.date:
        fwd_delay = max(0, int((msg.date - fwd_date).total_seconds()))

    # Detect the media type AND grab the stable file_unique_id of whichever
    # media object is attached — NO download required. Telegram returns the same
    # file_unique_id for the same underlying media across forwards/re-uploads, so
    # it doubles as the media identity stored in messages.media_hash (the future
    # MEDIA_REUSE extractor groups on it). Order matters: photo/video first, then
    # the rarer kinds. We probe a fixed list of (attr, type-label) pairs.
    media_type = None
    media_hash = None
    for attr, label in (
        ("photo", "photo"),
        ("video", "video"),
        ("document", "document"),
        ("animation", "animation"),
        ("audio", "audio"),
        ("voice", "voice"),
    ):
        media_obj = getattr(msg, attr, None)
        if media_obj is not None:
            media_type = label
            media_hash = getattr(media_obj, "file_unique_id", None)
            break

    return {
        "message_id": msg.id,
        "channel_id": channel_id,
        "timestamp": msg.date or datetime.now(timezone.utc),
        "text": msg.text or msg.caption or None,
        "language": None,
        "forward_from_channel_id": fwd_channel_id,
        "forward_from_message_id": fwd_message_id,
        "forward_delay_seconds": fwd_delay,
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
        "media_type": media_type,
        "media_hash": media_hash,
    }


def _extract_comment_row(msg, channel_id: int) -> dict | None:
    """Convert a linked-group message into a ``comments`` row, or None to skip.

    RGPD: this logs an INDIVIDUAL commenter (id + username) of a PUBLIC linked
    discussion group — see the 0003 migration / enrich_recrawl.py header for the
    public-interest legal basis and minimization rules. Messages without an
    identifiable author (``from_user`` is None — service messages, anonymous
    admins) are skipped: there is no individual to log.

    The ``channel_id`` recorded is the MONITORED channel (the broadcast channel),
    not the linked-group id, so co-commenter edges are keyed to the catalogue
    channel the discussion belongs to.
    """
    author = getattr(msg, "from_user", None)
    if author is None or getattr(author, "id", None) is None:
        return None
    return {
        "channel_id": channel_id,
        "message_id": getattr(msg, "id", None),
        "commenter_id": author.id,
        "commenter_username": getattr(author, "username", None),
        "text": getattr(msg, "text", None) or getattr(msg, "caption", None) or None,
        "timestamp": getattr(msg, "date", None),
    }


async def backfill_channel(
    client: TelegramClient,
    conn: asyncpg.Connection,
    channel: str | int,
    limit: int = 500,
) -> int:
    log.info("backfill_start", channel=str(channel), limit=limit)

    try:
        chat = await client.get_channel_info(channel)
    except Exception as e:
        log.error("channel_resolve_failed", channel=str(channel), error=str(e))
        return 0

    channel_id = chat.id
    await queries.upsert_channel(conn, channel_id, {
        "username": getattr(chat, "username", None),
        "title": getattr(chat, "title", None),
        "member_count": getattr(chat, "members_count", None),
        "description": getattr(chat, "description", None),
        "tier": "warm",
        "first_seen_at": datetime.now(timezone.utc),
    })

    inserted = 0
    origins: dict[int, tuple] = {}
    # Pass the numeric channel_id — avoids username re-resolution for fresh accounts
    async for msg in client.iter_history(channel_id, limit=limit):
        if not msg or not msg.id:
            continue
        parsed = _parse_message(msg, channel_id)
        ok = await queries.insert_message(conn, parsed)
        if ok:
            inserted += 1
        # Capture forward-origin identity (carried by the forward object): the
        # access_hash is lost once we only keep the numeric id, so persist title/
        # username here. This turns snowball hop-1 sources into named, re-backfillable nodes.
        fc = getattr(msg, "forward_from_chat", None)
        if fc is not None and getattr(fc, "id", None) and fc.id != channel_id:
            origins[fc.id] = (getattr(fc, "username", None), getattr(fc, "title", None))
        if inserted % 100 == 0 and inserted > 0:
            log.info("backfill_progress", inserted=inserted, channel=str(channel))

    # Persist discovered forward-origin channels (snowball hop-1, catalogue-ready)
    for oid, (ouname, otitle) in origins.items():
        await queries.upsert_channel(conn, oid, {
            "username": ouname, "title": otitle,
            "tier": "discovered", "is_in_catalogue": False,
            "catalogue_source": "forward_origin",
            "first_seen_at": datetime.now(timezone.utc),
        })

    log.info("backfill_complete", channel=str(channel), channel_id=channel_id,
             inserted=inserted, discovered=len(origins))
    return inserted


async def fetch_comments(
    client: TelegramClient,
    conn: asyncpg.Connection,
    channel: str | int,
    limit: int = 500,
) -> int:
    """Log commenters of a channel's PUBLIC linked discussion group.

    Telegram broadcast channels can have a linked discussion group; the messages
    posted there are the "comments" under channel posts. We resolve the channel,
    read ``chat.linked_chat`` (the discussion group), and iterate its history
    read-only (FLOOD_WAIT handled by the client). Each authored message yields a
    ``comments`` row (commenter id + username + text + timestamp), keyed to the
    MONITORED channel id.

    RGPD: collects INDIVIDUAL commenters of a PUBLIC group — public-interest
    legal basis, see the 0003 migration / enrich_recrawl.py header. NEVER touches
    private groups (resolution simply fails / returns no linked_chat).

    Returns the number of comment rows inserted (0 if there is no linked group,
    if resolution fails, or if all messages are author-less).
    """
    log.info("fetch_comments_start", channel=str(channel), limit=limit)

    # Résolution canal + groupe lié dans UN SEUL try : un groupe de discussion
    # INTERDIT (ChannelForbidden) fait lever une AttributeError quand Hydrogram
    # construit l'objet linked_chat -> on traite ça comme « pas de groupe
    # accessible » (gracieux) au lieu de planter (bug attrapé en validation live).
    try:
        chat = await client.get_channel_info(channel)
        channel_id = chat.id
        linked = getattr(chat, "linked_chat", None)
        linked_id = getattr(linked, "id", None) if linked is not None else None
    except Exception as e:
        log.warning("comments_resolve_failed", channel=str(channel), error=str(e)[:80])
        return 0

    if linked_id is None:
        log.info("no_linked_group", channel=str(channel), channel_id=channel_id)
        return 0

    inserted = 0
    # Itère le groupe lié en lecture seule (FLOOD_WAIT géré). Un groupe
    # inaccessible (interdit/privé) en cours d'itération -> on s'arrête
    # proprement sur ce qui a été collecté.
    try:
        async for msg in client.iter_history(linked_id, limit=limit):
            if not msg or not getattr(msg, "id", None):
                continue
            row = _extract_comment_row(msg, channel_id)
            if row is None:
                continue
            ok = await queries.insert_comment(conn, row)
            if ok:
                inserted += 1
            if inserted % 100 == 0 and inserted > 0:
                log.info("comments_progress", inserted=inserted, channel=str(channel))
    except Exception as e:
        log.warning("comments_group_inaccessible", channel=str(channel),
                    linked_chat_id=linked_id, error=str(e)[:80], inserted=inserted)
        return inserted

    log.info("fetch_comments_complete", channel=str(channel), channel_id=channel_id,
             linked_chat_id=linked_id, inserted=inserted)
    return inserted
