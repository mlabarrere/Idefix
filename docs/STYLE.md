# Documentation style guide

This is the house style for every Markdown file in the repository. Part of it
is enforced by `scripts/check_docs.py`, which runs in the `docs` job of
`.github/workflows/ci.yml`; the rest is for authors and reviewers. When a
document and this guide disagree, fix the document.

## 🧭 Overview

The guide covers spelling and punctuation, names, headings and emoji, alerts,
code blocks and commands, code references, numbers and facts, and which
document owns which topic. The last section lists the checks that enforce it.

Run the checks from the repository root before opening a pull request:

```bash
uv run --no-project python scripts/check_docs.py
```

`--rule anchors` runs one rule (repeat the option for several), `--strict`
treats warn-mode rules as blocking, `--summary` adds counts per rule and file,
and `--list-rules` prints every rule with its mode. The checker needs only the
Python standard library.

## 📝 Spelling and punctuation

Write Oxford British English: British spelling, with `-ize` where Oxford uses
it.

| Write | Not |
|---|---|
| `organize`, `organization`, `prioritize`, `recognize`, `normalize`, `optimize`, `realize` | `organise`, `organisation`, `prioritise`, `recognise`, `normalise`, `optimise`, `realise` |
| `analyse`, `analysing`, `paralyse` | `analyze`, `analyzing`, `paralyze` |
| `behaviour`, `colour`, `favour` | `behavior`, `color`, `favor` |
| `modelling`, `labelling`, `cancelled` | `modeling`, `labeling`, `canceled` |
| `artefact`, `catalogue`, `centre`, `defence` | `artifact`, `catalog`, `center`, `defense` |
| `judgement`, `towards`, `grey` | `judgment`, `toward`, `gray` |
| `licence` (noun), `license` (verb) | `license` (noun) |

Some words take `-ise` in every spelling and stay as they are: advise,
comprise, compromise, devise, exercise, revise, supervise, and surprise.

Punctuation:

- **Serial comma.** 'Clone, install, and run', never 'clone, install and run'.
- **Em dash, unspaced.** 'One command—no credentials—sets it up.' Keep dashes
  out of headings: GitHub drops them from the anchor.
- **Quotation marks.** Single quotes, with double quotes inside a quotation:
  'the "critical" label'.
- **En dash** for joint names and ranges: Benjamini–Hochberg, Erdős–Rényi,
  pages 867–891.
- **Numbers.** Commas as thousands separators in prose (12,500). Never in code,
  years, ports, or version numbers.
- **`ID`** and **`IDs`** in prose, never 'id' or 'Id'. Code identifiers keep
  their own spelling.
- **Acronyms** are defined on first use in each document: 'false discovery rate
  (FDR)'.

The `spelling` rule flags a fixed deny-list of US forms and non-Oxford `-ise`
forms in prose. It skips code spans, fenced blocks, URLs, link targets, and
words that look like code (`snake_case`, `dotted.names`, `--flags`). A file
can allow a word or a phrase, such as a published title in US spelling, with
an HTML comment anywhere in the file:

```markdown
<!-- spelling-allow: Coordinated Behavior, color -->
```

Allow-lists shared by several files live in `SPELLING_ALLOW` in
`scripts/check_docs.py`.

## 📝 Names and terms

| Write | Not |
|---|---|
| Node.js | `Node`, `NodeJS`, `node.js` |
| PostgreSQL | `Postgres`, `postgres`, `PostGreSQL` |
| Tailwind CSS | `Tailwind`, `TailwindCSS`, `tailwind` |
| Alembic | `alembic` (in prose) |
| Hugging Face Hub | `HuggingFace`, `HF hub`, `the Hub` (on first use) |
| GitHub Release | `GitHub release`, `Github release` |
| GitHub Actions, Docker Compose, Python, Telegram | `Github`, `docker-compose` (in prose), `python` (in prose) |

Tool names that are lower case by design stay lower case: uv, npm, pytest, git.
Terms of the method are defined once, in `docs/reference/glossary.md`; link to
the glossary rather than redefining a term.

## 📝 Headings and emoji

- One H1 per file: its title. Headings use sentence case and no trailing
  punctuation.
- Each H2 starts with one emoji from the legend below, then a space. H1, H3, and
  deeper headings carry no emoji.
- Do not skip levels (H2 straight to H4).
- Keep headings unique within a file. GitHub numbers duplicates (`#setup`,
  `#setup-1`), and those anchors silently change meaning when sections move.
- Give a section that other files link to a stable anchor of its own, on its
  own line just above the heading. Defects use `d` and their number:

  ```markdown
  <a id="d19"></a>

  ### D19. Family (f) is not combined
  ```

  and are linked as `docs/limitations.md#d19`.
