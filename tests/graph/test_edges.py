"""Tests for the multiplex edge derivation (Chantier 2b).

Pure-function tests only — NO DB I/O. Messages are simulated as plain dicts
exposing the columns the derivers read (channel_id, message_id, timestamp, text,
forward_from_channel_id, forward_delay_seconds).

Covers: FORWARD aggregation + self-loop exclusion, MENTIONS resolution against
known channels, CITES_DOMAIN via handlers (platform exclusion, lowercase, never
''), CO_FORWARD / CO_URL windowed pairing, src<dst canonicalization, and the Δt
window boundary (load-bearing rules 1, 2, 4).
"""

from datetime import datetime, timedelta, timezone

from src.graph.edges import (
    DEFAULT_WINDOW_SECONDS,
    derive_cites_domain_edges,
    derive_co_forward_edges,
    derive_co_hashtag_edges,
    derive_co_url_edges,
    derive_co_url_exact_edges,
    derive_forward_edges,
    derive_media_reuse_edges,
    derive_mention_edges,
)

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _msg(
    channel_id, mid, *, text=None, fwd=None, delay=None, offset_s=0, media_hash=None
):
    """Build a simulated messages row."""
    return {
        "channel_id": channel_id,
        "message_id": mid,
        "timestamp": T0 + timedelta(seconds=offset_s),
        "text": text,
        "forward_from_channel_id": fwd,
        "forward_delay_seconds": delay,
        "media_hash": media_hash,
    }


# --------------------------------------------------------------------------- #
# FORWARD                                                                      #
# --------------------------------------------------------------------------- #
class TestForward:
    def test_aggregates_count_and_min_delay(self):
        msgs = [
            _msg(200, 1, fwd=100, delay=600),
            _msg(200, 2, fwd=100, delay=120),  # same A->B, smaller delay
            _msg(200, 3, fwd=100, delay=None),  # missing delay ignored for min
        ]
        edges = derive_forward_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "FORWARD"
        assert (e.src_channel_id, e.dst_channel_id) == (100, 200)  # origin -> relayer
        assert e.count == 3
        assert e.delay_seconds == 120
        assert e.dst_domain is None  # channel target only

    def test_excludes_self_loop(self):
        msgs = [_msg(100, 1, fwd=100, delay=5)]  # origin == relayer
        assert derive_forward_edges(msgs) == []

    def test_ignores_non_forwards(self):
        assert derive_forward_edges([_msg(200, 1, text="plain post")]) == []


# --------------------------------------------------------------------------- #
# MENTIONS                                                                     #
# --------------------------------------------------------------------------- #
class TestMentions:
    def test_resolves_known_username_case_insensitive(self):
        known = {"RFI_Fr": 300, "Dugin_Aleksandr": 400}
        msgs = [_msg(200, 1, text="Relayez @rfi_fr et @Dugin_Aleksandr")]
        edges = derive_mention_edges(msgs, known)
        targets = {e.dst_channel_id for e in edges}
        assert targets == {300, 400}
        assert all(e.edge_type == "MENTIONS" and e.src_channel_id == 200 for e in edges)

    def test_unresolved_mention_ignored(self):
        # @unknown_channel resolves to no known channel -> no edge to a ghost node
        msgs = [_msg(200, 1, text="voir @unknown_channel")]
        assert derive_mention_edges(msgs, {"RFI_Fr": 300}) == []

    def test_aggregates_occurrences(self):
        known = {"target_chan": 300}
        msgs = [
            _msg(200, 1, text="@target_chan"),
            _msg(200, 2, text="encore @Target_Chan"),
        ]
        edges = derive_mention_edges(msgs, known)
        assert len(edges) == 1
        assert edges[0].count == 2

    def test_self_mention_excluded(self):
        known = {"selfchan": 200}
        msgs = [_msg(200, 1, text="je suis @selfchan")]
        assert derive_mention_edges(msgs, known) == []


