# Idéfix—methodology

| Field | Value |
|---|---|
| Version | 0.4.1 |
| Date | 2026-10-26 |
| Status | Pre-publication |
| Supersedes | 0.4.0 (2026-09-10) |

This document is the versioned cover page of the Idéfix methodology. Its path is
stable because dossier outputs embed a hash of it (`methodology_version_hash`,
the first eight hexadecimal characters of its SHA-256, computed in
`src/shared/dossier.py`).

> [!WARNING]
> The hash does **not** reach every export, and it does not cover the whole
> method. Static bundles and their manifests carry a fixed version string,
> `scripts/export_static.py::METHODOLOGY_VERSION`, not this hash. And because the
> hash covers this file only, a change made in `docs/method/` or in the code is
> invisible to it unless this page is revised too. Both gaps are recorded as
> [D20](./docs/limitations.md#d20).

**The methodology itself lives in [`docs/method/`](./docs/method/).** This page
declares the documents that make up the method at this version, the version
history, and the standing claim.

---

## Documents that make up the method

| Document | Contents |
|---|---|
| [`docs/method/01-problem-and-scope.md`](./docs/method/01-problem-and-scope.md) | Problem, scope, non-goals, coverage limit, mission model |
| [`docs/method/02-graph-model.md`](./docs/method/02-graph-model.md) | Graph construction and edge types |
| [`docs/method/03-suspicion-score.md`](./docs/method/03-suspicion-score.md) | Score families, combination, null model, gate |
| [`docs/method/04-thematic-relevance.md`](./docs/method/04-thematic-relevance.md) | Targeting engine and relevance signals |
| [`docs/method/05-semantic-family.md`](./docs/method/05-semantic-family.md) | Semantic family (f) |
| [`docs/method/06-episodes-and-communities.md`](./docs/method/06-episodes-and-communities.md) | Episode discovery and community detection |
| [`docs/method/07-tiers-and-governance.md`](./docs/method/07-tiers-and-governance.md) | Attribution tiers, output discipline, governance |
| [`docs/limitations.md`](./docs/limitations.md) | Permanent limits and known defects |
| [`docs/experiments/`](./docs/experiments/) | Falsification protocols |
| [`docs/reference/references.md`](./docs/reference/references.md) | Verified bibliography |

The labelling protocol (`PROTOCOLE_LABELLISATION.md`, kept with the
annotations) is not part of this list: it governs human annotation, not the
score, and has its own provenance hash
(`src/labeling/io.py::LABELING_METHODOLOGY_FILES`).

---

## Standing claim

> [!IMPORTANT]
> Idéfix is defensible as a **T1 demonstrator**: it reconstructs observable
> diffusion structure on Telegram public channels and presents it with
> per-signal evidence. It is **not** a validated manipulation detector.

Two gaps bound every stronger claim, and neither is an engineering problem.
Both require human annotation: a corpus of **organic** coordination to serve as
the negative class, and a **real** external seed list for a documented
operation. Until they close, no output is presented as more than T1 or T2.

**The corpus is reproducible; no result has been regenerated from it yet.** The
complete snapshot is published as dataset v1.0.0 (see
[`dataset/`](./dataset/)), and `scripts/bootstrap.py` rebuilds every derived
table and bundle from it. Figures published before version 0.4.0 are
quarantined in [`archive/`](./archive/) and may not be cited.
`docs/experiments/` therefore contains protocols, not results.

---

## Version history

### 0.4.0 → 0.4.1

Editorial and factual corrections to this page; no change to the method.

- The claim that every export embeds this page's hash was false and is
  withdrawn ([D20](./docs/limitations.md#d20)).
- The claim that family (f) is wired into the score was false and is withdrawn:
  (f) is computed, not scored ([D19](./docs/limitations.md#d19)).
- The language-partition defect is described as fixed, and the corpus as
  published, consistently with the rest of this page.

The method itself changed after the 0.4.0 text was written, in commit `cc258e4`
(2026-09-10), without a version bump: the credibility prior became
evidence-based instead of a language partition
([D1](./docs/limitations.md#d1)), the combiner's discontinuity at zero was
removed ([D4](./docs/limitations.md#d4)), `n_bootstrap` rose from 100 to 1,000
([D7](./docs/limitations.md#d7)), two evaluation scripts were corrected
([D11](./docs/limitations.md#d11)), and isolated channels no longer score 1.0
in family (b) ([D15b](./docs/limitations.md#d15b)). Version 0.4.1 is the first
cover page that reflects those changes.

### 0.3.0-poc → 0.4.0

An adversarial review compared every documented claim against the code. The
methodology was restructured around what the implementation does, and claims
that the code contradicted were withdrawn rather than softened.

**Withdrawn as false.**

- *'`fr_score` is a display field only and is never used as a filter or
  anchor.'* At the time, `src/graph/loader.py` set
  `credibility_prior = "suspect"` if and only if `fr_score < 0.15`, and that
  prior drove the largest severity modulator, so the ranking was substantially
  a language partition. Recorded as [D1](./docs/limitations.md#d1), with a
  dedicated ablation protocol; fixed in `cc258e4`.
- *The score is a renormalized weighted sum of triggered families.* The
  implementation combines per-family p-values by Stouffer's method under
  Benjamini–Hochberg control of the false discovery rate. The weighted sum
  describes bundles shipped before 0.4.0, not the method. **Stouffer with
  Benjamini–Hochberg is canonical.**
- *'Confidence bands propagate through the same combination.'* True of the
  machinery, false of the inputs: only families (b) and (d) receive bootstrap
  intervals. The other bands are constants written in the source
  ([D6](./docs/limitations.md#d6)).
- *Family (d) measures cross-episode recidivism.* There are no episodes in the
  score. It measures out-degree and out-strength on one aggregate forward
  graph.

**Withdrawn as unreproducible.** Every numeric result. The database those
figures came from was decommissioned before the corpus was published, so none
of them can be checked or falsified. The artefacts moved to `archive/` with an
explicit prohibition on citing them.

**Newly disclosed.** Defects verified against the code and recorded in
[`docs/limitations.md`](./docs/limitations.md)—among them the absence of a null
model for family (c), the violation of Stouffer's independence assumption, a
discontinuity in the combiner, `CO_HASHTAG` manufacturing coordination edges,
silent failure in family (f), and two mis-specified evaluation scripts. The
register, not this page, holds the current list.

**Removed from the system.** Six modules documented as part of the method but
imported only by tests (`pockets`, the former `src/registry/` package,
`readiness`, `coordination_fabric`, `dossier/v1`, and `analytical_contract`),
together with their documentation. The mission registry,
`src/missions/registry.py`, is unrelated and live. The analyst interface no
longer embeds a hand-maintained copy of this documentation; the repository is
the single source.

### 0.2.0-poc → 0.3.0-poc

The semantic-coherence family (f) was added to the pipeline; it has never
entered the combined score ([D19](./docs/limitations.md#d19)). Automatic
episode discovery replaced a hand-maintained list. The multi-source gate became
traceable (`gate_families`, migration `0008`). A non-circular validation track
was built.

### 0.1.0 → 0.2.0

The shipped detection core was corrected from a GraphSAGE+LSTM graph neural
network to the explainable per-channel score. The platform became multi-mission.
Infrastructure claims (Neo4j, Docker Compose) were corrected to the implemented
stack.
