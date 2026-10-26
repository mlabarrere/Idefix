# Idéfix methodology

| Field | Value |
|---|---|
| Version | 0.4.1 |
| Date | 2026-10-26 |
| Status | Pre-publication |
| Supersedes | 0.4.0 (2026-09-10) |

This is the versioned cover page of the Idéfix methodology. It declares which
documents make up the method at this version, states the claim the project
stands behind, and records the version history. **The method itself lives in
[`docs/method/`](./docs/method/).**

<a id="methodology-hash"></a>

## What the methodology hash covers

The dossier schema defines `methodology_version_hash`, the first eight
hexadecimal characters of the SHA-256 of this file
(`src/shared/dossier.py::get_methodology_version_hash`). The path of this file
is stable for that reason. The hash is a far weaker chain-of-custody mark than
earlier versions of this page claimed:

- **No output carries it today.** The static bundles and their manifests carry
  a fixed version string, `scripts/export_static.py::METHODOLOGY_VERSION`,
  which does not follow this page; the one dossier the pipeline writes,
  `dugin_cluster.json`, validates the hash and then leaves it out
  ([D20](./docs/limitations.md#d20)).
- **It covers this file only.** A change to `docs/method/` or to the code is
  invisible to it unless this page is revised too
  ([D23](./docs/limitations.md#d23)).
- **It depends on line endings.** The function hashes the bytes of the working
  copy, so a checkout that converts line endings to CRLF (Git's
  `core.autocrlf` on Windows) yields a different hash for the same commit
  ([D27](./docs/limitations.md#d27)). The hash recorded for each version in
  [`CHANGELOG.md`](./CHANGELOG.md) is computed on the file's LF bytes, as Git
  stores them.

> [!WARNING]
> A methodology revision is therefore not detectable from an output. Compare
> the commit that produced an output, not its methodology field.

<a id="documents"></a>

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
annotations) is not part of this list. It governs human annotation, not the
score, and it has its own provenance hash
(`src/labeling/io.py::LABELING_METHODOLOGY_FILES`).

<a id="standing-claim"></a>

## Standing claim

> [!IMPORTANT]
> Idéfix is defensible as a **T1 demonstrator**: it reconstructs observable
> diffusion structure on Telegram public channels and presents it with
> per-signal evidence. It is **not** a validated manipulation detector, and no
> output is presented as more than T1 or T2.

Two gaps bound every stronger claim, and neither is an engineering problem.
Both require human annotation: a corpus of **organic** coordination to serve as
the negative class, and a **real** external seed list for a documented
operation ([L4](./docs/limitations.md#l4), [L5](./docs/limitations.md#l5)).

**The corpus is reproducible; no result has been regenerated from it yet.** The
complete database snapshot is published as dataset `v1.0.0`
([`dataset/`](./dataset/)), and `scripts/bootstrap.py` rebuilds every derived
table and bundle from it. That snapshot includes personal data: the
identifiers, usernames and text of people who commented in public discussion
groups ([`dataset/DATASHEET.md`](./dataset/DATASHEET.md)). Figures published
before version 0.4.0 are quarantined in [`archive/`](./archive/) and may not be
cited, so [`docs/experiments/`](./docs/experiments/) holds protocols, not
results.

<a id="version-history"></a>

## Version history

<a id="v0-4-1"></a>

### 0.4.0 → 0.4.1

A documentation release. **The method did not change in 0.4.1, and no ranking
moved.** Where the documentation claimed behaviour that the code lacks, the
documentation was rewritten to what the code does and the gap was registered as
a defect; the code fixes are separate, later, versioned changes.

**Withdrawn as false.**

- *Family (f) is active and can help a channel cross the multi-source gate.*
  The pipeline does not compute it, and even when `build_scores.py
  --embeddings` computes it, its result reaches neither the combiner, nor the
  gate, nor the tier, nor the bundle. It is computed, not scored
  ([D19](./docs/limitations.md#d19)).
- *Every export embeds the hash of this page.* None does: bundles carry a
  static version string, and the dossier drops the hash it computes
  ([D20](./docs/limitations.md#d20)). The hash would ignore `docs/method/` in
  any case ([D23](./docs/limitations.md#d23)).
- *No escalated severity without at least two triggered families.* The
  severity factor multiplies every channel's base score, whether or not the
  channel meets the gate ([D21](./docs/limitations.md#d21)).
- *Deletions are detected by polling.* Nothing sets `messages.is_deleted`
  ([D22](./docs/limitations.md#d22)).
- *The coverage callout is permanently visible in the analyst interface.* Every
  bundle manifest carries it, but the interface no longer displays it
  ([D31](./docs/limitations.md#d31)).
- *Member identifiers are never collected.* Channel member lists are not, but
  the identifiers, usernames and text of commenters in public linked
  discussion groups are collected, published in dataset `v1.0.0`, and partly
  copied into the analyst bundle.

**Clarified.** 'Flagged' has one meaning: the set of channels that
Benjamini–Hochberg control rejects at the mission's `alpha`. It is independent
of the multi-source gate, which a channel *meets*.

**Recorded late.** Commit `cc258e4` (2026-09-10) changed the method after the
0.4.0 text was written, without a version bump: the credibility prior became
evidence-based instead of a language partition
([D1](./docs/limitations.md#d1)), the combiner's discontinuity at zero was
removed ([D4](./docs/limitations.md#d4)), `n_bootstrap` rose from 100 to 1,000
([D7](./docs/limitations.md#d7)), two evaluation scripts were corrected
([D11](./docs/limitations.md#d11)), and a channel with no edges no longer
scores the maximum in family (b) ([D15b](./docs/limitations.md#d15b)). Version
0.4.1 is the first cover page that reflects those changes. The size of the
resulting ranking change has not been measured.

<a id="v0-4-0"></a>

### 0.3.0-poc → 0.4.0

An adversarial review compared every documented claim against the code. The
methodology was restructured around what the implementation does, and claims
that the code contradicted were withdrawn rather than softened.

**Withdrawn as false.**

- *'`fr_score` is a display field only and is never used as a filter or
  anchor.'* At the time, `src/graph/loader.py` set
  `credibility_prior = "suspect"` if and only if `fr_score < 0.15`, and that
  prior drove one of the two largest severity modulators, so the ranking was
  substantially a language partition. Recorded as
  [D1](./docs/limitations.md#d1), with a dedicated ablation protocol, and fixed
  in `cc258e4`.
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
of them can be checked or falsified. The artefacts moved to `archive/`, which
may not be cited.

**Newly disclosed.** Defects verified against the code and recorded in
[`docs/limitations.md`](./docs/limitations.md), among them the absence of a
null model for family (c), the violation of Stouffer's independence
assumption, a discontinuity in the combiner, `CO_HASHTAG` manufacturing
coordination edges, silent failure in family (f), and two mis-specified
evaluation scripts. The register, not this page, holds the current list.

**Removed from the system.** Six modules documented as part of the method but
imported only by tests (`pockets`, the former `src/registry/` package,
`readiness`, `coordination_fabric`, `dossier/v1` and `analytical_contract`),
together with their documentation. The mission registry,
`src/missions/registry.py`, is unrelated and live. The analyst interface no
longer embeds a hand-maintained copy of this documentation; the repository is
the single source.

<a id="v0-3-0"></a>

### 0.2.0-poc → 0.3.0-poc

The semantic-coherence family (f) was added to the scorer. It was described
as part of the score; it has never entered it
([D19](./docs/limitations.md#d19)). Automatic episode discovery replaced a
hand-maintained list. The multi-source gate became traceable (`gate_families`,
Alembic revision `0008`). A non-circular validation track was built.

<a id="v0-2-0"></a>

### 0.1.0 → 0.2.0-poc

The shipped detection core was corrected from a GraphSAGE+LSTM graph neural
network to the explainable per-channel score. The platform became
multi-mission. Infrastructure claims, among them a Neo4j graph database, were
corrected to the stack as then implemented.
