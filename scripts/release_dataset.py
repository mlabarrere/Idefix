#!/usr/bin/env python
"""Build (or verify) the public dataset release from a PostgreSQL snapshot.

What a release is
-----------------
Two files, pinned by SHA-256 in ``dataset/manifest.json``:

* ``idefix-corpus-v<V>.dump`` -- the COMPLETE source snapshot, restored
  losslessly, migrated additively to the alembic head, and re-dumped portably
  (``pg_dump -Fc --no-owner --no-privileges``). No row is deleted, no table
  emptied, no column nulled: that includes ``comments`` (commenter ids,
  usernames and text of private individuals -- see ``dataset/DATASHEET.md``)
  and every derived table of the run that produced the snapshot.
* ``idefix-annotations-v<V>.tar.gz`` -- every file under ``data/annotations/``
  and ``data/claims/``, byte-for-byte, in a deterministic archive (sorted
  members, fixed mtime, uid/gid 0, members relative to ``data/``).

Lossless is proved, not asserted: for every table the row count and a content
MD5 (``md5(string_agg(md5(ROW(<cols>)::text), '' ORDER BY <pk>))``) are taken on
the source restore BEFORE the upgrade and must be identical afterwards, on the
source columns. Columns added by the upgrade must be NULL on every row and
tables it creates must be empty. The produced dump is then restored into a
second database and must reproduce the same fingerprints.

Everything runs in a throw-away ``postgres:17-alpine`` container bound to
127.0.0.1. ``DATABASE_URL`` is built here and injected into alembic explicitly;
the script never connects anywhere else. The source file is mounted read-only.

A read-only secret scan (``src.ingestor.session.secret_values()``, i.e. the
collector's Telegram session/phone/api_hash and the LLM key) runs over every
table and every archived file. It prints COUNTS only, never values, never
modifies data, and refuses to write the manifest when it finds anything
(``--allow-secret-hits`` overrides, for an informed maintainer decision).

Usage:
    uv run python scripts/release_dataset.py \\
        --source backups/idefix-supabase-post-cutover-20260618-132009.dump \\
        --version 1.0.0 --out dataset/downloads [--keep-db]

    # re-check built or downloaded artefacts against dataset/manifest.json
    uv run python scripts/release_dataset.py --verify-only [--out dataset/downloads]
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET_NAME = "idefix-telegram-public-corpus"
SCHEMA_VERSION = 1
RELEASE_BASE_URL = "https://github.com/mlabarrere/Idefix/releases/download"

POSTGRES_IMAGE = "postgres:17-alpine"
POSTGRES_MAJOR = 17
ALEMBIC_HEAD = "0008"
DB_USER = "idefix"
DB_PASSWORD = "idefix"
DB_NAME = "idefix"
VERIFY_DB = "idefix_verify"

DEFAULT_SOURCE = ROOT / "backups" / "idefix-supabase-post-cutover-20260618-132009.dump"
DEFAULT_OUT = ROOT / "dataset" / "downloads"
DEFAULT_MANIFEST = ROOT / "dataset" / "manifest.json"
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_CONTAINER = "idefix-release"
DEFAULT_PORT = 55434

# Sub-directories of data/ shipped in the annotations archive, verbatim.
ARCHIVE_SUBDIRS = ("annotations", "claims")
ARCHIVE_EXTRACT_TO = "data"

# Migration bookkeeping: its single row records the upgrade itself, so it is the
# one table whose content is expected to change (0006 -> 0008).
BOOKKEEPING_TABLES = frozenset({"alembic_version"})

# pg_restore errors that do not affect the restored content. The source snapshot
# was taken on a hosted instance whose dump re-creates schema "public".
BENIGN_RESTORE_ERRORS = ('schema "public" already exists',)

# Session settings that make ``ROW(...)::text`` byte-stable (timestamptz output
# depends on TimeZone, float output on extra_float_digits, ...).
CHECKSUM_SETTINGS = {
    "TimeZone": "UTC",
    "DateStyle": "ISO, MDY",
    "IntervalStyle": "postgres",
    "extra_float_digits": "1",
    "bytea_output": "hex",
}
CHECKSUM_METHOD = (
    "per table: md5(coalesce(string_agg(md5(ROW(<all columns in ordinal order>)::text), "
    "'' ORDER BY <primary key>), '')), PostgreSQL 17, session settings "
    + ", ".join(f"{k}={v}" for k, v in CHECKSUM_SETTINGS.items())
)

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_SNAPSHOT_TS_RE = re.compile(r"(\d{8})-(\d{6})$")


class ReleaseError(RuntimeError):
    """A release invariant does not hold; nothing must be published."""


# --------------------------------------------------------------------------- names


def validate_version(version: str) -> str:
    if not _VERSION_RE.fullmatch(version):
        raise ReleaseError(f"version must be MAJOR.MINOR.PATCH, got {version!r}")
    return version


def release_tag(version: str) -> str:
    return f"dataset-v{version}"


def dump_name(version: str) -> str:
    return f"idefix-corpus-v{version}.dump"


def archive_name(version: str) -> str:
    return f"idefix-annotations-v{version}.tar.gz"


def asset_url(version: str, name: str, base_url: str = RELEASE_BASE_URL) -> str:
    return f"{base_url.rstrip('/')}/{release_tag(version)}/{name}"


def snapshot_epoch(snapshot: str) -> int:
    """Epoch of a ``...-YYYYMMDD-HHMMSS`` snapshot name (UTC), 0 when absent.

    Used as the fixed mtime of every archive member: deterministic for a given
    source, and a meaningful date once extracted.
    """
    m = _SNAPSHOT_TS_RE.search(snapshot)
    if not m:
        return 0
    dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- hashing / tar


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def collect_archive_members(
    data_dir: Path, subdirs: Sequence[str] = ARCHIVE_SUBDIRS
) -> list[tuple[str, Path]]:
    """Every regular file under ``data_dir/<subdir>``, as ``(arcname, path)``.

    ``arcname`` is POSIX and relative to ``data_dir``. Nothing is filtered out;
    anything that is not a regular file (symlink, device) is refused instead of
    silently skipped.
    """
    members: list[tuple[str, Path]] = []
    for sub in subdirs:
        base = data_dir / sub
        if not base.is_dir():
            raise ReleaseError(f"archive source missing: {base}")
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ReleaseError(f"refusing to archive a symlink: {path}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ReleaseError(f"refusing to archive a non-regular file: {path}")
            members.append((path.relative_to(data_dir).as_posix(), path))
    members.sort(key=lambda m: m[0])
    if not members:
        raise ReleaseError(f"no file to archive under {data_dir} / {list(subdirs)}")
    return members


def build_deterministic_tar_gz(members: Iterable[tuple[str, Path]], out: Path, mtime: int) -> None:
    """Write a byte-reproducible ``.tar.gz``.

    Same inputs -> same bytes: members sorted by name, fixed mtime, mode 0644,
    uid/gid 0 with empty owner names, and a gzip header without file name or
    timestamp. Only file contents are read from disk, never their metadata.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for arcname, path in sorted(members, key=lambda m: m[0]):
            if arcname.startswith("/") or ".." in arcname.split("/"):
                raise ReleaseError(f"unsafe archive member name: {arcname!r}")
            data = path.read_bytes()
            info = tarfile.TarInfo(arcname)
            info.size = len(data)
            info.mtime = mtime
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0, compresslevel=9) as gz:
            gz.write(buf.getvalue())


