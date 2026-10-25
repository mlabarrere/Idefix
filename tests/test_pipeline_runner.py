"""Tests of the offline pipeline runner ``scripts/pipeline.py`` (contract C5).

No database, no network, no real stage: ``subprocess.run`` is replaced by a
recorder, so these tests pin the PLAN (which script, which arguments, in which
order) and the control flow (``--list``, ``--only``, ``--from``,
``--skip-embeddings``, stop on the first failure with a non-zero exit).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "pipeline.py"


def _load():
    spec = importlib.util.spec_from_file_location("pipeline_runner_under_test", _SCRIPT)
    m = importlib.util.module_from_spec(spec)
    # dataclasses resolve string annotations through sys.modules[cls.__module__].
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


pipeline = _load()

# The validated sequence for --mission all (stage-major, db-wide stages once).
EXPECTED_ALL = [
    ("build_edges", None),
    ("tag_france", None),
    ("tag_gan", None),
    ("build_scores", "russosphere"),
    ("build_scores", "france_ukraine"),
    ("build_scores", "gan"),
    ("build_dossier", "russosphere"),
    ("analyze_communities", "russosphere"),
    ("analyze_communities", "france_ukraine"),
    ("analyze_communities", "gan"),
    ("analyze_communities_embed", "russosphere"),
    ("analyze_communities_embed", "france_ukraine"),
    ("analyze_communities_embed", "gan"),
    ("precompute_galaxy_layout", "russosphere"),
    ("precompute_galaxy_layout", "france_ukraine"),
    ("precompute_galaxy_layout", "gan"),
    ("analyze_porosity", "russosphere"),
    ("mine_episodes", "russosphere"),
    ("build_gan_footprint", "russosphere"),
    ("build_commenters", "russosphere"),
    ("build_commenters", "france_ukraine"),
    ("build_commenters", "gan"),
    ("export_static", "russosphere"),
    ("export_static", "france_ukraine"),
    ("export_static", "gan"),
    ("build_stories", "russosphere"),
    ("build_stories", "france_ukraine"),
    ("build_stories", "gan"),
]


# Scripts with no --mission flag that always write the russosphere bundle.
RUSSOSPHERE_ONLY_NO_FLAG = frozenset({"build_dossier", "analyze_porosity", "build_gan_footprint"})


class Recorder:
    """Stand-in for ``subprocess.run``: records calls, returns scripted exit codes."""

    def __init__(self, fail: dict[str, int] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail = fail or {}

    def __call__(self, cmd, **kwargs):
        self.calls.append({"cmd": list(cmd), **kwargs})
        script = Path(cmd[1]).stem
        return subprocess.CompletedProcess(cmd, self.fail.get(script, 0))

    def scripts(self) -> list[str]:
        return [Path(c["cmd"][1]).stem for c in self.calls]

    def steps(self) -> list[tuple[str, str | None]]:
        """(script, mission) for each call, read from the command line itself."""
        out = []
        for c in self.calls:
            cmd = c["cmd"]
            script = Path(cmd[1]).stem
            if "--mission" in cmd:
                mission = cmd[cmd.index("--mission") + 1]
            elif script == "precompute_galaxy_layout":
                mission = Path(cmd[2]).parent.name
            elif script in RUSSOSPHERE_ONLY_NO_FLAG:
                mission = "russosphere"
            else:
                mission = None
            out.append((script, mission))
        return out


@pytest.fixture
def rec(monkeypatch):
    r = Recorder()
    monkeypatch.setattr(pipeline.subprocess, "run", r)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:1/db")
    return r


# --------------------------------------------------------------------------- #
# Declaration
# --------------------------------------------------------------------------- #
def test_every_stage_script_exists_and_names_are_unique():
    assert len(set(pipeline.STAGE_NAMES)) == len(pipeline.STAGE_NAMES)
    for stage in pipeline.STAGES:
        assert (_REPO / "scripts" / stage.script).is_file(), stage.script


def test_missions_match_the_implemented_registry():
    from src.missions import registry

    implemented = set()
    for name in registry.available():
        try:
            registry.get(name)
        except ValueError:  # planned, not implemented (dircom_minarm)
            continue
        implemented.add(name)
    assert set(pipeline.MISSIONS) == implemented
    assert pipeline.MISSIONS[0] == registry.DEFAULT_MISSION


def test_only_embedding_stage_is_the_embed_snapshot():
    assert [s.name for s in pipeline.STAGES if s.embeddings] == ["analyze_communities_embed"]


# --------------------------------------------------------------------------- #
# Run order
# --------------------------------------------------------------------------- #
def test_mission_all_runs_the_validated_sequence(rec):
    assert pipeline.main(["--mission", "all"]) == 0
    assert rec.steps() == EXPECTED_ALL


def test_default_mission_is_all(rec):
    assert pipeline.main([]) == 0
    assert rec.steps() == EXPECTED_ALL


def test_children_use_sys_executable_repo_cwd_and_inherited_env(rec, monkeypatch):
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    assert pipeline.main(["--mission", "gan", "--only", "build_scores"]) == 0
    (call,) = rec.calls
    assert call["cmd"][0] == sys.executable
    assert call["cmd"][1:] == [str(_REPO / "scripts" / "build_scores.py"), "--mission", "gan"]
    assert Path(call["cwd"]) == _REPO
    assert call["env"]["DATABASE_URL"] == "postgresql+asyncpg://u:p@localhost:1/db"
    assert call["env"]["PYTHONUTF8"] == "1"
    assert call["check"] is False


def test_caller_pythonutf8_is_respected(rec, monkeypatch):
    monkeypatch.setenv("PYTHONUTF8", "0")
    pipeline.main(["--mission", "gan", "--only", "tag_gan"])
    assert rec.calls[0]["env"]["PYTHONUTF8"] == "0"


def test_single_mission_keeps_db_wide_stages_and_drops_foreign_ones(rec):
    assert pipeline.main(["--mission", "gan"]) == 0
    steps = rec.steps()
    assert steps[:3] == [("build_edges", None), ("tag_france", None), ("tag_gan", None)]
    assert all(m in (None, "gan") for _, m in steps)
    for russosphere_only in ("build_dossier", "analyze_porosity", "mine_episodes",
                             "build_gan_footprint"):
        assert russosphere_only not in rec.scripts()
    assert rec.scripts()[-2:] == ["export_static", "build_stories"]


def test_layout_stage_targets_the_mission_snapshots(rec):
    pipeline.main(["--mission", "france_ukraine", "--only", "precompute_galaxy_layout"])
    assert rec.calls[0]["cmd"][2:] == [
        "webapp/public/data/france_ukraine/russosphere_snapshot.json",
        "webapp/public/data/france_ukraine/france_ukraine_embed_snapshot.json",
    ]


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
def test_only_runs_one_stage_for_each_selected_mission(rec):
    assert pipeline.main(["--only", "export_static"]) == 0
    assert rec.steps() == [("export_static", m) for m in pipeline.MISSIONS]


def test_from_resumes_at_the_stage(rec):
    assert pipeline.main(["--mission", "russosphere", "--from", "export_static"]) == 0
    assert rec.steps() == [("export_static", "russosphere"), ("build_stories", "russosphere")]


def test_from_first_stage_is_the_full_run(rec):
    assert pipeline.main(["--from", "build_edges"]) == 0
    assert rec.steps() == EXPECTED_ALL


def test_only_a_stage_that_does_not_apply_is_a_usage_error(rec, capsys):
    assert pipeline.main(["--mission", "gan", "--only", "analyze_porosity"]) == 2
    assert rec.calls == []
    assert "Nothing to run" in capsys.readouterr().err


def test_only_and_from_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        pipeline.parse_args(["--only", "tag_gan", "--from", "tag_gan"])
    assert exc.value.code == 2


@pytest.mark.parametrize("argv", [["--mission", "dircom_minarm"], ["--only", "nope"]])
def test_unknown_mission_or_stage_is_rejected(argv):
    with pytest.raises(SystemExit) as exc:
        pipeline.parse_args(argv)
    assert exc.value.code == 2


# --------------------------------------------------------------------------- #
# --skip-embeddings
# --------------------------------------------------------------------------- #
def test_skip_embeddings_drops_the_embed_stage_and_disables_episode_embeddings(rec):
    assert pipeline.main(["--skip-embeddings"]) == 0
    assert "analyze_communities_embed" not in rec.scripts()
    expected = [s for s in EXPECTED_ALL if s[0] != "analyze_communities_embed"]
    assert rec.steps() == expected
    (mine,) = [c["cmd"] for c in rec.calls if Path(c["cmd"][1]).stem == "mine_episodes"]
    assert mine[-1] == "--no-embeddings"
    assert all("--embeddings" not in c["cmd"] and "--embed" not in c["cmd"] for c in rec.calls)


def test_default_run_never_enables_opt_in_embedding_flags(rec):
    """Family (f) and TEXT_SIM edges are opt-in (docs/method/05, D10): never on."""
    pipeline.main([])
    assert all("--embeddings" not in c["cmd"] and "--embed" not in c["cmd"] for c in rec.calls)


def test_only_embed_stage_with_skip_embeddings_is_a_usage_error(rec):
    assert pipeline.main(["--only", "analyze_communities_embed", "--skip-embeddings"]) == 2
    assert rec.calls == []


# --------------------------------------------------------------------------- #
# --list
# --------------------------------------------------------------------------- #
def _listed_names(out: str) -> list[str]:
    names = []
    for line in out.splitlines():
        head = line.strip().split(" ", 1)
        if len(head) == 2 and head[0].rstrip(".").isdigit():
            names.append(head[1].split()[0])
    return names


def test_list_prints_stage_names_in_order_and_runs_nothing(rec, capsys):
    assert pipeline.main(["--list"]) == 0
    assert rec.calls == []
    assert _listed_names(capsys.readouterr().out) == list(pipeline.STAGE_NAMES)


def test_list_honours_mission_and_skip_embeddings(rec, capsys):
    assert pipeline.main(["--list", "--mission", "gan", "--skip-embeddings"]) == 0
    names = _listed_names(capsys.readouterr().out)
    assert "analyze_communities_embed" not in names
    assert "analyze_porosity" not in names
    assert names[:3] == ["build_edges", "tag_france", "tag_gan"]
    assert rec.calls == []


def test_list_works_without_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(pipeline, "REPO", Path("/nonexistent-repo"))
    assert pipeline.main(["--list"]) == 0


# --------------------------------------------------------------------------- #
# Failure handling and timings
# --------------------------------------------------------------------------- #
def test_failure_stops_the_run_with_the_stage_exit_code(monkeypatch, capsys):
    r = Recorder(fail={"build_scores": 3})
    monkeypatch.setattr(pipeline.subprocess, "run", r)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:1/db")
    assert pipeline.main(["--mission", "all"]) == 3
    # db-wide stages, then the first build_scores, then nothing else.
    assert r.steps() == EXPECTED_ALL[:4]
    err = capsys.readouterr().err
    assert "FAILED: build_scores [russosphere] (exit 3)" in err
    assert "--from build_scores" in err


def test_signal_like_exit_code_still_fails(monkeypatch):
    r = Recorder(fail={"tag_france": -9})
    monkeypatch.setattr(pipeline.subprocess, "run", r)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:1/db")
    assert pipeline.main([]) == 1
    assert r.scripts() == ["build_edges", "tag_france"]


def test_each_stage_timing_is_printed(rec, capsys):
    pipeline.main(["--mission", "russosphere", "--from", "export_static"])
    out = capsys.readouterr().out
    assert "--- ok: export_static [russosphere] in " in out
    assert "--- ok: build_stories [russosphere] in " in out
    timings = out.split("Stage timings:")[1]
    assert "export_static [russosphere]" in timings
    assert "build_stories [russosphere]" in timings
    assert "total" in timings


def test_missing_database_url_without_dotenv_is_a_usage_error(monkeypatch, tmp_path, capsys):
    r = Recorder()
    monkeypatch.setattr(pipeline.subprocess, "run", r)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(pipeline, "REPO", tmp_path)  # no .env there
    assert pipeline.main(["--only", "build_edges"]) == 2
    assert r.calls == []
    assert "DATABASE_URL is not set" in capsys.readouterr().err


def test_db_free_stage_runs_without_database_url(monkeypatch, tmp_path):
    r = Recorder()
    monkeypatch.setattr(pipeline.subprocess, "run", r)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(pipeline, "REPO", tmp_path)
    assert pipeline.main(["--mission", "gan", "--only", "build_stories"]) == 0
    assert r.scripts() == ["build_stories"]
