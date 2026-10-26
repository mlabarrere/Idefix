"""Tests for scripts/bootstrap.py (the one-command reproducible setup).

No Docker, no network: ``bootstrap.run`` (every subprocess) and ``bootstrap._open``
(every download) are replaced by fakes, so these tests pin the behaviour that
matters for a newcomer -- integrity checks, safe extraction, the exact commands
handed to Docker Compose / pg_restore / Alembic / the pipeline, and the
"restore only into an empty database" rule.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import urllib.error
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("bootstrap", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bootstrap"] = m  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(m)
    return m


bs = _load_module()

DATA = bytes(range(256)) * 4  # 1 KiB, deterministic


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_file(name: str = "corpus.dump", data: bytes = DATA, role: str = "database", **kw):
    return bs.ManifestFile(
        name=name,
        role=role,
        url=f"https://example.org/releases/{name}",
        sha256=sha(data),
        bytes=len(data),
        **kw,
    )


def make_manifest(*files, row_counts=None):
    return bs.Manifest(
        path=Path("manifest.json"),
        name="idefix-telegram-public-corpus",
        version="1.0.0",
        files=tuple(files) or (make_file(),),
        row_counts=row_counts or {},
    )


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class FakeResponse:
    def __init__(self, data: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._buf = io.BytesIO(data)
        self.status = status
        self.headers = headers or {}

    def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


@pytest.fixture
def net(monkeypatch):
    """Queue fake HTTP responses; returns the list of requests made."""
    requests: list[Any] = []
    queue: list[Any] = []

    def fake_open(req, timeout):
        requests.append(req)
        if not queue:
            raise AssertionError(f"unexpected network access: {req.full_url}")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(bs, "_open", fake_open)

    def respond(*items):
        queue.extend(items)
        return requests

    respond.requests = requests  # type: ignore[attr-defined]
    return respond


class FakeRunner:
    """Records every command; ``handler(cmd, kwargs) -> (rc, stdout, stderr)``."""

    def __init__(self, handler):
        self.handler = handler
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, cmd, **kw):
        cmd = [str(c) for c in cmd]
        self.calls.append((cmd, kw))
        rc, out, err = self.handler(cmd, kw)
        if kw.get("check", True) and rc != 0:
            raise bs.BootstrapError(f"command failed (exit {rc}): {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, rc, out, err)

    def find(self, word: str) -> list[tuple[list[str], dict[str, Any]]]:
        return [(c, kw) for c, kw in self.calls if word in c]

    def index(self, word: str) -> int:
        return next(i for i, (c, _) in enumerate(self.calls) if word in c)


HARMLESS = (
    "pg_restore: while PROCESSING TOC:\n"
    'pg_restore: error: could not execute query: ERROR:  schema "public" already exists\n'
    "Command was: CREATE SCHEMA public;\n"
    "pg_restore: warning: errors ignored on restore: 1\n"
)


def db_handler(
    tables: int = 0, marker: dict | None = None, restore=(1, "", HARMLESS), revision="0008"
):
    """A database container (and alembic) answering the bootstrap's commands."""
    comments: list[str] = []
    sql_seen: list[str] = []

    def handler(cmd, kw):
        if "psql" in cmd:
            sql = kw.get("input_text") or ""
            sql_seen.append(sql)
            if sql.startswith("COMMENT ON DATABASE"):
                comments.append(sql)
                return 0, "", ""
            if "shobj_description" in sql:
                state = {"tables": tables, "marker": json.dumps(marker) if marker else None}
                return 0, json.dumps(state), ""
            if "alembic_version" in sql:
                return 0, revision, ""
            if "query_to_xml" in sql:
                return 0, json.dumps({"channels": 3, "messages": 5}), ""
            raise AssertionError(sql)
        if "pg_restore" in cmd:
            return restore
        if cmd[-2:] == ["alembic", "heads"]:
            return 0, "0008 (head)\n", ""
        return 0, "", ""

    handler.comments = comments  # type: ignore[attr-defined]
    handler.sql = sql_seen  # type: ignore[attr-defined]
    return handler