# ------------------------------------------------------------------ fingerprinting


@dataclass(frozen=True)
class TableLayout:
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]


@dataclass(frozen=True)
class Fingerprint:
    rows: int
    md5: str


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def fingerprint_sql(table: str, layout: TableLayout) -> str:
    """Row count + order-independent-of-storage content MD5 of one table.

    Rows are ordered by the primary key (by the row text when there is none),
    each row is hashed, and the concatenation of row hashes is hashed again: one
    pass, no table-sized string in memory.
    """
    if not layout.columns:
        raise ReleaseError(f"table {table} has no column")
    row = "ROW(" + ", ".join(f"t.{quote_ident(c)}" for c in layout.columns) + ")::text"
    order = (
        ", ".join(f"t.{quote_ident(c)}" for c in layout.primary_key)
        if layout.primary_key
        else row
    )
    return (
        f"SELECT count(*) AS rows, "
        f"md5(coalesce(string_agg(md5({row}), '' ORDER BY {order}), '')) AS md5 "
        f"FROM public.{quote_ident(table)} AS t"
    )


def compare_fingerprints(
    expected: dict[str, Fingerprint],
    actual: dict[str, Fingerprint],
    *,
    ignore: Iterable[str] = (),
) -> list[str]:
    """Human-readable differences (missing tables, counts, checksums)."""
    skip = set(ignore)
    problems: list[str] = []
    for table in sorted(set(expected) - skip):
        got = actual.get(table)
        want = expected[table]
        if got is None:
            problems.append(f"{table}: missing")
        elif got.rows != want.rows:
            problems.append(f"{table}: {got.rows} rows, expected {want.rows}")
        elif got.md5 != want.md5:
            problems.append(f"{table}: content md5 differs ({got.rows} rows)")
    return problems


