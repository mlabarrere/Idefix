#!/usr/bin/env python
"""One-command reproducible setup on the public corpus.

    uv run --extra embed python scripts/bootstrap.py [STEP] [options]

Steps (``all``, the default, runs them in this order):

    check     prerequisites: Python 3.14, Docker daemon + Compose v2, Node + npm,
              a free database port, the embedding extra, a valid manifest
    fetch     download every file listed in dataset/manifest.json into
              dataset/downloads/, verify size + SHA-256, extract the archives
    db        start the local PostgreSQL 17 (docker-compose.yml); when the
              database is EMPTY, restore the database artefact into it, then
              `alembic upgrade head`
    pipeline  scripts/pipeline.py --mission M against that database
    webapp    `npm ci` when node_modules is missing or stale, then `npm run dev`

Options:
    --dataset-dir PATH   copy the release files from a local folder instead of
                         downloading them (offline machines, pre-fetched copies)
    --manifest PATH      use another manifest (default: dataset/manifest.json)
    --mission M          mission(s) for the pipeline (default: all)
    --skip-embeddings    forwarded to the pipeline; drops the embedding extra need
    --no-webapp          `all` stops after the pipeline (CI, headless machines)

Environment:
    IDEFIX_DB_PORT            host port of the local database (default 5433)
    IDEFIX_DATASET_BASE_URL   mirror: fetch <base>/<file name> instead of the
                              URLs pinned in the manifest (hashes still apply)

No Telegram credentials and no .env are needed. The bootstrap never reads .env:
it injects the local DATABASE_URL into every child process itself, and passes a
null env file to Docker Compose so that only the process environment configures
the database port.

The bootstrap never deletes data. It does not remove containers or volumes,
never drops or truncates anything, and restores only into an empty database.
A database that already holds data is left untouched (no restore, no
migration), and `all` runs the pipeline automatically only on a database the
bootstrap itself restored, once; `pipeline` on its own always runs.

Re-running is therefore safe and fast: verified downloads are kept, the restore
is skipped, and a completed pipeline run is not repeated by `all`.

Standard library only, by design: this script runs before anything optional is
installed, so it must not depend on anything but the interpreter.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO, Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO / "dataset" / "manifest.json"
DOWNLOADS = REPO / "dataset" / "downloads"
COMPOSE_FILE = REPO / "docker-compose.yml"
PIPELINE = REPO / "scripts" / "pipeline.py"
WEBAPP = REPO / "webapp"

COMPOSE_PROJECT = "idefix"
DB_SERVICE = "db"
DB_USER = "idefix"
DB_PASSWORD = "idefix"
DB_NAME = "idefix"
DEFAULT_DB_PORT = 5433
# ./dataset/downloads is mounted read-only here (docker-compose.yml).
CONTAINER_DATASET_DIR = "/dataset"
HEALTH_TIMEOUT_S = 180

MIN_PYTHON = (3, 14)
# `up --wait-timeout` appeared in Compose 2.17.
MIN_COMPOSE = (2, 17)
# Vite 8 engines field: ^20.19.0 || >=22.12.0.
NODE_REQUIREMENT = "Node.js 20.19+ or 22.12+"

STEPS = ("check", "fetch", "db", "pipeline", "webapp", "all")
CHUNK = 1 << 20
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TABLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
DEFAULT_COUNTED_TABLES = ("channels", "messages", "comments")
# The marker lives in the database comment, so it disappears with the volume.
MARKER_TOOL = "idefix-bootstrap"
MARKER_QUOTE = "$idefix_marker$"
# pg_restore errors that are expected on a fresh PostgreSQL 17 database: the
# dump re-creates the `public` schema, which `initdb` already created.
HARMLESS_RESTORE_ERRORS = ('schema "public" already exists',)


class BootstrapError(Exception):
    """A failure with an actionable message, printed without a traceback."""


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def configure_output() -> None:
    """Never crash on a console that cannot encode a character (Windows cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def info(msg: str) -> None:
    print(msg, flush=True)


def warn(msg: str) -> None:
    print(f"warning: {msg}", flush=True)


def heading(title: str) -> None:
    print(f"\n== {title} ==", flush=True)


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"  # pragma: no cover - loop always returns


class Progress:
    """Byte progress on one line (TTY) or every few seconds (logs, CI)."""

    def __init__(self, label: str, total: int, start: int = 0, stream: IO[str] | None = None):
        self.label = label
        self.total = total
        self.done = start
        self.start = start
        self.stream = stream if stream is not None else sys.stderr
        self.tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.t0 = time.monotonic()
        self.last = 0.0
        self.emitted = -1

    def update(self, n: int) -> None:
        self.done += n
        now = time.monotonic()
        if now - self.last >= (0.2 if self.tty else 5.0):
            self.last = now
            self._emit(final=False)

    def finish(self) -> None:
        if self.tty or self.emitted != self.done:
            self._emit(final=True)

    def _emit(self, final: bool) -> None:
        self.emitted = self.done
        elapsed = max(time.monotonic() - self.t0, 1e-6)
        rate = (self.done - self.start) / elapsed
        pct = f"{100 * self.done / self.total:5.1f}%" if self.total else "  ?  "
        line = (
            f"  {self.label}: {human_bytes(self.done)} / {human_bytes(self.total)} "
            f"({pct}) {human_bytes(rate)}/s"
        )
        if self.tty:
            self.stream.write("\r" + line.ljust(78) + ("\n" if final else ""))
        else:
            self.stream.write(line + "\n")
        self.stream.flush()


# --------------------------------------------------------------------------- #
# Subprocesses
# --------------------------------------------------------------------------- #


def run(
    cmd: Sequence[str],
    *,
    cwd: Path = REPO,
    env: dict[str, str] | None = None,
    capture: bool = False,
    input_text: str | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command without a shell. Output is inherited unless ``capture``."""
    argv = [str(c) for c in cmd]
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=capture,
            input=input_text,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise BootstrapError(f"cannot run {argv[0]!r}: {exc}") from exc
    except subprocess.TimeoutExpired:
        if check:
            raise BootstrapError(f"timed out after {timeout}s: {' '.join(argv)}") from None
        return subprocess.CompletedProcess(argv, 124, "", f"timed out after {timeout}s")
    if check and proc.returncode != 0:
        detail = (proc.stderr or "").strip() if capture else ""
        raise BootstrapError(
            f"command failed (exit {proc.returncode}): {' '.join(argv)}"
            + (f"\n{detail}" if detail else "")
        )
    return proc


def db_port() -> int:
    raw = os.environ.get("IDEFIX_DB_PORT", "").strip()
    if not raw:
        return DEFAULT_DB_PORT
    if not raw.isdigit() or not 1 <= int(raw) <= 65535:
        raise BootstrapError(f"IDEFIX_DB_PORT={raw!r} is not a valid TCP port (1-65535).")
    return int(raw)


def database_url(port: int) -> str:
    return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@localhost:{port}/{DB_NAME}"


def child_env(port: int) -> dict[str, str]:
    """Environment for every child: local DATABASE_URL injected, UTF-8 forced."""
    env = dict(os.environ)
    env.update(
        DATABASE_URL=database_url(port),
        IDEFIX_DB_PORT=str(port),
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONUNBUFFERED="1",
    )
    return env


def docker_exe() -> str:
    exe = shutil.which("docker")
    if exe is None:
        raise BootstrapError(
            "Docker is not installed (no `docker` on PATH). Install Docker Desktop "
            "(Windows/macOS) or Docker Engine with the compose plugin (Linux): "
            "https://docs.docker.com/get-docker/"
        )
    return exe


def compose_cmd(*args: str) -> list[str]:
    """`docker compose` pinned to this repo's file and project.

    `--env-file <null device>` keeps Compose from reading the repo's `.env` (which
    holds real secrets and may not even parse as a Compose env file); the port is
    configured by the process environment only, exactly like DATABASE_URL.
    """
    return [
        docker_exe(),
        "compose",
        "--file",
        str(COMPOSE_FILE),
        "--project-name",
        COMPOSE_PROJECT,
        "--env-file",
        os.devnull,
        *args,
    ]


def psql(sql: str, port: int) -> str:
    """Run SQL (via stdin, so no quoting issue on any OS) in the db container."""
    cmd = compose_cmd(
        "exec",
        "-T",
        DB_SERVICE,
        "psql",
        "--username",
        DB_USER,
        "--dbname",
        DB_NAME,
        "--no-psqlrc",
        "--quiet",
        "--tuples-only",
        "--no-align",
        "--set",
        "ON_ERROR_STOP=1",
    )
    return run(cmd, env=child_env(port), capture=True, input_text=sql).stdout.strip()


# --------------------------------------------------------------------------- #
# Manifest (contract C2)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ManifestFile:
    name: str
    role: str
    url: str
    sha256: str
    bytes: int
    extract_to: str | None = None


@dataclass(frozen=True)
class Manifest:
    path: Path
    name: str
    version: str
    files: tuple[ManifestFile, ...]
    row_counts: dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name} {self.version}"

    def database(self) -> ManifestFile:
        dbs = [f for f in self.files if f.role == "database"]
        if len(dbs) != 1:
            raise BootstrapError(
                f"{self.path} must list exactly one file with role 'database' (found {len(dbs)})."
            )
        return dbs[0]


def is_plain_filename(name: str) -> bool:
    return (
        bool(name)
        and name not in (".", "..")
        and PurePosixPath(name).name == name
        and PureWindowsPath(name).name == name
    )


def relative_safe_path(raw: str) -> PurePosixPath:
    """Validate a path that must stay inside its root: no absolute path, no `..`."""
    if not raw or raw.startswith(("/", "\\")) or PureWindowsPath(raw).drive:
        raise BootstrapError(f"unsafe path (absolute): {raw!r}")
    path = PurePosixPath(raw.replace("\\", "/"))
    if ".." in path.parts:
        raise BootstrapError(f"unsafe path (path traversal): {raw!r}")
    return path


def load_manifest(path: Path) -> Manifest:
    if not path.is_file():
        raise BootstrapError(
            f"dataset manifest not found: {path}. It pins the public dataset release "
            "(dataset/manifest.json); restore it with `git checkout -- dataset/` or "
            "pass --manifest PATH."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BootstrapError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise BootstrapError(f"{path}: unsupported manifest (expected schema_version 1).")
    raw_files = data.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise BootstrapError(f"{path}: 'files' must be a non-empty list.")
    files = []
    for i, raw in enumerate(raw_files):
        where = f"{path}: files[{i}]"
        if not isinstance(raw, dict):
            raise BootstrapError(f"{where} must be an object.")
        name = raw.get("name")
        if not isinstance(name, str) or not is_plain_filename(name):
            raise BootstrapError(f"{where}: 'name' must be a plain file name, got {name!r}.")
        sha = str(raw.get("sha256", "")).lower()
        if not SHA256_RE.match(sha):
            raise BootstrapError(f"{where}: 'sha256' must be 64 hex characters.")
        size = raw.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise BootstrapError(f"{where}: 'bytes' must be a positive integer.")
        url = raw.get("url")
        if not isinstance(url, str) or not url:
            raise BootstrapError(f"{where}: 'url' is missing.")
        role = str(raw.get("role", ""))
        extract_to = raw.get("extract_to")
        if role == "archive":
            if not isinstance(extract_to, str):
                raise BootstrapError(f"{where}: archives need 'extract_to'.")
            relative_safe_path(extract_to)
        files.append(ManifestFile(name, role, url, sha, size, extract_to))
    counts = data.get("row_counts") or {}
    row_counts = {
        str(k): int(v) for k, v in counts.items() if isinstance(v, int) and TABLE_RE.match(str(k))
    }
    return Manifest(
        path=path,
        name=str(data.get("name", "dataset")),
        version=str(data.get("version", "?")),
        files=tuple(files),
        row_counts=row_counts,
    )


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #


def file_sha256(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def verify(path: Path, f: ManifestFile) -> None:
    """Raise unless ``path`` has the manifest size and SHA-256 (size first: cheap)."""
    size = path.stat().st_size
    if size != f.bytes:
        raise BootstrapError(f"size mismatch for {f.name}: expected {f.bytes} bytes, got {size}.")
    digest = file_sha256(path)
    if digest != f.sha256:
        raise BootstrapError(f"SHA-256 mismatch for {f.name}: expected {f.sha256}, got {digest}.")


def resolve_url(f: ManifestFile) -> str:
    base = os.environ.get("IDEFIX_DATASET_BASE_URL", "").strip()
    if base:
        return base.rstrip("/") + "/" + urllib.parse.quote(f.name)
    return f.url


def _open(req: urllib.request.Request, timeout: float) -> Any:
    """Seam for tests: everything network goes through here."""
    return urllib.request.urlopen(req, timeout=timeout)


def _content_range_start(header: str | None) -> int | None:
    m = re.match(r"bytes (\d+)-", header or "")
    return int(m.group(1)) if m else None


def download(url: str, part: Path, expected: int) -> bool:
    """Stream ``url`` into ``part``, resuming a partial file when the server allows.

    Returns True when the download resumed an existing partial file.
    """
    offset = part.stat().st_size if part.exists() else 0
    if offset >= expected:
        # A complete (or oversized) leftover is not trusted: start again.
        part.unlink()
        offset = 0
    headers = {"User-Agent": "idefix-bootstrap"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    try:
        resp = _open(urllib.request.Request(url, headers=headers), timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and offset:
            part.unlink()
            return download(url, part, expected)
        raise BootstrapError(f"download failed: HTTP {exc.code} for {url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise BootstrapError(
            f"cannot download {url}: {reason}. Check the connection, set "
            "IDEFIX_DATASET_BASE_URL to a mirror, or pass --dataset-dir with local copies."
        ) from exc
    with resp:
        resumed = (
            offset > 0
            and getattr(resp, "status", None) == 206
            and _content_range_start(resp.headers.get("Content-Range")) == offset
        )
        if offset and not resumed:
            info("  server ignored the resume request: downloading from the start")
            offset = 0
        elif resumed:
            info(f"  resuming at {human_bytes(offset)}")
        progress = Progress(part.name.removesuffix(".part"), expected, start=offset)
        try:
            with part.open("ab" if resumed else "wb") as out:
                while chunk := resp.read(CHUNK):
                    out.write(chunk)
                    progress.update(len(chunk))
        except (OSError, http.client.HTTPException) as exc:
            raise BootstrapError(
                f"download of {url} interrupted ({exc!r}); re-run to resume."
            ) from exc
        progress.finish()
    return resumed


def copy_local(src: Path, part: Path, expected: int) -> None:
    progress = Progress(src.name, expected)
    with src.open("rb") as fin, part.open("wb") as fout:
        while chunk := fin.read(CHUNK):
            fout.write(chunk)
            progress.update(len(chunk))
    progress.finish()


def fetch_file(f: ManifestFile, downloads: Path, dataset_dir: Path | None = None) -> Path:
    """Make ``downloads/<name>`` a verified copy of the manifest file."""
    dest = downloads / f.name
    source = dataset_dir / f.name if dataset_dir is not None else None
    if source is not None and source.resolve() == dest.resolve():
        verify(dest, f)
        info(f"  {f.name}: ok (already in place)")
        return dest
    if dest.exists():
        try:
            verify(dest, f)
            info(f"  {f.name}: ok (cached, SHA-256 verified)")
            return dest
        except BootstrapError as exc:
            warn(f"{exc} Fetching it again.")
            dest.unlink()
    part = dest.with_name(dest.name + ".part")
    if part.is_file() and part.stat().st_size == f.bytes:
        # Complete download interrupted before the final rename.
        try:
            verify(part, f)
            part.replace(dest)
            info(f"  {f.name}: ok (completed earlier, SHA-256 verified)")
            return dest
        except BootstrapError:
            part.unlink()
    if source is not None:
        if not source.is_file():
            raise BootstrapError(f"{f.name} not found in --dataset-dir {dataset_dir}.")
        info(f"  {f.name}: copying from {source}")
        copy_local(source, part, f.bytes)
        attempts = 1
    else:
        url = resolve_url(f)
        info(f"  {f.name}: downloading {url}")
        attempts = 2 if download(url, part, f.bytes) else 1
    for attempt in range(attempts):
        try:
            verify(part, f)
            break
        except BootstrapError:
            part.unlink(missing_ok=True)
            if attempt + 1 == attempts:
                raise
            # The resumed bytes may be the corrupt ones: one clean retry.
            warn(f"{f.name}: verification failed after a resume, downloading from scratch")
            download(resolve_url(f), part, f.bytes)
    part.replace(dest)
    info(f"  {f.name}: ok ({human_bytes(f.bytes)}, SHA-256 verified)")
    return dest


def check_member(member: tarfile.TarInfo) -> PurePosixPath:
    """Only plain files and directories, only below the extraction root."""
    path = relative_safe_path(member.name)
    if not (member.isfile() or member.isdir()):
        raise BootstrapError(
            f"unsafe archive member (links and special files are refused): {member.name!r}"
        )
    return path


def extract_archive(archive: Path, f: ManifestFile, repo: Path, downloads: Path) -> None:
    """Extract into ``repo/<extract_to>``. Never overwrites a differing local file."""
    assert f.extract_to is not None
    root = (repo / relative_safe_path(f.extract_to)).resolve()
    if not root.is_relative_to(repo.resolve()):
        raise BootstrapError(f"{f.name}: extract_to escapes the repository: {f.extract_to!r}")
    stamp = downloads / f".{f.name}.extracted"
    if stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == f.sha256:
        info(f"  {f.name}: already extracted into {f.extract_to}/")
        return
    with tarfile.open(archive, "r:*") as tar:
        members = tar.getmembers()
        paths = [check_member(m) for m in members]  # validate everything first
        written, kept = 0, []
        for member, rel in zip(members, paths, strict=True):
            target = (root / rel).resolve()
            if not target.is_relative_to(root):
                raise BootstrapError(f"unsafe archive member (escapes root): {member.name!r}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            fh = tar.extractfile(member)
            data = fh.read() if fh is not None else b""
            if target.exists():
                if target.read_bytes() != data:
                    kept.append(rel.as_posix())
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(target)
            written += 1
    stamp.write_text(f.sha256 + "\n", encoding="utf-8")
    info(f"  {f.name}: extracted {written} new file(s) into {f.extract_to}/")
    if kept:
        warn(
            f"kept {len(kept)} local file(s) that differ from the release (delete them "
            f"to take the release version): {', '.join(kept[:5])}"
            + (" ..." if len(kept) > 5 else "")
        )


def step_fetch(
    manifest: Manifest,
    downloads: Path = DOWNLOADS,
    repo: Path = REPO,
    dataset_dir: Path | None = None,
) -> None:
    heading(f"fetch: {manifest.label}")
    downloads.mkdir(parents=True, exist_ok=True)
    for f in manifest.files:
        path = fetch_file(f, downloads, dataset_dir)
        if f.role == "archive":
            extract_archive(path, f, repo, downloads)
        elif f.role != "database":
            info(f"  {f.name}: role {f.role!r} is downloaded and verified only")


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    required: bool = True


def parse_version(text: str) -> tuple[int, int] | None:
    m = re.search(r"(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def node_version_ok(text: str) -> bool:
    version = parse_version(text)
    if version is None:
        return False
    major, minor = version
    if major == 20:
        return minor >= 19
    if major == 22:
        return minor >= 12
    return major >= 23


def port_available(port: int) -> bool:
    """Nothing listens on 127.0.0.1:port and we could bind it ourselves."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def port_hint(port: int) -> str:
    return (
        f"127.0.0.1:{port} is taken: pick another port and re-run, e.g. "
        "`export IDEFIX_DB_PORT=55432` (bash/zsh) or `$env:IDEFIX_DB_PORT=55432` "
        "(PowerShell). On Windows, Hyper-V may also reserve it: "
        "`netsh interface ipv4 show excludedportrange protocol=tcp`."
    )


def docker_daemon_hint(stderr: str) -> str:
    if "permission denied" in (stderr or "").lower():
        return (
            "your user cannot reach the Docker socket: `sudo usermod -aG docker $USER`, "
            "log out and back in (or use Docker Desktop)."
        )
    return (
        "Docker is installed but not running: start Docker Desktop (Windows/macOS) or "
        "the service (Linux: `sudo systemctl start docker`), wait until it is ready, re-run."
    )


def docker_daemon_ok() -> bool:
    exe = shutil.which("docker")
    if exe is None:
        return False
    proc = run(
        [exe, "info", "--format", "{{.ServerVersion}}"], capture=True, check=False, timeout=60
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


def db_running(port: int) -> bool:
    proc = run(
        compose_cmd("ps", "--status", "running", "--quiet", DB_SERVICE),
        env=child_env(port),
        capture=True,
        check=False,
        timeout=60,
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


def check_docker(port: int) -> list[Check]:
    exe = shutil.which("docker")
    if exe is None:
        return [
            Check(
                "docker",
                False,
                "not installed (no `docker` on PATH)",
                "install Docker Desktop (Windows/macOS) or Docker Engine with the "
                "compose plugin (Linux): https://docs.docker.com/get-docker/",
            )
        ]
    proc = run(
        [exe, "info", "--format", "{{.ServerVersion}}"], capture=True, check=False, timeout=60
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return [Check("docker", False, "daemon not reachable", docker_daemon_hint(proc.stderr))]
    checks = [Check("docker", True, f"daemon {proc.stdout.strip()}")]
    comp = run([exe, "compose", "version", "--short"], capture=True, check=False, timeout=60)
    version = parse_version(comp.stdout) if comp.returncode == 0 else None
    if version is None:
        checks.append(
            Check(
                "compose",
                False,
                "Docker Compose v2 not available",
                "install the Compose v2 plugin (bundled with Docker Desktop): "
                "https://docs.docker.com/compose/install/",
            )
        )
    elif version < MIN_COMPOSE:
        checks.append(
            Check(
                "compose",
                False,
                f"{comp.stdout.strip()} is too old",
                f"update Docker Compose to {MIN_COMPOSE[0]}.{MIN_COMPOSE[1]}+",
            )
        )
    else:
        checks.append(Check("compose", True, comp.stdout.strip()))
    if db_running(port):
        checks.append(Check("db port", True, f"127.0.0.1:{port} (idefix database running)"))
    elif port_available(port):
        checks.append(Check("db port", True, f"127.0.0.1:{port} free"))
    else:
        checks.append(Check("db port", False, f"127.0.0.1:{port} already in use", port_hint(port)))
    return checks


def check_node(required: bool) -> list[Check]:
    why = "" if required else " (only needed for the webapp)"
    node = shutil.which("node")
    if node is None:
        return [
            Check(
                "node",
                False,
                "not installed" + why,
                f"install {NODE_REQUIREMENT}: https://nodejs.org/",
                required,
            )
        ]
    version = run([node, "--version"], capture=True, check=False, timeout=60).stdout.strip()
    if not node_version_ok(version):
        return [
            Check(
                "node",
                False,
                f"{version or 'unknown version'} is too old" + why,
                f"install {NODE_REQUIREMENT} (Vite 8): https://nodejs.org/",
                required,
            )
        ]
    npm = shutil.which("npm")
    if npm is None:
        return [
            Check(
                "node",
                False,
                f"{version}, but no `npm` on PATH" + why,
                "reinstall Node.js with npm",
                required,
            )
        ]
    npm_version = run([npm, "--version"], capture=True, check=False, timeout=60).stdout.strip()
    return [Check("node", True, f"{version}, npm {npm_version}", required=required)]


def check_embeddings(required: bool) -> Check:
    if importlib.util.find_spec("sentence_transformers") is not None:
        return Check("embeddings", True, "sentence-transformers installed", required=required)
    return Check(
        "embeddings",
        False,
        "the `embed` extra is not installed",
        "run `uv run --extra embed python scripts/bootstrap.py ...` (installs "
        "sentence-transformers + torch, about 1 GB), or pass --skip-embeddings",
        required,
    )


def step_check(manifest_path: Path, port: int, need_node: bool, need_embeddings: bool) -> None:
    heading("check")
    checks: list[Check] = []
    py = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info[:2] >= MIN_PYTHON:
        checks.append(Check("python", True, py))
    else:
        checks.append(
            Check(
                "python",
                False,
                f"{py} (needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)",
                "run through uv: `uv run python scripts/bootstrap.py`",
            )
        )
    checks += check_docker(port)
    checks += check_node(need_node)
    checks.append(check_embeddings(need_embeddings))
    if PIPELINE.is_file():
        checks.append(Check("pipeline", True, "scripts/pipeline.py present"))
    else:
        checks.append(
            Check(
                "pipeline",
                False,
                "scripts/pipeline.py is missing",
                "update the checkout (git pull)",
            )
        )
    try:
        manifest = load_manifest(manifest_path)
        total = sum(f.bytes for f in manifest.files)
        checks.append(
            Check(
                "manifest",
                True,
                f"{manifest.label} ({len(manifest.files)} files, {human_bytes(total)})",
            )
        )
    except BootstrapError as exc:
        checks.append(Check("manifest", False, str(exc)))
    failed = []
    for c in checks:
        tag = " ok " if c.ok else ("FAIL" if c.required else "warn")
        info(f"  [{tag}] {c.name:<11} {c.detail}")
        if not c.ok and c.fix:
            info(f"         {'':<11} -> {c.fix}")
        if not c.ok and c.required:
            failed.append(c.name)
    if failed:
        raise BootstrapError(f"prerequisites missing: {', '.join(failed)} (see above).")


# --------------------------------------------------------------------------- #
# db
# --------------------------------------------------------------------------- #


@dataclass
class DbState:
    tables: int
    marker: dict[str, Any] | None


def compose_up(port: int) -> None:
    """Start the db service and wait for its healthcheck."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)  # bind-mount source must exist
    cmd = compose_cmd(
        "up", "--detach", "--wait", "--wait-timeout", str(HEALTH_TIMEOUT_S), DB_SERVICE
    )
    if run(cmd, env=child_env(port), check=False).returncode == 0:
        return
    if not docker_daemon_ok():
        raise BootstrapError(docker_daemon_hint(""))
    if db_running(port):
        raise BootstrapError(
            "the database container started but did not become healthy. Logs: "
            f"`docker compose -p {COMPOSE_PROJECT} logs {DB_SERVICE}`."
        )
    if not port_available(port):
        raise BootstrapError(port_hint(port))
    raise BootstrapError(
        "could not start the database (see the Docker output above). Logs: "
        f"`docker compose -p {COMPOSE_PROJECT} logs {DB_SERVICE}`."
    )


STATE_SQL = (
    "SELECT json_build_object("
    "'tables', (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'),"
    "'marker', shobj_description("
    "(SELECT oid FROM pg_database WHERE datname = current_database()), 'pg_database'));"
)


def db_state(port: int) -> DbState:
    raw = json.loads(psql(STATE_SQL, port) or "{}")
    marker = None
    try:
        parsed = json.loads(raw.get("marker") or "null")
        if isinstance(parsed, dict) and parsed.get("tool") == MARKER_TOOL:
            marker = parsed
    except ValueError:
        pass
    return DbState(tables=int(raw.get("tables") or 0), marker=marker)


def write_marker(marker: dict[str, Any], port: int) -> None:
    payload = json.dumps(marker, sort_keys=True)
    if MARKER_QUOTE in payload:  # pragma: no cover - defensive, never produced
        raise BootstrapError("cannot store the bootstrap marker")
    psql(f"COMMENT ON DATABASE {DB_NAME} IS {MARKER_QUOTE}{payload}{MARKER_QUOTE};", port)


def row_counts_sql(tables: Sequence[str]) -> str:
    names = ",".join(f"'{t}'" for t in tables if TABLE_RE.match(t))
    if not names:
        return "SELECT '{}'::json;"
    return (
        "SELECT coalesce(json_object_agg(table_name, n), '{}'::json) FROM ("
        "SELECT table_name, (xpath('/row/n/text()', query_to_xml("
        "format('SELECT count(*) AS n FROM public.%I', table_name), false, true, '')))[1]"
        "::text::bigint AS n FROM information_schema.tables "
        f"WHERE table_schema = 'public' AND table_name IN ({names})) t;"
    )


def row_counts(tables: Sequence[str], port: int) -> dict[str, int]:
    return {k: int(v) for k, v in json.loads(psql(row_counts_sql(tables), port) or "{}").items()}


def restore_cmd(db_file: ManifestFile) -> list[str]:
    return compose_cmd(
        "exec",
        "-T",
        DB_SERVICE,
        "pg_restore",
        "--no-owner",
        "--no-privileges",
        "--username",
        DB_USER,
        "--dbname",
        DB_NAME,
        f"{CONTAINER_DATASET_DIR}/{db_file.name}",
    )


def unexpected_restore_errors(stderr: str) -> list[str]:
    errors = [line for line in stderr.splitlines() if "pg_restore: error:" in line]
    return [e for e in errors if not any(h in e for h in HARMLESS_RESTORE_ERRORS)]


def restore(db_file: ManifestFile, port: int) -> None:
    info(f"  restoring {db_file.name} with pg_restore inside the container ...")
    t0 = time.monotonic()
    proc = run(restore_cmd(db_file), env=child_env(port), capture=True, check=False)
    unexpected = unexpected_restore_errors(proc.stderr)
    if proc.returncode != 0 and (unexpected or "pg_restore: error:" not in proc.stderr):
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise BootstrapError(
            f"pg_restore failed (exit {proc.returncode}):\n{tail}\n"
            "The database is probably partially restored. The bootstrap never deletes data, "
            "so later runs will leave it as it is. To start over, remove the "
            f"`{COMPOSE_PROJECT}_pgdata` Docker volume yourself (this deletes the local "
            "database), then re-run."
        )
    note = " (ignored the expected 'schema public already exists')" if proc.returncode else ""
    info(f"  restored in {time.monotonic() - t0:.1f} s{note}")


def alembic_cmd() -> list[str]:
    return [sys.executable, "-m", "alembic", "upgrade", "head"]


# Read-only: no error when the table does not exist (query_to_xml runs lazily).
REVISION_SQL = (
    "SELECT CASE WHEN to_regclass('public.alembic_version') IS NULL THEN '' ELSE "
    "(xpath('/row/v/text()', query_to_xml("
    "'SELECT string_agg(version_num, '','') AS v FROM public.alembic_version', "
    "false, true, '')))[1]::text END;"
)


def alembic_head(port: int) -> str | None:
    """Head revision of the migration scripts (reads files only, not the database)."""
    proc = run(
        [sys.executable, "-m", "alembic", "heads"], env=child_env(port), capture=True, check=False
    )
    m = re.search(r"^(\S+) \(head\)", proc.stdout, re.MULTILINE)
    return m.group(1) if m else None


def step_db(manifest: Manifest, port: int, downloads: Path = DOWNLOADS) -> DbState:
    """Restore into an empty database only; a database with data is left untouched."""
    heading(f"db: PostgreSQL 17 on 127.0.0.1:{port} (compose project {COMPOSE_PROJECT})")
    db_file = manifest.database()
    compose_up(port)
    state = db_state(port)
    if state.tables == 0:
        local = downloads / db_file.name
        if not local.is_file():
            raise BootstrapError(
                f"{db_file.name} is not in {downloads}: run "
                "`uv run python scripts/bootstrap.py fetch` first."
            )
        verify(local, db_file)
        restore(db_file, port)
        write_marker(
            {
                "tool": MARKER_TOOL,
                "dataset": manifest.name,
                "version": manifest.version,
                "file": db_file.name,
                "sha256": db_file.sha256,
                "restored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "pipeline": {},
            },
            port,
        )
        if manifest.row_counts:
            got = row_counts(list(manifest.row_counts), port)
            diff = {t: (n, got.get(t)) for t, n in manifest.row_counts.items() if got.get(t) != n}
            if diff:
                warn(f"restored row counts differ from the manifest (expected, got): {diff}")
        # A no-op when the artefact is already at head; upgrades an older one.
        info("  alembic upgrade head ...")
        run(alembic_cmd(), env=child_env(port))
        state = db_state(port)
    else:
        if state.marker and state.marker.get("sha256") == db_file.sha256:
            origin = f"restored from {db_file.name} on {state.marker.get('restored_at')}"
        elif state.marker:
            origin = (
                f"restored from {state.marker.get('file')}, not {db_file.name} ({manifest.label})"
            )
        else:
            origin = f"{state.tables} tables, not restored by this bootstrap"
        info(
            f"  the database already holds data ({origin}): left untouched "
            "(no restore, no migration; the bootstrap never deletes or replaces data)"
        )
        revision = psql(REVISION_SQL, port)
        head = alembic_head(port)
        if head and revision != head:
            warn(
                f"its schema is at revision {revision or 'none'}, the code expects {head}. "
                f"To migrate it yourself: DATABASE_URL={database_url(port)} "
                "uv run alembic upgrade head"
            )
    revision = psql(REVISION_SQL, port)
    counts = row_counts(list(manifest.row_counts) or list(DEFAULT_COUNTED_TABLES), port)
    info(
        f"  schema at alembic revision {revision or 'none'}; rows: "
        + ", ".join(f"{t} {n}" for t, n in sorted(counts.items()))
    )
    info(f"  DATABASE_URL={database_url(port)}")
    return state


# --------------------------------------------------------------------------- #
# pipeline
# --------------------------------------------------------------------------- #


def pipeline_cmd(mission: str, skip_embeddings: bool) -> list[str]:
    cmd = [sys.executable, str(PIPELINE), "--mission", mission]
    if skip_embeddings:
        cmd.append("--skip-embeddings")
    return cmd


def pipeline_key(mission: str, skip_embeddings: bool) -> str:
    return mission + ("/skip-embeddings" if skip_embeddings else "")


def pipeline_done(marker: dict[str, Any] | None, mission: str, skip_embeddings: bool) -> bool:
    runs = (marker or {}).get("pipeline") or {}
    flags = (False, True) if skip_embeddings else (False,)
    return any(pipeline_key(m, s) in runs for m in (mission, "all") for s in flags)


def step_pipeline(mission: str, skip_embeddings: bool, port: int, automatic: bool) -> None:
    """Run the offline pipeline.

    ``automatic`` (inside ``all``): only on a database this bootstrap restored, and
    only once. Explicitly (``bootstrap.py pipeline``): always, on whatever is there.
    """
    heading(f"pipeline: --mission {mission}")
    if not PIPELINE.is_file():
        raise BootstrapError(f"{PIPELINE} not found; this checkout has no pipeline runner.")
    compose_up(port)
    state = db_state(port)
    if state.tables == 0:
        raise BootstrapError(
            "the database is empty: run `uv run python scripts/bootstrap.py db` first."
        )
    rerun = "`uv run python scripts/bootstrap.py pipeline` runs it explicitly"
    if automatic and state.marker is None:
        info(f"  skipped: this database was not restored by the bootstrap ({rerun})")
        return
    if automatic and pipeline_done(state.marker, mission, skip_embeddings):
        info(f"  skipped: already completed on this database ({rerun})")
        return
    if state.marker is None:
        info("  note: this database was not restored by the bootstrap")
    proc = run(pipeline_cmd(mission, skip_embeddings), env=child_env(port), check=False)
    if proc.returncode != 0:
        raise BootstrapError(
            f"the pipeline failed (exit {proc.returncode}). Stages: "
            "`uv run python scripts/pipeline.py --list`; resume with `--from STAGE`, with "
            f"DATABASE_URL={database_url(port)} in the environment."
        )
    if state.marker is not None:
        state.marker.setdefault("pipeline", {})[pipeline_key(mission, skip_embeddings)] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        )
        write_marker(state.marker, port)


# --------------------------------------------------------------------------- #
# webapp
# --------------------------------------------------------------------------- #


def npm_install_needed(webapp: Path) -> bool:
    """node_modules missing, or older than package-lock.json (e.g. after a pull)."""
    hidden_lock = webapp / "node_modules" / ".package-lock.json"
    lock = webapp / "package-lock.json"
    if not hidden_lock.is_file():
        return True
    return lock.is_file() and lock.stat().st_mtime > hidden_lock.stat().st_mtime


def npm_exe() -> str:
    npm = shutil.which("npm")  # npm.cmd on Windows: which() resolves PATHEXT
    if npm is None:
        raise BootstrapError(f"npm not found: install {NODE_REQUIREMENT} from https://nodejs.org/")
    return npm


def prepare_webapp(webapp: Path = WEBAPP) -> None:
    heading("webapp")
    npm = npm_exe()
    if npm_install_needed(webapp):
        info("  npm ci ...")
        run([npm, "ci"], cwd=webapp)
    else:
        info("  node_modules up to date")
    if not any((webapp / "public" / "data").glob("*/channels_index.json")):
        warn(
            "no analyst bundle under webapp/public/data/ yet: run "
            "`uv run python scripts/bootstrap.py pipeline` (or, for a synthetic demo, "
            "`uv run python scripts/make_fixture_bundle.py`)."
        )


def serve_webapp(webapp: Path = WEBAPP) -> None:
    info(
        "\nServing the analyst webapp: Vite prints the URL (default http://localhost:5173/). "
        "Ctrl+C stops it."
    )
    try:
        run([npm_exe(), "run", "dev"], cwd=webapp, check=False)
    except KeyboardInterrupt:
        info("\nwebapp stopped")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="Reproducible setup on the public corpus: check, fetch, db, pipeline, "
        "webapp (default: all). No Telegram credentials, no .env.",
    )
    ap.add_argument("step", nargs="?", default="all", choices=STEPS)
    ap.add_argument("--dataset-dir", type=Path, help="copy release files from this folder")
    ap.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="dataset manifest (default: dataset/manifest.json)",
    )
    ap.add_argument("--mission", default="all", help="pipeline mission(s) (default: all)")
    ap.add_argument(
        "--skip-embeddings", action="store_true", help="forwarded to scripts/pipeline.py"
    )
    ap.add_argument("--no-webapp", action="store_true", help="`all` stops after the pipeline")
    return ap.parse_args(argv)


def run_all(args: argparse.Namespace, port: int) -> None:
    timings: list[tuple[str, float]] = []

    def timed(name: str, fn: Callable[[], object]) -> None:
        t0 = time.monotonic()
        fn()
        timings.append((name, time.monotonic() - t0))

    timed(
        "check",
        lambda: step_check(args.manifest, port, not args.no_webapp, not args.skip_embeddings),
    )
    manifest = load_manifest(args.manifest)
    timed("fetch", lambda: step_fetch(manifest, dataset_dir=args.dataset_dir))
    timed("db", lambda: step_db(manifest, port))
    timed(
        "pipeline",
        lambda: step_pipeline(args.mission, args.skip_embeddings, port, automatic=True),
    )
    if not args.no_webapp:
        timed("webapp", prepare_webapp)
    heading("ready")
    for name, seconds in timings:
        info(f"  {name:<9} {seconds:8.1f} s")
    info(f"  DATABASE_URL={database_url(port)}")
    if not args.no_webapp:
        serve_webapp()


def main(argv: Sequence[str] | None = None) -> int:
    configure_output()
    args = parse_args(argv)
    try:
        port = db_port()
        if args.step == "all":
            run_all(args, port)
        elif args.step == "check":
            step_check(
                args.manifest,
                port,
                need_node=not args.no_webapp,
                need_embeddings=not args.skip_embeddings,
            )
        elif args.step == "fetch":
            step_fetch(load_manifest(args.manifest), dataset_dir=args.dataset_dir)
        elif args.step == "db":
            step_db(load_manifest(args.manifest), port)
        elif args.step == "pipeline":
            step_pipeline(args.mission, args.skip_embeddings, port, automatic=False)
        elif args.step == "webapp":
            prepare_webapp()
            serve_webapp()
    except BootstrapError as exc:
        print(f"\nerror: {exc}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr, flush=True)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
