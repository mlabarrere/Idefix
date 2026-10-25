# Archived metrics — `russosphere`, June 2026

> **Do not cite these files.** They are kept for provenance only.

These JSON artefacts are the output of a scoring and evaluation run performed in
June 2026 on the `russosphere` corpus. They are archived rather than deleted so
that the project's history stays inspectable, but **no document in this
repository may quote a number from this directory as a result.**

Three independent reasons, any one of which is sufficient:

1. **The state these runs read is not identified.** The PostgreSQL instance
   holding the 3 699 scored channels and the 3 788-node forward graph has been
   decommissioned. A complete snapshot of it survived and is now published as
   dataset `v1.0.0` — see `dataset/DATASHEET.md` — including the derived
   tables (edges, scores) as they stood when it was taken. That does not make
   these files reproducible: which pipeline run produced those derived tables,
   and whether these files were computed from the same state, is not recorded;
   and the bootstrap recomputes the derived tables with the current pipeline
   anyway. A number regenerated from the public corpus is a new result, not a
   check of one of these (`docs/limitations.md` D18).

2. **They were produced by a combiner that is no longer the method.** These runs
   used a renormalized weighted average of triggered family values. The
   implementation in `src/scorer/channel_suspicion.py` combines per-family
   p-values with Stouffer's method under Benjamini-Hochberg FDR control. The
   published numbers were therefore never produced by the statistics the project
   describes.

3. **They embed a language bias that is now treated as a defect.** The scoring
   run inherited `credibility_prior = "suspect"` from `fr_score < 0.15`
   (`src/graph/loader.py`) — that is, from a channel writing in few French
   keywords. `discriminant_organic.json` measures the consequence directly:
   Spearman(suspicion, adversary-linkage) = 0.765 against
   Spearman(suspicion, coordination) = 0.253. The ranking these files describe is
   substantially a ranking by language. See `docs/limitations.md`.

Two further artefacts in this directory are internally inconsistent and are
described in `docs/limitations.md`:

- `episode_recovery.json` — `random_control_recall@k` is an expected *hit count*,
  not a recall, yet it is printed beside a genuine recall. The same file supports
  both "at chance" and "12.35× chance".
- `embedding_discrimination_russosphere.json` — the run embedded channel handles
  (`@username`) rather than message content, so its ROC-AUC of 0.506 measures
  nothing about the semantic family it purports to test.

Current experiment protocols, with their falsification criteria, live in
`docs/experiments/`. Results regenerated from the public corpus (dataset
`v1.0.0`) will be written to `docs/experiments/results/` and are the only
numbers this project stands behind.