def restrict_layouts(
    current: dict[str, TableLayout], reference: dict[str, TableLayout]
) -> dict[str, TableLayout]:
    """The tables of ``reference`` with only their ``reference`` columns.

    Used to fingerprint the upgraded database on the SOURCE columns, so a
    column added by a migration does not hide a change to existing data.
    """
    out: dict[str, TableLayout] = {}
    for table, ref in reference.items():
        if table not in current:
            raise ReleaseError(f"table {table} disappeared during the upgrade")
        missing = [c for c in ref.columns if c not in current[table].columns]
        if missing:
            raise ReleaseError(f"{table}: column(s) {missing} disappeared during the upgrade")
        out[table] = ref
    return out


def schema_additions(
    before: dict[str, TableLayout], after: dict[str, TableLayout]
) -> tuple[list[str], dict[str, list[str]]]:
    """Tables and columns created between two layouts."""
    new_tables = sorted(set(after) - set(before))
    new_columns = {
        t: [c for c in after[t].columns if c not in before[t].columns]
        for t in sorted(set(before) & set(after))
    }
    return new_tables, {t: cols for t, cols in new_columns.items() if cols}


# ------------------------------------------------------------------ restore output


def unexpected_restore_errors(stderr: str) -> list[str]:
    """``pg_restore`` error lines that are NOT in ``BENIGN_RESTORE_ERRORS``."""
    return [
        line
        for line in stderr.splitlines()
        if line.startswith("pg_restore: error:")
        and not any(b in line for b in BENIGN_RESTORE_ERRORS)
    ]


# -------------------------------------------------------------- secrets (counts only)


def count_secret_hits(text: str, secrets: Iterable[str]) -> int:
    """Occurrences of any secret in ``text``. Never returns or prints a value."""
    return sum(text.count(s) for s in secrets if s)


# ------------------------------------------------------------------------ manifest


@dataclass(frozen=True)
class ReleaseFacts:
    """Everything the manifest states, measured during the build."""

    version: str
    source_snapshot: str
    source_revision: str
    head_revision: str
    window_start: datetime
    window_end: datetime
    row_counts: dict[str, int]
    content_md5: dict[str, str]
    new_tables: list[str]
    new_columns: dict[str, list[str]]
    rls_tables: int
    public_functions: list[str]
    secrets_checked: int
    secret_hits: int
    archive_files: int


