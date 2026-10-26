# Idéfix

[![CI](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml/badge.svg)](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.14%2B-blue)](./pyproject.toml)

> **Propagation and coordination analysis for Telegram public channels.**
> A demonstrator that maps observable diffusion structure and produces a ranked,
> explainable examination queue for human analysts.

**Idéfix is not a fake-news detector.** It never judges whether a message is
true. It describes *observable structures* of diffusion and coordination and
shows, for each channel, the concrete signals that justify its rank. The
deliverable is a prioritized review queue — never a verdict.

**Idéfix is also not a validated manipulation detector.** Whether a high rank
corresponds to coordinated manipulation rather than to prominence within an
adversarial media ecosystem is an open question this project has not answered.
Read [`docs/limitations.md`](./docs/limitations.md) before drawing any
conclusion from an output.

> [!CAUTION]
> **Personal data.** Idéfix collects, and dataset `v1.0.0` publishes, the
> Telegram user ID, username and comment text of private individuals who
> commented in the public discussion groups linked to collected channels (the
> `comments` table). The pipeline also writes the IDs and usernames of each
> channel's most frequent commenters into the analyst bundle
> (`commenters.json`, by `scripts/build_commenters.py`), and the analyst
> interface displays them. Read the [datasheet's terms of use](./dataset/DATASHEET.md#uses)
> before you download the corpus or deploy a bundle anywhere others can reach it.

> ### Reproducibility status
>
> **The corpus is public; the results are not regenerated yet.**
>
> - The previously collected corpus is published as **dataset `v1.0.0`**: the
>   complete database snapshot — channels, channel posts and comments from
>   public Telegram channels and their public discussion groups — as a GitHub
>   Release asset pinned by SHA-256 in
>   [`dataset/manifest.json`](./dataset/manifest.json), described by its
>   datasheet, [`dataset/DATASHEET.md`](./dataset/DATASHEET.md).
> - From it, anyone can rebuild every derived table and every analyst bundle
>   with one command ([§5](#5-run-it-on-the-public-corpus)). No Telegram
>   account is needed. The snapshot also carries the derived tables of an
>   earlier pipeline run; the bootstrap recomputes them, and only regenerated
>   numbers may be cited ([D18](./docs/limitations.md)).
> - [`docs/experiments/`](./docs/experiments/) contains falsification
>   protocols. `docs/experiments/results/` stays empty until each figure is
>   regenerated from that corpus.
> - The figures from the June 2026 runs stay quarantined under
>   [`archive/`](./archive/) and may not be cited: they came from an earlier
>   pipeline, and recomputing on the public corpus is not expected to reproduce
>   them ([D18](./docs/limitations.md)).

**Start here:** [`docs/`](./docs/) — method, experiments, limitations,
references. [`METHODOLOGY.md`](./METHODOLOGY.md) is the versioned cover page
whose hash ships in every export.

---

## 1. Principle

**One engine, N missions.** A mission is a *configuration* — source universe,
lexicon, targeting weights, scoring profile, dashboard, export — never a code
fork. The structural score families are theme-agnostic; missions differ in
seeds, lexicons, relevance signals and weights.

| Mission | `implemented` | Object |
|---|---|---|
| `russosphere` | `True` | Coordinated disinformation targeting the image, integrity or sovereignty of France |
| `france_ukraine` | `True` | Narratives targeting France in the Ukraine conflict |
| `gan` | `True` | Telegram-observable informational footprint of the French Carrier Strike Group (OPSEC objective). Gate calibration **not reconciled** with `russosphere` — see [`limitations.md`](./docs/limitations.md) D15 |
| `dircom_minarm` | `False` | Reuse and distortion of official French MoD communication. Packaged, refuses live selection until a crawl populates it |

**Load-bearing constraint:** thematic relevance and adversary linkage modulate
**severity**, never **inclusion**. No channel is excluded from the queue for
being off-theme, and because the modulation is multiplicative, a channel with
zero structural suspicion stays at zero whatever its relevance.

## 2. Architecture

Two strictly disjoint halves: an **offline analytical pipeline** (Python) that
materializes JSON bundles, and a **fully static analyst interface** (React) that
reads only those bundles. The browser never touches the database.

The pipeline reads raw channels and posts from PostgreSQL. They get there in
one of two ways: restored from the public dataset (the default, no credentials),
or collected from Telegram with your own account (optional).

```
┌──────────────────────────── RAW DATA (one of) ─────────────────────────────┐
│  public dataset v1.0.0 ─▶ pg_restore     │  your own collection (MTProto)  │
│  scripts/bootstrap.py, no credentials    │  optional, Telegram account     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      ▼   PostgreSQL 17: channels, messages
┌──────────────── OFFLINE PIPELINE (Python, scripts/pipeline.py) ────────────┐
│  build_edges ─▶ build_scores ─▶ analyze_communities ─▶ export_static       │
│    (graph)      (Stouffer/BH)       (Leiden)             (JSON)            │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      ▼
┌──────────────────── ANALYST INTERFACE (React, static) ─────────────────────┐
│  webapp/public/data/<mission>/   ◀── precomputed bundles                   │
│  vite build ─▶ static site ─▶ browser (local JSON fetch, no backend)       │
└────────────────────────────────────────────────────────────────────────────┘
```

```
Idefix/
├── METHODOLOGY.md      versioned cover page (hash shipped in every export)
├── docs/               method · experiments · limitations · references · ops
├── dataset/            public corpus: manifest (SHA-256 pins), datasheet, README
│   └── downloads/      fetched artefacts land here (gitignored)
├── docker-compose.yml  local PostgreSQL 17 for the public corpus
├── archive/            artefacts from an earlier pipeline — do not cite
├── src/
│   ├── ingestor/       MTProto client (public channels, read-only)
│   ├── normalizer/     text, URLs, media fingerprints, thematic targeting
│   ├── graph/          channel-centric multiplex graph (NetworkX/igraph)
│   ├── scorer/         score families, null model, Stouffer/BH combination
│   ├── embed/          local sentence-transformers encoder, offline cache
│   ├── dossier/        evidence-first episode dossiers
│   ├── missions/       one mission = one MissionDefinition (auto-discovered)
│   ├── validation_lab/ external-gold schemas (non-circular validation)
│   └── shared/         DB, secret scrubbing, snapshot store
├── scripts/            bootstrap, pipeline runner, collection and evaluation CLIs
├── webapp/             React + Vite + TS analyst interface (static build)
├── alembic/            PostgreSQL migrations (head: 0008)
└── tests/              pytest suite + strict frontend typecheck
```

**Bundles are not published in this repository.** They are corpus- and
run-specific by construction, so shipping them would publish numbers nobody can
regenerate. The bootstrap produces them locally from the public corpus
(`scripts/export_static.py` is the stage that writes them).

## 3. Stack

| Layer | Technology | Notes |
|---|---|---|
| Corpus | Public dataset `v1.0.0` | Complete `pg_dump` snapshot of the collected database, fetched and verified against `dataset/manifest.json` |
| Ingestion (optional) | MTProto (Telegram) | **Public channels only**, one dedicated read-only account, `FLOOD_WAIT` discipline |
| Storage | PostgreSQL 17 | Messages, edges, scores. Docker Compose locally (`docker-compose.yml`); any PostgreSQL 17, e.g. Supabase, otherwise |
| Graph | NetworkX `MultiDiGraph` + igraph/Leiden | Rebuilt **in memory, on demand**. No graph-database server |
| Scoring | Pure Python, no network calls | Per-family p-values, Stouffer combination, Benjamini-Hochberg FDR control |
| Embeddings | `sentence-transformers`, local | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, FR/RU/EN), deterministic offline cache |
| Communities | Leiden, two tracks | **analytics** (link graph) and **embeddings** (plus semantic edges) |
| Frontend | React 18 + Vite + TypeScript | Strict mode, Cytoscape, Radix, Tailwind v4. **100% static build** |
| Delivery | Any static host | `vite build`; the browser reads local JSON only |

## 4. The suspicion score, in brief

Each family produces a one-sided p-value; the p-values are combined by weighted
Stouffer and controlled for false discovery rate across channels. Full
treatment, including the defects, in
[`docs/method/03-suspicion-score.md`](./docs/method/03-suspicion-score.md).

| Family | Status | Method |
|---|---|---|
| **b** · Cascade role | Active, **with null model** | Bridge-Score composite on the forward graph |
| **c** · Coordination | Active, **no null model** | Windowed coordination edges. Its p-value is a placeholder — [D2](./docs/limitations.md) |
| **d** · Forward influence | Active, **with null model** | Out-degree and out-strength on the aggregate forward graph. **Not** cross-episode |
| **f** · Semantic coherence | Active, opt-in | Distance to an organic-FR baseline, proximity to known adversary channels |
| a · Claim proximity · e · GenAI origin | **Never wired** | Injection seams. They have never produced a value |

**Multi-source gate:** a channel crosses only when **at least 2 distinct
families** trigger. The triggered set is persisted (`channel_scores.gate_families`,
migration `0008`), so tier assignment is auditable from the stored record.

## 5. Run it on the public corpus

One command takes a fresh clone to a running analyst interface. It needs **no
Telegram account and no credentials**.

Requirements: [Docker](https://docs.docker.com/get-docker/) with Compose
v2.17+, running · [`uv`](https://docs.astral.sh/uv/) (it can install Python
3.14 itself) · [Node.js](https://nodejs.org/) 20.19+ or 22.12+ with npm.

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
uv run --extra embed python scripts/bootstrap.py   # any OS
# or, where make is available:
make setup
```

When the dev server reports ready, open <http://localhost:5173>.

What the bootstrap does, in order (each step is also a subcommand —
`check`, `fetch`, `db`, `pipeline`, `webapp`):

1. **check** — Python 3.14, Docker daemon and Compose v2, Node and npm, a free
   database port, the `embed` extra, a valid manifest. It stops with a fix
   for each failed check.
2. **fetch** — reads [`dataset/manifest.json`](./dataset/manifest.json),
   downloads each release file into `dataset/downloads/`, verifies its SHA-256
   and size, and unpacks the archives it lists. Files already present with the
   right hash are skipped.
3. **db** — starts a local PostgreSQL 17 with Docker Compose
   ([`docker-compose.yml`](./docker-compose.yml), loopback only, local
   credentials `idefix`/`idefix`). If the database is empty, it restores the
   corpus and runs `alembic upgrade head`. A database that already holds data
   is left untouched — no restore, no migration; if its schema is behind, the
   bootstrap prints the `alembic upgrade head` command to run.
4. **pipeline** — runs every offline stage for every mission with
   `scripts/pipeline.py`: edges, scores, episodes, communities, bundles. No
   Telegram contact and no paid API.
5. **webapp** — installs the frontend dependencies if needed and starts the
   Vite dev server on <http://localhost:5173>.

The bootstrap never reads or writes `.env` (Docker Compose is given an empty
env file too); it passes `DATABASE_URL` to each step itself. It never deletes
data. Re-running it is safe: verified downloads are kept, the restore happens
only into an empty database, and `all` runs the pipeline automatically only on
a database it restored itself, until one run has completed.
`bootstrap.py pipeline` always runs it.

`--extra embed` installs sentence-transformers and PyTorch for the
embedding-based stages, which also download a sentence-transformers model from
the Hugging Face hub on first use. For a lighter run without them:
`uv run python scripts/bootstrap.py --skip-embeddings`.

Options, troubleshooting (port already taken, Docker not running, Windows
encoding, reset, offline mirror):
[`docs/ops/quickstart.md`](./docs/ops/quickstart.md). Full setup, including a
managed database: [`docs/ops/install.md`](./docs/ops/install.md). What the
corpus contains, how it was collected and under which terms it may be used:
[`dataset/DATASHEET.md`](./dataset/DATASHEET.md).

## 6. Running the pipeline

The bootstrap's `pipeline` step is `scripts/pipeline.py`. Run it directly to
redo one mission or one stage:

```bash
uv run --extra embed python scripts/pipeline.py --mission russosphere --list   # print the stages
uv run --extra embed python scripts/pipeline.py --mission russosphere          # run them all
uv run --extra embed python scripts/pipeline.py --mission gan --from <stage>   # resume
uv run python scripts/pipeline.py --mission all --skip-embeddings
make pipeline MISSION=russosphere                                              # via the bootstrap
```

`--mission` takes `russosphere`, `france_ukraine`, `gan` or `all`; `--only` and
`--from` select stages by name. The runner stops at the first failing stage and
prints per-stage timings. `bootstrap.py pipeline` (and `make pipeline`) runs it
with the local `DATABASE_URL` already set.

The stages are the individual scripts under [`scripts/`](./scripts/README.md) —
in outline `build_edges` → `tag_france` / `tag_gan` → `build_scores` →
`mine_episodes` → `analyze_communities` (and its embedding variant) →
`analyze_porosity` → `export_static` → `build_stories`. `--list` prints the
authoritative order. Every stage is mission-scoped and idempotent and only
reads and writes PostgreSQL and local files.

Run outside the bootstrap, the scripts take `DATABASE_URL` from the environment
or from `.env`, and an explicit environment variable wins. `.env.example`
points at the local database; so does:

```bash
export DATABASE_URL=postgresql+asyncpg://idefix:idefix@localhost:5433/idefix
# PowerShell: $env:DATABASE_URL="postgresql+asyncpg://idefix:idefix@localhost:5433/idefix"
```

### Evaluation

Protocols, falsification criteria and current status:
[`docs/experiments/`](./docs/experiments/). The public corpus makes the
experiments runnable in principle, but the evaluation harness still cannot run
from a clean clone ([D12](./docs/limitations.md)) — read the protocol page
before running one.

## 7. Analyst interface

The bootstrap starts it; `make webapp` restarts it. By hand:

```bash
cd webapp
npm ci
npm run dev        # http://localhost:5173
npm run build      # static dist/
```

The webapp reads JSON bundles from `webapp/public/data/<mission>/`, produced by
the pipeline's `export_static` and `build_stories` stages. Those bundles are
**not** in the repository — the pipeline generates them. The browser never
touches the database.

To look at the interface with no database at all,
`uv run python scripts/make_fixture_bundle.py` writes an obviously
**synthetic** bundle (invented channels, fixed seed) into
`webapp/public/data/russosphere/`, replacing whatever is there. Nothing it
shows means anything about Telegram.

## 8. Collect your own data (optional, advanced)

Nothing above needs this. Collection extends or replaces the public corpus with
channels you crawl yourself, and it is the only part of the system that
contacts Telegram.

- **Credentials.** A dedicated Telegram account, an API id and hash from
  [my.telegram.org](https://my.telegram.org), and a session string generated
  once with `make session` (`scripts/session_web.py`). They go in `.env`
  (`cp .env.example .env`); `.env` is gitignored. Step by step:
  [`docs/ops/install.md`](./docs/ops/install.md#optional-collect-your-own-data-from-telegram).
- **Target database.** Collection scripts write wherever `DATABASE_URL`
  points — the local Compose database with the `.env.example` default (see §6).
- **Entry points** (MTProto, read-only, public channels, one serialized
  session — never run two at once):

  | Script | Collects |
  |---|---|
  | `scripts/backfill.py --channel @name --limit 500` | One channel's history (`make backfill CH=@name`) |
  | `scripts/backfill_seeds.py [@channel ...]` | The hop-0 seed set, in one session |
  | `scripts/snowball_crawl.py [--waves N] [--dry-run]` | Bounded snowball frontier: the most-forwarded channels not yet collected |
  | `scripts/crawl_france_ukraine.py [--dry-run]` | Bounded France–Ukraine campaign in russophone networks |
  | `scripts/paced_backfill.py` | Paced long-running backfill of catalogued but empty channels (`make crawl`) |
  | `scripts/enrich_recrawl.py` | Media hashes, channel bios, and **commenters of linked public groups — personal data**, see §11 |

- **Then** recompute the offline stages: `make pipeline`, or
  `uv run --extra embed python scripts/bootstrap.py pipeline`.

A database you have collected into is no longer dataset `v1.0.0`; results from
it are not comparable with results from the public corpus.

## 9. Tests

```bash
uv run --extra dev python -m pytest        # offline: no database, no network
cd webapp && npx tsc --noEmit              # strict frontend typecheck
cd webapp && npx tsx scripts/check-i18n-parity.ts
uv run python scripts/check_docs.py        # documentation integrity
```

Coverage is uneven: the rigorous path (`rigor.py`) has no dedicated test file
([D17](./docs/limitations.md)).

## 10. The load-bearing limitation

> **Telegram coverage only.** The mass-amplification layer on other platforms is
> not observed. An operation reaching France mainly through other platforms,
> without a Telegram stage, **will not be detected.** What is measured is a
> footprint *observable on Telegram*, never the total footprint of a phenomenon.

This is a mandatory, validated field of every exported bundle. The complete
register of limits and known defects is
[`docs/limitations.md`](./docs/limitations.md).

## 11. Governance

- **Arm-only.** Outputs go to designated institutional recipients — never to
  platforms, the public, candidates or press.
- **Tiered vocabulary** (T1/T2/T3) rather than true/false. Any T3 claim
  (real-world attribution) is out of scope and a reportable defect.
- **Structural corroboration.** No T2 label and no escalated severity without at
  least 2 independent families triggered.
- **ToS-respecting collection.** Public channels only, no scraping outside the
  terms of service, no deanonymization. Channel member lists are not collected.
  `scripts/enrich_recrawl.py` does collect the identifiers, usernames and text
  of **commenters** in public linked discussion groups (`comments` table) —
  personal data of private individuals. The `build_commenters` pipeline stage
  copies the IDs and usernames of each channel's most frequent commenters,
  without their text, into the analyst bundle, where the channel drawer shows
  them. Secrets are scrubbed by key and by value from the static export.
- **What the public dataset publishes.** The complete database snapshot:
  channel metadata and channel posts (public broadcast content); the
  `comments` table, **including commenter identifiers, usernames and text**;
  and the derived tables of an earlier pipeline run, including its per-channel
  scores — outputs that the arm-only rule above otherwise reserves for
  designated recipients. Contents and terms of use:
  [`dataset/DATASHEET.md`](./dataset/DATASHEET.md).

## 12. License and contributing

- **License:** [Apache-2.0](./LICENSE)
- **Contributing:** [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the
  [code of conduct](./CODE_OF_CONDUCT.md)
- **Security:** report via [`SECURITY.md`](./SECURITY.md) — never as a public issue
- **Dataset:** [`dataset/README.md`](./dataset/README.md) (fetch, verify,
  rebuild) · licence and terms of use in
  [`dataset/DATASHEET.md`](./dataset/DATASHEET.md)
- **Citing:** [`CITATION.cff`](./CITATION.cff) — cite the software and, for any
  result computed from the corpus, dataset `v1.0.0`
- **History:** [`CHANGELOG.md`](./CHANGELOG.md)