# --------------------------------------------------------------------------- #
# CITES_DOMAIN                                                                 #
# --------------------------------------------------------------------------- #
class TestCitesDomain:
    def test_extracts_lowercase_domain(self):
        msgs = [_msg(200, 1, text="preuve sur https://WWW.Pravda-FR.com/article")]
        edges = derive_cites_domain_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "CITES_DOMAIN"
        assert e.src_channel_id == 200
        assert e.dst_domain == "pravda-fr.com"  # lowercase, www stripped
        assert e.dst_channel_id is None  # domain target only

    def test_excludes_platform_hosts(self):
        msgs = [_msg(200, 1, text="https://t.me/x https://youtube.com/v https://bit.ly/z")]
        assert derive_cites_domain_edges(msgs) == []

    def test_never_empty_domain(self):
        # a bare/garbage 'url' that canonical_domain cannot resolve must not yield ''
        msgs = [_msg(200, 1, text="texte sans url")]
        edges = derive_cites_domain_edges(msgs)
        assert all(e.dst_domain for e in edges)  # vacuously true, but guards regressions

    def test_aggregates_citations(self):
        msgs = [
            _msg(200, 1, text="https://geopolitika.ru/a"),
            _msg(200, 2, text="https://geopolitika.ru/b"),
        ]
        edges = derive_cites_domain_edges(msgs)
        assert len(edges) == 1
        assert edges[0].count == 2


# --------------------------------------------------------------------------- #
# CO_FORWARD (windowed coordination)                                          #
# --------------------------------------------------------------------------- #
class TestCoForward:
    def test_pairs_channels_sharing_origin_in_window(self):
        # channels 200 and 300 both relay origin 100 within 1h
        msgs = [
            _msg(200, 1, fwd=100, offset_s=0),
            _msg(300, 2, fwd=100, offset_s=3600),
        ]
        edges = derive_co_forward_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "CO_FORWARD"
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)  # a < b canonical
        assert e.window_delta_seconds == 3600  # non-NULL, observed spread
        assert e.attrs == {"common_origins": 1}

    def test_canonical_order_regardless_of_input_order(self):
        # higher id posts first — pair must still be (200, 300)
        msgs = [
            _msg(300, 1, fwd=100, offset_s=0),
            _msg(200, 2, fwd=100, offset_s=60),
        ]
        e = derive_co_forward_edges(msgs)[0]
        assert e.src_channel_id < e.dst_channel_id == 300
        assert e.src_channel_id == 200

    def test_outside_window_no_edge(self):
        # 200 and 300 relay origin 100 but 4 days apart -> outside 72h default
        msgs = [
            _msg(200, 1, fwd=100, offset_s=0),
            _msg(300, 2, fwd=100, offset_s=4 * 86400),
        ]
        assert derive_co_forward_edges(msgs) == []

    def test_window_is_configurable(self):
        msgs = [
            _msg(200, 1, fwd=100, offset_s=0),
            _msg(300, 2, fwd=100, offset_s=4 * 86400),
        ]
        # widen the window to 5 days -> edge appears
        edges = derive_co_forward_edges(msgs, window_seconds=5 * 86400)
        assert len(edges) == 1
        assert edges[0].window_delta_seconds == 4 * 86400

    def test_single_channel_no_self_pair(self):
        # only one channel relays origin 100 -> no coordination pair
        msgs = [_msg(200, 1, fwd=100), _msg(200, 2, fwd=100)]
        assert derive_co_forward_edges(msgs) == []

    def test_common_origins_aggregate(self):
        # 200 and 300 share TWO origins (100, 101) within window
        msgs = [
            _msg(200, 1, fwd=100, offset_s=0),
            _msg(300, 2, fwd=100, offset_s=100),
            _msg(200, 3, fwd=101, offset_s=200),
            _msg(300, 4, fwd=101, offset_s=300),
        ]
        edges = derive_co_forward_edges(msgs)
        assert len(edges) == 1
        assert edges[0].attrs == {"common_origins": 2}
        assert edges[0].count == 2