def sanitization_statements(f: ReleaseFacts) -> list[str]:
    """The truthful list of what was (and was not) done to the source."""
    compared = sorted(set(f.row_counts) - set(f.new_tables))
    out = [
        "none -- complete snapshot: no row deleted, no table emptied, no column nulled, "
        "including comments (commenter ids, usernames and text) and every derived table",
        f"lossless restore verified: row count and content md5 of each of the "
        f"{len(compared)} source tables equal the source restore before the upgrade "
        f"(on the source columns; {', '.join(sorted(BOOKKEEPING_TABLES))} excepted, "
        f"it records the upgrade)",
    ]
    additions: list[str] = []
    if f.new_tables:
        additions.append("new empty table(s) " + ", ".join(f.new_tables))
    if f.new_columns:
        cols = ", ".join(f"{t}.{c}" for t, cs in f.new_columns.items() for c in cs)
        additions.append(f"new column(s) {cols}, NULL on every existing row")
    out.append(
        f"only additive migrations applied: alembic {f.source_revision} -> {f.head_revision}"
        + (" (" + "; ".join(additions) + ")" if additions else "")
    )
    out.append(
        "owners and privileges stripped (pg_dump -Fc --no-owner --no-privileges); "
        "restore with pg_restore --no-owner --no-privileges"
    )
    if f.rls_tables or f.public_functions:
        residue = []
        if f.rls_tables:
            residue.append(f"row-level-security flag on {f.rls_tables} table(s), no policy")
        if f.public_functions:
            residue.append("function(s) " + ", ".join(f"public.{p}()" for p in f.public_functions))
        out.append("source hosting residue kept unchanged: " + "; ".join(residue))
    if f.secrets_checked:
        out.append(
            f"read-only secret scan: {f.secrets_checked} collector secret value(s) from "
            f"src.ingestor.session.secret_values() searched in every table and archived "
            f"file -- {f.secret_hits} occurrence(s); data not modified"
        )
    else:
        out.append(
            "secret scan not performed: no collector secret value resolved in the "
            "release environment"
        )
    out.append(
        f"annotations archive: all {f.archive_files} files under data/annotations/ and "
        f"data/claims/ included byte-for-byte; nothing excluded or stripped"
    )
    return out


def file_entry(path: Path, version: str, role: str, fmt: str, base_url: str) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": path.name, "role": role, "format": fmt}
    if role == "archive":
        entry["extract_to"] = ARCHIVE_EXTRACT_TO
    entry["bytes"] = path.stat().st_size
    entry["sha256"] = sha256_file(path)
    entry["url"] = asset_url(version, path.name, base_url)
    return entry


def build_manifest(
    facts: ReleaseFacts,
    files: list[dict[str, Any]],
    *,
    created_at: datetime,
) -> dict[str, Any]:
    """``dataset/manifest.json`` per contract C2, plus the per-table content md5."""
    return {
        "schema_version": SCHEMA_VERSION,
        "name": DATASET_NAME,
        "version": facts.version,
        "release_tag": release_tag(facts.version),
        "created_at": iso_utc(created_at),
        "source_snapshot": facts.source_snapshot,
        "collection_window": {
            "start": iso_utc(facts.window_start),
            "end": iso_utc(facts.window_end),
        },
        "postgres_major": POSTGRES_MAJOR,
        "alembic_revision": facts.head_revision,
        "license": "see DATASHEET.md",
        "files": files,
        "row_counts": dict(sorted(facts.row_counts.items())),
        "content_md5": {
            "method": CHECKSUM_METHOD,
            "tables": dict(sorted(facts.content_md5.items())),
        },
        "sanitization": sanitization_statements(facts),
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# -------------------------------------------------------------------------- docker


def _run(cmd: list[str], *, check: bool = True, **kw: Any) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, text=True, capture_output=True, **kw)
    if check and res.returncode != 0:
        raise ReleaseError(
            f"command failed ({res.returncode}): {' '.join(cmd[:4])} ...\n{res.stderr.strip()}"
        )
    return res


def container_exists(name: str) -> bool:
    res = _run(["docker", "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"])
    return name in res.stdout.split()


def start_container(name: str, port: int, mount: tuple[Path, str] | None = None) -> None:
    cmd = [
        "docker", "run", "-d", "--name", name,
        "-e", f"POSTGRES_USER={DB_USER}",
        "-e", f"POSTGRES_PASSWORD={DB_PASSWORD}",
        "-e", f"POSTGRES_DB={DB_NAME}",
        "-p", f"127.0.0.1:{port}:5432",
    ]
    if mount is not None:
        cmd += ["-v", f"{mount[0]}:{mount[1]}:ro"]
    _run(cmd + [POSTGRES_IMAGE])


def wait_ready(name: str, timeout: float = 120.0) -> None:
    # TCP probe: the image's init-time server listens on the unix socket only,
    # so a socket probe can report "ready" before the real server is up.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = _run(
            ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", DB_USER, "-d", DB_NAME],
            check=False,
        )
        if res.returncode == 0:
            return
        time.sleep(1.0)
    raise ReleaseError(f"postgres in {name} not ready after {timeout:.0f}s")


