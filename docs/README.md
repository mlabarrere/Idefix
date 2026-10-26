# Documentation

Everything this project claims, and the evidence for it. Organized as a paper:
method, experiments, limitations, and references, followed by operations and
product documents.

> [!IMPORTANT]
> If you read one file, read [`limitations.md`](./limitations.md). It is the
> register of what bounds every claim here, including the defects we know about
> and have not yet fixed.

## 🧭 Contents

- [Method](#-method)
- [Experiments](#-experiments)
- [Limitations](#-limitations)
- [Reference](#-reference)
- [Operations](#-operations)
- [Dataset](#-dataset)
- [Product](#-product)
- [Project files](#-project-files)
- [Not documentation](#-not-documentation)
- [Conventions](#-conventions)

## 🧩 Method

What the system actually computes, traceable throughout to code references that
name a path and a symbol, such as `src/scorer/rigor.py::compute_family_significance`.

| Document | What it covers |
|---|---|
| [`../METHODOLOGY.md`](../METHODOLOGY.md) | The versioned cover page of the method |
| [01 Problem and scope](./method/01-problem-and-scope.md) | What this is, what it is not, the single-platform limit, the mission model |
| [02 Graph model](./method/02-graph-model.md) | Nodes, the edge types, the windowing rule |
| [03 Suspicion score](./method/03-suspicion-score.md) | Families (a)–(f), the Stouffer/BH combiner, the null model, the gate |
| [04 Thematic relevance](./method/04-thematic-relevance.md) | The targeting engine, and the `targeting_score` / `fr_score` distinction |
| [05 Semantic family](./method/05-semantic-family.md) | Family (f) and embedding-based communities |
| [06 Episodes and communities](./method/06-episodes-and-communities.md) | Episode discovery, Leiden, labelling, the cohesion/modularity trade-off |
| [07 Tiers and governance](./method/07-tiers-and-governance.md) | T1/T2/T3, output discipline, collection posture |

## 🧪 Experiments

Falsification protocols. **No experiment currently has a result.** The corpus
is now public and rebuildable (dataset `v1.0.0`), but no protocol has been run
against it yet.

| Document | What it covers |
|---|---|
| [Protocol contract and index](./experiments/README.md) | What a protocol page must contain |
| [Exp 1: centrality ablation](./experiments/exp1-centrality-ablation.md) | Is the score just centrality? |
| [Exp 2: episode recovery](./experiments/exp2-episode-recovery.md) | Blocked: no real external gold |
| [Exp 3: hostile vs organic](./experiments/exp3-hostile-vs-organic.md) | Blocked: no negative class |
| [Exp f: embedding discrimination](./experiments/expf-embedding-discrimination.md) | Does the representation behind family (f) separate organic from scored channels? |
| [Language-prior ablation](./experiments/exp-language-prior-ablation.md) | How much of the ranking is language? |
| [Parameter sensitivity](./experiments/exp-parameter-sensitivity.md) | Do the free parameters carry the results? |
| [Validation lab contracts](./experiments/validation-lab.md) | Schemas for external gold and organic corpora |

## 📊 Limitations

| Document | What it covers |
|---|---|
| [Limitations](./limitations.md) | Structural limits (L1, L2, …) and known defects (D1, D2, …), each with its status |

## 📚 Reference

| Document | What it covers |
|---|---|
| [References](./reference/references.md) | Every entry verified against Crossref or arXiv, each stating where it is used |
| [references.bib](./reference/references.bib) | Machine-readable form of the references |
| [Glossary](./reference/glossary.md) | Technical, institutional, and project vocabulary, and acronyms |
| [Style guide](./STYLE.md) | House style for every Markdown file, and the documentation checks |

## 🔧 Operations

| Document | What it covers |
|---|---|
| [Quickstart](./ops/quickstart.md) | The one setup tutorial: from a fresh clone to the analyst interface on the public corpus |
| [Troubleshooting](./ops/troubleshooting.md) | Every known error message, by setup step, with its fix |
| [Install](./ops/install.md) | Manual setup: Python extras, local or managed database, pipeline, webapp, optional Telegram collection |
| [Migrations](./ops/migrations.md) | Alembic reference |
| [Multi-mission](./ops/multi-mission.md) | Adding or configuring a mission |
| [Demo runbook](./ops/demo-runbook.md) | Five-minute walkthrough of the narrative galaxy |
| [Scripts](../scripts/README.md) | Every command-line script, its flags, and what it reads and writes |

## 📊 Dataset

The public corpus lives outside `docs/`, next to the code that fetches it.

| Document | What it covers |
|---|---|
| [Datasheet](../dataset/DATASHEET.md) | What dataset `v1.0.0` contains (including personal data in `comments`), how it was collected, licence, and terms of use |
| [Dataset README](../dataset/README.md) | How to fetch and verify it, and how a release is rebuilt |
| [Manifest](../dataset/manifest.json) | Release files with their SHA-256 and size, source snapshot, row counts |

## 🧩 Product

| Document | What it covers |
|---|---|
| [Product](./product/product.md) | Functional view: the deliverables and non-goals |
| [Frontend](./product/frontend.md) | The analyst interface |
| [i18n](./product/i18n.md) | Locale contract |
| [Webapp README](../webapp/README.md) | Developing and building the analyst interface |

## 🤝 Project files

| Document | What it covers |
|---|---|
| [README](../README.md) | The front door: what Idéfix is, where to start, supported platforms |
| [Contributing](../CONTRIBUTING.md) | Workflow, checks, conventions, personal data |
| [Code of conduct](../CODE_OF_CONDUCT.md) | Expected behaviour |
| [Security](../SECURITY.md) | How to report a vulnerability |
| [Changelog](../CHANGELOG.md) | Release history and the `METHODOLOGY.md` hash of each release |

## 🔒 Not documentation

`../archive/2026-06-russosphere/` holds metric artefacts from the June 2026
runs on a since-decommissioned database. They are kept for provenance and **may
not be cited**: they came from an earlier pipeline, and recomputing on the
public corpus is not expected to reproduce them. See that directory's README
for why.

## 📝 Conventions

- **Language.** British English throughout ([`STYLE.md`](./STYLE.md)), except
  that [`reference/glossary.md`](./reference/glossary.md) preserves French
  institutional terms in their official form (VIGINUM / EU usage:
  *manipulations de l'information*, *ingérences numériques étrangères*), with
  translations. Not 'fake news'.
- **Numbers.** No figure appears in experiment prose without a matching
  artefact under `experiments/results/`. CI enforces this for
  `experiments/*.md` (`scripts/check_docs.py::check_numbers`).
- **Claims.** Every methodological statement resolves to a code reference
  (a path and a symbol) or an artefact. Anything else is a defect and
  belongs in `limitations.md`.