- GitHub builds an anchor from a heading by lowercasing it, dropping
  punctuation and emoji, and turning each space into a hyphen. Accented letters
  survive. An emoji heading therefore yields an anchor that starts with a
  hyphen: `## 🚀 Quickstart` is `#-quickstart`.

### Emoji legend

| Emoji | Role of the H2 | Typical headings |
|---|---|---|
| 🧭 | Orientation | Overview, What this is, How to read this |
| 🚀 | Getting started | Quickstart, First run |
| 📦 | Installation | Prerequisites, Install, Dependencies |
| 🔧 | Configuration and operation | Options, Environment variables, Commands |
| 🧩 | Structure | Architecture, Repository layout, Components |
| 📊 | Data and results | Dataset, Outputs, Results |
| 🧪 | Testing and checks | Tests, Verification, Checks |
| 🩺 | Troubleshooting | Troubleshooting, Common errors |
| 🔒 | Security and privacy | Security, Privacy, Governance |
| 📝 | Writing and conventions | Style, Conventions, Changelog |
| 🤝 | Contributing | Contributing, Code of conduct, Support |
| 📚 | Reference | Glossary, References, Further reading, Licence, Citation |

Status markers, in tables and lists only, always beside a word that carries
the meaning on its own:

| Marker | Meaning | Example |
|---|---|---|
| ✅ | Done, verified, supported | ✅ Verified |
| 🟠 | Partial, unverified, use with care | 🟠 Partly fixed |
| 🔴 | Broken, missing, not supported | 🔴 Not implemented |

Every emoji in the legend is a single code point. Avoid emoji that need a
variation selector (U+FE0F), such as the gear or the warning sign: GitHub keeps
the invisible selector in the anchor.

The method and its audit trail stay restrained: `METHODOLOGY.md`,
`docs/method/`, `docs/limitations.md`, and `dataset/DATASHEET.md` carry no
emoji in headings, and use status markers only in a status column.

## 📝 Alerts

GitHub renders five alerts:

```markdown
> [!NOTE]
> The bootstrap never reads `.env`.
```

| Alert | Use it for |
|---|---|
| `[!NOTE]` | Context a reader skimming the page should still see |
| `[!TIP]` | An optional shortcut or a better way |
| `[!IMPORTANT]` | Something the reader must do for the steps to work |
| `[!WARNING]` | Something that can break the setup or mislead a reading of the results |
| `[!CAUTION]` | Privacy, or an action that cannot be undone (deleting data, publishing personal data). Nothing else |

Use at most one alert per section, never stack two, and keep each to a few
lines. Routine information belongs in the prose.

## 🔧 Code blocks and commands

- Every fenced block has a language tag: `bash`, `powershell`, `python`,
  `text` (output, trees), `json`, `toml`, `yaml`, `sql`, or `markdown`.
- One shell per block. Where commands differ, give a `bash` block and a
  `powershell` block, each introduced by a line of prose.
- No prompts (`$`, `>`, `PS>`), so that a block pastes as it is.
- No `<placeholders>`. Write a value the reader can run, such as
  `--mission russosphere`, or an environment variable set in an earlier block.
- Output goes in its own `text` block after the command.
- Commands run from the repository root unless the text says otherwise.
- A command that runs a script may only pass flags the script declares with
  `add_argument` (the `flags` rule). A script without `argparse` takes no
  flags.

Quote these commands exactly:

| Purpose | Command |
|---|---|
| Install for development | `uv sync --extra dev` |
| Run the tests (no `llm` extra needed) | `uv run --extra dev python -m pytest` |
| Telegram collection | add the `collect` extra: `--extra collect`; credentials in `TELEGRAM_*` variables (`TG_*` accepted as a fallback) |
| Check the documentation | `uv run --no-project python scripts/check_docs.py` |

## 📚 Code references

Cite code by path and symbol, with the full repository-relative path:

- a function or constant: `src/shared/dossier.py::get_methodology_version_hash`;
- a method: `scripts/check_docs.py::Context.resolve_source`;
- a nested name: chain it with dots, `::Outer.Inner.name`.

The `symbols` rule parses each Python file with `ast` and fails a reference
whose symbol no longer exists; other files are searched for the name.