@pytest.fixture
def docker(monkeypatch, tmp_path):
    """Fake docker binary + no writes into the real dataset/downloads."""
    monkeypatch.setattr(bs, "docker_exe", lambda: "docker")
    monkeypatch.setattr(bs, "DOWNLOADS", tmp_path / "downloads")
    monkeypatch.delenv("IDEFIX_DATASET_BASE_URL", raising=False)

    def install(handler):
        runner = FakeRunner(handler)
        monkeypatch.setattr(bs, "run", runner)
        return runner

    return install


COMPOSE = [
    "docker", "compose", "--file", str(bs.COMPOSE_FILE), "--project-name", "idefix",
    "--env-file", os.devnull,
]  # fmt: skip
LOCAL_URL = "postgresql+asyncpg://idefix:idefix@localhost:55435/idefix"


# --------------------------------------------------------------------------- #
# fetch: integrity
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _no_mirror(monkeypatch):
    monkeypatch.delenv("IDEFIX_DATASET_BASE_URL", raising=False)


def test_download_verifies_and_renames(tmp_path, net):
    f = make_file()
    requests = net(FakeResponse(DATA))
    path = bs.fetch_file(f, tmp_path)
    assert path.read_bytes() == DATA
    assert not (tmp_path / "corpus.dump.part").exists()
    assert requests[0].full_url == f.url
    assert requests[0].get_header("Range") is None


