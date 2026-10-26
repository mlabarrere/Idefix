#!/usr/bin/env python
"""Documentation integrity checks. Run in CI; fails the build on a blocking rule.

Each rule guards a failure mode this repository has actually hit:

``links``
    ``docs/README.md`` once indexed 19 documents, 8 of which did not exist.
    Every relative Markdown link and image must resolve.
``anchors``
    Same-file ``#…`` and cross-file ``file.md#…`` links must name a heading
    (GitHub's slug rules) or an explicit ``<a id="…">`` / ``<a name="…">``.
``file-line``
    Commit ``cc258e4`` silently broke 23 bare ``file.py:123`` references.
    Code is cited as ``path/to/file.py::symbol``; bare ``file:line`` and
    unpinned ``#L123`` links are rejected. Each finding says whether the
    reference is also visibly stale (see ``_stale_reason``).
``symbols`` / ``symbol-paths``
    Every ``path.py::symbol`` (or ``::Class.method``) must name a definition
    that exists, verified with ``ast``; ``symbol-paths`` also requires the
    full repository-relative path.
``flags``
    A command quoted in the docs (``python scripts/x.py --flag``) may only
    use flags declared by that script's ``add_argument`` calls (read with
    ``ast``, never by running ``--help``).
``spelling``
    Oxford British English: a deny-list of US and non-Oxford ``-ise`` forms.
``checkpoints``
    Numbers wrapped in a fact marker must equal their source (see
    ``docs/STYLE.md``); in ``docs/ops/quickstart.md`` every count must be
    wrapped.
``alembic-head`` / ``version`` / ``methodology-hash``
    The Alembic head quoted in the docs, the release version, and the
    ``METHODOLOGY.md`` hash recorded in ``CHANGELOG.md`` must match the code.
``numbers``
    Every figure quoted in ``docs/experiments/*.md`` must exist in an artefact
    under ``docs/experiments/results/``.
``archive``
    ``archive/`` holds artefacts from a decommissioned corpus. Documentation
    must not reference them as results.

Every rule is either ``blocking`` (fails the build) or ``warn`` (reported
only). The modes live in ``RULES`` below and the warn-mode list is mirrored in
``docs/STYLE.md``. Standard library only: CI runs it with ``--no-project``.

Usage:
    uv run --no-project python scripts/check_docs.py
    uv run --no-project python scripts/check_docs.py --rule anchors --rule links
    uv run --no-project python scripts/check_docs.py --strict      # warn = blocking
    uv run --no-project python scripts/check_docs.py --summary     # counts per file
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tokenize
import tomllib
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Findings and rule registry                                                   #
# --------------------------------------------------------------------------- #

BLOCKING = "blocking"
WARN = "warn"


@dataclass(frozen=True, order=True)
class Finding:
    path: str  # repository-relative, POSIX separators
    line: int  # 1-based; 0 for a file-level finding
    rule: str
    message: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.message}"


# --------------------------------------------------------------------------- #
# Repository context: which files exist, which Markdown is in scope            #
# --------------------------------------------------------------------------- #

# Vendored agent tooling and dependencies are not documentation.
_EXCLUDED_PARTS = (".agents", "node_modules")
_EXCLUDED_PREFIX = "_bmad"
# The checker's own test fixtures hold deliberate defects.
FIXTURES = "tests/fixtures/"
# Directories never walked when the tree is not a git checkout (a `git archive`
# export, for instance).
_WALK_SKIP = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".claude", ".agents",
}


def _in_scope(rel: str) -> bool:
    if rel.startswith(FIXTURES):
        return False
    parts = rel.split("/")
    if any(p in _EXCLUDED_PARTS or p.startswith(_EXCLUDED_PREFIX) for p in parts[:-1]):
        return False
    return rel.endswith(".md")


def _git_files(root: Path) -> list[str] | None:
    """Tracked files when ``root`` is the top of a git work tree, else None."""
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root:
            return None
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True, check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    names = out.stdout.decode("utf-8", errors="replace").split("\0")
    return sorted(n for n in names if n and (root / n).is_file())


def _walk_files(root: Path) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in _WALK_SKIP and not d.startswith(_EXCLUDED_PREFIX)
        ]
        base = Path(dirpath)
        found += [(base / f).relative_to(root).as_posix() for f in filenames]
    return sorted(found)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


class Context:
    """Everything a rule needs to know about one checkout, computed lazily."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        files = _git_files(self.root)
        self.files: list[str] = files if files is not None else _walk_files(self.root)
        self.file_set = set(self.files)
        self.md_files = [f for f in self.files if _in_scope(f)]
        self._docs: dict[str, Doc] = {}
        self._anchors: dict[str, set[str]] = {}
        self._by_name: dict[str, list[str]] = defaultdict(list)
        for f in self.files:
            if "node_modules/" not in f:
                self._by_name[f.rsplit("/", 1)[-1]].append(f)

    def doc(self, rel: str) -> Doc:
        if rel not in self._docs:
            self._docs[rel] = Doc(rel, _read(self.root / rel))
        return self._docs[rel]

    def anchors(self, rel: str) -> set[str]:
        if rel not in self._anchors:
            self._anchors[rel] = document_anchors(self.doc(rel))
        return self._anchors[rel]

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def resolve_source(self, ref: str) -> tuple[str | None, list[str]]:
        """Resolve a cited path: exact repository-relative, else unique suffix.

        Returns ``(path, candidates)``: ``path`` is None when the reference
        matches no file or several.
        """
        ref = ref.lstrip("./")
        if ref in self.file_set:
            return ref, [ref]
        name = ref.rsplit("/", 1)[-1]
        cands = [f for f in self._by_name.get(name, []) if f.endswith("/" + ref) or f == ref]
        return (cands[0] if len(cands) == 1 else None), cands


# --------------------------------------------------------------------------- #
# Markdown model: fences, front matter, comments, code spans                   #
# --------------------------------------------------------------------------- #

FENCE_OPEN_RE = re.compile(r"^\s*(?:>\s?)*(`{3,}|~{3,})\s*([^`\s]*)(.*)$")
# GFM code span: a run of N backticks, content, the same run of N backticks.
CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
URL_RE = re.compile(r"(?:https?|ftp)://[^\s<>()`\]]+|mailto:[^\s<>()`\]]+|www\.[^\s<>()`\]]+")

PROSE = "prose"
FENCE = "fence"
META = "meta"  # fence delimiters, front matter, HTML comment-only lines