Never cite a bare `file:line`: line numbers drift with every edit, and commit
`cc258e4` silently broke 23 of them. Where one line truly matters, link a
permalink pinned to a commit, which cannot drift:
[`get_methodology_version_hash` at `4665744`](https://github.com/mlabarrere/Idefix/blob/4665744a0c35e67a8eb57cf4b23a5ecb8f832f71/src/shared/dossier.py#L25-L34).
Line links on a branch (`blob/main/…#L25`) and relative line links
(`../src/x.py#L25`) are rejected.

## 📊 Numbers and facts

**Never write a count that can drift: link to the source.** A count of rows,
tests, files, stages, or rules is out of date the day something is added. Say
where the number lives instead: 'the row counts are listed in
[`dataset/manifest.json`](../dataset/manifest.json)'.

The exception is a checkpoint, a value the reader compares with their own
screen, as in `docs/ops/quickstart.md`. Wrap it in a fact marker, which GitHub
does not render and the `checkpoints` rule verifies against its source:

```markdown
The restored database holds <!-- fact:manifest.row_counts.messages -->12,500<!-- /fact --> messages.
```

| Key | Source |
|---|---|
| `manifest.` followed by a dotted path, such as `manifest.row_counts.channels` or `manifest.version` | The value at that path in `dataset/manifest.json` |
| `alembic.head` | The head revision of `alembic/versions` |
| `version` | `[project].version` in `pyproject.toml` |
| `methodology.hash` | The `METHODOLOGY.md` hash described below |

The comparison ignores thousands separators, spaces, backticks, and emphasis.
A marker inside a code block or a code span is not a marker: GitHub shows the
comment literally there, so put checkpoints in prose or tables. In
`docs/ops/quickstart.md`, every count (a number with thousands separators, or
one equal to a row count in the manifest) must be wrapped.

Three facts are checked without a marker:

- **Version.** One release version, in `pyproject.toml`, `CITATION.cff`, the
  version row of `METHODOLOGY.md`, and a release heading in `CHANGELOG.md`
  such as `## [0.4.1] - 2026-10-26`.
- **METHODOLOGY hash.** The newest release entry in `CHANGELOG.md` records the
  hash of `METHODOLOGY.md` on one line, in this form:

  ```markdown
  - METHODOLOGY.md hash `0123abcd`.
  ```

  The hash is the first 8 hexadecimal characters of the SHA-256 of
  `METHODOLOGY.md` with CRLF line endings normalized to LF, as computed by
  `src/shared/dossier.py::get_methodology_version_hash` plus the normalization
  ([D27](./limitations.md#d27)). When they differ, the `methodology-hash` rule
  prints the current one.
- **Alembic head.** A quoted head ('head' followed by a revision, or a
  revision followed by '(head)') must be the head of `alembic/versions`.

## 🧩 One owner per topic

Each topic has one owning document. Others link to it and do not repeat it: a
step written in two places drifts in one of them.

| Topic | Owner |
|---|---|
| Setup steps | `docs/ops/quickstart.md`, the one canonical setup tutorial |
| Errors and their fixes | `docs/ops/troubleshooting.md` |
| Manual installation | `docs/ops/install.md` |
| The method | `docs/method/` and `METHODOLOGY.md` |
| Known defects | `docs/limitations.md` |
| Terms | `docs/reference/glossary.md` |
| Scripts | `scripts/README.md` |
| Contributing | `CONTRIBUTING.md` |

## 🧪 Documentation checks

The checker reads every git-tracked `.md` file except vendored agent tooling
(`.agents/`, `_bmad*/`), dependencies (`node_modules/`), and its own test
fixtures (`tests/fixtures/`). Each rule is either blocking (a finding fails CI)
or warn (reported, never fatal).

<a id="checker-rules"></a>

| Rule | What it checks |
|---|---|
| `links` | Every relative link and image resolves to a file or a folder |
| `anchors` | Every `#anchor`, in the same file or in another `.md` file, names a heading or an explicit `<a id>` or `<a name>` |
| `file-line` | No bare `file:line` reference and no unpinned line link; each finding says whether the reference is also visibly stale |
| `symbols` | Every `path::symbol` names a definition that exists |
| `symbol-paths` | Every `path::symbol` uses the full repository-relative path |
| `flags` | A quoted command such as `uv run python scripts/pipeline.py --list` uses only flags the script declares |
| `spelling` | Oxford British spelling, against a deny-list |
| `checkpoints` | Every fact marker matches its source, and every count in `docs/ops/quickstart.md` is marked |
| `alembic-head` | A quoted Alembic head is the head of `alembic/versions` |
| `version` | One version across `pyproject.toml`, `CITATION.cff`, `METHODOLOGY.md`, and `CHANGELOG.md` |
| `methodology-hash` | The newest `METHODOLOGY.md` hash recorded in `CHANGELOG.md` is the current one |
| `numbers` | Every figure in the prose of `docs/experiments/*.md` exists in an artefact under `docs/experiments/results/` |
| `archive` | `docs/` mentions the quarantined `archive/` only with a do-not-cite disclaimer |

### Rules in warn mode

<a id="warn-mode-rules"></a>

Every rule is blocking: none is in warn mode. A new rule may start in warn mode
while documents on `main` do not pass it yet; list it in this table until it
does, and keep the table in step with `RULES` in `scripts/check_docs.py`. A
test compares them.

| Rule | What still fails |
|---|---|
