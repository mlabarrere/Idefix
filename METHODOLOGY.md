# Idéfix — Methodology

**Version:** 0.4.0
**Date:** 2026-09-10
**Status:** pre-publication
**Supersedes:** 0.3.0-poc (2026-06-29)

This document is the versioned cover page of the Idéfix methodology. Its path is
stable because exported bundles embed a SHA-256 hash of it as a chain-of-custody
field: a methodology revision is therefore detectable after the fact.

**The methodology itself lives in [`docs/method/`](./docs/method/).** This page
declares the scope of the hash, the version history, and the standing claim.

---

## Scope of the hash

The hash covers this file. This file names, by path, the documents that
constitute the methodology at this version:

| | |
|---|---|
| [`docs/method/01-problem-and-scope.md`](./docs/method/01-problem-and-scope.md) | Problem, scope, non-goals, coverage limit, mission model |
| [`docs/method/02-graph-model.md`](./docs/method/02-graph-model.md) | Graph construction and edge families |
| [`docs/method/03-suspicion-score.md`](./docs/method/03-suspicion-score.md) | Score families, combination, null model, gate |
| [`docs/method/04-thematic-relevance.md`](./docs/method/04-thematic-relevance.md) | Targeting engine and relevance signals |
| [`docs/method/05-semantic-family.md`](./docs/method/05-semantic-family.md) | Semantic family (f) |
| [`docs/method/06-episodes-and-communities.md`](./docs/method/06-episodes-and-communities.md) | Episode discovery and community detection |
| [`docs/method/07-tiers-and-governance.md`](./docs/method/07-tiers-and-governance.md) | Attribution tiers, output discipline, governance |
| [`docs/limitations.md`](./docs/limitations.md) | Permanent limits and open defects |
| [`docs/experiments/`](./docs/experiments/) | Falsification protocols |
| [`docs/reference/references.md`](./docs/reference/references.md) | Verified bibliography |

---

## Standing claim

> Idéfix is defensible as a **T1 demonstrator**: it reconstructs observable
> diffusion structure on Telegram public channels and presents it with
> per-signal evidence. It is **not** a validated manipulation detector.

Two gaps bound every stronger claim, and neither is an engineering problem.
Both require human annotation: a corpus of **organic** coordination to serve as
the negative class, and a **real** external seed list for a documented
operation. Until they close, no output is presented as more than T1 or T2.

**No result in this repository is currently reproducible.** The corpus behind
every figure published before this version has been decommissioned. Those
artefacts are quarantined in [`archive/`](./archive/) and may not be cited.
`docs/experiments/` therefore contains protocols, not results.

---

## Version history

### 0.3.0-poc → 0.4.0

An adversarial review compared every documented claim against the code. The
methodology was restructured around what the implementation does, and claims
that the code contradicted were withdrawn rather than softened.

**Withdrawn as false.**

- *"`fr_score` is a display field only and is never used as a filter or
  anchor."* `src/graph/loader.py:66,128` sets `credibility_prior = "suspect"`
  **iff `fr_score < 0.15`**, and that prior drives the largest severity
  modulator. The ranking was substantially a language partition. Now tracked as
  defect D1, with a dedicated ablation protocol.
- *The score is a renormalized weighted sum of triggered families.* The
  implementation combines per-family p-values by Stouffer's method under
  Benjamini-Hochberg FDR control. The weighted sum describes bundles shipped
  before this version, not the method. **Stouffer + BH is now canonical.**
- *"Confidence bands propagate through the same combination."* True of the
  machinery, false of the inputs: only families (b) and (d) receive real
  bootstrap intervals. Everything else ships hardcoded constants that the source
  itself calls fabricated.
- *Family (d) measures cross-episode recidivism.* There are no episodes. It
  measures out-degree and out-strength on one aggregate forward graph.

**Withdrawn as unreproducible.** Every numeric result. The corpus is gone, so
none of it can be checked or falsified. Artefacts moved to `archive/` with an
explicit prohibition on citing them.

**Newly disclosed.** Sixteen defects verified against the code and recorded in
`docs/limitations.md` — among them the absence of a null model for family (c),
the violation of Stouffer's independence assumption, a discontinuity in the
combiner, `CO_HASHTAG` manufacturing coordination edges, silent failure in
family (f), and two mis-specified evaluation scripts.

**Removed from the system.** Six modules documented as part of the method but
imported only by tests (`pockets`, `registry`, `readiness`,
`coordination_fabric`, `dossier/v1`, `analytical_contract`), together with their
documentation. The analyst interface no longer embeds a hand-maintained copy of
this documentation; the repository is the single source.

### 0.2.0-poc → 0.3.0-poc

Semantic-coherence family (f) wired into the score. Automatic episode discovery
replaced a hand-maintained registry. The multi-source gate became traceable
(`gate_families`, migration `0008`). A non-circular validation track was built.

### 0.1.0 → 0.2.0

The shipped detection core was corrected from a GraphSAGE+LSTM graph neural
network to the explainable per-channel score. The platform became multi-mission.
Infrastructure claims (Neo4j, Docker Compose) were corrected to the implemented
stack.
