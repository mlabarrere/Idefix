# Experiments

This directory holds **falsification protocols**. Each one states a hypothesis,
a criterion that would falsify it, the exact command that tests it, and the
artefact the command must produce.

## Current status

**No experiment has a current result.** The corpus behind every historical
figure has been decommissioned, so nothing published so far can be regenerated
or checked. Historical artefacts are quarantined in
`archive/2026-06-russosphere/` and may not be cited — see
`../limitations.md` Part III.

`results/` is empty. It will contain only figures produced against a corpus that
a third party can rebuild.

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
| [exp-language-prior-ablation.md](./exp-language-prior-ablation.md) | How much of the ranking is explained by the language prior? | `NOT YET RUN` |
| [exp-parameter-sensitivity.md](./exp-parameter-sensitivity.md) | Do the free parameters carry the results? | `NOT YET RUN` |

`BLOCKED` means the experiment cannot be run at all until a missing input
exists, and the missing input requires human annotation rather than
engineering. It is not a scheduling status.
