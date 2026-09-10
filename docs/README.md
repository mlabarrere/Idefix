# Documentation

Everything this project claims, and the evidence for it. Organised as a paper:
method, experiments, limitations, references.

**If you read one file, read [`limitations.md`](./limitations.md).** It is the
register of what bounds every claim here, including the defects we know about
and have not yet fixed.

## Method

What the system actually computes, traceable to `file:line` throughout.

| | |
|---|---|
| [01 — Problem and scope](./method/01-problem-and-scope.md) | What this is, what it is not, the single-platform limit, the mission model |
| [02 — Graph model](./method/02-graph-model.md) | Nodes, the nine edge families, the windowing rule |
| [03 — Suspicion score](./method/03-suspicion-score.md) | Families (a)–(f), the Stouffer/BH combiner, the null model, the gate |
| [04 — Thematic relevance](./method/04-thematic-relevance.md) | The targeting engine, and the `targeting_score` / `fr_score` distinction |
| [05 — Semantic family](./method/05-semantic-family.md) | Family (f) and embedding-based communities |
| [06 — Episodes and communities](./method/06-episodes-and-communities.md) | Episode discovery, Leiden, labelling, the cohesion/modularity trade-off |
| [07 — Tiers and governance](./method/07-tiers-and-governance.md) | T1/T2/T3, output discipline, collection posture |

## Experiments

Falsification protocols. **No experiment currently has a result** — the corpus
behind every historical figure has been decommissioned.

| | |
|---|---|
| [Protocol contract and index](./experiments/README.md) | What a protocol page must contain |
| [Exp 1 — Centrality ablation](./experiments/exp1-centrality-ablation.md) | Is the score just centrality? |
| [Exp 2 — Episode recovery](./experiments/exp2-episode-recovery.md) | Blocked: no real external gold |
| [Exp 3 — Hostile vs organic](./experiments/exp3-hostile-vs-organic.md) | Blocked: no negative class |
| [Exp f — Embedding discrimination](./experiments/expf-embedding-discrimination.md) | Script must be fixed first |
| [Language-prior ablation](./experiments/exp-language-prior-ablation.md) | How much of the ranking is language? |
| [Parameter sensitivity](./experiments/exp-parameter-sensitivity.md) | Do the free parameters carry the results? |
| [Validation lab contracts](./experiments/validation-lab.md) | Schemas for external gold and organic corpora |

## Reference

| | |
|---|---|
| [References](./reference/references.md) | Every entry verified against Crossref or arXiv, each stating where it is used |
| [references.bib](./reference/references.bib) | Machine-readable form |
| [Glossary](./reference/glossary.md) | Technical and institutional vocabulary |

## Operations

| | |
|---|---|
| [Install](./ops/install.md) | Full setup: database, Python, Telegram credentials, webapp |
| [Quickstart](./ops/quickstart.md) | Fastest path to a running system |
| [Migrations](./ops/migrations.md) | Alembic reference |
| [Multi-mission](./ops/multi-mission.md) | Adding or configuring a mission |
| [Demo runbook](./ops/demo-runbook.md) | Five-minute walkthrough |

## Product

| | |
|---|---|
| [Product](./product/product.md) | Functional view: the deliverables and non-goals |
| [Frontend](./product/frontend.md) | The analyst interface |
| [i18n](./product/i18n.md) | Locale contract |

## Not documentation

`../archive/2026-06-russosphere/` holds metric artefacts from a decommissioned
corpus. They are kept for provenance and **may not be cited**. See that
directory's README for why.

## Conventions

- **Language.** English throughout, except that
  [`reference/glossary.md`](./reference/glossary.md) preserves French
  institutional terms in their official form (VIGINUM / EU usage —
  *manipulations de l'information*, *ingérences numériques étrangères*), with
  translations. Not "fake news".
- **Numbers.** No figure appears in prose without a matching artefact under
  `experiments/results/`. This is enforced in CI.
- **Claims.** Every methodological statement resolves to a `file:line` reference
  or an artefact. Anything else is a defect and belongs in `limitations.md`.