class Doc:
    """One Markdown file split into prose lines and fenced lines."""

    def __init__(self, rel: str, text: str):
        self.rel = rel
        self.text = text
        self.lines = text.split("\n")
        self.kind: list[str] = [PROSE] * len(self.lines)
        self.lang: list[str] = [""] * len(self.lines)  # fence info string
        # Prose with HTML comments removed (multi-line comments included).
        self.clean: list[str] = list(self.lines)
        self._classify()

    def _classify(self) -> None:
        lines = self.lines
        i = 0
        if lines and lines[0].strip() == "---":  # YAML front matter
            for j in range(1, len(lines)):
                if lines[j].strip() in ("---", "..."):
                    for k in range(j + 1):
                        self.kind[k] = META
                    i = j + 1
                    break
        fence: tuple[str, int] | None = None
        lang = ""
        in_comment = False
        for n in range(i, len(lines)):
            line = lines[n]
            if fence is not None:
                m = FENCE_OPEN_RE.match(line)
                if (
                    m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]
                    and not m.group(2) and not m.group(3).strip()
                ):
                    self.kind[n] = META
                    fence = None
                else:
                    self.kind[n] = FENCE
                    self.lang[n] = lang
                continue
            m = FENCE_OPEN_RE.match(line)
            if m and not in_comment and not (m.group(1)[0] == "`" and "`" in m.group(3)):
                fence = (m.group(1)[0], len(m.group(1)))
                lang = m.group(2).lower()
                self.kind[n] = META
                continue
            # Strip HTML comments, which may span lines.
            out, rest = "", line
            while rest:
                if in_comment:
                    end = rest.find("-->")
                    if end < 0:
                        rest = ""
                        break
                    rest = rest[end + 3 :]
                    in_comment = False
                else:
                    start = rest.find("<!--")
                    if start < 0:
                        out += rest
                        break
                    out += rest[:start]
                    rest = rest[start + 4 :]
                    in_comment = True
            self.clean[n] = out
            if not out.strip() and line.strip():
                self.kind[n] = META

    def prose(self) -> Iterator[tuple[int, str]]:
        """``(lineno, text)`` for prose lines, HTML comments removed."""
        for n, kind in enumerate(self.kind):
            if kind == PROSE:
                yield n + 1, self.clean[n]

    def fenced(self) -> Iterator[tuple[int, str, str]]:
        """``(lineno, text, info string)`` for lines inside fenced code blocks."""
        for n, kind in enumerate(self.kind):
            if kind == FENCE:
                yield n + 1, self.lines[n], self.lang[n]


def strip_code_spans(text: str, repl: str = " ") -> str:
    return CODE_SPAN_RE.sub(repl, text)


# --------------------------------------------------------------------------- #
# Headings and GitHub anchors                                                  #
# --------------------------------------------------------------------------- #