def remove_container(name: str) -> None:
    _run(["docker", "rm", "-f", name], check=False)


def pg_restore(name: str, db: str, path_in_container: str, *, strict: bool) -> list[str]:
    """Restore a custom-format dump; return the benign errors it reported."""
    res = _run(
        [
            "docker", "exec", name, "pg_restore", "--no-owner", "--no-privileges",
            "-U", DB_USER, "-d", db, path_in_container,
        ],
        check=False,
    )
    errors = [ln for ln in res.stderr.splitlines() if ln.startswith("pg_restore: error:")]
    unexpected = unexpected_restore_errors(res.stderr)
    if unexpected or (res.returncode != 0 and not errors):
        detail = res.stderr.strip() or f"exit {res.returncode}"
        raise ReleaseError("pg_restore failed:\n" + detail)
    if strict and errors:
        raise ReleaseError("pg_restore of the release dump is not clean:\n" + "\n".join(errors))
    return errors


# ------------------------------------------------------------------------ database


def dsn(port: int, db: str = DB_NAME) -> str:
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{port}/{db}"


async def _connect(port: int, db: str = DB_NAME) -> Any:
    import asyncpg

    last: Exception | None = None
    for _ in range(30):
        try:
            return await asyncpg.connect(dsn(port, db), server_settings=CHECKSUM_SETTINGS)
        except (OSError, asyncpg.PostgresError) as e:  # server still starting
            last = e
            await asyncio.sleep(1.0)
    raise ReleaseError(f"cannot connect to 127.0.0.1:{port}/{db}: {last}")


async def table_layouts(conn: Any) -> dict[str, TableLayout]:
    rows = await conn.fetch(
        """
        SELECT c.relname AS table,
               array(SELECT a.attname FROM pg_attribute a
                     WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                     ORDER BY a.attnum) AS columns,
               array(SELECT a.attname
                     FROM pg_index i
                     JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, ord) ON true
                     JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
                     WHERE i.indrelid = c.oid AND i.indisprimary
                     ORDER BY k.ord) AS pk
        FROM pg_class c
        WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p')
        ORDER BY c.relname
        """
    )
    return {r["table"]: TableLayout(tuple(r["columns"]), tuple(r["pk"])) for r in rows}


async def fingerprints(conn: Any, layouts: dict[str, TableLayout]) -> dict[str, Fingerprint]:
    out: dict[str, Fingerprint] = {}
    for table, layout in sorted(layouts.items()):
        row = await conn.fetchrow(fingerprint_sql(table, layout))
        out[table] = Fingerprint(int(row["rows"]), str(row["md5"]))
    return out


async def alembic_revision(conn: Any) -> str:
    rows = await conn.fetch("SELECT version_num FROM alembic_version")
    if len(rows) != 1:
        raise ReleaseError(f"alembic_version holds {len(rows)} rows, expected 1")
    return str(rows[0]["version_num"])


async def non_null_count(conn: Any, table: str, column: str) -> int:
    return int(
        await conn.fetchval(
            f"SELECT count(*) FROM public.{quote_ident(table)} "
            f"WHERE {quote_ident(column)} IS NOT NULL"
        )
    )


async def secret_hits_by_table(
    conn: Any, tables: Iterable[str], secrets: list[str]
) -> dict[str, int]:
    """Rows containing any secret, per table. Secrets travel as bind parameters."""
    out: dict[str, int] = {}
    for table in sorted(tables):
        out[table] = int(
            await conn.fetchval(
                f"SELECT count(*) FROM public.{quote_ident(table)} AS r "
                f"WHERE EXISTS (SELECT 1 FROM unnest($1::text[]) AS s(v) "
                f"WHERE strpos(r::text, s.v) > 0)",
                secrets,
            )
        )
    return out


async def hosting_residue(conn: Any) -> tuple[int, list[str]]:
    rls = await conn.fetchval(
        "SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace "
        "AND relkind = 'r' AND relrowsecurity"
    )
    funcs = await conn.fetch(
        "SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace ORDER BY 1"
    )
    return int(rls), [str(r["proname"]) for r in funcs]


