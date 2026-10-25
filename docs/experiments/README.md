# Experiments

This directory holds **falsification protocols**. Each one states a hypothesis,
a criterion that would falsify it, the exact command that tests it, and the
artefact the command must produce.

## Current status

**No experiment has a current result.** A corpus that a third party can rebuild
now exists — dataset `v1.0.0`, restored and recomputed by
`scripts/bootstrap.py` (`../ops/quickstart.md`) — but no protocol has been run
against it yet. Historical artefacts are quarantined in
`archive/2026-06-russosphere/` and may not be cited; they came from an earlier
pipeline and recomputing is not expected to reproduce them — see
`../limitations.md` Part III and D18.

`results/` is empty. It will contain only figures regenerated from the public
corpus by the current pipeline — never values read from the derived tables the
snapshot carries (`../limitations.md` D18) — each recording the commit and
dataset version that produced it. One known obstacle stands before the first
run: the evaluation harness still cannot read the local database
(`../limitations.md` D12).

## The contract

A protocol page in this directory must contain, in this order:

1. **Question** — what is being asked, in one sentence.
2. **Hypothesis** — the claim under test, stated so it can fail.
3. **Falsification criterion** — a numeric threshold decided *before* the run.
   Without one, the experiment is a demonstration, not a test.
4. **Method** — inputs, statistic, null or control.
5. **Command** — the exact invocation.
6. **Artefact** — the path under `results/` the run must write.
7. **Interpretation limits** — what a pass would and would not establish.
8. **Status** — `NOT YET RUN`, or a link to the artefact.

Two rules follow from this repository's history:

- **No number appears in prose without an artefact under `results/`.** CI
  enforces this.
- **A falsification criterion is fixed before the run**, not after seeing the
  output.

## Index

| Protocol | Question | Status |
|---|---|---|
| [exp1-centrality-ablation.md](./exp1-centrality-ablation.md) | Is the score just centrality in disguise? | `NOT YET RUN` |
| [exp2-episode-recovery.md](./exp2-episode-recovery.md) | Does the ranking recover a documented operation? | `BLOCKED` — no real external gold |
| [exp3-hostile-vs-organic.md](./exp3-hostile-vs-organic.md) | Does it separate hostile coordination from organic coordination? | `BLOCKED` — no negative class |
| [expf-embedding-discrimination.md](./expf-embedding-discrimination.md) | Does family (f) separate organic-FR from scored channels? | `NOT YET RUN` — script must be fixed first |
| [exp-language-prior-ablation.md](./exp-language-prior-ablation.md) | How much of the ranking is explained by the language prior? | `NOT YET RUN` — script to be written |
| [exp-parameter-sensitivity.md](./exp-parameter-sensitivity.md) | Do the free parameters carry the results? | `NOT YET RUN` — script to be written |

`BLOCKED` means the experiment cannot be run at all until a missing input
exists, and the missing input requires human annotation rather than
engineering. It is not a scheduling status.