# --------------------------------------------------------------------------- #
# CO_URL (windowed coordination)                                              #
# --------------------------------------------------------------------------- #
class TestCoUrl:
    def test_pairs_channels_sharing_domain_in_window(self):
        msgs = [
            _msg(200, 1, text="https://geopolitika.ru/a", offset_s=0),
            _msg(300, 2, text="https://geopolitika.ru/b", offset_s=1800),
        ]
        edges = derive_co_url_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "CO_URL"
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)
        assert e.window_delta_seconds == 1800  # non-NULL
        assert e.attrs == {"shared_domains": ["geopolitika.ru"]}

    def test_platform_domains_excluded(self):
        msgs = [
            _msg(200, 1, text="https://t.me/a", offset_s=0),
            _msg(300, 2, text="https://t.me/b", offset_s=60),
        ]
        assert derive_co_url_edges(msgs) == []

    def test_outside_window_no_edge(self):
        msgs = [
            _msg(200, 1, text="https://geopolitika.ru/a", offset_s=0),
            _msg(300, 2, text="https://geopolitika.ru/b", offset_s=10 * 86400),
        ]
        assert derive_co_url_edges(msgs) == []

    def test_default_window_constant(self):
        assert DEFAULT_WINDOW_SECONDS == 72 * 3600


# --------------------------------------------------------------------------- #
# CO_URL_EXACT (windowed coordination on the FULL url)                         #
# --------------------------------------------------------------------------- #
class TestCoUrlExact:
    def test_same_full_url_pairs_channels(self):
        # both channels post the IDENTICAL deep-link within the window
        msgs = [
            _msg(200, 1, text="https://pravda-fr.com/article-42", offset_s=0),
            _msg(300, 2, text="https://pravda-fr.com/article-42", offset_s=1800),
        ]
        edges = derive_co_url_exact_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "CO_URL_EXACT"
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)  # a < b canonical
        assert e.window_delta_seconds == 1800  # non-NULL Δt
        assert e.attrs == {"shared_urls": ["https://pravda-fr.com/article-42"]}

    def test_same_domain_different_url_no_exact_edge(self):
        # same host, DIFFERENT path -> CO_URL fires but CO_URL_EXACT must NOT.
        msgs = [
            _msg(200, 1, text="https://pravda-fr.com/a", offset_s=0),
            _msg(300, 2, text="https://pravda-fr.com/b", offset_s=60),
        ]
        assert derive_co_url_edges(msgs)  # domain-level edge exists
        assert derive_co_url_exact_edges(msgs) == []  # exact-url edge does not

    def test_platform_urls_excluded(self):
        msgs = [
            _msg(200, 1, text="https://t.me/x/42", offset_s=0),
            _msg(300, 2, text="https://t.me/x/42", offset_s=60),
        ]
        assert derive_co_url_exact_edges(msgs) == []

    def test_outside_window_no_edge(self):
        msgs = [
            _msg(200, 1, text="https://pravda-fr.com/a-42", offset_s=0),
            _msg(300, 2, text="https://pravda-fr.com/a-42", offset_s=10 * 86400),
        ]
        assert derive_co_url_exact_edges(msgs) == []

    def test_single_channel_no_self_pair(self):
        msgs = [
            _msg(200, 1, text="https://pravda-fr.com/a-42", offset_s=0),
            _msg(200, 2, text="https://pravda-fr.com/a-42", offset_s=60),
        ]
        assert derive_co_url_exact_edges(msgs) == []