# --------------------------------------------------------------------------- steps


def _log(msg: str) -> None:
    print(msg, flush=True)


def _resolve_secrets(use_dotenv: bool) -> list[str]:
    if use_dotenv:
        from dotenv import load_dotenv

        load_dotenv()  # same as every pipeline script; never overrides the env
    from src.ingestor.session import secret_values

    return sorted(secret_values())


def _alembic_upgrade(port: int) -> None:
    # Explicit DATABASE_URL: alembic/env.py calls load_dotenv() without override,
    # so this local URL always wins over anything in .env.
    url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{port}/{DB_NAME}"
    env = {**os.environ, "DATABASE_URL": url}
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    if res.returncode != 0:
        raise ReleaseError(f"alembic upgrade head failed:\n{res.stderr.strip()}")


async def _inspect_source(port: int) -> tuple[dict[str, TableLayout], dict[str, Fingerprint], str]:
    conn = await _connect(port)
    try:
        layouts = await table_layouts(conn)
        return layouts, await fingerprints(conn, layouts), await alembic_revision(conn)
    finally:
        await conn.close()


@dataclass
class _HeadState:
    layouts: dict[str, TableLayout]
    fingerprints: dict[str, Fingerprint]
    revision: str
    window: tuple[datetime, datetime]
    rls_tables: int
    functions: list[str]
    secret_hits: dict[str, int]


async def _inspect_head(
    port: int,
    src_layouts: dict[str, TableLayout],
    src_fp: dict[str, Fingerprint],
    secrets: list[str],
) -> _HeadState:
    conn = await _connect(port)
    try:
        layouts = await table_layouts(conn)
        revision = await alembic_revision(conn)
        if revision != ALEMBIC_HEAD:
            raise ReleaseError(f"alembic revision is {revision}, expected {ALEMBIC_HEAD}")

        # 1. existing data untouched, on the source columns
        on_source_cols = await fingerprints(conn, restrict_layouts(layouts, src_layouts))
        problems = compare_fingerprints(src_fp, on_source_cols, ignore=BOOKKEEPING_TABLES)
        if problems:
            raise ReleaseError("upgrade is not lossless:\n  " + "\n  ".join(problems))

        # 2. additions are empty
        new_tables, new_columns = schema_additions(src_layouts, layouts)
        head_fp = await fingerprints(conn, layouts)
        for t in new_tables:
            if head_fp[t].rows:
                raise ReleaseError(f"new table {t} is not empty ({head_fp[t].rows} rows)")
        for t, cols in new_columns.items():
            for c in cols:
                n = await non_null_count(conn, t, c)
                if n:
                    raise ReleaseError(f"new column {t}.{c} is set on {n} rows")

        start, end = await conn.fetchrow("SELECT min(timestamp), max(timestamp) FROM messages")
        if start is None:
            raise ReleaseError("messages is empty: no collection window")
        rls, funcs = await hosting_residue(conn)
        hits = await secret_hits_by_table(conn, layouts, secrets) if secrets else {}
        return _HeadState(layouts, head_fp, revision, (start, end), rls, funcs, hits)
    finally:
        await conn.close()


async def _verify_restored(
    port: int, db: str, expected: dict[str, Fingerprint], revision: str
) -> None:
    conn = await _connect(port, db)
    try:
        got_rev = await alembic_revision(conn)
        if got_rev != revision:
            raise ReleaseError(f"restored alembic revision {got_rev}, expected {revision}")
        layouts = await table_layouts(conn)
        problems = compare_fingerprints(expected, await fingerprints(conn, layouts))
        extra = sorted(set(layouts) - set(expected))
        if extra:
            problems.append(f"unexpected table(s) {extra}")
        if problems:
            raise ReleaseError("restored dump differs:\n  " + "\n  ".join(problems))
    finally:
        await conn.close()


