"""Tests for queries.insert_comment and upsert_channel(description) — OFFLINE.

asyncpg is mocked: a fake connection records the SQL + args of execute() and
returns a canned command tag. No real PostgreSQL.
"""
import pytest

from src.ingestor import queries


class _FakeConn:
    """Records execute() calls; returns a configurable command tag."""

    def __init__(self, exec_result="INSERT 0 1"):
        self.calls = []
        self._exec_result = exec_result

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        return self._exec_result


class TestInsertComment:
    @pytest.mark.asyncio
    async def test_inserts_and_reports_new_row(self):
        conn = _FakeConn("INSERT 0 1")
        row = {
            "channel_id": 100,
            "message_id": 42,
            "commenter_id": 777,
            "commenter_username": "alice_fr",
            "text": "d'accord",
            "timestamp": None,
        }
        ok = await queries.insert_comment(conn, row)
        assert ok is True
        sql, args = conn.calls[0]
        assert "INSERT INTO comments" in sql
        assert "ON CONFLICT" in sql and "DO NOTHING" in sql
        # args in column order: channel_id, message_id, commenter_id, username, text, ts
        assert args[0] == 100
        assert args[2] == 777
        assert args[3] == "alice_fr"

    @pytest.mark.asyncio
    async def test_conflict_reports_no_new_row(self):
        conn = _FakeConn("INSERT 0 0")  # ON CONFLICT DO NOTHING hit
        ok = await queries.insert_comment(conn, {"channel_id": 1, "message_id": 2})
        assert ok is False

    @pytest.mark.asyncio
    async def test_missing_fields_default_to_none(self):
        conn = _FakeConn()
        await queries.insert_comment(conn, {"channel_id": 1, "message_id": 2})
        _, args = conn.calls[0]
        # commenter_id / username / text / timestamp absent -> None
        assert args[2] is None and args[3] is None and args[4] is None and args[5] is None


class TestUpsertChannelDescription:
    @pytest.mark.asyncio
    async def test_description_passed_through(self):
        conn = _FakeConn()
        await queries.upsert_channel(
            conn, 100, {"username": "u", "title": "t", "description": "bio FR"}
        )
        sql, args = conn.calls[0]
        assert "description" in sql
        assert "bio FR" in args

    @pytest.mark.asyncio
    async def test_description_absent_is_none_not_crash(self):
        conn = _FakeConn()
        await queries.upsert_channel(conn, 100, {"username": "u"})
        sql, args = conn.calls[0]
        # COALESCE on update preserves an existing bio when this poll has none
        assert "COALESCE(EXCLUDED.description" in sql
        assert None in args

    @pytest.mark.asyncio
    async def test_extra_metadata_is_merged_not_replaced(self):
        conn = _FakeConn()
        await queries.upsert_channel(
            conn, 100, {"username": "u", "extra": {"campaign": "france_ukraine"}}
        )
        sql, args = conn.calls[0]
        assert "COALESCE(channels.extra" in sql
        assert "|| COALESCE(EXCLUDED.extra" in sql
        assert args[-1] == {"campaign": "france_ukraine"}


class TestInsertMessage:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("command_tag", "expected"),
        [("INSERT 0 1", True), ("INSERT 0 0", False)],
    )
    async def test_reports_actual_insert_not_attempt(self, command_tag, expected):
        conn = _FakeConn(command_tag)
        row = {
            "message_id": 1,
            "channel_id": 2,
            "timestamp": None,
        }
        assert await queries.insert_message(conn, row) is expected