# --------------------------------------------------------------------------- #
# CO_HASHTAG (windowed coordination on a shared #hashtag)                      #
# --------------------------------------------------------------------------- #
class TestCoHashtag:
    def test_same_hashtag_pairs_channels_in_window(self):
        msgs = [
            _msg(200, 1, text="vive #France2027", offset_s=0),
            _msg(300, 2, text="bravo #france2027", offset_s=3600),  # case-insensitive
        ]
        edges = derive_co_hashtag_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "CO_HASHTAG"
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)  # a < b canonical
        assert e.window_delta_seconds == 3600  # non-NULL Δt
        assert e.attrs == {"shared_hashtags": ["france2027"]}

    def test_cyrillic_hashtag_pairs_channels(self):
        msgs = [
            _msg(200, 1, text="#Новости du jour", offset_s=0),
            _msg(300, 2, text="encore #новости", offset_s=120),
        ]
        edges = derive_co_hashtag_edges(msgs)
        assert len(edges) == 1
        assert edges[0].attrs == {"shared_hashtags": ["новости"]}

    def test_canonical_order_regardless_of_input_order(self):
        msgs = [
            _msg(300, 1, text="#otan", offset_s=0),
            _msg(200, 2, text="#otan", offset_s=60),
        ]
        e = derive_co_hashtag_edges(msgs)[0]
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)

    def test_outside_window_no_edge(self):
        msgs = [
            _msg(200, 1, text="#france2027", offset_s=0),
            _msg(300, 2, text="#france2027", offset_s=4 * 86400),  # > 72h default
        ]
        assert derive_co_hashtag_edges(msgs) == []

    def test_self_loop_excluded(self):
        # one channel using the same hashtag twice is not coordination
        msgs = [
            _msg(200, 1, text="#france2027", offset_s=0),
            _msg(200, 2, text="#france2027", offset_s=60),
        ]
        assert derive_co_hashtag_edges(msgs) == []

    def test_shared_hashtags_aggregate(self):
        # 200 and 300 share TWO hashtags within window -> count == 2
        msgs = [
            _msg(200, 1, text="#otan #france2027", offset_s=0),
            _msg(300, 2, text="#OTAN #France2027", offset_s=100),
        ]
        edges = derive_co_hashtag_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.count == 2
        assert e.attrs == {"shared_hashtags": ["france2027", "otan"]}

    def test_no_hashtag_no_edge(self):
        msgs = [
            _msg(200, 1, text="aucun tag", offset_s=0),
            _msg(300, 2, text="rien non plus", offset_s=60),
        ]
        assert derive_co_hashtag_edges(msgs) == []


# --------------------------------------------------------------------------- #
# MEDIA_REUSE (windowed coordination on a shared media_hash)                   #
# --------------------------------------------------------------------------- #
class TestMediaReuse:
    def test_same_media_hash_pairs_channels_in_window(self):
        msgs = [
            _msg(200, 1, media_hash="ffaa00bb", offset_s=0),
            _msg(300, 2, media_hash="ffaa00bb", offset_s=1800),
        ]
        edges = derive_media_reuse_edges(msgs)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "MEDIA_REUSE"
        assert (e.src_channel_id, e.dst_channel_id) == (200, 300)  # a < b canonical
        assert e.window_delta_seconds == 1800  # non-NULL Δt
        assert e.attrs == {"shared_media": ["ffaa00bb"]}

    def test_null_media_hash_ignored(self):
        # media_hash is NULL across the corpus today -> nothing derived
        msgs = [
            _msg(200, 1, media_hash=None, offset_s=0),
            _msg(300, 2, media_hash=None, offset_s=60),
        ]
        assert derive_media_reuse_edges(msgs) == []

    def test_different_media_hash_no_edge(self):
        msgs = [
            _msg(200, 1, media_hash="aaaa", offset_s=0),
            _msg(300, 2, media_hash="bbbb", offset_s=60),
        ]
        assert derive_media_reuse_edges(msgs) == []

    def test_outside_window_no_edge(self):
        msgs = [
            _msg(200, 1, media_hash="ffaa00bb", offset_s=0),
            _msg(300, 2, media_hash="ffaa00bb", offset_s=10 * 86400),
        ]
        assert derive_media_reuse_edges(msgs) == []

    def test_self_loop_excluded(self):
        msgs = [
            _msg(200, 1, media_hash="ffaa00bb", offset_s=0),
            _msg(200, 2, media_hash="ffaa00bb", offset_s=60),
        ]
        assert derive_media_reuse_edges(msgs) == []
