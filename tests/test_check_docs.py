"""Tests for scripts/check_docs.py, the documentation guard-rails.

Every rule has a good and a bad fixture under ``tests/fixtures/check_docs/``:
a miniature repository that must produce no finding (good) or exactly the
findings listed below (bad). The regression test replays the ``file-line``
rule against the pre-pass tree, exported with ``git archive`` -- never checked
out, because old commits track generated files under ``webapp/public/data``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "check_docs"
_SCRIPT = REPO / "scripts" / "check_docs.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_docs", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


cd = _load_module()

# Rules that share another rule's fixture tree.
FIXTURE_OF = {"symbol-paths": "symbols"}


def _findings(root: Path, rule: str) -> list[tuple[str, int, str]]:
    return [(f.path, f.line, f.message) for f in cd.run(root, [rule])[rule]]


def _tree(rule: str, kind: str) -> Path:
    return FIXTURES / FIXTURE_OF.get(rule, rule) / kind


# --------------------------------------------------------------------------- #
# Good and bad fixtures, one pair per rule                                     #
# --------------------------------------------------------------------------- #

# rule -> [(path, line, substring of the message)], in report order.
EXPECTED_BAD: dict[str, list[tuple[str, int, str]]] = {
    "links": [
        ("README.md", 3, "dead link -> docs/chart.png"),
        ("README.md", 3, "dead link -> missing.md"),
        ("README.md", 5, "dead link -> gone.html"),
        ("README.md", 7, "dead link -> ../../outside.md"),
        ("README.md", 9, "dead link -> nowhere.md"),
    ],
    "anchors": [
        ("README.md", 9, "no anchor #Overview in this file"),
        ("README.md", 9, "no anchor #fenced-heading in this file"),
        ("README.md", 9, "no anchor #missing in this file"),
        ("README.md", 9, "no anchor #overview-1 in this file"),
        ("README.md", 10, "no anchor #nope in docs/guide.md"),
    ],
    "file-line": [
        ("README.md", 3, "bare file:line reference `mod.py:5`; cite"),
        ("README.md", 5, "`src/pkg/mod.py:1`; cite `path/to/file.py::symbol` (stale: "
                         "src/pkg/mod.py line 1 holds no code)"),
        ("README.md", 5, "`src/pkg/mod.py:40`; cite `path/to/file.py::symbol` (stale: "
                         "past the end of src/pkg/mod.py (7 lines))"),
        ("README.md", 9, "(stale: none of TRIGGER_LIMIT, 0.7 appears at src/pkg/mod.py "
                         "lines 5-6)"),
        ("README.md", 11, "`src/pkg/gone.py:12`; cite `path/to/file.py::symbol` (stale: "
                          "no such file)"),
        ("README.md", 13, "line link `src/pkg/mod.py#L5` drifts"),
        ("README.md", 14, "line permalink on `main` is not pinned to a commit"),
    ],
    "symbols": [
        ("README.md", 3, "`src/pkg/mod.py::Engine.halt`: no `Engine.halt` defined"),
        ("README.md", 3, "`src/pkg/mod.py::missing`: no `missing` defined"),
        ("README.md", 4, "`src/pkg/mod.py::compute.inner`: no `compute.inner` defined"),
        ("README.md", 4, "`webapp/src/app.ts::renderTable`: no `renderTable` defined"),
        ("README.md", 6, "`src/pkg/gone.py::compute`: no such file"),
        ("README.md", 6, "`util.py::helper`: ambiguous path: src/a/util.py, src/b/util.py"),
    ],
    "symbol-paths": [
        ("README.md", 8, "`mod.py::compute`: write the full path `src/pkg/mod.py::compute`"),
    ],
    "flags": [
        ("README.md", 4, "`scripts/tool.py` declares no `--dryrun` option"),
        ("README.md", 5, "declares no `--miss` option; write it in full: --mission"),
        ("README.md", 6, "`scripts/noargs.py` has no argparse parser; `--mission`"),
        ("README.md", 7, "command runs `scripts/absent.py`, which does not exist"),
        ("README.md", 8, "`scripts/tool.py` declares no `--bogus` option"),
    ],
    "spelling": [
        ("README.md", 3, "'Center' -> 'Centre'"),
        ("README.md", 3, "'analyze' -> 'analyse'"),
        ("README.md", 3, "'behavior' -> 'behaviour'"),
        ("README.md", 3, "'color' -> 'colour'"),
        ("README.md", 3, "'organise' -> 'organize'"),
        ("README.md", 3, "'toward' -> 'towards'"),
        ("README.md", 4, "'Modeling' -> 'Modelling'"),
        ("README.md", 4, "'Optimisation' -> 'Optimization'"),
        ("README.md", 4, "'artifacts' -> 'artefacts'"),
        ("README.md", 4, "'gray' -> 'grey'"),
        ("README.md", 4, "'judgment' -> 'judgement'"),
        ("README.md", 4, "'labeling' -> 'labelling'"),
    ],
    "checkpoints": [
        ("docs/ops/quickstart.md", 3, "says '166,000', source says '166188'"),
        ("docs/ops/quickstart.md", 4, "count '166188' has no fact marker"),
        ("docs/ops/quickstart.md", 4, "count '3,699' has no fact marker"),
        ("docs/ops/quickstart.md", 6, "dataset/manifest.json has no `row_counts.nope`"),
        ("docs/ops/quickstart.md", 7, "unknown fact key `bogus`"),
    ],
    "alembic-head": [
        ("README.md", 3, "quotes Alembic head 0001; alembic/versions head is 0002"),
        ("README.md", 6, "quotes Alembic head 0001; alembic/versions head is 0002"),
    ],
    "version": [
        ("CHANGELOG.md", 0, "no `## [0.4.1]` release heading"),
        ("CITATION.cff", 0, "version 0.3.0-poc != pyproject.toml 0.4.1"),
        ("METHODOLOGY.md", 0, "version 0.4.0 != pyproject.toml 0.4.1"),
    ],
    "methodology-hash": [
        ("CHANGELOG.md", 5, "newest recorded METHODOLOGY.md hash `deadbeef` != current "
                            "`2538ea39`"),
    ],
    "numbers": [
        ("docs/experiments/exp1.md", 3, "number '0.87' has no artefact"),
        ("docs/experiments/exp1.md", 3, "number '4,321' has no artefact"),
    ],
    "archive": [
        ("docs/results.md", 3, "references archive/ without a do-not-cite disclaimer"),
    ],
}


def test_every_rule_has_fixtures():
    assert set(EXPECTED_BAD) == set(cd.RULES)
    for rule in cd.RULES:
        assert _tree(rule, "good").is_dir(), rule
        assert _tree(rule, "bad").is_dir(), rule


@pytest.mark.parametrize("rule", sorted(cd.RULES))
def test_good_fixture_is_clean(rule):
    assert _findings(_tree(rule, "good"), rule) == []


@pytest.mark.parametrize("rule", sorted(cd.RULES))
def test_bad_fixture_reports_each_defect(rule):
    found = _findings(_tree(rule, "bad"), rule)
    expected = EXPECTED_BAD[rule]
    assert [(p, n) for p, n, _ in found] == [(p, n) for p, n, _ in expected], found
    for (_, _, message), (_, _, needle) in zip(found, expected, strict=True):
        assert needle in message


# --------------------------------------------------------------------------- #
# Building blocks                                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Idéfix — guide", "idéfix--guide"),
        ("🧭 Overview", "-overview"),
        ("D2. Family (c) — critical", "d2-family-c--critical"),
        ("C++ & Rust", "c--rust"),
        ("snake_case and kebab-case", "snake_case-and-kebab-case"),
        ("Ünïcödé Straße 2026", "ünïcödé-straße-2026"),
        ("What's new?", "whats-new"),
    ],
)
def test_github_slug(heading, slug):
    assert cd.github_slug(heading) == slug


@pytest.mark.parametrize(
    ("raw", "text"),
    [
        ("`check_docs.py` options", "check_docs.py options"),
        ("See [the guide](docs/guide.md)", "See the guide"),
        ("![logo](logo.svg) Logo", "logo Logo"),
        ('<a id="d19"></a>D19. Not combined', "D19. Not combined"),
        ("_Emphasis_ and \\_escaped\\_", "Emphasis and _escaped_"),
        ("Fish &amp; chips", "Fish & chips"),
    ],
)
def test_heading_text(raw, text):
    assert cd.heading_text(raw) == text


def test_duplicate_headings_get_numbered():
    doc = cd.Doc("x.md", "# A\n\n## A\n\n## A\n\n## A 1\n")
    assert cd.document_anchors(doc) == {"a", "a-1", "a-2", "a-1-1"}


def test_methodology_hash_ignores_line_endings(tmp_path):
    body = b"# Methodology\n\nLine one.\nLine two.\n"
    (tmp_path / "METHODOLOGY.md").write_bytes(body.replace(b"\n", b"\r\n"))
    ctx = cd.Context(tmp_path)
    assert cd.methodology_hash(ctx) == hashlib.sha256(body).hexdigest()[:8]


def test_methodology_hash_missing_from_changelog(tmp_path):
    (tmp_path / "METHODOLOGY.md").write_text("# M\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (finding,) = _findings(tmp_path, "methodology-hash")
    assert finding[0] == "CHANGELOG.md"
    assert "records no METHODOLOGY.md hash" in finding[2]


@pytest.mark.parametrize(
    "line",
    [
        "- METHODOLOGY.md hash `{h}`.",
        "- `METHODOLOGY.md` hash: `{h}`",
        "- Methodology hash {h} (SHA-256, first 8 characters).",
        "- `methodology_version_hash` = `{h}`",
    ],
)
def test_changelog_hash_phrasings(tmp_path, line):
    (tmp_path / "METHODOLOGY.md").write_text("# M\n", encoding="utf-8")
    current = hashlib.sha256(b"# M\n").hexdigest()[:8]
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.4.1]\n\n" + line.format(h=current) + "\n", encoding="utf-8"
    )
    assert _findings(tmp_path, "methodology-hash") == []


def test_alembic_head_ignores_years(tmp_path):
    versions = tmp_path / "alembic" / "versions"
    versions.mkdir(parents=True)
    (versions / "0001_a.py").write_text('revision = "0001"\ndown_revision = None\n')
    (tmp_path / "README.md").write_text("# R\n\nThe head of 2026 is near.\n")
    assert _findings(tmp_path, "alembic-head") == []


def test_alembic_head_detects_branches(tmp_path):
    versions = tmp_path / "alembic" / "versions"
    versions.mkdir(parents=True)
    (versions / "a.py").write_text('revision = "0001"\ndown_revision = None\n')
    (versions / "b.py").write_text('revision = "0002"\ndown_revision = "0001"\n')
    (versions / "c.py").write_text('revision = "0003"\ndown_revision = "0001"\n')
    (finding,) = _findings(tmp_path, "alembic-head")
    assert finding[2] == "alembic/versions has 2 heads: 0002, 0003"


def test_scope_excludes_vendored_and_fixture_markdown(tmp_path):
    for rel in (
        "README.md", "docs/a.md", ".agents/skill.md", "_bmad-output/plan.md",
        "webapp/node_modules/pkg/README.md", "tests/fixtures/x/README.md", "notes.txt",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("# x\n", encoding="utf-8")
    assert cd.Context(tmp_path).md_files == ["README.md", "docs/a.md"]


def test_exit_code_follows_rule_modes(tmp_path, capsys, monkeypatch):
    (tmp_path / "README.md").write_text(
        "# Doc\n\nA [dead link](missing.md). The color.\n", encoding="utf-8"
    )
    assert cd.main(["--root", str(tmp_path), "--rule", "spelling"]) == 1  # blocking
    spelling = cd.RULES["spelling"]
    monkeypatch.setitem(cd.RULES, "spelling", cd.Rule(cd.WARN, spelling.check, spelling.summary))
    assert cd.main(["--root", str(tmp_path), "--rule", "spelling"]) == 0  # warn
    assert cd.main(["--root", str(tmp_path), "--rule", "spelling", "--strict"]) == 1
    assert cd.main(["--root", str(tmp_path), "--rule", "links"]) == 1  # blocking
    out = capsys.readouterr()
    assert "README.md:3: dead link -> missing.md" in out.err


def _style_table(anchor: str) -> set[str]:
    """Rule names in the first column of the table that follows ``anchor``."""
    style = (REPO / "docs" / "STYLE.md").read_text(encoding="utf-8")
    after = style.split(f'<a id="{anchor}"></a>', 1)[1]
    names: set[str] = set()
    started = False
    for line in after.splitlines():
        if line.startswith("|"):
            started = True
            m = re.match(r"\|\s*`([\w-]+)`\s*\|", line)
            if m:
                names.add(m.group(1))
        elif started:
            break
    return names


def test_style_guide_documents_every_rule():
    assert _style_table("checker-rules") == set(cd.RULES)


def test_style_guide_lists_the_warn_mode_rules():
    """docs/STYLE.md must name exactly the rules that are in warn mode."""
    warn = {name for name, rule in cd.RULES.items() if rule.mode == cd.WARN}
    assert _style_table("warn-mode-rules") == warn


def test_fact_markers_inside_code_are_ignored(tmp_path):
    (tmp_path / "dataset").mkdir()
    (tmp_path / "dataset" / "manifest.json").write_text('{"row_counts": {"messages": 5}}')
    (tmp_path / "README.md").write_text(
        "# Doc\n\n`<!-- fact:manifest.row_counts.messages -->9<!-- /fact -->`\n\n"
        "```markdown\n<!-- fact:manifest.row_counts.messages -->9<!-- /fact -->\n```\n",
        encoding="utf-8",
    )
    assert _findings(tmp_path, "checkpoints") == []


# --------------------------------------------------------------------------- #
# Regression: the bare file:line references of the pre-pass tree             #
# --------------------------------------------------------------------------- #

PRE_PASS = "4665744"

# Every bare file:line reference in the Markdown of commit 4665744: 45 in five
# files. The 2026-10 audit counted 111 references and judged 23 broken by
# reading each target; it counted more forms and files than Markdown prose,
# and judged by hand. The rule rejects all 45 and marks the 15 below as
# visibly stale (the target is blank, a comment or docstring, past the end of
# the file, or holds none of the identifiers and numbers quoted beside the
# reference).
PRE_PASS_BARE = [
    ("docs/experiments/exp-parameter-sensitivity.md", 41, "embed/community.py:52"),
    ("docs/experiments/exp-parameter-sensitivity.md", 44, "analyze_communities.py:293"),
    ("docs/experiments/exp-parameter-sensitivity.md", 46, "channel_suspicion.py:145-151"),
    ("docs/experiments/exp-parameter-sensitivity.md", 47, "graph/edges.py:86"),
    ("docs/experiments/exp-parameter-sensitivity.md", 48, "channel_suspicion.py:157-167"),
    ("docs/experiments/exp2-episode-recovery.md", 47, "eval_episode_recovery.py:49"),
    ("docs/experiments/expf-embedding-discrimination.md", 27,
     "eval_embedding_discrimination.py:77"),
    ("docs/experiments/expf-embedding-discrimination.md", 53, "embedding_signals.py:98"),
    ("docs/limitations.md", 110, "rigor.py:111-130"),
    ("docs/limitations.md", 111, "channel_suspicion.py:501"),
    ("docs/limitations.md", 125, "rigor.py:136-138"),
    ("docs/limitations.md", 156, "cascade_role.py:212"),
    ("docs/limitations.md", 157, "coordination.py:326"),
    ("docs/limitations.md", 157, "recidivism.py:93"),
    ("docs/limitations.md", 157, "telegram_footprint.py:41"),
    ("docs/limitations.md", 158, "embedding_signals.py:165"),
    ("docs/limitations.md", 158, "significance.py:16"),
    ("docs/limitations.md", 173, "cascade_role.py:103"),
    ("docs/limitations.md", 173, "recidivism.py:87-89"),
    ("docs/limitations.md", 179, "cascade_role.py:93-97"),
    ("docs/limitations.md", 211, "embedding_signals.py:98"),
    ("docs/limitations.md", 222, "eval_episode_recovery.py:49"),
    ("docs/limitations.md", 228, "eval_embedding_discrimination.py:77"),
    ("docs/limitations.md", 243, "scripts/_eval_common.py:22-27"),
    ("docs/limitations.md", 263, "graph/edges.py:454-455"),
    ("docs/limitations.md", 274, "channel_suspicion.py:145-151"),
    ("docs/limitations.md", 275, "channel_suspicion.py:157-167"),
    ("docs/limitations.md", 276, "cascade_role.py:42"),
    ("docs/limitations.md", 278, "france_targeting.py:136-141"),
    ("docs/limitations.md", 279, "embed/community.py:52"),
    ("docs/limitations.md", 280, "analyze_communities.py:293"),
    ("docs/limitations.md", 281, "analyze_communities.py:105-209"),
    ("docs/limitations.md", 282, "eefi_rubric.py:30-74"),
    ("docs/limitations.md", 283, "channel_suspicion.py:124-140"),
    ("docs/limitations.md", 284, "russosphere/__init__.py:109-114"),
    ("docs/limitations.md", 308, "scripts/build_dossier.py:198"),
    ("docs/limitations.md", 318, "src/dossier/builder.py:339"),
    ("docs/limitations.md", 320, "channel_suspicion.py:617"),
    ("docs/limitations.md", 325, "src/dossier/builder.py:79-103"),
    ("docs/limitations.md", 360, "scripts/build_scores.py:106-114"),
    ("docs/limitations.md", 362, "src/graph/edges.py:594"),
    ("docs/reference/references.md", 70, "src/scorer/significance.py:197-211"),
    ("docs/reference/references.md", 76, "significance.py:180-194"),
    ("docs/reference/references.md", 87, "significance.py:42-75"),
    ("docs/reference/references.md", 144, "src/graph/edges.py:454-455"),
]
PRE_PASS_STALE = [
    ("docs/experiments/exp-parameter-sensitivity.md", 41, "embed/community.py:52"),
    ("docs/experiments/exp-parameter-sensitivity.md", 44, "analyze_communities.py:293"),
    ("docs/experiments/exp-parameter-sensitivity.md", 46, "channel_suspicion.py:145-151"),
    ("docs/limitations.md", 111, "channel_suspicion.py:501"),
    ("docs/limitations.md", 156, "cascade_role.py:212"),
    ("docs/limitations.md", 158, "significance.py:16"),
    ("docs/limitations.md", 173, "cascade_role.py:103"),
    ("docs/limitations.md", 179, "cascade_role.py:93-97"),
    ("docs/limitations.md", 222, "eval_episode_recovery.py:49"),
    ("docs/limitations.md", 274, "channel_suspicion.py:145-151"),
    ("docs/limitations.md", 279, "embed/community.py:52"),
    ("docs/limitations.md", 280, "analyze_communities.py:293"),
    ("docs/limitations.md", 283, "channel_suspicion.py:124-140"),
    ("docs/limitations.md", 318, "src/dossier/builder.py:339"),
    ("docs/limitations.md", 362, "src/graph/edges.py:594"),
]


@pytest.fixture(scope="module")
def pre_pass_tree(tmp_path_factory) -> Path:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    probe = subprocess.run(
        [git, "-C", str(REPO), "cat-file", "-e", f"{PRE_PASS}^{{commit}}"],
        capture_output=True, check=False,
    )
    if probe.returncode != 0:
        pytest.skip(f"commit {PRE_PASS} is not available (shallow clone?)")
    archive = subprocess.run(
        [git, "-C", str(REPO), "archive", "--format=tar", PRE_PASS],
        capture_output=True, check=True,
    )
    dest = tmp_path_factory.mktemp("pre-pass")
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(dest, filter="data")
    return dest


def test_pre_pass_tree_bare_file_line_refs(pre_pass_tree):
    findings = cd.run(pre_pass_tree, ["file-line"])["file-line"]
    refs = [(f.path, f.line, re.search(r"`([^`]+)`", f.message).group(1)) for f in findings]
    assert refs == PRE_PASS_BARE
    stale = [ref for ref, f in zip(refs, findings, strict=True) if "(stale:" in f.message]
    assert stale == PRE_PASS_STALE
