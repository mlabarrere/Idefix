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

> ### Reproducibility status
>
> **No result in this repository is currently reproducible.** The PostgreSQL
> instance holding the corpus behind every previously published figure has been
> decommissioned. Those artefacts are quarantined under
> [`archive/`](./archive/) and may not be cited.
> [`docs/experiments/`](./docs/experiments/) contains falsification protocols;
> `docs/experiments/results/` is empty and will hold only figures regenerated
> against a corpus a third party can rebuild.

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

```
┌──────────────────── OFFLINE PIPELINE (Python) ─────────────────────┐
│  crawl ─▶ build_edges ─▶ build_scores ─▶ analyze_communities ─▶ export │
│ (MTProto)   (graph)     (Stouffer/BH)      (Leiden)          (JSON)  │
└──────────────────────────────────────────────────────────────┬─────┘
                                                               │
┌──────────── ANALYST INTERFACE (React, static) ───────────────┴─────┐
│  webapp/public/data/<mission>/   ◀── precomputed bundles            │
│        ▼                                                            │
│  vite build ─▶ static site ─▶ browser (local JSON fetch, no backend)│
└─────────────────────────────────────────────────────────────────────┘
```

```
Idefix/
├── METHODOLOGY.md      versioned cover page (hash shipped in every export)
├── docs/               method · experiments · limitations · references · ops
├── archive/            decommissioned-corpus artefacts — do not cite
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
├── scripts/            pipeline and evaluation CLIs
├── webapp/             React + Vite + TS analyst interface (static build)
├── alembic/            PostgreSQL migrations (head: 0008)
└── tests/              478 pytest tests + strict frontend typecheck
```

**Bundles are not published in this repository.** They are corpus- and
run-specific by construction, so shipping them would publish numbers nobody can
regenerate. Produce them locally with `scripts/export_static.py`.

## 3. Stack

| Layer | Technology | Notes |
|---|---|---|
| Ingestion | MTProto (Telegram) | **Public channels only**, one dedicated read-only account, `FLOOD_WAIT` discipline |
| Storage | PostgreSQL 17 | Messages, edges, scores. Docker in development; Supabase or any PostgreSQL in production |
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

## 5. Install

Requirements: Python 3.14+, [`uv`](https://docs.astral.sh/uv/), Node 20+, Docker
(for PostgreSQL).

```bash
uv sync --extra embed

docker run -d --name idefix-db --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=disinfo -e POSTGRES_PASSWORD=<password> \
  -e POSTGRES_DB=disinfo_trace postgres:17-alpine

cp .env.example .env   # then edit DATABASE_URL + Telegram credentials
uv run alembic upgrade head
```

Full guide: [`docs/ops/install.md`](./docs/ops/install.md) ·
Fastest path: [`docs/ops/quickstart.md`](./docs/ops/quickstart.md)

## 6. Running the pipeline

Every stage is mission-scoped (`--mission <name>`, default `russosphere`) and
idempotent. PostgreSQL reads and writes only — no Telegram contact outside the
collection stage.

```bash
uv run alembic upgrade head

uv run python scripts/crawl.py                     --mission russosphere
uv run python scripts/build_edges.py
uv run python scripts/build_scores.py              --mission russosphere --embeddings
uv run python scripts/mine_episodes.py             --mission russosphere
uv run python scripts/analyze_communities.py       --mission russosphere
uv run python scripts/analyze_communities_embed.py --mission russosphere
uv run python scripts/export_static.py             --mission russosphere
```

### Evaluation

Protocols, falsification criteria and current status:
[`docs/experiments/`](./docs/experiments/). Note that several `eval_*` scripts
cannot run from a clean clone ([D12](./docs/limitations.md)) and two are
mis-specified ([D11](./docs/limitations.md)) — read the protocol page before
running one.

## 7. Analyst interface

```bash
cd webapp
npm install
npm run dev        # http://localhost:5173
npm run build      # static dist/
```

The webapp reads JSON bundles from `webapp/public/data/<mission>/`, produced by
`export_static.py`. Those bundles are **not** in the repository — generate them
first. The browser never touches the database.

## 8. Tests

```bash
uv run python -m pytest                    # 478 tests
cd webapp && npx tsc --noEmit              # strict frontend typecheck
cd webapp && npx tsx scripts/check-i18n-parity.ts
```

Coverage is uneven: families (b) and (d) and the rigorous path have no dedicated
test files ([D17](./docs/limitations.md)).

## 9. The load-bearing limitation

> **Telegram coverage only.** The mass-amplification layer on other platforms is
> not observed. An operation reaching France mainly through other platforms,
> without a Telegram stage, **will not be detected.** What is measured is a
> footprint *observable on Telegram*, never the total footprint of a phenomenon.

This is a mandatory, validated field of every exported bundle. The complete
register of limits and known defects is
[`docs/limitations.md`](./docs/limitations.md).

## 10. Governance

- **Arm-only.** Outputs go to designated institutional recipients — never to
  platforms, the public, candidates or press.
- **Tiered vocabulary** (T1/T2/T3) rather than true/false. Any T3 claim
  (real-world attribution) is out of scope and a reportable defect.
- **Structural corroboration.** No T2 label and no escalated severity without at
  least 2 independent families triggered.
- **ToS-respecting collection.** Public channels only, no scraping outside the
  terms of service, no deanonymization. Member identifiers are not collected.
  Secrets are scrubbed by key and by value from every export.

## 11. License and contributing

- **License:** [Apache-2.0](./LICENSE)
- **Contributing:** [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the
  [code of conduct](./CODE_OF_CONDUCT.md)
- **Security:** report via [`SECURITY.md`](./SECURITY.md) — never as a public issue
- **Citing:** [`CITATION.cff`](./CITATION.cff)
- **History:** [`CHANGELOG.md`](./CHANGELOG.md)