def build(args: argparse.Namespace) -> int:
    version = validate_version(args.version)
    source: Path = args.source.resolve()
    if not source.is_file():
        raise ReleaseError(f"source snapshot not found: {source}")
    out: Path = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    snapshot = source.stem
    secrets = _resolve_secrets(not args.no_dotenv)
    _log(f"secret scan: {len(secrets)} secret value(s) resolved (values never printed)")

    # The annotations archive does not need the database: build and scan it first.
    members = collect_archive_members(args.data_dir.resolve())
    archive_path = out / archive_name(version)
    build_deterministic_tar_gz(members, archive_path, snapshot_epoch(snapshot))
    file_hits = sum(
        count_secret_hits(p.read_bytes().decode("utf-8", errors="replace"), secrets)
        for _, p in members
    )
    _log(f"archive: {archive_path.name}, {len(members)} files, secret hits {file_hits}")

    if container_exists(args.container):
        raise ReleaseError(
            f"container {args.container} already exists; remove it first "
            f"(docker rm -f {args.container}) -- it is this script's scratch container"
        )
    t0 = time.monotonic()
    start_container(args.container, args.port, mount=(source.parent, "/src"))
    try:
        wait_ready(args.container)
        _log(f"[{time.monotonic() - t0:6.1f}s] container {args.container} ready on {args.port}")

        benign = pg_restore(args.container, DB_NAME, f"/src/{source.name}", strict=False)
        _log(f"[{time.monotonic() - t0:6.1f}s] source restored ({len(benign)} benign error(s))")

        src_layouts, src_fp, src_rev = asyncio.run(_inspect_source(args.port))
        _log(f"[{time.monotonic() - t0:6.1f}s] source fingerprinted: alembic {src_rev}, "
             f"{len(src_fp)} tables")
        for t, fp in src_fp.items():
            _log(f"    {t:<20} {fp.rows:>8} rows  md5 {fp.md5}")

        _alembic_upgrade(args.port)
        head = asyncio.run(_inspect_head(args.port, src_layouts, src_fp, secrets))
        _log(f"[{time.monotonic() - t0:6.1f}s] upgraded to {head.revision}; existing data "
             f"identical; additions empty")
        db_hits = sum(head.secret_hits.values())
        if secrets:
            _log("secret scan (rows with a hit): " + ", ".join(
                f"{t}={n}" for t, n in sorted(head.secret_hits.items())))
        total_hits = db_hits + file_hits
        if total_hits and not args.allow_secret_hits:
            raise ReleaseError(
                f"secret scan found {total_hits} occurrence(s) ({db_hits} row(s), {file_hits} "
                f"in archived files). Nothing modified, no manifest written. Report it; rerun "
                f"with --allow-secret-hits only after an explicit decision."
            )

        dump_path = out / dump_name(version)
        in_container = f"/tmp/{dump_path.name}"
        _run([
            "docker", "exec", args.container, "pg_dump", "-Fc", "--no-owner",
            "--no-privileges", "-U", DB_USER, "-d", DB_NAME, "-f", in_container,
        ])
        _run(["docker", "cp", f"{args.container}:{in_container}", str(dump_path)])
        _log(f"[{time.monotonic() - t0:6.1f}s] dumped {dump_path.name} "
             f"({dump_path.stat().st_size} bytes)")

        _run(["docker", "exec", args.container, "createdb", "-U", DB_USER, VERIFY_DB])
        pg_restore(args.container, VERIFY_DB, in_container, strict=True)
        asyncio.run(_verify_restored(args.port, VERIFY_DB, head.fingerprints, head.revision))
        _log(f"[{time.monotonic() - t0:6.1f}s] release dump restores cleanly and reproduces "
             f"every fingerprint")

        new_tables, new_columns = schema_additions(src_layouts, head.layouts)
        data_tables = {t: fp for t, fp in head.fingerprints.items() if t not in BOOKKEEPING_TABLES}
        facts = ReleaseFacts(
            version=version,
            source_snapshot=snapshot,
            source_revision=src_rev,
            head_revision=head.revision,
            window_start=head.window[0],
            window_end=head.window[1],
            row_counts={t: fp.rows for t, fp in data_tables.items()},
            content_md5={t: fp.md5 for t, fp in data_tables.items()},
            new_tables=new_tables,
            new_columns=new_columns,
            rls_tables=head.rls_tables,
            public_functions=head.functions,
            secrets_checked=len(secrets),
            secret_hits=total_hits,
            archive_files=len(members),
        )
        files = [
            file_entry(dump_path, version, "database", "pg_dump-custom", args.base_url),
            file_entry(archive_path, version, "archive", "tar.gz", args.base_url),
        ]
        manifest = build_manifest(facts, files, created_at=datetime.now(timezone.utc))
        write_manifest(manifest, args.manifest)
        _log(f"manifest written: {args.manifest}")
        for f in files:
            _log(f"    {f['name']}  {f['bytes']} bytes  sha256 {f['sha256']}")
    finally:
        if args.keep_db:
            _log(f"--keep-db: container {args.container} left running on 127.0.0.1:{args.port}")
        else:
            remove_container(args.container)
    return 0