def test_sha256_mismatch_is_rejected_and_nothing_kept(tmp_path, net):
    f = make_file()
    net(FakeResponse(bytes(len(DATA))))  # right size, wrong content
    with pytest.raises(bs.BootstrapError, match="SHA-256 mismatch"):
        bs.fetch_file(f, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_size_mismatch_is_rejected(tmp_path, net):
    f = make_file()
    net(FakeResponse(DATA[:-10]))
    with pytest.raises(bs.BootstrapError, match="size mismatch"):
        bs.fetch_file(f, tmp_path)
    assert not (tmp_path / "corpus.dump").exists()


def test_verified_cached_file_skips_the_network(tmp_path, net):
    (tmp_path / "corpus.dump").write_bytes(DATA)
    requests = net()  # any request raises
    bs.fetch_file(make_file(), tmp_path)
    assert requests == []


def test_corrupt_cached_file_is_downloaded_again(tmp_path, net):
    (tmp_path / "corpus.dump").write_bytes(b"stale")
    net(FakeResponse(DATA))
    assert bs.fetch_file(make_file(), tmp_path).read_bytes() == DATA


def test_partial_download_resumes_with_range(tmp_path, net):
    (tmp_path / "corpus.dump.part").write_bytes(DATA[:400])
    requests = net(
        FakeResponse(
            DATA[400:], status=206, headers={"Content-Range": f"bytes 400-1023/{len(DATA)}"}
        )
    )
    assert bs.fetch_file(make_file(), tmp_path).read_bytes() == DATA
    assert requests[0].get_header("Range") == "bytes=400-"


def test_resume_ignored_by_server_restarts_from_zero(tmp_path, net):
    (tmp_path / "corpus.dump.part").write_bytes(b"\xff" * 400)
    net(FakeResponse(DATA, status=200))
    assert bs.fetch_file(make_file(), tmp_path).read_bytes() == DATA


def test_corrupt_resume_retries_once_from_scratch(tmp_path, net):
    (tmp_path / "corpus.dump.part").write_bytes(b"\xff" * 400)  # bad prefix
    requests = net(
        FakeResponse(DATA[400:], status=206, headers={"Content-Range": "bytes 400-1023/1024"}),
        FakeResponse(DATA),
    )
    assert bs.fetch_file(make_file(), tmp_path).read_bytes() == DATA
    assert [r.get_header("Range") for r in requests] == ["bytes=400-", None]


def test_mirror_override_replaces_the_url_prefix(tmp_path, net, monkeypatch):
    monkeypatch.setenv("IDEFIX_DATASET_BASE_URL", "https://mirror.example.net/idefix/")
    requests = net(FakeResponse(DATA))
    bs.fetch_file(make_file(), tmp_path)
    assert requests[0].full_url == "https://mirror.example.net/idefix/corpus.dump"


def test_network_error_is_actionable(tmp_path, net):
    net(urllib.error.URLError("Name or service not known"))
    with pytest.raises(bs.BootstrapError, match="IDEFIX_DATASET_BASE_URL"):
        bs.fetch_file(make_file(), tmp_path)


def test_dataset_dir_copies_without_network(tmp_path, net):
    src = tmp_path / "usb"
    src.mkdir()
    (src / "corpus.dump").write_bytes(DATA)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    requests = net()
    assert bs.fetch_file(make_file(), downloads, dataset_dir=src).read_bytes() == DATA
    assert requests == []


def test_dataset_dir_missing_file(tmp_path, net):
    with pytest.raises(bs.BootstrapError, match="not found in --dataset-dir"):
        bs.fetch_file(make_file(), tmp_path, dataset_dir=tmp_path / "empty")


# --------------------------------------------------------------------------- #
# fetch: archives
# --------------------------------------------------------------------------- #


def make_tar(path: Path, members: list[tarfile.TarInfo | tuple[str, bytes]]) -> bytes:
    with tarfile.open(path, "w:gz") as tar:
        for m in members:
            if isinstance(m, tarfile.TarInfo):
                tar.addfile(m)
            else:
                name, data = m
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return path.read_bytes()


def archive_file(data: bytes):
    return make_file("ann.tar.gz", data, role="archive", extract_to="data")


def test_archive_extracts_files_once(tmp_path):
    repo, downloads = tmp_path / "repo", tmp_path / "dl"
    repo.mkdir()
    downloads.mkdir()
    arc = downloads / "ann.tar.gz"
    data = make_tar(arc, [("annotations/judgments.jsonl", b'{"a": 1}\n'), ("claims/c.jsonl", b"x")])
    f = archive_file(data)
    bs.extract_archive(arc, f, repo, downloads)
    target = repo / "data" / "annotations" / "judgments.jsonl"
    assert target.read_bytes() == b'{"a": 1}\n'
    assert (repo / "data" / "claims" / "c.jsonl").read_bytes() == b"x"
    # Idempotent: the stamp short-circuits a second extraction.
    target.write_bytes(b"edited locally")
    bs.extract_archive(arc, f, repo, downloads)
    assert target.read_bytes() == b"edited locally"


def test_archive_never_overwrites_a_differing_local_file(tmp_path, capsys):
    repo, downloads = tmp_path / "repo", tmp_path / "dl"
    (repo / "data" / "annotations").mkdir(parents=True)
    downloads.mkdir()
    local = repo / "data" / "annotations" / "judgments.jsonl"
    local.write_bytes(b"my own work")
    arc = downloads / "ann.tar.gz"
    data = make_tar(arc, [("annotations/judgments.jsonl", b"release")])
    bs.extract_archive(arc, archive_file(data), repo, downloads)
    assert local.read_bytes() == b"my own work"
    assert "kept 1 local file" in capsys.readouterr().out


@pytest.mark.parametrize(
    "name",
    ["../evil.txt", "annotations/../../evil.txt", "/tmp/evil.txt", "C:/evil.txt", "\\evil.txt"],
)
def test_archive_path_traversal_is_rejected(tmp_path, name):
    repo, downloads = tmp_path / "repo", tmp_path / "dl"
    repo.mkdir()
    downloads.mkdir()
    arc = downloads / "ann.tar.gz"
    data = make_tar(arc, [("annotations/ok.txt", b"ok"), (name, b"pwned")])
    with pytest.raises(bs.BootstrapError, match="unsafe"):
        bs.extract_archive(arc, archive_file(data), repo, downloads)
    # Validation happens before any write.
    assert not (repo / "data").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_archive_links_are_rejected(tmp_path):
    repo, downloads = tmp_path / "repo", tmp_path / "dl"
    repo.mkdir()
    downloads.mkdir()
    link = tarfile.TarInfo("annotations/passwd")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    arc = downloads / "ann.tar.gz"
    data = make_tar(arc, [link])
    with pytest.raises(bs.BootstrapError, match="links"):
        bs.extract_archive(arc, archive_file(data), repo, downloads)


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #


def write_manifest(tmp_path: Path, **override) -> Path:
    entry = {
        "name": "idefix-corpus-v1.0.0.dump",
        "role": "database",
        "format": "pg_dump-custom",
        "bytes": len(DATA),
        "sha256": sha(DATA).upper(),
        "url": "https://github.com/x/y/releases/download/dataset-v1.0.0/idefix-corpus-v1.0.0.dump",
    }
    entry.update(override)
    doc = {
        "schema_version": 1,
        "name": "idefix-telegram-public-corpus",
        "version": "1.0.0",
        "files": [entry],
        "row_counts": {"channels": 3, "messages": 5, "bad name; drop": 1},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_manifest_loads_and_normalises(tmp_path):
    m = bs.load_manifest(write_manifest(tmp_path))
    assert m.database().name == "idefix-corpus-v1.0.0.dump"
    assert m.database().sha256 == sha(DATA)  # lower-cased
    assert m.row_counts == {"channels": 3, "messages": 5}  # unsafe table name dropped


@pytest.mark.parametrize(
    "override, message",
    [
        ({"name": "../escape.dump"}, "plain file name"),
        ({"name": "sub/dir.dump"}, "plain file name"),
        ({"sha256": "abc"}, "64 hex"),
        ({"bytes": 0}, "positive integer"),
        ({"role": "archive", "extract_to": "../outside"}, "path traversal"),
        ({"role": "archive"}, "extract_to"),
    ],
)
def test_manifest_rejects_unsafe_entries(tmp_path, override, message):
    with pytest.raises(bs.BootstrapError, match=message):
        bs.load_manifest(write_manifest(tmp_path, **override))


def test_missing_manifest_is_explained(tmp_path):
    with pytest.raises(bs.BootstrapError, match="manifest not found"):
        bs.load_manifest(tmp_path / "nope.json")


# --------------------------------------------------------------------------- #
# Environment and command construction
# --------------------------------------------------------------------------- #


def test_child_env_injects_the_local_url_over_any_inherited_one(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://someone@remote.example/prod")
    env = bs.child_env(55435)
    assert env["DATABASE_URL"] == LOCAL_URL
    assert env["PYTHONUTF8"] == "1"
    assert env["IDEFIX_DB_PORT"] == "55435"


def test_db_port_from_environment(monkeypatch):
    monkeypatch.delenv("IDEFIX_DB_PORT", raising=False)
    assert bs.db_port() == 5433
    monkeypatch.setenv("IDEFIX_DB_PORT", "55435")
    assert bs.db_port() == 55435
    monkeypatch.setenv("IDEFIX_DB_PORT", "not-a-port")
    with pytest.raises(bs.BootstrapError, match="IDEFIX_DB_PORT"):
        bs.db_port()


def test_compose_command_is_pinned_and_never_reads_dotenv(docker):
    assert bs.compose_cmd("up", "--detach") == [*COMPOSE, "up", "--detach"]


def test_pg_restore_command(monkeypatch):
    # The command is built, never run: do not require Docker on the runner.
    monkeypatch.setattr(bs, "docker_exe", lambda: "docker")
    cmd = bs.restore_cmd(make_file("idefix-corpus-v1.0.0.dump"))
    assert cmd[cmd.index("exec") :] == [
        "exec", "-T", "db", "pg_restore", "--no-owner", "--no-privileges",
        "--username", "idefix", "--dbname", "idefix", "/dataset/idefix-corpus-v1.0.0.dump",
    ]  # fmt: skip


def test_alembic_and_pipeline_use_this_interpreter():
    assert bs.alembic_cmd() == [sys.executable, "-m", "alembic", "upgrade", "head"]
    assert bs.pipeline_cmd("russosphere", skip_embeddings=True) == [
        sys.executable, str(bs.PIPELINE), "--mission", "russosphere", "--skip-embeddings",
    ]  # fmt: skip
    assert bs.pipeline_cmd("all", skip_embeddings=False)[-2:] == ["--mission", "all"]


def test_only_the_known_harmless_restore_error_is_ignored():
    assert bs.unexpected_restore_errors(HARMLESS) == []
    bad = HARMLESS + 'pg_restore: error: could not create extension "pg_graphql"\n'
    assert len(bs.unexpected_restore_errors(bad)) == 1


@pytest.mark.parametrize(
    "version, ok",
    [
        ("v18.20.0", False),
        ("v20.18.1", False),
        ("v20.19.0", True),
        ("v21.7.3", False),
        ("v22.11.0", False),
        ("v22.12.0", True),
        ("v24.1.0", True),
        ("v26.11.0", True),
        ("", False),
    ],
)
def test_node_version_rule_matches_vite(version, ok):
    assert bs.node_version_ok(version) is ok


# --------------------------------------------------------------------------- #
# db step
# --------------------------------------------------------------------------- #


def test_db_restores_into_an_empty_database(docker, tmp_path):
    runner = docker(handler := db_handler(tables=0))
    downloads = tmp_path / "dl"
    downloads.mkdir()
    (downloads / "corpus.dump").write_bytes(DATA)
    manifest = make_manifest(row_counts={"channels": 3, "messages": 5})

    bs.step_db(manifest, 55435, downloads=downloads)

    up, _ = runner.calls[0]
    assert up == [*COMPOSE, "up", "--detach", "--wait", "--wait-timeout", "180", "db"]
    restore, kw = runner.find("pg_restore")[0]
    assert restore == bs.restore_cmd(manifest.database())
    assert kw["env"]["IDEFIX_DB_PORT"] == "55435"
    upgrade, kw = runner.find("upgrade")[0]
    assert upgrade == bs.alembic_cmd()
    assert kw["env"]["DATABASE_URL"] == LOCAL_URL
    assert runner.index("up") < runner.index("pg_restore") < runner.index("upgrade")
    marker = json.loads(handler.comments[0].split("$idefix_marker$")[1])
    assert marker["sha256"] == sha(DATA) and marker["tool"] == "idefix-bootstrap"


@pytest.mark.parametrize(
    "marker",
    [
        {"tool": "idefix-bootstrap", "sha256": sha(DATA), "file": "corpus.dump"},
        {"tool": "idefix-bootstrap", "sha256": "0" * 64, "file": "older-release.dump"},
        None,  # a database the bootstrap did not restore (e.g. the maintainer's own)
    ],
)
def test_db_leaves_a_database_with_data_untouched(docker, tmp_path, capsys, marker):
    runner = docker(handler := db_handler(tables=12, marker=marker))
    bs.step_db(make_manifest(), 55435, downloads=tmp_path)
    assert runner.find("pg_restore") == []
    assert runner.find("upgrade") == []  # not even a migration
    assert handler.comments == []  # nor the marker
    assert "left untouched" in capsys.readouterr().out


def test_db_reports_an_outdated_schema_without_migrating_it(docker, tmp_path, capsys):
    runner = docker(db_handler(tables=12, revision="0006"))
    bs.step_db(make_manifest(), 55435, downloads=tmp_path)
    assert runner.find("upgrade") == []
    out = capsys.readouterr().out
    assert "revision 0006, the code expects 0008" in out
    assert "alembic upgrade head" in out


def test_db_without_the_dump_points_at_fetch(docker, tmp_path):
    docker(db_handler(tables=0))
    with pytest.raises(bs.BootstrapError, match="fetch"):
        bs.step_db(make_manifest(), 55435, downloads=tmp_path)


def test_failed_restore_deletes_nothing(docker, tmp_path):
    runner = docker(db_handler(tables=0, restore=(1, "", "pg_restore: error: out of disk space\n")))
    (tmp_path / "corpus.dump").write_bytes(DATA)
    with pytest.raises(bs.BootstrapError, match="never deletes data"):
        bs.step_db(make_manifest(), 55435, downloads=tmp_path)
    assert runner.find("upgrade") == []


DESTRUCTIVE_ARGS = {"down", "rm", "kill", "--volumes", "-v", "dropdb", "--clean", "prune"}
DESTRUCTIVE_SQL = ("DROP ", "TRUNCATE", "DELETE ", "--clean")


def test_no_step_ever_issues_a_destructive_command(docker, tmp_path, pipeline_script):
    (tmp_path / "corpus.dump").write_bytes(DATA)
    manifest = make_manifest(row_counts={"channels": 3})
    empty, filled = db_handler(tables=0), db_handler(tables=12, marker={"tool": "idefix-bootstrap"})
    first = docker(empty)
    bs.step_db(manifest, 55435, downloads=tmp_path)  # restore path
    second = docker(filled)
    bs.step_db(manifest, 55435, downloads=tmp_path)  # left-untouched path
    bs.step_pipeline("all", False, 55435, automatic=False)
    for cmd, _ in first.calls + second.calls:
        assert not DESTRUCTIVE_ARGS & set(cmd), cmd
    for sql in empty.sql + filled.sql:
        assert not any(word in sql.upper() for word in DESTRUCTIVE_SQL), sql


def test_source_has_no_destructive_command():
    """Ratchet for the maintainer's rule: nothing in the bootstrap or Makefile deletes data."""
    source = _SCRIPT.read_text(encoding="utf-8")
    for token in ('"down"', '"--volumes"', '"rm"', "dropdb", "TRUNCATE", "DROP ", "--clean"):
        assert token not in source, token
    makefile = (_SCRIPT.parents[1] / "Makefile").read_text(encoding="utf-8")
    db_recipes = [
        line.strip()
        for line in makefile.splitlines()
        if line.startswith("\t") and any(w in line for w in ("COMPOSE", "docker", "BOOTSTRAP"))
    ]
    assert db_recipes  # the targets exist
    for line in db_recipes:
        assert not {"down", "-v", "--volumes", "rm", "dropdb", "--force"} & set(line.split()), line
    assert "db-reset" not in makefile


def test_force_option_no_longer_exists():
    with pytest.raises(SystemExit):
        bs.parse_args(["db", "--force"])


def test_port_conflict_suggests_another_port(docker, monkeypatch):
    docker(lambda cmd, kw: (1, "", "") if "up" in cmd else (0, "", ""))
    monkeypatch.setattr(bs, "docker_daemon_ok", lambda: True)
    monkeypatch.setattr(bs, "db_running", lambda port: False)
    monkeypatch.setattr(bs, "port_available", lambda port: False)
    with pytest.raises(bs.BootstrapError, match="IDEFIX_DB_PORT"):
        bs.compose_up(5433)


def test_docker_not_running_is_explained(docker, monkeypatch):
    docker(lambda cmd, kw: (1, "", ""))
    monkeypatch.setattr(bs, "docker_daemon_ok", lambda: False)
    with pytest.raises(bs.BootstrapError, match="not running"):
        bs.compose_up(5433)


# --------------------------------------------------------------------------- #
# pipeline step
# --------------------------------------------------------------------------- #


@pytest.fixture
def pipeline_script(monkeypatch, tmp_path):
    script = tmp_path / "pipeline.py"
    script.write_text("# fake\n", encoding="utf-8")
    monkeypatch.setattr(bs, "PIPELINE", script)
    return script


def test_pipeline_runs_with_the_injected_url_and_is_stamped(docker, pipeline_script):
    marker = {"tool": "idefix-bootstrap", "sha256": sha(DATA), "pipeline": {}}
    runner = docker(handler := db_handler(tables=12, marker=marker))
    bs.step_pipeline("russosphere", False, 55435, automatic=True)
    cmd, kw = runner.find(str(pipeline_script))[0]
    assert cmd == [sys.executable, str(pipeline_script), "--mission", "russosphere"]
    assert kw["env"]["DATABASE_URL"] == LOCAL_URL
    stamped = json.loads(handler.comments[-1].split("$idefix_marker$")[1])
    assert "russosphere" in stamped["pipeline"]


def test_all_skips_a_pipeline_that_already_ran(docker, pipeline_script):
    marker = {"tool": "idefix-bootstrap", "pipeline": {"all": "2026-10-24T10:00:00+00:00"}}
    runner = docker(db_handler(tables=12, marker=marker))
    bs.step_pipeline("russosphere", True, 55435, automatic=True)
    assert runner.find(str(pipeline_script)) == []


def test_all_never_runs_the_pipeline_on_a_database_it_did_not_restore(docker, pipeline_script):
    runner = docker(db_handler(tables=12, marker=None))
    bs.step_pipeline("all", False, 55435, automatic=True)
    assert runner.find(str(pipeline_script)) == []


def test_explicit_pipeline_runs_on_any_database(docker, pipeline_script):
    runner = docker(handler := db_handler(tables=12, marker=None))
    bs.step_pipeline("all", False, 55435, automatic=False)
    assert runner.find(str(pipeline_script))
    assert handler.comments == []  # no marker invented on a foreign database


def test_pipeline_with_embeddings_is_not_covered_by_a_skip_embeddings_run():
    marker = {"pipeline": {"all/skip-embeddings": "t"}}
    assert bs.pipeline_done(marker, "all", skip_embeddings=True)
    assert not bs.pipeline_done(marker, "all", skip_embeddings=False)


def test_pipeline_refuses_an_empty_database(docker, pipeline_script):
    docker(db_handler(tables=0))
    with pytest.raises(bs.BootstrapError, match="bootstrap.py db"):
        bs.step_pipeline("all", False, 55435, automatic=False)


def test_pipeline_failure_explains_how_to_resume(docker, pipeline_script):
    def handler(cmd, kw):
        if str(pipeline_script) in cmd:
            return 2, "", ""
        return db_handler(tables=12)(cmd, kw)

    docker(handler)
    with pytest.raises(bs.BootstrapError, match="--from STAGE"):
        bs.step_pipeline("all", False, 55435, automatic=False)


# --------------------------------------------------------------------------- #
# webapp step
# --------------------------------------------------------------------------- #


def test_webapp_runs_npm_ci_when_node_modules_is_missing(docker, monkeypatch, tmp_path):
    runner = docker(lambda cmd, kw: (0, "", ""))
    monkeypatch.setattr(bs, "npm_exe", lambda: "npm.cmd")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    bs.prepare_webapp(tmp_path)
    bs.serve_webapp(tmp_path)
    assert [c for c, _ in runner.calls] == [["npm.cmd", "ci"], ["npm.cmd", "run", "dev"]]
    assert all(kw["cwd"] == tmp_path for _, kw in runner.calls)


def test_webapp_skips_npm_ci_when_dependencies_are_current(docker, monkeypatch, tmp_path):
    runner = docker(lambda cmd, kw: (0, "", ""))
    monkeypatch.setattr(bs, "npm_exe", lambda: "npm")
    lock = tmp_path / "package-lock.json"
    lock.write_text("{}", encoding="utf-8")
    hidden = tmp_path / "node_modules" / ".package-lock.json"
    hidden.parent.mkdir()
    hidden.write_text("{}", encoding="utf-8")
    os.utime(lock, (1_000_000, 1_000_000))
    bs.prepare_webapp(tmp_path)
    assert runner.calls == []
    os.utime(lock, None)  # lockfile now newer than node_modules (e.g. after a pull)
    os.utime(hidden, (1_000_000, 1_000_000))
    bs.prepare_webapp(tmp_path)
    assert [c for c, _ in runner.calls] == [["npm", "ci"]]


# --------------------------------------------------------------------------- #
# check step
# --------------------------------------------------------------------------- #


def test_check_reports_a_stopped_docker_daemon(monkeypatch):
    monkeypatch.setattr(bs.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        bs, "run", FakeRunner(lambda cmd, kw: (1, "", "Cannot connect to the Docker daemon"))
    )
    (check,) = bs.check_docker(5433)
    assert not check.ok and "start Docker Desktop" in check.fix
