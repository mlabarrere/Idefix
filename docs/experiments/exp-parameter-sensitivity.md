# Experiment — Parameter sensitivity

**Status:** `NOT YET RUN` — script to be written
**Artefact:** `results/parameter_sensitivity.json`
**Addresses:** [D14](../limitations.md#d14)

## Question

Do the free parameters carry the results?

## Why this experiment exists

The pipeline contains a long list of constants that the literature does not
justify and that no experiment has probed. They were chosen by inspection of the
output — in at least one case explicitly so: the Leiden resolution was raised to
1.6 because at 1.0 the clusters were too large to label honestly.

A result that changes qualitatively when an unjustified constant moves by a
plausible amount is not a result. This experiment establishes which conclusions
are robust and which are artefacts of tuning.

## Hypothesis

The reported structure is **stable** under plausible perturbation of the free
parameters.

## Falsification criterion

Fixed before the run. For each parameter, sweep the range below and compare each
run against the default. The hypothesis is **falsified** for that parameter if:

```text
Jaccard@50(top-50 suspicion) < 0.70    (score parameters)
NMI(partition, default_partition) < 0.70    (community parameters)
```

## Parameters and sweeps

| Parameter | Default | Sweep | Location |
|---|---|---|---|
| `EMB_SIM` k | 5 | 3, 5, 10, 20 | `src/embed/community.py::add_embedding_edges` |
| `EMB_SIM` threshold | 0.5 | 0.4, 0.5, 0.6, 0.7 | same |
| `EMB_SIM` weight scale | 3.0 | 1.0, 3.0, 5.0 | same |
| Leiden resolution | 1.6 | 0.8, 1.0, 1.4, 1.6, 2.0 | `scripts/analyze_communities.py::detect_communities` |
| `TRIGGER_THRESHOLD` | 0.3 | 0.2, 0.3, 0.4, 0.5 | five modules, [D14](../limitations.md#d14) |
| Family weights | .30/.25/.30 | uniform; each family +/-50% | `src/scorer/channel_suspicion.py::BASE_FAMILY_WEIGHTS` |
| Coordination window | 72 h | 24, 48, 72, 168 h | `src/graph/edges.py::DEFAULT_WINDOW_SECONDS` |
| Severity bounds | .20/.15/.20 | all zero; doubled | `src/scorer/channel_suspicion.py::MAX_REFORWARD_BOOST` and its two neighbours |

The 'all severity bounds zero' run is worth reporting on its own: it isolates the
structural base score from every modulator.

## Ablations, not just sweeps

Two structural ablations belong here because they test whether a *component*
carries the result rather than a *value*:

- **Drop `CO_HASHTAG`** and recompute. Family (c) triggers on two distinct edge
  types alone, so if `CO_HASHTAG` is doing the work the coordination family is
  largely noise ([D5](../limitations.md#d5)).
- **Swap the embedding model** — MiniLM-L12-v2 against e5 and MPNet. No ablation
  has ever been run, so it is unknown whether family (f) and the embedding
  community track depend on the specific encoder.

## Command

No script exists yet. The planned one, `scripts/eval_parameter_sensitivity.py`, should take
the mission as an argument (`--mission russosphere`) and write the artefact
above; until it is written there is no command to run.

## What this would establish

Which reported structure survives its own tuning. A parameter that fails the
criterion is not necessarily wrong, but every conclusion resting on it must
carry that dependency explicitly — and it becomes a candidate for principled
selection rather than inspection.
