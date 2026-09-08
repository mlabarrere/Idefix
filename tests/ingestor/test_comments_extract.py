"""Tests for commenter extraction (_extract_comment_row) — OFFLINE.

The function turns a linked-group message into a comments row, or None when there
is no identifiable individual author. Pure function, no DB, no Telegram.
"""
from datetime import datetime, timezone

from src.ingestor.handlers import _extract_comment_row

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _User:
    def __init__(self, uid, username=None):
        self.id = uid
        self.username = username


class _GroupMsg:
    def __init__(self, *, mid=10, date=T0, text=None, caption=None, from_user="unset"):
        self.id = mid
        self.date = date
        self.text = text
        self.caption = caption
        # default to an author so "no from_user" is an explicit None in the test
        self.from_user = _User(555, "commenter_a") if from_user == "unset" else from_user


class TestExtractCommentRow:
    def test_authored_message_yields_row(self):
        msg = _GroupMsg(mid=42, text="d'accord", from_user=_User(777, "alice_fr"))
        row = _extract_comment_row(msg, channel_id=100)
        assert row == {
            "channel_id": 100,        # the MONITORED channel, not the group id
            "message_id": 42,
            "commenter_id": 777,
            "commenter_username": "alice_fr",
            "text": "d'accord",
            "timestamp": T0,
        }

    def test_no_from_user_is_skipped(self):
        # Service message / anonymous admin: no individual to log.
        assert _extract_comment_row(_GroupMsg(from_user=None), channel_id=100) is None

    def test_from_user_without_id_is_skipped(self):
        bare = type("Anon", (), {"id": None, "username": None})()
        assert _extract_comment_row(_GroupMsg(from_user=bare), channel_id=100) is None

    def test_username_may_be_none(self):
        # Many Telegram accounts have no @username — still a valid commenter row.
        row = _extract_comment_row(_GroupMsg(from_user=_User(888, None)), channel_id=100)
        assert row["commenter_id"] == 888
        assert row["commenter_username"] is None

    def test_caption_used_when_no_text(self):
        row = _extract_comment_row(
            _GroupMsg(text=None, caption="légende image"), channel_id=100
        )
        assert row["text"] == "légende image"
