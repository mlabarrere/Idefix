"""Tests of ``scripts/release_dataset.py`` -- the pure parts of the release build.

Pins the contract of the public dataset release (C2 manifest, deterministic
annotations archive, lossless fingerprints, truthful sanitisation list). No
Docker, no database, no network: subprocess calls are mocked.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_dataset.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_dataset", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["release_dataset"] = m  # dataclasses resolve their module by name
    spec.loader.exec_module(m)
    return m


rd = _load_module()

SNAPSHOT = "idefix-supabase-post-cutover-20260618-132009"


# ------------------------------------------------------------------------ helpers


def _data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "annotations" / "judgments").mkdir(parents=True)
    (data / "claims").mkdir()
    (data / "annotations" / "batch.jsonl").write_bytes(b'{"item_id": 1}\n')
    (data / "annotations" / "judgments" / "batch__claude.jsonl").write_bytes(b'{"v": "x"}\r\n')
    (data / "annotations" / ".gitkeep").write_bytes(b"")
    (data / "annotations" / "README.md").write_text("# annotations\n", encoding="utf-8")
    (data / "claims" / "claims_fr.jsonl").write_bytes('{"claim": "é"}\n'.encode())
    return data


def _facts(**over):
    base = dict(
        version="1.0.0",
        source_snapshot=SNAPSHOT,
        source_revision="0006",
        head_revision="0008",
        window_start=datetime(2018, 12, 14, 2, 45, 39, tzinfo=timezone.utc),
        window_end=datetime(2026, 6, 10, 15, 16, 34, tzinfo=timezone.utc),
        row_counts={"messages": 5, "channels": 2, "comments": 3, "channel_llm_scores": 0},
        content_md5={"messages": "a" * 32, "channels": "b" * 32, "comments": "c" * 32,
                     "channel_llm_scores": "d41d8cd98f00b204e9800998ecf8427e"},
        new_tables=["channel_llm_scores"],
        new_columns={"channel_scores": ["gate_families"]},
        rls_tables=9,
        public_functions=["rls_auto_enable"],
        secrets_checked=3,
        secret_hits=0,
        archive_files=8,
    )
    base.update(over)
    return rd.ReleaseFacts(**base)


# -------------------------------------------------------------------------- names


def test_release_names_and_urls():
    assert rd.release_tag("1.0.0") == "dataset-v1.0.0"
    assert rd.dump_name("1.0.0") == "idefix-corpus-v1.0.0.dump"
    assert rd.archive_name("1.0.0") == "idefix-annotations-v1.0.0.tar.gz"
    assert rd.asset_url("1.0.0", "idefix-corpus-v1.0.0.dump") == (
        "https://github.com/mlabarrere/Idefix/releases/download/"
        "dataset-v1.0.0/idefix-corpus-v1.0.0.dump"
    )
    assert rd.asset_url("1.0.0", "x", "https://mirror.example/") == (
        "https://mirror.example/dataset-v1.0.0/x"
    )


@pytest.mark.parametrize("bad", ["1.0", "v1.0.0", "1.0.0-rc1", ""])
def test_validate_version_rejects_non_semver(bad):
    with pytest.raises(rd.ReleaseError):
        rd.validate_version(bad)


def test_snapshot_epoch_parses_trailing_timestamp():
    want = int(datetime(2026, 6, 18, 13, 20, 9, tzinfo=timezone.utc).timestamp())
    assert rd.snapshot_epoch(SNAPSHOT) == want
    assert rd.snapshot_epoch("no-timestamp-here") == 0


def test_iso_utc_normalises_to_z():
    assert rd.iso_utc(datetime(2026, 6, 10, 15, 16, 34)) == "2026-06-10T15:16:34Z"
    paris = timezone(timedelta(hours=2))
    assert rd.iso_utc(datetime(2026, 6, 10, 17, 16, 34, tzinfo=paris)) == "2026-06-10T15:16:34Z"


# ------------------------------------------------------------------------ hashing


def test_sha256_file_matches_hashlib(tmp_path):
    p = tmp_path / "blob"
    payload = os.urandom(3 * 1024 + 7)
    p.write_bytes(payload)
    assert rd.sha256_file(p, chunk=1024) == hashlib.sha256(payload).hexdigest()
    empty = tmp_path / "empty"
    empty.write_bytes(b"")
    assert rd.sha256_file(empty) == hashlib.sha256(b"").hexdigest()


# --------------------------------------------------------------- annotations archive


def test_collect_archive_members_takes_every_file_sorted(tmp_path):
    data = _data_dir(tmp_path)
    names = [a for a, _ in rd.collect_archive_members(data)]
    assert names == [
        "annotations/.gitkeep",
        "annotations/README.md",
        "annotations/batch.jsonl",
        "annotations/judgments/batch__claude.jsonl",
        "claims/claims_fr.jsonl",
    ]  # nothing excluded, not even dotfiles; POSIX, relative to data/


def test_collect_archive_members_requires_both_sources(tmp_path):
    data = _data_dir(tmp_path)
    with pytest.raises(rd.ReleaseError):
        rd.collect_archive_members(data, ("annotations", "missing"))


def test_tar_gz_is_byte_reproducible_and_normalised(tmp_path):
    data = _data_dir(tmp_path)
    members = rd.collect_archive_members(data)
    a, b = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    rd.build_deterministic_tar_gz(members, a, mtime=1_781_788_809)
    # Disk metadata must not leak in: touch every file, reverse the input order.
    for _, p in members:
        os.utime(p, (1_000_000_000, 1_000_000_000))
    rd.build_deterministic_tar_gz(list(reversed(members)), b, mtime=1_781_788_809)
    assert a.read_bytes() == b.read_bytes()

    raw = a.read_bytes()
    assert raw[3] & 0x08 == 0  # gzip FNAME flag unset: no file name in header
    assert raw[4:8] == b"\x00\x00\x00\x00"  # gzip MTIME zero

    with tarfile.open(a, "r:gz") as tar:
        infos = tar.getmembers()
        assert [i.name for i in infos] == sorted(n for n, _ in members)
        for i in infos:
            assert i.isreg()
            assert (i.uid, i.gid, i.uname, i.gname) == (0, 0, "", "")
            assert i.mtime == 1_781_788_809
            assert i.mode == 0o644
            assert not i.name.startswith("/") and ".." not in i.name.split("/")
        # contents byte-for-byte, CRLF and UTF-8 untouched
        by_name = dict(members)
        for i in infos:
            assert tar.extractfile(i).read() == by_name[i.name].read_bytes()


def test_tar_gz_changes_when_content_changes(tmp_path):
    data = _data_dir(tmp_path)
    members = rd.collect_archive_members(data)
    a, b = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    rd.build_deterministic_tar_gz(members, a, mtime=0)
    (data / "claims" / "claims_fr.jsonl").write_bytes(b'{"claim": "changed"}\n')
    rd.build_deterministic_tar_gz(members, b, mtime=0)
    assert rd.sha256_file(a) != rd.sha256_file(b)


def test_tar_gz_refuses_unsafe_member_names(tmp_path):
    f = tmp_path / "f"
    f.write_bytes(b"x")
    for bad in ("../escape", "/abs/path", "annotations/../../x"):
        with pytest.raises(rd.ReleaseError):
            rd.build_deterministic_tar_gz([(bad, f)], tmp_path / "o.tar.gz", mtime=0)


# ------------------------------------------------------------------ fingerprinting


def test_fingerprint_sql_orders_by_primary_key_and_quotes():
    sql = rd.fingerprint_sql(
        "channel_scores",
        rd.TableLayout(("channel_id", "suspicion", "mission"), ("mission", "channel_id")),
    )
    assert 'ROW(t."channel_id", t."suspicion", t."mission")::text' in sql
    assert 'ORDER BY t."mission", t."channel_id"' in sql
    assert 'FROM public."channel_scores" AS t' in sql
    assert "count(*) AS rows" in sql and "md5(coalesce(string_agg(md5(" in sql


def test_fingerprint_sql_without_pk_orders_by_row_text_and_escapes():
    sql = rd.fingerprint_sql('we"ird', rd.TableLayout(("a",), ()))
    assert 'FROM public."we""ird" AS t' in sql
    assert 'ORDER BY ROW(t."a")::text' in sql
    with pytest.raises(rd.ReleaseError):
        rd.fingerprint_sql("empty", rd.TableLayout((), ()))


def test_compare_fingerprints_reports_every_kind_of_difference():
    fp = rd.Fingerprint
    expected = {"a": fp(1, "x"), "b": fp(2, "y"), "c": fp(3, "z"), "alembic_version": fp(1, "o")}
    actual = {"a": fp(1, "x"), "b": fp(5, "y"), "c": fp(3, "DIFF"), "alembic_version": fp(1, "n")}
    assert rd.compare_fingerprints(expected, actual, ignore={"alembic_version"}) == [
        "b: 5 rows, expected 2",
        "c: content md5 differs (3 rows)",
    ]
    assert rd.compare_fingerprints({"gone": fp(0, "e")}, {}) == ["gone: missing"]
    assert rd.compare_fingerprints(expected, dict(expected)) == []


def test_restrict_layouts_keeps_source_columns_and_detects_losses():
    src = {"t": rd.TableLayout(("id", "a"), ("id",))}
    head = {"t": rd.TableLayout(("id", "a", "added"), ("id",)), "new": rd.TableLayout(("x",), ())}
    assert rd.restrict_layouts(head, src) == src
    with pytest.raises(rd.ReleaseError):
        rd.restrict_layouts({"t": rd.TableLayout(("id",), ("id",))}, src)
    with pytest.raises(rd.ReleaseError):
        rd.restrict_layouts({}, src)


def test_schema_additions_lists_new_tables_and_columns():
    before = {"channel_scores": rd.TableLayout(("channel_id",), ()),
              "channels": rd.TableLayout(("channel_id",), ())}
    after = {**before,
             "channel_scores": rd.TableLayout(("channel_id", "gate_families"), ()),
             "channel_llm_scores": rd.TableLayout(("mission",), ())}
    assert rd.schema_additions(before, after) == (
        ["channel_llm_scores"],
        {"channel_scores": ["gate_families"]},
    )


# ------------------------------------------------------------------ restore output


_BENIGN = (
    'pg_restore: error: could not execute query: ERROR:  schema "public" already exists\n'
    "Command was: CREATE SCHEMA public;\n"
    "pg_restore: warning: errors ignored on restore: 1\n"
)


def test_unexpected_restore_errors_filters_the_known_benign_one():
    assert rd.unexpected_restore_errors(_BENIGN) == []
    bad = _BENIGN + (
        'pg_restore: error: could not execute query: ERROR:  role "anon" does not exist\n'
    )
    assert rd.unexpected_restore_errors(bad) == [bad.splitlines()[-1]]


def _fake_run(returncode: int, stderr: str):
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)

    return run, calls


def test_pg_restore_tolerates_benign_error_unless_strict(monkeypatch):
    run, calls = _fake_run(1, _BENIGN)
    monkeypatch.setattr(rd.subprocess, "run", run)
    assert len(rd.pg_restore("c", "idefix", "/src/x.dump", strict=False)) == 1
    cmd = calls[0][0]
    assert cmd[:4] == ["docker", "exec", "c", "pg_restore"]
    assert "--no-owner" in cmd and "--no-privileges" in cmd
    with pytest.raises(rd.ReleaseError):
        rd.pg_restore("c", "idefix", "/src/x.dump", strict=True)


def test_pg_restore_fails_on_unexpected_error_or_silent_failure(monkeypatch):
    run, _ = _fake_run(1, "pg_restore: error: could not open input file\n")
    monkeypatch.setattr(rd.subprocess, "run", run)
    with pytest.raises(rd.ReleaseError):
        rd.pg_restore("c", "idefix", "/src/x.dump", strict=False)
    run, _ = _fake_run(1, "")
    monkeypatch.setattr(rd.subprocess, "run", run)
    with pytest.raises(rd.ReleaseError):
        rd.pg_restore("c", "idefix", "/src/x.dump", strict=False)


def test_alembic_upgrade_injects_local_database_url(monkeypatch):
    run, calls = _fake_run(0, "")
    monkeypatch.setattr(rd.subprocess, "run", run)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://remote.example/prod")
    rd._alembic_upgrade(55434)
    cmd, kw = calls[0]
    assert cmd == [sys.executable, "-m", "alembic", "upgrade", "head"]
    assert kw["env"]["DATABASE_URL"] == "postgresql+asyncpg://idefix:idefix@127.0.0.1:55434/idefix"
    assert kw["cwd"] == rd.ROOT


def test_start_container_binds_loopback_and_mounts_read_only(monkeypatch, tmp_path):
    run, calls = _fake_run(0, "")
    monkeypatch.setattr(rd.subprocess, "run", run)
    rd.start_container("idefix-release", 55434, mount=(tmp_path, "/src"))
    cmd = calls[0][0]
    assert "127.0.0.1:55434:5432" in cmd
    assert f"{tmp_path}:/src:ro" in cmd
    assert cmd[-1] == "postgres:17-alpine"


# ------------------------------------------------------------------------ secrets


def test_count_secret_hits_counts_without_exposing_values():
    text = "token=abc123; again abc123; phone +33600000000"
    assert rd.count_secret_hits(text, {"abc123", "+33600000000"}) == 3
    assert rd.count_secret_hits(text, set()) == 0
    assert rd.count_secret_hits(text, {""}) == 0  # an empty secret never matches


# ----------------------------------------------------------- sanitisation statement


def test_sanitization_states_complete_snapshot_and_every_rule():
    s = rd.sanitization_statements(_facts())
    text = "\n".join(s)
    assert s[0].startswith("none -- complete snapshot")
    assert "comments (commenter ids, usernames and text)" in s[0]
    assert "3 source tables" in s[1]  # messages, channels, comments; new table excluded
    assert "alembic_version excepted" in s[1]
    assert "alembic 0006 -> 0008" in text
    assert "new empty table(s) channel_llm_scores" in text
    assert "channel_scores.gate_families, NULL on every existing row" in text
    assert "--no-owner --no-privileges" in text
    assert "row-level-security flag on 9 table(s)" in text
    assert "public.rls_auto_enable()" in text
    assert "3 collector secret value(s)" in text and "0 occurrence(s)" in text
    assert "all 8 files" in text and "nothing excluded or stripped" in text
    for forbidden in ("deleted", "emptied", "dropped", "redacted"):
        # only allowed as a negation in the first statement
        assert all(forbidden not in line for line in s[1:]), forbidden


def test_sanitization_without_secrets_or_residue_says_so():
    s = rd.sanitization_statements(
        _facts(secrets_checked=0, rls_tables=0, public_functions=[], new_columns={})
    )
    text = "\n".join(s)
    assert "secret scan not performed" in text
    assert "hosting residue" not in text
    assert "new column" not in text


# ------------------------------------------------------------------------ manifest


def test_file_entry_shapes_database_and_archive(tmp_path):
    dump = tmp_path / "idefix-corpus-v1.0.0.dump"
    dump.write_bytes(b"PGDMP")
    arc = tmp_path / "idefix-annotations-v1.0.0.tar.gz"
    arc.write_bytes(b"\x1f\x8b")
    d = rd.file_entry(dump, "1.0.0", "database", "pg_dump-custom", rd.RELEASE_BASE_URL)
    a = rd.file_entry(arc, "1.0.0", "archive", "tar.gz", rd.RELEASE_BASE_URL)
    assert list(d) == ["name", "role", "format", "bytes", "sha256", "url"]
    assert list(a) == ["name", "role", "format", "extract_to", "bytes", "sha256", "url"]
    assert a["extract_to"] == "data"
    assert d["bytes"] == 5 and d["sha256"] == hashlib.sha256(b"PGDMP").hexdigest()
    assert d["url"].endswith("/dataset-v1.0.0/idefix-corpus-v1.0.0.dump")


def test_build_manifest_follows_contract_c2(tmp_path):
    files = [{"name": "x"}]
    m = rd.build_manifest(
        _facts(), files, created_at=datetime(2026, 10, 25, 9, 0, 0, tzinfo=timezone.utc)
    )
    assert list(m) == [
        "schema_version", "name", "version", "release_tag", "created_at",
        "source_snapshot", "collection_window", "postgres_major", "alembic_revision",
        "license", "files", "row_counts", "content_md5", "sanitization",
    ]
    assert m["schema_version"] == 1
    assert m["name"] == "idefix-telegram-public-corpus"
    assert m["release_tag"] == "dataset-v1.0.0"
    assert m["created_at"] == "2026-10-25T09:00:00Z"
    assert m["source_snapshot"] == SNAPSHOT
    assert m["collection_window"] == {
        "start": "2018-12-14T02:45:39Z",
        "end": "2026-06-10T15:16:34Z",
    }
    assert m["postgres_major"] == 17
    assert m["alembic_revision"] == "0008"
    assert m["license"] == "see DATASHEET.md"
    assert m["files"] is files
    assert list(m["row_counts"]) == sorted(m["row_counts"])
    assert m["row_counts"]["comments"] == 3  # comments ship, counted
    assert set(m["content_md5"]["tables"]) == set(m["row_counts"])
    assert "ORDER BY <primary key>" in m["content_md5"]["method"]
    assert m["sanitization"] == rd.sanitization_statements(_facts())


def test_write_manifest_is_utf8_json_with_trailing_newline(tmp_path):
    p = tmp_path / "dataset" / "manifest.json"
    rd.write_manifest({"k": "é"}, p)
    raw = p.read_bytes()
    assert raw.endswith(b"\n") and "é".encode() in raw


def test_gzip_member_roundtrip_is_plain_tar(tmp_path):
    data = _data_dir(tmp_path)
    out = tmp_path / "o.tar.gz"
    rd.build_deterministic_tar_gz(rd.collect_archive_members(data), out, mtime=0)
    with gzip.open(out, "rb") as fh:
        inner = fh.read()
    with tarfile.open(fileobj=io.BytesIO(inner), mode="r:") as tar:
        assert len(tar.getmembers()) == 5