ATX_RE = re.compile(r"^\s{0,3}(?:>\s?)*(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
SETEXT_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
EXPLICIT_ANCHOR_RE = re.compile(
    r"<a\b[^>]*?\b(?:id|name)\s*=\s*([\"'])(.+?)\1", re.IGNORECASE
)
IMAGE_RE = re.compile(r"!\[((?:[^\[\]]|\[[^\]]*\])*)\]\([^)]*\)")
INLINE_LINK_RE = re.compile(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\([^)]*\)")
REF_LINK_RE = re.compile(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\[[^\]]*\]")
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
UNDERSCORE_EMPHASIS_RE = re.compile(r"(?<![\w\\])(_{1,3})(?=\S)(.+?)(?<=\S)\1(?!\w)")
_NOT_PARAGRAPH = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|>|\||<|#|`{3}|~{3})")


def heading_text(raw: str) -> str:
    """The text GitHub renders for a heading's inline Markdown."""
    pieces: list[str] = []
    last = 0
    for m in CODE_SPAN_RE.finditer(raw):
        pieces.append(_inline_to_text(raw[last : m.start()]))
        pieces.append(m.group(2).strip() if m.group(2).strip() else m.group(2))
        last = m.end()
    pieces.append(_inline_to_text(raw[last:]))
    return "".join(pieces).strip()


def _inline_to_text(s: str) -> str:
    s = IMAGE_RE.sub(lambda m: m.group(1), s)
    s = INLINE_LINK_RE.sub(lambda m: m.group(1), s)
    s = REF_LINK_RE.sub(lambda m: m.group(1), s)
    s = HTML_TAG_RE.sub("", s)
    s = UNDERSCORE_EMPHASIS_RE.sub(lambda m: m.group(2), s)
    s = re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", s)  # backslash escapes
    return html.unescape(s)


def github_slug(text: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation and emoji, spaces to -.

    Mirrors github-slugger: letters (accented ones included), marks, digits,
    ``_``, ``-`` and spaces survive; everything else, emoji included, is
    removed; each space becomes ``-``. Uniqueness is handled by the caller.
    """
    out = []
    for ch in text.lower():
        if ch in " -_":
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat[0] in "LM" or cat in ("Nd", "Nl", "Pc"):
            out.append(ch)
    return "".join(out).replace(" ", "-")


def headings(doc: Doc) -> Iterator[tuple[int, str]]:
    """``(lineno, rendered heading text)`` for ATX and setext headings."""
    for n, line in enumerate(doc.lines):
        if doc.kind[n] != PROSE:
            continue
        m = ATX_RE.match(doc.clean[n])
        if m:
            yield n + 1, heading_text(m.group(2) or "")
            continue
        if n and SETEXT_RE.match(line) and doc.kind[n - 1] == PROSE:
            first = n - 1
            if not doc.clean[first].strip() or _NOT_PARAGRAPH.match(doc.clean[first]):
                continue
            if ATX_RE.match(doc.clean[first]):
                continue
            while (
                first > 0 and doc.kind[first - 1] == PROSE and doc.clean[first - 1].strip()
                and not _NOT_PARAGRAPH.match(doc.clean[first - 1])
                and not ATX_RE.match(doc.clean[first - 1])
            ):
                first -= 1
            text = " ".join(doc.clean[k].strip() for k in range(first, n))
            yield n + 1, heading_text(text)


def document_anchors(doc: Doc) -> set[str]:
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    for _, text in headings(doc):
        base = github_slug(text)
        slug = base
        while slug in occurrences:  # github-slugger's de-duplication
            occurrences[base] += 1
            slug = f"{base}-{occurrences[base]}"
        occurrences[slug] = 0
        anchors.add(slug)
    for _, line in doc.prose():
        for m in EXPLICIT_ANCHOR_RE.finditer(strip_code_spans(line)):
            anchors.add(m.group(2))
    return anchors


# --------------------------------------------------------------------------- #
# Links: extraction, dead links, anchors                                       #
# --------------------------------------------------------------------------- #

LINK_TARGET_RE = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>]*>|[^\s)]+)(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
# A footnote definition, ``[^id]: text``, is not a link reference definition.
REF_DEF_RE = re.compile(r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*(<[^>]*>|\S+)")
HTML_LINK_RE = re.compile(r"<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def link_targets(doc: Doc) -> Iterator[tuple[int, str]]:
    """``(lineno, raw target)`` for every link and image in the prose."""
    for lineno, line in doc.prose():
        text = strip_code_spans(line)
        for m in LINK_TARGET_RE.finditer(text):
            yield lineno, m.group(1).strip("<>")
        m = REF_DEF_RE.match(text)
        if m:
            yield lineno, m.group(1).strip("<>")
        for m in HTML_LINK_RE.finditer(text):
            yield lineno, m.group(2)


def _split_target(md_rel: str, target: str) -> tuple[str | None, str | None]:
    """Repository-relative path (None = same file) and anchor of a local link."""
    path, _, anchor = target.partition("#")
    path = unquote(path.split("?", 1)[0])
    anchor_or_none = unquote(anchor) if anchor else None
    if not path:
        return None, anchor_or_none
    if path.startswith("/"):
        resolved = Path(path.lstrip("/"))
    else:
        resolved = Path(md_rel).parent / path
    parts: list[str] = []
    for p in resolved.as_posix().split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if not parts:
                return "..", anchor_or_none  # escapes the repository
            parts.pop()
        else:
            parts.append(p)
    return "/".join(parts), anchor_or_none


def _is_local(target: str) -> bool:
    return bool(target) and not SCHEME_RE.match(target) and not target.startswith("//")


def check_links(ctx: Context) -> list[Finding]:
    """Every relative link or image must resolve to a file or directory."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        for lineno, target in link_targets(ctx.doc(md)):
            if not _is_local(target) or target.startswith("#"):
                continue
            path, _ = _split_target(md, target)
            if path is None:
                continue
            if path == ".." or not ctx.exists(path):
                errors.append(Finding(md, lineno, "links", f"dead link -> {target}"))
    return errors


LINE_ANCHOR_RE = re.compile(r"^L\d+(?:C\d+)?(?:-L\d+(?:C\d+)?)?$")


def check_anchors(ctx: Context) -> list[Finding]:
    """Same-file and cross-file anchors must exist in the target document."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        for lineno, target in link_targets(ctx.doc(md)):
            if not _is_local(target):
                continue
            path, anchor = _split_target(md, target)
            if not anchor:
                continue
            dest = md if path is None else path
            if dest == ".." or not dest.endswith(".md") or not (ctx.root / dest).is_file():
                continue  # dead links and line anchors belong to other rules
            if anchor not in ctx.anchors(dest):
                where = "this file" if path is None else dest
                errors.append(
                    Finding(md, lineno, "anchors", f"no anchor #{anchor} in {where} -> {target}")
                )
    return errors


# --------------------------------------------------------------------------- #
# Code references: bare file:line (rejected) and path::symbol (verified)       #
# --------------------------------------------------------------------------- #

_SRC_EXT = (
    r"py|pyi|ipynb|ts|tsx|js|jsx|mjs|cjs|vue|svelte|css|scss|html|sql|sh|bash|ps1|"
    r"toml|ya?ml|json|cfg|ini|rs|go|java|kt|c|h|cc|cpp|hpp|rb|php|r|jl|md"
)
FILE_LINE_RE = re.compile(
    rf"(?<![\w/.\-:])((?:[\w.\-]+/)*[\w\-]+(?:\.[\w\-]+)*\.(?:{_SRC_EXT})):(\d+)(?:[-–](\d+))?(?![\w.])"
)
SYMBOL_RE = re.compile(
    rf"(?<![\w/.\-])((?:[\w.\-]+/)*[\w\-]+(?:\.[\w\-]+)*\.(?:{_SRC_EXT}))::([A-Za-z_][\w.]*)"
)
GITHUB_BLOB_RE = re.compile(r"https?://github\.com/[^/\s]+/[^/\s]+/blob/([^/\s]+)/[^\s#)]+#L\d+")
PINNED_REF_RE = re.compile(r"^[0-9a-f]{7,40}$")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUM_RE = re.compile(r"(?<![\w.])(\d*\.\d+|\d{2,})(?![\w.])")
_CLOSERS = set("()[]{}:,;")


def _code_lines(ctx: Context, rel: str) -> tuple[list[str], set[int]]:
    """Source lines and the 1-based numbers of lines that hold code."""
    text = _read(ctx.root / rel)
    lines = text.split("\n")
    code: set[int] = set()
    if rel.endswith((".py", ".pyi")):
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type in (tokenize.NAME, tokenize.NUMBER) or (
                    tok.type == tokenize.OP and tok.string not in _CLOSERS
                ):
                    code.add(tok.start[0])
                elif tok.type == tokenize.STRING:
                    # A string is code unless it is a docstring-like statement.
                    if tok.line.strip() != tok.string.strip():
                        code.update(range(tok.start[0], tok.end[0] + 1))
        except (tokenize.TokenError, SyntaxError, IndentationError):
            code = set(range(1, len(lines) + 1))
    else:
        comment = ("#", "//", "--", "/*", "*", "<!--", ";")
        for n, line in enumerate(lines, 1):
            s = line.strip()
            if s and not s.startswith(comment) and not set(s) <= _CLOSERS:
                code.add(n)
    return lines, code


def _evidence(line: str) -> tuple[set[str], set[float]]:
    """Identifiers and numbers quoted beside a reference.

    Code spans anywhere on the line; in a table row, also the plain numbers of
    the other cells (a row such as ``| Window | 72 h | edges.py:86 |``).
    """
    idents: set[str] = set()
    numbers: set[float] = set()
    for m in CODE_SPAN_RE.finditer(line):
        span = m.group(2)
        if FILE_LINE_RE.search(span) or SYMBOL_RE.search(span):
            continue
        for tok in _IDENT_RE.findall(span):
            if len(tok) >= 4 or "_" in tok:
                idents.add(tok)
        for num in _NUM_RE.findall(span):
            numbers.add(float(num))
    if line.lstrip().startswith("|"):
        for cell in re.split(r"(?<!\\)\|", line):
            if not FILE_LINE_RE.search(cell):
                numbers.update(float(n) for n in _NUM_RE.findall(strip_code_spans(cell)))
    return idents, numbers


def _stale_reason(ctx: Context, ref: str, start: int, end: int, line: str) -> str | None:
    """Why a ``file:line`` reference visibly points at the wrong place, if it does.

    A heuristic: the file is missing or ambiguous, the range runs past the end
    of the file, the range holds no code (blank lines, comments, docstrings,
    closing brackets), or none of the identifiers and numbers quoted in code
    spans on the same line appear in the range.
    """
    path, cands = ctx.resolve_source(ref)
    if path is None:
        return "no such file" if not cands else f"ambiguous: {len(cands)} files match"
    lines, code = _code_lines(ctx, path)
    if end > len(lines):
        return f"past the end of {path} ({len(lines)} lines)"
    where = f"{path} line {start}" if end == start else f"{path} lines {start}-{end}"
    if not any(n in code for n in range(start, end + 1)):
        return f"{where} hold{'s' if end == start else ''} no code"
    idents, numbers = _evidence(line)
    if idents or numbers:
        target = "\n".join(lines[start - 1 : end])
        words = set(_IDENT_RE.findall(target))
        nums = {float(x) for x in _NUM_RE.findall(target)}
        if not (idents & words) and not (numbers & nums):
            quoted = ", ".join(sorted(idents) + [f"{x:g}" for x in sorted(numbers)])
            return f"none of {quoted} appears at {where}"
    return None


def file_line_refs(doc: Doc) -> Iterator[tuple[int, str, int, int, str]]:
    """``(lineno, ref, start, end, line)`` for every bare file:line in prose."""
    for lineno, line in doc.prose():
        scrubbed = URL_RE.sub(" ", line)
        for m in FILE_LINE_RE.finditer(scrubbed):
            start = int(m.group(2))
            end = int(m.group(3) or start)
            yield lineno, m.group(0), start, max(start, end), line


def check_file_line(ctx: Context) -> list[Finding]:
    """Reject bare ``file:line`` references and unpinned line links."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        doc = ctx.doc(md)
        for lineno, ref, start, end, line in file_line_refs(doc):
            path = FILE_LINE_RE.match(ref).group(1)  # type: ignore[union-attr]
            msg = f"bare file:line reference `{ref}`; cite `path/to/file.py::symbol`"
            stale = _stale_reason(ctx, path, start, end, line)
            if stale:
                msg += f" (stale: {stale})"
            errors.append(Finding(md, lineno, "file-line", msg))
        for lineno, target in link_targets(doc):
            if _is_local(target):
                path, anchor = _split_target(md, target)
                if path and anchor and LINE_ANCHOR_RE.match(anchor) and not path.endswith(".md"):
                    errors.append(
                        Finding(md, lineno, "file-line",
                                f"line link `{target}` drifts with every edit; cite "
                                "`path::symbol`, or a permalink pinned to a commit")
                    )
            else:
                m = GITHUB_BLOB_RE.match(target)
                if m and not PINNED_REF_RE.match(m.group(1)):
                    errors.append(
                        Finding(md, lineno, "file-line",
                                f"line permalink on `{m.group(1)}` is not pinned to a commit "
                                f"-> {target}")
                    )
    return errors


def _python_symbols(tree: ast.Module) -> Callable[[str], bool]:
    def names_in(body: list[ast.stmt]) -> dict[str, ast.AST]:
        found: dict[str, ast.AST] = {}
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found[node.name] = node
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    for n in ast.walk(target):
                        if isinstance(n, ast.Name):
                            found[n.id] = node
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                if isinstance(node.target, ast.Name):
                    found[node.target.id] = node
            elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
                found[node.name.id] = node
            elif isinstance(node, (ast.If, ast.Try, ast.With, ast.AsyncWith)):
                blocks = [node.body, getattr(node, "orelse", []), getattr(node, "finalbody", [])]
                blocks += [h.body for h in getattr(node, "handlers", [])]
                for block in blocks:
                    found.update({k: v for k, v in names_in(block).items() if k not in found})
        return found

    def has(symbol: str) -> bool:
        scope: ast.AST = tree
        for part in symbol.split("."):
            body = getattr(scope, "body", None)
            if not isinstance(body, list):
                return False
            nxt = names_in(body).get(part)
            if nxt is None:
                return False
            scope = nxt
        return True

    return has


def symbol_refs(doc: Doc) -> Iterator[tuple[int, str, str]]:
    """``(lineno, path, symbol)`` for every ``path::symbol`` in prose."""
    for lineno, line in doc.prose():
        for m in SYMBOL_RE.finditer(URL_RE.sub(" ", line)):
            yield lineno, m.group(1), m.group(2).rstrip(".")


def _symbol_checker(ctx: Context, path: str) -> Callable[[str], bool] | None:
    text = _read(ctx.root / path)
    if path.endswith((".py", ".pyi")):
        try:
            return _python_symbols(ast.parse(text))
        except SyntaxError:
            return None
    return lambda symbol: re.search(rf"\b{re.escape(symbol.split('.')[-1])}\b", text) is not None


def check_symbols(ctx: Context) -> list[Finding]:
    """Every ``path::symbol`` must name a definition that exists."""
    errors: list[Finding] = []
    cache: dict[str, Callable[[str], bool] | None] = {}
    for md in ctx.md_files:
        for lineno, ref_path, symbol in symbol_refs(ctx.doc(md)):
            path, cands = ctx.resolve_source(ref_path)
            if path is None:
                why = "no such file" if not cands else f"ambiguous path: {', '.join(cands)}"
                errors.append(Finding(md, lineno, "symbols", f"`{ref_path}::{symbol}`: {why}"))
                continue
            if path not in cache:
                cache[path] = _symbol_checker(ctx, path)
            has = cache[path]
            if has is None:
                errors.append(Finding(md, lineno, "symbols", f"`{path}` does not parse"))
            elif not has(symbol):
                errors.append(
                    Finding(md, lineno, "symbols", f"`{ref_path}::{symbol}`: no `{symbol}` "
                            f"defined in {path}")
                )
    return errors


def check_symbol_paths(ctx: Context) -> list[Finding]:
    """``path::symbol`` must use the full repository-relative path."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        for lineno, ref_path, symbol in symbol_refs(ctx.doc(md)):
            path, _ = ctx.resolve_source(ref_path)
            if path is not None and path != ref_path:
                errors.append(
                    Finding(md, lineno, "symbol-paths",
                            f"`{ref_path}::{symbol}`: write the full path `{path}::{symbol}`")
                )
    return errors


# --------------------------------------------------------------------------- #
# Command-line flags quoted in the docs                                        #
# --------------------------------------------------------------------------- #

COMMAND_RE = re.compile(
    r"(?:^|[\s(`'\"])(?:python3?|py)(?:\s+-[A-Za-z]+(?:\s+(?!-)\S+)?)*?\s+"
    r"(?:-m\s+([\w.]+)|([\w./\\-]+\.py))(?=\s|$|[`'\")])(.*)"
)
_SHELL_STOP_RE = re.compile(r"\s(?:&&|\|\||\||;|#|>|2>|<)\s|[`]")
_FLAG_RE = re.compile(r"^(--?[A-Za-z][\w-]*)")


def _argparse_calls(node: ast.AST) -> tuple[set[str], bool, bool]:
    """``(options, uses_argparse, add_help)`` from the calls under ``node``."""
    options: set[str] = set()
    uses_argparse = False
    add_help = True
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        name = call.func.attr if isinstance(call.func, ast.Attribute) else (
            call.func.id if isinstance(call.func, ast.Name) else ""
        )
        if name == "ArgumentParser":
            uses_argparse = True
            for kw in call.keywords:
                if kw.arg == "add_help" and isinstance(kw.value, ast.Constant):
                    add_help = bool(kw.value.value)
        elif name == "add_argument":
            uses_argparse = True
            for arg in call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("-"):
                        options.add(arg.value)
    return options, uses_argparse, add_help


def _script_options(ctx: Context, rel: str) -> tuple[set[str], bool]:
    """Option strings declared by ``add_argument`` and whether argparse is used.

    Follows one level of helpers imported from the repository, such as
    ``src/missions/loader.py::add_mission_arg``, which adds ``--mission``.
    """
    try:
        tree = ast.parse(_read(ctx.root / rel))
    except SyntaxError:
        return set(), False
    options, uses_argparse, add_help = _argparse_calls(tree)
    imported: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            module = node.module.replace(".", "/") + ".py"
            if module in ctx.file_set:
                for alias in node.names:
                    imported[alias.asname or alias.name] = (module, alias.name)
    called = {
        n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in imported
    }
    for local in sorted(called):
        module, name = imported[local]
        try:
            mod_tree = ast.parse(_read(ctx.root / module))
        except SyntaxError:
            continue
        for fn in mod_tree.body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == name:
                opts, uses, helps = _argparse_calls(fn)
                options |= opts
                uses_argparse = uses_argparse or uses
                add_help = add_help and helps
    if uses_argparse and add_help:
        options |= {"-h", "--help"}
    return options, uses_argparse


def command_lines(doc: Doc) -> Iterator[tuple[int, str]]:
    """Candidate shell commands: fenced lines and inline code spans."""
    pending = ""
    pending_line = 0
    for lineno, line, lang in doc.fenced():
        if pending:
            line = pending + " " + line.strip()
            lineno = pending_line
        continuation = "`" if lang in ("powershell", "pwsh", "ps1") else "\\"
        if line.rstrip().endswith(continuation):
            pending, pending_line = line.rstrip()[:-1], lineno
            continue
        pending = ""
        yield lineno, line
    for lineno, line in doc.prose():
        for m in CODE_SPAN_RE.finditer(line):
            yield lineno, m.group(2)


def check_flags(ctx: Context) -> list[Finding]:
    """Flags in quoted commands must exist in the script's ``add_argument`` calls."""
    errors: list[Finding] = []
    cache: dict[str, tuple[set[str], bool]] = {}
    for md in ctx.md_files:
        for lineno, line in command_lines(ctx.doc(md)):
            for m in COMMAND_RE.finditer(line):
                if m.group(1):
                    script = m.group(1).replace(".", "/") + ".py"
                    if script not in ctx.file_set:
                        continue  # an installed module (pytest, pip, ...)
                else:
                    script = m.group(2).replace("\\", "/").removeprefix("./")
                if script not in ctx.file_set:
                    if not script.startswith(("scripts/", "src/")):
                        continue  # a path relative to some other directory
                    errors.append(
                        Finding(md, lineno, "flags",
                                f"command runs `{script}`, which does not exist")
                    )
                    continue
                if script not in cache:
                    cache[script] = _script_options(ctx, script)
                options, uses_argparse = cache[script]
                args = _SHELL_STOP_RE.split(" " + m.group(3) + " ", maxsplit=1)[0]
                for token in args.split():
                    flag_m = _FLAG_RE.match(token.strip("[]()'\",|"))
                    if not flag_m:
                        continue
                    flag = flag_m.group(1)
                    if flag in options:
                        continue
                    if not uses_argparse:
                        errors.append(
                            Finding(md, lineno, "flags",
                                    f"`{script}` has no argparse parser; `{flag}` cannot be "
                                    "verified (and is probably ignored)")
                        )
                        continue
                    near = sorted(o for o in options if o.startswith(flag) and o != flag)
                    hint = f"; write it in full: {', '.join(near)}" if near else ""
                    errors.append(
                        Finding(md, lineno, "flags",
                                f"`{script}` declares no `{flag}` option{hint}")
                    )
    return errors


# --------------------------------------------------------------------------- #
# Spelling: Oxford British English                                             #
# --------------------------------------------------------------------------- #

# US form -> Oxford British form. Inflections are listed explicitly so that the
# rule never guesses: anything absent here is allowed.
_US_TO_UK = {
    "color": "colour", "colors": "colours", "colored": "coloured", "coloring": "colouring",
    "colorful": "colourful", "colorless": "colourless", "colorize": "colourize",
    "behavior": "behaviour", "behaviors": "behaviours", "behavioral": "behavioural",
    "analyze": "analyse", "analyzed": "analysed", "analyzes": "analyses",
    "analyzing": "analysing", "analyzer": "analyser", "analyzers": "analysers",
    "catalyze": "catalyse", "catalyzed": "catalysed", "paralyze": "paralyse",
    "paralyzed": "paralysed",
    "modeling": "modelling", "modeled": "modelled", "modeler": "modeller",
    "modelers": "modellers",
    "labeling": "labelling", "labeled": "labelled", "labeler": "labeller",
    "labelers": "labellers",
    "canceled": "cancelled", "canceling": "cancelling", "traveled": "travelled",
    "traveling": "travelling", "traveler": "traveller", "travelers": "travellers",
    "signaled": "signalled", "signaling": "signalling", "leveled": "levelled",
    "leveling": "levelling", "totaled": "totalled", "totaling": "totalling",
    "fueled": "fuelled", "fueling": "fuelling", "funneled": "funnelled",
    "tunneled": "tunnelled", "channeled": "channelled", "channeling": "channelling",
    "counseling": "counselling", "marshaled": "marshalled", "unraveled": "unravelled",
    "catalog": "catalogue", "catalogs": "catalogues", "cataloged": "catalogued",
    "cataloging": "cataloguing",
    "center": "centre", "centers": "centres", "centered": "centred", "centering": "centring",
    "defense": "defence", "defenses": "defences", "offense": "offence",
    "offenses": "offences", "pretense": "pretence",
    "artifact": "artefact", "artifacts": "artefacts",
    "judgment": "judgement", "judgments": "judgements",
    "acknowledgment": "acknowledgement", "acknowledgments": "acknowledgements",
    "toward": "towards", "afterward": "afterwards",
    "gray": "grey", "grays": "greys", "grayed": "greyed", "grayscale": "greyscale",
    "grayish": "greyish",
    "favor": "favour", "favors": "favours", "favored": "favoured", "favoring": "favouring",
    "favorable": "favourable", "favorite": "favourite", "favorites": "favourites",
    "honor": "honour", "honors": "honours", "honored": "honoured", "labor": "labour",
    "neighbor": "neighbour", "neighbors": "neighbours", "neighboring": "neighbouring",
    "neighborhood": "neighbourhood", "neighborhoods": "neighbourhoods",
    "flavor": "flavour", "flavors": "flavours", "humor": "humour", "rumor": "rumour",
    "rumors": "rumours", "endeavor": "endeavour", "endeavors": "endeavours",
    "harbor": "harbour", "vapor": "vapour", "armor": "armour", "odor": "odour",
    "vigor": "vigour", "rigor": "rigour", "candor": "candour", "clamor": "clamour",
    "demeanor": "demeanour", "fervor": "fervour", "savior": "saviour", "tumor": "tumour",
    "valor": "valour",
    "fulfill": "fulfil", "fulfills": "fulfils", "fulfillment": "fulfilment",
    "enrollment": "enrolment", "installment": "instalment", "skillful": "skilful",
    "willful": "wilful",
    "aging": "ageing",
    "skeptic": "sceptic", "skeptics": "sceptics", "skeptical": "sceptical",
    "skepticism": "scepticism",
    "fiber": "fibre", "fibers": "fibres", "liter": "litre", "liters": "litres",
    "theater": "theatre", "meager": "meagre", "somber": "sombre", "caliber": "calibre",
    "specter": "spectre", "maneuver": "manoeuvre", "maneuvers": "manoeuvres",
    "mold": "mould", "molds": "moulds", "smolder": "smoulder", "plow": "plough",
    "practiced": "practised", "practicing": "practising",
}

# Non-Oxford -ise stems. Oxford spelling keeps -ize for these (but analyse,
# paralyse, and the -ise words that never take -ize: advise, comprise, ...).
_ISE_STEMS = (
    "organis", "reorganis", "disorganis", "prioritis", "deprioritis", "recognis", "normalis",
    "denormalis", "optimis", "realis", "summaris", "categoris", "minimis", "maximis",
    "emphasis", "characteris", "standardis", "utilis", "serialis", "deserialis", "tokenis",
    "finalis", "specialis", "generalis", "visualis", "initialis", "parametris", "parameteris",
    "randomis", "synchronis", "customis", "authoris", "criticis", "apologis", "memoris",
    "sanitis", "materialis", "operationalis", "localis", "centralis", "decentralis",
    "legitimis", "stabilis", "destabilis", "harmonis", "neutralis", "vectoris", "digitis",
    "capitalis", "mobilis", "polaris", "democratis", "familiaris", "jeopardis", "modernis",
    "penalis", "publicis", "regularis", "scrutinis", "socialis", "stigmatis", "subsidis",
    "symbolis", "systematis", "theoris", "trivialis", "anonymis", "pseudonymis", "amortis",
    "contextualis", "conceptualis", "dramatis", "economis", "equalis", "formalis",
    "globalis", "homogenis", "hypothesis", "idealis", "industrialis", "itemis",
    "marginalis", "mechanis", "monetis", "monopolis", "nationalis", "naturalis",
    "personalis", "plagiaris", "popularis", "privatis", "radicalis", "rationalis",
    "sensitis", "desensitis", "sterilis", "sympathis", "terroris", "weaponis",
    "compartmentalis", "dehumanis", "demonis", "lemmatis", "binaris", "discretis",
    "quantis", "vocalis", "verbalis", "fantasis", "galvanis", "ostracis", "patronis",
    "antagonis", "agonis", "mesmeris", "pasteuris", "visualis", "templatis", "containeris",
)
# No "-iser": it would catch French infinitives (utiliser, organiser) quoted in prose.
_ISE_SUFFIXES = ("e", "ed", "es", "ing", "ation", "ations", "ational", "able")
for _stem in _ISE_STEMS:
    for _suffix in _ISE_SUFFIXES:
        _US_TO_UK.setdefault(_stem + _suffix, _stem[:-1] + "z" + _suffix)

# Words or phrases allowed in a given file ("*" = everywhere): published
# titles, proper names, code identifiers written in prose. A file can also
# carry its own list in an HTML comment: <!-- spelling-allow: Word, A Phrase -->
SPELLING_ALLOW: dict[str, tuple[str, ...]] = {
    "*": (),
    # Published paper titles keep their original (US) spelling.
    "docs/reference/references.md": ("behavior",),
}
SPELLING_ALLOW_RE = re.compile(r"<!--\s*spelling-allow:(.*?)-->", re.IGNORECASE | re.DOTALL)
_WORD_RE = re.compile(r"[A-Za-z]+")
# Tokens that are code or paths even outside backticks.
_CODEISH_RE = re.compile(r"\S*[_/\\]\S*|\S+\.[A-Za-z]\w*\b|\b\w+\(\)|--?[\w-]+|#[\w-]+|\[!\w+\]")
_LINK_DEST_RE = re.compile(r"\]\([^)]*\)|\]\[[^\]]*\]|^\s{0,3}\[[^\]]+\]:.*$")


def _allowed_phrases(ctx: Context, md: str) -> list[str]:
    allowed = list(SPELLING_ALLOW.get("*", ())) + list(SPELLING_ALLOW.get(md, ()))
    for m in SPELLING_ALLOW_RE.finditer(_markers_text(ctx.doc(md))):
        allowed += [w.strip() for w in m.group(1).split(",") if w.strip()]
    return allowed


def check_spelling(ctx: Context) -> list[Finding]:
    """Deny-listed US and non-Oxford -ise spellings in prose."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        allowed = _allowed_phrases(ctx, md)
        words_ok = {a.lower() for a in allowed if " " not in a}
        phrases = [a for a in allowed if " " in a]
        for lineno, line in ctx.doc(md).prose():
            text = strip_code_spans(line)
            text = _LINK_DEST_RE.sub(" ", text)
            text = URL_RE.sub(" ", text)
            text = HTML_TAG_RE.sub(" ", text)
            for phrase in phrases:
                text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)
            text = _CODEISH_RE.sub(" ", text)
            for word in _WORD_RE.findall(text):
                low = word.lower()
                if low in _US_TO_UK and low not in words_ok:
                    errors.append(
                        Finding(md, lineno, "spelling",
                                f"'{word}' -> '{_match_case(word, _US_TO_UK[low])}'")
                    )
    return errors


def _match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# --------------------------------------------------------------------------- #
# Facts: checkpoints, Alembic head, version, METHODOLOGY hash                  #
# --------------------------------------------------------------------------- #

QUICKSTART = "docs/ops/quickstart.md"
MANIFEST = "dataset/manifest.json"
FACT_RE = re.compile(r"<!--\s*fact:([\w.\-]+)\s*-->(.*?)<!--\s*/fact\s*-->", re.DOTALL)
# A count: digits grouped by thousands separators, or four digits and more.
COUNT_RE = re.compile(
    r"(?<![\w.,])\d{1,3}(?:[,\u202f\u00a0]\d{3})+(?![\w.,]\d)|(?<![\w.,])\d{4,}(?![\w.,]\d)"
)


def _norm_value(raw: str) -> str:
    v = re.sub(r"[`*_\s,\u202f\u00a0]", "", raw)
    return v


def alembic_head(ctx: Context) -> tuple[str | None, str]:
    """The single Alembic head revision, read from ``alembic/versions`` with ``ast``."""
    revisions: dict[str, set[str]] = {}
    for rel in ctx.files:
        if not (rel.startswith("alembic/versions/") and rel.endswith(".py")):
            continue
        try:
            tree = ast.parse(_read(ctx.root / rel))
        except SyntaxError:
            continue
        rev, down = None, set()
        for node in tree.body:
            target = value = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            elif isinstance(node, ast.AnnAssign):
                target, value = node.target, node.value
            if not isinstance(target, ast.Name) or value is None:
                continue
            if target.id == "revision" and isinstance(value, ast.Constant):
                rev = str(value.value)
            elif target.id == "down_revision":
                for c in ast.walk(value):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        down.add(c.value)
        if rev:
            revisions[rev] = down
    if not revisions:
        return None, "no revision found under alembic/versions"
    referenced = set().union(*revisions.values())
    heads = sorted(set(revisions) - referenced)
    if len(heads) != 1:
        return None, f"alembic/versions has {len(heads)} heads: {', '.join(heads)}"
    return heads[0], ""


def project_version(ctx: Context) -> str | None:
    try:
        data = tomllib.loads(_read(ctx.root / "pyproject.toml"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data.get("project", {}).get("version")


def methodology_hash(ctx: Context) -> str | None:
    """First 8 hex digits of SHA-256 of METHODOLOGY.md, CRLF normalized to LF.

    Mirrors ``src/shared/dossier.py::get_methodology_version_hash``, plus the
    line-ending normalization that makes the hash platform-independent.
    """
    path = ctx.root / "METHODOLOGY.md"
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:8]


def fact_value(ctx: Context, key: str) -> tuple[str | None, str]:
    """Resolve a fact key to its source value. Returns ``(value, error)``."""
    if key.startswith("manifest."):
        try:
            node = json.loads(_read(ctx.root / MANIFEST))
        except (OSError, json.JSONDecodeError) as exc:
            return None, f"cannot read {MANIFEST}: {exc}"
        for part in key.removeprefix("manifest.").split("."):
            if not isinstance(node, dict) or part not in node:
                return None, f"{MANIFEST} has no `{key.removeprefix('manifest.')}`"
            node = node[part]
        return str(node), ""
    if key == "alembic.head":
        head, err = alembic_head(ctx)
        return head, err
    if key == "version":
        v = project_version(ctx)
        return v, "" if v else "pyproject.toml has no [project].version"
    if key == "methodology.hash":
        h = methodology_hash(ctx)
        return h, "" if h else "METHODOLOGY.md is missing"
    return None, f"unknown fact key `{key}` (see docs/STYLE.md)"


def _markers_text(doc: Doc) -> str:
    """The document with fenced blocks and code spans blanked out.

    An HTML comment inside code renders literally, so it is not a marker.
    Blanking keeps every offset, hence every line number, unchanged.
    """
    out = []
    for n, line in enumerate(doc.lines):
        if doc.kind[n] == FENCE or FENCE_OPEN_RE.match(line):
            out.append(" " * len(line))
        else:
            out.append(CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line))
    return "\n".join(out)


def check_checkpoints(ctx: Context) -> list[Finding]:
    """Fact markers match their source; quickstart counts are all marked."""
    errors: list[Finding] = []
    for md in ctx.md_files:
        text = _markers_text(ctx.doc(md))
        for m in FACT_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            expected, err = fact_value(ctx, m.group(1))
            if expected is None:
                errors.append(Finding(md, lineno, "checkpoints", err))
            elif _norm_value(m.group(2)) != _norm_value(expected):
                errors.append(
                    Finding(md, lineno, "checkpoints",
                            f"fact `{m.group(1)}` says {m.group(2).strip()!r}, source says "
                            f"{expected!r}")
                )
    if QUICKSTART in ctx.md_files:
        doc = ctx.doc(QUICKSTART)
        counts: set[str] = set()
        try:
            manifest = json.loads(_read(ctx.root / MANIFEST))
            counts = {str(v) for v in manifest.get("row_counts", {}).values() if int(v) >= 10}
        except (OSError, json.JSONDecodeError, ValueError, AttributeError):
            pass
        # Blank out marked values, keeping newlines so line numbers hold.
        unmarked = FACT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), doc.text)
        unmarked_lines = unmarked.split("\n")
        for lineno, _ in doc.prose():
            line = strip_code_spans(URL_RE.sub(" ", unmarked_lines[lineno - 1]))
            for m in COUNT_RE.finditer(line):
                value = _norm_value(m.group(0))
                if "," in m.group(0) or value in counts:
                    errors.append(
                        Finding(QUICKSTART, lineno, "checkpoints",
                                f"count {m.group(0)!r} has no fact marker; wrap it as "
                                "<!-- fact:manifest.row_counts.TABLE -->N<!-- /fact -->")
                    )
    return errors


HEAD_CLAIM_RE = re.compile(
    r"\bhead\b[^`\n\d]{0,20}`?(\d{4})`?|`?(\d{4})`?\s*\(head\)", re.IGNORECASE
)


def check_alembic_head(ctx: Context) -> list[Finding]:
    """Every 'head 0008' / '0008 (head)' in the docs names the real head."""
    head, err = alembic_head(ctx)
    if head is None:
        return [Finding("alembic/versions", 0, "alembic-head", err)]
    revisions = {
        m.group(1) for f in ctx.files
        if (m := re.match(r"alembic/versions/(\d{4})_", f))
    }
    errors: list[Finding] = []
    for md in ctx.md_files:
        doc = ctx.doc(md)
        lines = [(n, line) for n, line in doc.prose()]
        lines += [(n, line) for n, line, _ in doc.fenced()]
        for lineno, line in lines:
            for m in HEAD_CLAIM_RE.finditer(line):
                quoted = m.group(1) or m.group(2)
                if re.fullmatch(r"(19|20)\d{2}", quoted) and quoted not in revisions:
                    continue  # 'the head of 2026 ...' is a year, not a revision
                if quoted != head:
                    errors.append(
                        Finding(md, lineno, "alembic-head",
                                f"quotes Alembic head {quoted}; alembic/versions head is {head}")
                    )
    return errors


CFF_VERSION_RE = re.compile(r"^version:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
METHODOLOGY_VERSION_RE = re.compile(r"^\|\s*Version\s*\|\s*`?([^|`\s]+)`?\s*\|", re.MULTILINE)


def check_version(ctx: Context) -> list[Finding]:
    """One version: pyproject.toml = CITATION.cff = METHODOLOGY.md = a CHANGELOG release."""
    version = project_version(ctx)
    if not version:
        return [Finding("pyproject.toml", 0, "version", "no [project].version")]
    errors: list[Finding] = []
    cff = ctx.root / "CITATION.cff"
    if cff.is_file():
        m = CFF_VERSION_RE.search(_read(cff))
        if not m:
            errors.append(Finding("CITATION.cff", 0, "version", "no top-level `version:`"))
        elif m.group(1) != version:
            errors.append(
                Finding("CITATION.cff", 0, "version",
                        f"version {m.group(1)} != pyproject.toml {version}")
            )
    meth = ctx.root / "METHODOLOGY.md"
    if meth.is_file():
        m = METHODOLOGY_VERSION_RE.search(_read(meth))
        if m and m.group(1) != version:
            errors.append(
                Finding("METHODOLOGY.md", 0, "version",
                        f"version {m.group(1)} != pyproject.toml {version}")
            )
    changelog = ctx.root / "CHANGELOG.md"
    if changelog.is_file():
        release = re.compile(rf"^##\s+\[?v?{re.escape(version)}\]?(?:\s|$)", re.MULTILINE)
        if not release.search(_read(changelog)):
            errors.append(
                Finding("CHANGELOG.md", 0, "version", f"no `## [{version}]` release heading")
            )
    return errors


# "METHODOLOGY.md hash `f8486e18`", "`METHODOLOGY.md` hash: f8486e18",
# "methodology_version_hash `f8486e18`": the word METHODOLOGY, then "hash", then
# eight hexadecimal digits, on one line.
CHANGELOG_HASH_RE = re.compile(
    r"METHODOLOGY[\w.]*[^\n]{0,40}?hash\b[^\n]{0,20}?(?<![0-9a-z])([0-9a-f]{8})(?![0-9a-z])",
    re.IGNORECASE,
)


def check_methodology_hash(ctx: Context) -> list[Finding]:
    """The newest METHODOLOGY.md hash recorded in CHANGELOG.md is the current one."""
    current = methodology_hash(ctx)
    changelog = ctx.root / "CHANGELOG.md"
    if current is None or not changelog.is_file():
        return []
    text = _read(changelog)
    found: list[tuple[int, str]] = []
    for m in CHANGELOG_HASH_RE.finditer(text):
        found.append((m.start(), m.group(1)))
    for m in FACT_RE.finditer(text):
        if m.group(1) == "methodology.hash":
            found.append((m.start(), _norm_value(m.group(2))))
    if not found:
        return [
            Finding("CHANGELOG.md", 0, "methodology-hash",
                    f"records no METHODOLOGY.md hash; the current one is `{current}`")
        ]
    pos, recorded = min(found)
    if recorded.lower() != current:
        lineno = text.count("\n", 0, pos) + 1
        return [
            Finding("CHANGELOG.md", lineno, "methodology-hash",
                    f"newest recorded METHODOLOGY.md hash `{recorded}` != current `{current}`")
        ]
    return []


# --------------------------------------------------------------------------- #
# Legacy rules: unbacked numbers, archive citations                            #
# --------------------------------------------------------------------------- #

# Numbers that constitute an empirical claim: decimals, and integers of 3+
# digits. Small integers are section numbers, counts of families, thresholds
# quoted from code -- not results.
# Thousands separators (1,240) are part of the number, per docs/STYLE.md.
NUMBER_RE = re.compile(
    r"(?<![\w.,\-/])(\d{1,3}(?:,\d{3})+(?!\d)|\d+\.\d+|\d{3,})(?![\w.\-/%]|,\d)"
)

# Figures that are part of the method (constants read off the code), not
# results. Documented in the method chapters, so they are allowed in prose.
ALLOWED = {
    # thresholds and weights defined in source
    "0.15", "0.30", "0.25", "0.20", "0.10", "0.40", "0.60", "0.70", "0.50",
    "0.55", "0.35", "0.45", "0.65", "0.80", "0.90", "0.75", "1.00", "0.05",
    "0.715", "0.693", "0.85", "1.6", "3.0", "4.0", "0.0", "1.0",
    "0.0001", "0.9999", "384", "100", "200", "1000", "1312", "3600", "500",
}
# Section cross-references (§5.1, §3.8) are navigation, not measurements.
SECTION_REF_RE = re.compile(r"§\s*\d+(\.\d+)*")


def check_numbers(ctx: Context) -> list[Finding]:
    """Numbers quoted in experiment prose must appear in a results artefact."""
    known: set[str] = set()
    results = ctx.root / "docs" / "experiments" / "results"
    for artefact in sorted(results.glob("*.json")):
        rel = artefact.relative_to(ctx.root).as_posix()
        try:
            blob = json.loads(_read(artefact))
        except json.JSONDecodeError:
            return [Finding(rel, 0, "numbers", "invalid JSON")]
        known.update(n.replace(",", "") for n in NUMBER_RE.findall(json.dumps(blob)))

    errors: list[Finding] = []
    for md in ctx.md_files:
        if not re.fullmatch(r"docs/experiments/[^/]+\.md", md):
            continue
        for lineno, line in ctx.doc(md).prose():
            # Table rows enumerate parameters and sweep ranges, not results.
            if line.lstrip().startswith("|"):
                continue
            prose = SECTION_REF_RE.sub(" ", strip_code_spans(line))
            for num in sorted(set(NUMBER_RE.findall(prose))):
                if num in ALLOWED or num.replace(",", "") in known:
                    continue
                if re.fullmatch(r"(19|20)\d{2}", num):  # years in citations
                    continue
                errors.append(
                    Finding(md, lineno, "numbers",
                            f"number {num!r} has no artefact under docs/experiments/results/")
                )
    return errors


def check_archive(ctx: Context) -> list[Finding]:
    """docs/ may point at archive/ only to say 'do not cite'."""
    errors: list[Finding] = []
    disclaimers = ("do not cite", "may not be cited", "quarantin", "decommission")
    for md in ctx.md_files:
        if not md.startswith("docs/"):
            continue
        lines = ctx.doc(md).lines
        for i, line in enumerate(lines):
            if "archive/" not in line:
                continue
            # Prose wraps, so accept a disclaimer anywhere in the sentence
            # surrounding the reference.
            window = " ".join(lines[max(0, i - 2) : i + 3]).lower()
            if any(d in window for d in disclaimers):
                continue
            errors.append(
                Finding(md, i + 1, "archive",
                        f"references archive/ without a do-not-cite disclaimer -> "
                        f"{line.strip()[:80]}")
            )
    return errors


# --------------------------------------------------------------------------- #
# Registry and CLI                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Rule:
    mode: str
    check: Callable[[Context], list[Finding]]
    summary: str


# Warn-mode rules are listed in docs/STYLE.md ("Rules in warn mode"); keep the
# two in step. PR 5 flips every rule to blocking.
RULES: dict[str, Rule] = {
    "links": Rule(BLOCKING, check_links, "relative links and images resolve"),
    "anchors": Rule(WARN, check_anchors, "#anchors exist (GitHub slugs, <a id>)"),
    "file-line": Rule(WARN, check_file_line, "no bare file:line or unpinned #L links"),
    "symbols": Rule(WARN, check_symbols, "path::symbol names a real definition"),
    "symbol-paths": Rule(WARN, check_symbol_paths, "path::symbol uses the full path"),
    "flags": Rule(WARN, check_flags, "quoted script flags exist in add_argument"),
    "spelling": Rule(WARN, check_spelling, "Oxford British spelling"),
    "checkpoints": Rule(BLOCKING, check_checkpoints, "fact markers match their source"),
    "alembic-head": Rule(BLOCKING, check_alembic_head, "quoted Alembic head is the head"),
    "version": Rule(WARN, check_version, "one version across the release files"),
    "methodology-hash": Rule(WARN, check_methodology_hash, "CHANGELOG records the hash"),
    "numbers": Rule(BLOCKING, check_numbers, "experiment figures have an artefact"),
    "archive": Rule(BLOCKING, check_archive, "archive/ is never cited as a result"),
}


def run(root: Path = ROOT, rules: list[str] | None = None) -> dict[str, list[Finding]]:
    """Run the selected rules (default: all) and return findings per rule."""
    ctx = Context(root)
    return {name: sorted(set(RULES[name].check(ctx))) for name in (rules or list(RULES))}


def _summary(results: dict[str, list[Finding]]) -> None:
    for name, findings in results.items():
        if not findings:
            continue
        print(f"\n{name} [{RULES[name].mode}]: {len(findings)}")
        for path, count in sorted(Counter(f.path for f in findings).items()):
            print(f"  {count:5d}  {path}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Documentation integrity checks.")
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root to check")
    ap.add_argument("--rule", action="append", choices=sorted(RULES), help="run only this rule")
    ap.add_argument("--strict", action="store_true", help="treat warn-mode rules as blocking")
    ap.add_argument("--summary", action="store_true", help="also print counts per rule and file")
    ap.add_argument("--list-rules", action="store_true", help="list the rules and their modes")
    args = ap.parse_args(argv)

    if args.list_rules:
        for name, rule in RULES.items():
            print(f"{name:<17} {rule.mode:<9} {rule.summary}")
        return 0

    results = run(args.root, args.rule)
    failed = False
    for name, findings in results.items():
        mode = RULES[name].mode
        blocking = mode == BLOCKING or args.strict
        if not findings:
            print(f"ok   - {name} [{mode}]")
            continue
        failed = failed or blocking
        tag = "FAIL" if blocking else "warn"
        stream = sys.stderr if blocking else sys.stdout
        print(f"\n{tag} - {name} [{mode}] ({len(findings)}):", file=stream)
        for f in findings:
            print(f"  {f}", file=stream)
    if args.summary:
        _summary(results)
    if failed:
        print("\nDocumentation checks failed.", file=sys.stderr)
        return 1
    print("\nAll blocking documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
