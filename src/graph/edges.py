"""edges — derive the channel-centric multiplex graph from PostgreSQL.

Chantier 2b. This module materializes the multiplex edge model defined in
``_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md`` §2.3
(SOURCE OF TRUTH) into the persistent ``edges`` table created by
``alembic/versions/0002_edges.py``.

Edge families materialized THIS round (graph-model §2.3):

  Propagation   FORWARD       directed  origin -> relayer   (channel->channel)
  Influence     MENTIONS      directed  channel -> channel  (resolved @username)
                CITES_DOMAIN  directed  channel -> domain   (non-platform host)
  Coordination  CO_FORWARD    undirected, time-windowed (Δt)  (same forward origin)
  (windowed)    CO_URL        undirected, time-windowed (Δt)  (same cited domain)
                CO_URL_EXACT  undirected, time-windowed (Δt)  (same FULL url)
                CO_HASHTAG    undirected, time-windowed (Δt)  (same #hashtag)
                MEDIA_REUSE   undirected, time-windowed (Δt)  (same media_hash)

CO_URL vs CO_URL_EXACT — both are kept, they are different signals:

  * CO_URL pairs channels that cited the same registrable DOMAIN within Δt
    (broad: "both link to pravda-fr.com"). Domain-level co-citation.
  * CO_URL_EXACT pairs channels that posted the same FULL URL within Δt
    (tight: "both link to pravda-fr.com/article-42"). Posting the identical
    deep-link is a much stronger coordination signal than sharing a host, so it
    is emitted as its own type rather than folded into CO_URL.

MEDIA_REUSE is wired but YIELDS NOTHING TODAY: ``messages.media_hash`` is NULL
across the corpus (no media-download stage yet — graph-model §4 "différée —
downloads"). The deriver activates automatically once media hashes are populated;
it is unit-tested against simulated rows that carry a media_hash.

DEFERRED (NOT this round — documented as TODO, see graph-model §2.3 / §4):

  * COPYPASTA / TEXT_SIM — text-similarity coordination edge. Needs threshold
    calibration (D3lta copypasta 0.693 / rewording 0.715 / translation 0.85) and
    a similarity backend (BGE-M3 / embeddings). TODO: add once thresholds are
    calibrated on the annotated corpus.

Design (mirrors the migration docstring):

  * Pure derivation functions (``derive_*``) turn simulated/real ``messages``
    rows into ``Edge`` dataclasses. They are I/O-free and fully unit-testable.
  * A single DB-facing entry point (``derive_and_upsert_edges``) reads
    ``messages`` / ``channels`` from PostgreSQL via asyncpg and UPSERTs the
    derived edges. No Telegram/MTProto contact — read-only on PostgreSQL.

Four load-bearing rules from code review (enforced here):

  1. Undirected coordination edges (CO_FORWARD / CO_URL) are canonicalized so
     ``src_channel_id < dst_channel_id`` — one row per unordered pair (the unique
     index does NOT dedupe (A,B) vs (B,A)).
  2. Every coordination edge carries a non-NULL ``window_delta_seconds`` (the
     observed temporal spread). A coordination edge without Δt has no probative
     value (graph-model §2.3.2) and is NOT emitted.
  3. UPSERT is idempotent on the expression unique index ``uq_edges_src_dst_type``
     ``(src_channel_id, COALESCE(dst_channel_id,-1), COALESCE(dst_domain,''),
     edge_type)`` — re-running the derivation never duplicates rows.
  4. ``dst_domain`` is always lowercase (``canonical_domain`` does this) and never
     ''. CITES_DOMAIN targets a domain; all other types target a channel — the
     ``ck_edges_exactly_one_dst`` CHECK is respected.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations

import structlog

from src.normalizer.handlers import (
    canonical_domain,
    clean_text,
    extract_hashtags,
    extract_mentions,
    extract_urls,
    is_platform_host,
)

log = structlog.get_logger(__name__)

# Default coordination window: multi-day (Telegram forward delays are heavy-tailed
# over days — docs/method/02-graph-model.md §2.2). 72h is a sane configurable default.
DEFAULT_WINDOW_SECONDS = 72 * 3600

EDGE_TYPES_DIRECTED = ("FORWARD", "MENTIONS", "CITES_DOMAIN")
EDGE_TYPES_COORDINATION = (
    "CO_FORWARD",
    "CO_URL",
    "CO_URL_EXACT",
    "CO_HASHTAG",
    "MEDIA_REUSE",
)


@dataclass
class Edge:
    """A single derived multiplex edge, ready to UPSERT into the ``edges`` table.

    Exactly one of ``dst_channel_id`` / ``dst_domain`` is set (CHECK
    ck_edges_exactly_one_dst). Coordination edges always carry
    ``window_delta_seconds`` (load-bearing rule 2).
    """

    src_channel_id: int
    edge_type: str
    dst_channel_id: int | None = None
    dst_domain: str | None = None
    count: int = 1
    weight: float | None = None
    delay_seconds: int | None = None
    text_sim: float | None = None
    window_delta_seconds: int | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    attrs: dict | None = field(default=None)


# --------------------------------------------------------------------------- #
# Pure derivation functions (no DB / no network — unit-testable)              #
# --------------------------------------------------------------------------- #
#
# Each takes an iterable of ``messages`` rows. A row is any mapping exposing:
#   channel_id, message_id, timestamp, text,
#   forward_from_channel_id, forward_delay_seconds
# (asyncpg.Record satisfies this; tests pass plain dicts.)


def _ts(row) -> datetime | None:
    return row.get("timestamp") if isinstance(row, dict) else row["timestamp"]


def _get(row, key, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        v = row[key]
    except (KeyError, IndexError):
        return default
    return default if v is None else v


def derive_forward_edges(messages) -> list[Edge]:
    """FORWARD A->B (origin -> relayer), aggregated.

    ``count`` = number of forwards; ``delay_seconds`` = min observed delay.
    Self-loops (origin == relayer) are EXCLUDED (build_graph.py convention).
    """
    agg: dict[tuple[int, int], dict] = {}
    for row in messages:
        origin = _get(row, "forward_from_channel_id")
        reposter = _get(row, "channel_id")
        if origin is None or reposter is None:
            continue
        if origin == reposter:  # self-loop excluded
            continue
        key = (origin, reposter)
        delay = _get(row, "forward_delay_seconds")
        bucket = agg.setdefault(key, {"count": 0, "min_delay": None})
        bucket["count"] += 1
        if delay is not None:
            cur = bucket["min_delay"]
            bucket["min_delay"] = delay if cur is None else min(cur, delay)

    return [
        Edge(
            src_channel_id=origin,
            dst_channel_id=reposter,
            edge_type="FORWARD",
            count=b["count"],
            delay_seconds=b["min_delay"],
        )
        for (origin, reposter), b in agg.items()
    ]


def derive_mention_edges(messages, known_usernames: dict[str, int]) -> list[Edge]:
    """MENTIONS A->B (directed), aggregated.

    ``known_usernames`` maps a LOWERCASE username -> channel_id. Mentions that do
    not resolve to a known channel are IGNORED (no edge to a non-existent node).
    ``count`` = number of resolved mention occurrences.
    """
    # Normalize the resolver to lowercase keys (channels.username may be mixed case).
    resolver = {(u or "").lower(): cid for u, cid in known_usernames.items() if u}
    agg: Counter[tuple[int, int]] = Counter()
    for row in messages:
        src = _get(row, "channel_id")
        if src is None:
            continue
        for username in extract_mentions(_get(row, "text")):  # already lowercased
            dst = resolver.get(username)
            if dst is None or dst == src:  # unresolved or self-mention
                continue
            agg[(src, dst)] += 1

    return [
        Edge(src_channel_id=src, dst_channel_id=dst, edge_type="MENTIONS", count=n)
        for (src, dst), n in agg.items()
    ]


def derive_cites_domain_edges(messages) -> list[Edge]:
    """CITES_DOMAIN channel->domain (directed), aggregated.

    URLs are re-derived from ``text`` (messages.urls is often empty — graph-model
    §2). Platform/shortener hosts are excluded (is_platform_host). ``dst_domain``
    is the lowercase canonical domain (canonical_domain). ``None`` domains are
    skipped — NEVER insert an empty dst_domain (load-bearing rule 4).
    ``count`` = number of citations.
    """
    agg: dict[tuple[int, str], int] = {}
    for row in messages:
        src = _get(row, "channel_id")
        if src is None:
            continue
        for url in extract_urls(_get(row, "text")):
            domain = canonical_domain(url)
            if not domain or is_platform_host(domain):
                continue
            agg[(src, domain)] = agg.get((src, domain), 0) + 1

    return [
        Edge(src_channel_id=src, dst_domain=domain, edge_type="CITES_DOMAIN", count=n)
        for (src, domain), n in agg.items()
    ]


def _coordination_edges(
    *,
    edge_type: str,
    # item_key -> list of (channel_id, timestamp) participations
    participations: dict,
    window_seconds: int,
    attr_builder,
) -> list[Edge]:
    """Generic windowed-coordination builder shared by CO_FORWARD / CO_URL.

    For each shared item (a forward origin, or a cited domain), pair up the
    channels that touched it WITHIN ``window_seconds`` of each other. Each pair is
    canonicalized to ``a < b`` (rule 1) and carries the observed temporal spread
    as ``window_delta_seconds`` (rule 2 — never NULL, never emitted without it).

    Aggregates across all shared items into one row per unordered pair: ``count``
    = number of shared items, attrs accumulate per ``attr_builder``.
    """
    # pair (a<b) -> {count, min_delta, max_delta, window_start, window_end, items[]}
    pairs: dict[tuple[int, int], dict] = {}

    for item_key, parts in participations.items():
        # de-dupe per channel: keep that channel's earliest touch of this item,
        # so one channel posting the same origin/domain many times is a single
        # participation (a self-pair is never coordination).
        earliest: dict[int, datetime] = {}
        for cid, ts in parts:
            if cid is None or ts is None:
                continue
            if cid not in earliest or ts < earliest[cid]:
                earliest[cid] = ts
        if len(earliest) < 2:
            continue

        for a, b in combinations(sorted(earliest), 2):  # a < b canonical (rule 1)
            ta, tb = earliest[a], earliest[b]
            delta = int(abs((tb - ta).total_seconds()))
            if delta > window_seconds:  # outside the Δt window — not coordination
                continue
            ws, we = (ta, tb) if ta <= tb else (tb, ta)
            p = pairs.get((a, b))
            if p is None:
                pairs[(a, b)] = {
                    "count": 1,
                    "min_delta": delta,
                    "max_delta": delta,
                    "window_start": ws,
                    "window_end": we,
                    "items": [item_key],
                }
            else:
                p["count"] += 1
                p["min_delta"] = min(p["min_delta"], delta)
                p["max_delta"] = max(p["max_delta"], delta)
                p["window_start"] = min(p["window_start"], ws)
                p["window_end"] = max(p["window_end"], we)
                p["items"].append(item_key)

    edges: list[Edge] = []
    for (a, b), p in pairs.items():
        edges.append(
            Edge(
                src_channel_id=a,
                dst_channel_id=b,
                edge_type=edge_type,
                count=p["count"],
                # tightness of coordination = the tightest observed pairing (rule 2)
                window_delta_seconds=p["min_delta"],
                window_start=p["window_start"],
                window_end=p["window_end"],
                attrs=attr_builder(p),
            )
        )
    return edges


def derive_co_forward_edges(messages, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> list[Edge]:
    """CO_FORWARD (undirected, windowed): channel pairs that relayed the SAME
    forward origin within Δt. ``attrs`` = number of common origins.
    """
    participations: dict[int, list] = {}
    for row in messages:
        origin = _get(row, "forward_from_channel_id")
        reposter = _get(row, "channel_id")
        ts = _ts(row)
        if origin is None or reposter is None or ts is None:
            continue
        if origin == reposter:  # self-forward is not a co-forward participation
            continue
        participations.setdefault(origin, []).append((reposter, ts))

    return _coordination_edges(
        edge_type="CO_FORWARD",
        participations=participations,
        window_seconds=window_seconds,
        attr_builder=lambda p: {"common_origins": p["count"]},
    )


def derive_co_url_edges(messages, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> list[Edge]:
    """CO_URL (undirected, windowed): channel pairs that cited the SAME domain
    within Δt. ``attrs`` = the shared domain(s). Platform/shortener hosts excluded.
    """
    participations: dict[str, list] = {}
    for row in messages:
        src = _get(row, "channel_id")
        ts = _ts(row)
        if src is None or ts is None:
            continue
        domains_here = set()
        for url in extract_urls(_get(row, "text")):
            domain = canonical_domain(url)
            if not domain or is_platform_host(domain):
                continue
            domains_here.add(domain)
        for domain in domains_here:
            participations.setdefault(domain, []).append((src, ts))

    return _coordination_edges(
        edge_type="CO_URL",
        participations=participations,
        window_seconds=window_seconds,
        # one domain per shared item; "shared_domains" lists the domains that
        # produced this pair (graph-model §2.3: CO_URL carries the domain).
        attr_builder=lambda p: {"shared_domains": sorted(set(p["items"]))},
    )


def derive_co_url_exact_edges(
    messages, window_seconds: int = DEFAULT_WINDOW_SECONDS
) -> list[Edge]:
    """CO_URL_EXACT (undirected, windowed): channel pairs that posted the SAME
    FULL URL within Δt. Tighter than CO_URL (which only requires the same domain):
    posting the identical deep-link is a strong coordination signal.

    URLs are re-derived from ``text`` (same source as CITES_DOMAIN / CO_URL).
    Platform/shortener hosts are excluded so a shared ``t.me/x`` or ``bit.ly/y``
    does not manufacture coordination. ``attrs`` = the shared URL(s).
    """
    participations: dict[str, list] = {}
    for row in messages:
        src = _get(row, "channel_id")
        ts = _ts(row)
        if src is None or ts is None:
            continue
        urls_here = set()
        for url in extract_urls(_get(row, "text")):
            domain = canonical_domain(url)
            if not domain or is_platform_host(domain):
                continue
            urls_here.add(url)
        for url in urls_here:
            participations.setdefault(url, []).append((src, ts))

    return _coordination_edges(
        edge_type="CO_URL_EXACT",
        participations=participations,
        window_seconds=window_seconds,
        attr_builder=lambda p: {"shared_urls": sorted(set(p["items"]))},
    )


def derive_co_hashtag_edges(
    messages, window_seconds: int = DEFAULT_WINDOW_SECONDS
) -> list[Edge]:
    """CO_HASHTAG (undirected, windowed): channel pairs that posted the SAME
    #hashtag within Δt. ``attrs`` = the shared hashtag(s).

    Hashtags are re-derived from ``text`` (extract_hashtags — multilingual,
    lowercased, deduped). One participation per (hashtag, channel): a channel
    spamming the same tag many times is a single touch (the shared builder keeps
    that channel's earliest occurrence). ``count`` = number of shared hashtags.
    """
    participations: dict[str, list] = {}
    for row in messages:
        src = _get(row, "channel_id")
        ts = _ts(row)
        if src is None or ts is None:
            continue
        for tag in extract_hashtags(_get(row, "text")):  # already deduped/lowered
            participations.setdefault(tag, []).append((src, ts))

    return _coordination_edges(
        edge_type="CO_HASHTAG",
        participations=participations,
        window_seconds=window_seconds,
        attr_builder=lambda p: {"shared_hashtags": sorted(set(p["items"]))},
    )


def derive_media_reuse_edges(
    messages, window_seconds: int = DEFAULT_WINDOW_SECONDS
) -> list[Edge]:
    """MEDIA_REUSE (undirected, windowed): channel pairs that posted the SAME
    ``media_hash`` (exact same media file / perceptual hash) within Δt.

    ``messages.media_hash`` is NULL across the corpus today (no media-download
    stage yet — graph-model §4 "différée — downloads"), so this returns an EMPTY
    list in production for now. It activates automatically once media hashes are
    populated; rows whose ``media_hash`` is None are skipped. ``attrs`` = the
    shared media hash(es).
    """
    participations: dict[str, list] = {}
    for row in messages:
        src = _get(row, "channel_id")
        ts = _ts(row)
        media_hash = _get(row, "media_hash")
        if src is None or ts is None or not media_hash:
            continue
        participations.setdefault(media_hash, []).append((src, ts))

    return _coordination_edges(
        edge_type="MEDIA_REUSE",
        participations=participations,
        window_seconds=window_seconds,
        attr_builder=lambda p: {"shared_media": sorted(set(p["items"]))},
    )


# Default semantic-similarity thresholds. Seeds align with the coordination-fabric
# registry (D3lta rewording 0.715 / translation 0.85), but they were tuned for
# OTHER backends and are MODEL-SPECIFIC: recalibrate for the chosen sentence-
# transformers model (scripts/calibrate_text_sim.py) before trusting the cutoffs.
TEXT_SIM_THRESHOLD = 0.715
TRANSLATION_THRESHOLD = 0.85
# Bound on messages embedded per pass (the similarity scan is O(N^2)).
MAX_TEXT_SIM_MESSAGES = 3000


def derive_text_sim_edges(
    messages,
    embedder,
    *,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    text_sim_threshold: float = TEXT_SIM_THRESHOLD,
    translation_threshold: float = TRANSLATION_THRESHOLD,
    max_messages: int = MAX_TEXT_SIM_MESSAGES,
) -> list[Edge]:
    """TEXT_SIM / TRANSLATION (undirected, windowed): channel pairs whose messages
    are semantically near-duplicate (rewording) or cross-lingual equivalents.

    Requires an ``embedder`` exposing ``encode_texts(list[str]) -> (N, D)``
    L2-normalized array — INJECTED so this stays unit-testable offline and so the
    default torch-free pipeline (``derive_all_edges``) never imports
    sentence-transformers. A pair is TRANSLATION when both message languages are
    known AND differ AND the cosine reaches ``translation_threshold``; otherwise
    TEXT_SIM at ``text_sim_threshold``. Aggregates per (channel pair, type):
    ``count`` = qualifying message-pairs, ``text_sim`` = max cosine,
    ``window_delta_seconds`` = tightest Δt (rule 2). Thresholds are model-specific
    — CALIBRATE.
    """
    import numpy as np

    items: list[tuple[int, datetime, str | None, str]] = []
    for row in messages:
        cid = _get(row, "channel_id")
        ts = _ts(row)
        text = clean_text(_get(row, "text"))
        if cid is None or ts is None or not text or len(text) <= 20:
            continue
        items.append((cid, ts, _get(row, "language"), text))

    # Bound the O(N^2) scan; keep the most substantial messages. Log the drop —
    # never silently cap coverage (no silent caps).
    if len(items) > max_messages:
        items.sort(key=lambda it: len(it[3]), reverse=True)
        log.info(
            "edges.text_sim.truncate", kept=max_messages, dropped=len(items) - max_messages
        )
        items = items[:max_messages]

    if len({it[0] for it in items}) < 2:
        return []

    emb = embedder.encode_texts([it[3] for it in items])
    if emb.shape[0] < 2:
        return []
    sim = emb @ emb.T  # cosine (rows are L2-normalized)

    iu, ju = np.triu_indices(len(items), k=1)
    keep = sim[iu, ju] >= text_sim_threshold
    cand_i, cand_j = iu[keep], ju[keep]

    # (a<b, edge_type) -> aggregate
    pairs: dict[tuple[int, int, str], dict] = {}
    for i, j in zip(cand_i.tolist(), cand_j.tolist()):
        ci, tsi, li, _ = items[i]
        cj, tsj, lj, _ = items[j]
        if ci == cj:  # same channel — not coordination
            continue
        delta = int(abs((tsj - tsi).total_seconds()))
        if delta > window_seconds:
            continue
        s = float(sim[i, j])
        cross = bool(li and lj and li != lj)
        etype = "TRANSLATION" if (cross and s >= translation_threshold) else "TEXT_SIM"
        a, b = (ci, cj) if ci < cj else (cj, ci)
        ws, we = (tsi, tsj) if tsi <= tsj else (tsj, tsi)
        key = (a, b, etype)
        p = pairs.get(key)
        if p is None:
            pairs[key] = {"count": 1, "max_sim": s, "min_delta": delta,
                          "window_start": ws, "window_end": we}
        else:
            p["count"] += 1
            p["max_sim"] = max(p["max_sim"], s)
            p["min_delta"] = min(p["min_delta"], delta)
            p["window_start"] = min(p["window_start"], ws)
            p["window_end"] = max(p["window_end"], we)

    return [
        Edge(
            src_channel_id=a,
            dst_channel_id=b,
            edge_type=etype,
            count=p["count"],
            text_sim=round(p["max_sim"], 4),
            window_delta_seconds=p["min_delta"],
            window_start=p["window_start"],
            window_end=p["window_end"],
            attrs={"max_text_sim": round(p["max_sim"], 4), "n_pairs": p["count"],
                   "model": getattr(embedder, "model_name", None)},
        )
        for (a, b, etype), p in pairs.items()
    ]


def derive_all_edges(
    messages,
    known_usernames: dict[str, int],
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> list[Edge]:
    """Derive every materialized edge family from a messages iterable.

    Note: ``messages`` is consumed once per family, so callers passing a generator
    should materialize it to a list first (DB path does).
    """
    rows = list(messages)
    return [
        *derive_forward_edges(rows),
        *derive_mention_edges(rows, known_usernames),
        *derive_cites_domain_edges(rows),
        *derive_co_forward_edges(rows, window_seconds),
        *derive_co_url_edges(rows, window_seconds),
        *derive_co_url_exact_edges(rows, window_seconds),
        *derive_co_hashtag_edges(rows, window_seconds),
        *derive_media_reuse_edges(rows, window_seconds),
    ]


# --------------------------------------------------------------------------- #
# DB I/O — read messages/channels, UPSERT edges (idempotent)                  #
# --------------------------------------------------------------------------- #

# ON CONFLICT targets the expression unique index uq_edges_src_dst_type. The
# conflict target must restate the index expressions EXACTLY (rule 3).
_UPSERT_SQL = """
INSERT INTO edges (
    src_channel_id, dst_channel_id, dst_domain, edge_type,
    count, weight, delay_seconds, text_sim,
    window_delta_seconds, window_start, window_end, attrs
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
ON CONFLICT (src_channel_id, COALESCE(dst_channel_id, -1), COALESCE(dst_domain, ''), edge_type)
DO UPDATE SET
    count                = EXCLUDED.count,
    weight               = EXCLUDED.weight,
    delay_seconds        = EXCLUDED.delay_seconds,
    text_sim             = EXCLUDED.text_sim,
    window_delta_seconds = EXCLUDED.window_delta_seconds,
    window_start         = EXCLUDED.window_start,
    window_end           = EXCLUDED.window_end,
    attrs                = EXCLUDED.attrs
"""


# _dsn() removed — connection pooling now handled by src.shared.db


async def _fetch_inputs(conn):
    """Read channels (id, username) + messages (forward + text) from PostgreSQL."""
    channels = await conn.fetch("SELECT channel_id, username FROM channels")
    messages = await conn.fetch(
        """
        SELECT channel_id, message_id, timestamp, text, language, media_hash,
               forward_from_channel_id, forward_delay_seconds
        FROM messages
        """
    )
    known = {r["username"]: r["channel_id"] for r in channels if r["username"]}
    return list(messages), known


async def derive_and_upsert_edges(
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    embedder=None,
) -> dict[str, int]:
    """Read PostgreSQL, derive all materialized edge families, UPSERT them.

    Idempotent (rule 3): re-running does not duplicate rows. Returns a per-type
    count of upserted edges. No Telegram/MTProto contact.

    When ``embedder`` is provided (parallel embedding track), the semantic
    similarity families (TEXT_SIM / TRANSLATION) are derived too; otherwise the
    default torch-free pipeline runs unchanged.
    """
    from src.shared.db import db_connection

    async with db_connection() as conn:
        messages, known = await _fetch_inputs(conn)
        edges = derive_all_edges(messages, known, window_seconds)
        if embedder is not None:
            edges = edges + derive_text_sim_edges(
                messages, embedder, window_seconds=window_seconds
            )
        await _ensure_channels(conn, edges)
        await _upsert_edges(conn, edges)

    return dict(Counter(e.edge_type for e in edges))


async def _ensure_channels(conn, edges: list[Edge]) -> None:
    """Garantit que tout canal référencé par une arête existe dans ``channels``.

    FK : ``edges.src/dst_channel_id -> channels.channel_id``. Certaines origines
    de forward ne sont connues que par leur id numérique (le ``forward_from_chat``
    n'a pas été upserté à l'ingestion) : on crée une ligne MINIMALE (tier 'cold'
    par défaut) pour éviter une violation de clé étrangère. Idempotent.
    """
    ids: set[int] = set()
    for e in edges:
        if e.src_channel_id is not None:
            ids.add(e.src_channel_id)
        if e.dst_channel_id is not None:
            ids.add(e.dst_channel_id)
    if not ids:
        return
    await conn.executemany(
        "INSERT INTO channels (channel_id) VALUES ($1) ON CONFLICT (channel_id) DO NOTHING",
        [(i,) for i in ids],
    )


async def _upsert_edges(conn, edges: list[Edge]) -> None:
    """UPSERT a batch of edges via the idempotent ON CONFLICT statement."""
    import json

    if not edges:
        return
    records = [
        (
            e.src_channel_id,
            e.dst_channel_id,
            e.dst_domain,
            e.edge_type,
            e.count,
            e.weight,
            e.delay_seconds,
            e.text_sim,
            e.window_delta_seconds,
            e.window_start,
            e.window_end,
            json.dumps(e.attrs) if e.attrs is not None else None,
        )
        for e in edges
    ]
    await conn.executemany(_UPSERT_SQL, records)