def verify(args: argparse.Namespace) -> int:
    """Check artefacts in ``--out`` against the manifest, then restore the dump."""
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    out: Path = args.out.resolve()
    dump: Path | None = None
    for f in manifest["files"]:
        path = out / f["name"]
        if not path.is_file():
            raise ReleaseError(f"missing artefact: {path}")
        size, digest = path.stat().st_size, sha256_file(path)
        if size != f["bytes"] or digest != f["sha256"]:
            raise ReleaseError(f"{f['name']}: size/sha256 do not match the manifest")
        _log(f"ok   {f['name']}  {size} bytes  sha256 {digest}")
        if f["role"] == "database":
            dump = path
    if dump is None:
        raise ReleaseError("manifest lists no database file")

    expected = {
        t: Fingerprint(n, manifest["content_md5"]["tables"][t])
        for t, n in manifest["row_counts"].items()
    }
    if container_exists(args.container):
        raise ReleaseError(f"container {args.container} already exists; remove it first")
    start_container(args.container, args.port, mount=(dump.parent, "/dataset"))
    try:
        wait_ready(args.container)
        pg_restore(args.container, DB_NAME, f"/dataset/{dump.name}", strict=True)
        _log("ok   pg_restore --no-owner --no-privileges: no error")

        async def _check() -> None:
            conn = await _connect(args.port)
            try:
                rev = await alembic_revision(conn)
                if rev != manifest["alembic_revision"]:
                    raise ReleaseError(f"alembic {rev}, manifest {manifest['alembic_revision']}")
                _log(f"ok   alembic_version = {rev}")
                layouts = {
                    t: lay for t, lay in (await table_layouts(conn)).items()
                    if t not in BOOKKEEPING_TABLES
                }
                got = await fingerprints(conn, layouts)
                problems = compare_fingerprints(expected, got)
                extra = sorted(set(got) - set(expected))
                if extra:
                    problems.append(f"table(s) not in the manifest: {extra}")
                if problems:
                    raise ReleaseError("restored content differs:\n  " + "\n  ".join(problems))
                for t, fp in sorted(got.items()):
                    _log(f"ok   {t:<20} {fp.rows:>8} rows  md5 {fp.md5}")
            finally:
                await conn.close()

        asyncio.run(_check())
    finally:
        if args.keep_db:
            _log(f"--keep-db: container {args.container} left running on 127.0.0.1:{args.port}")
        else:
            remove_container(args.container)
    _log("verification passed")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build or verify the public dataset release.")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help="pg_dump custom-format snapshot (read-only)")
    ap.add_argument("--version", default="1.0.0", help="dataset version, MAJOR.MINOR.PATCH")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="artefact directory")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                    help="directory holding annotations/ and claims/")
    ap.add_argument("--base-url", default=RELEASE_BASE_URL, help="release download URL prefix")
    ap.add_argument("--container", default=DEFAULT_CONTAINER, help="scratch container name")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="host port (127.0.0.1)")
    ap.add_argument("--keep-db", action="store_true", help="leave the scratch container running")
    ap.add_argument("--no-dotenv", action="store_true",
                    help="do not load .env before resolving secrets for the scan")
    ap.add_argument("--allow-secret-hits", action="store_true",
                    help="write the manifest even if the secret scan finds occurrences")
    ap.add_argument("--verify-only", action="store_true",
                    help="verify artefacts in --out against --manifest in a fresh container")
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return verify(args) if args.verify_only else build(args)
    except ReleaseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
