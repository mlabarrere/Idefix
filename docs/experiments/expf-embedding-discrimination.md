# Experiment f — Embedding discrimination

**Status:** `NOT YET RUN` — the script must be fixed before it tests anything
**Script:** `scripts/eval_embedding_discrimination.py`
**Artefact:** `results/embedding_discrimination_<mission>.json`

## Question

Does semantic family (f) separate an external organic-French baseline from the
scored population?

## Hypothesis

Channel embeddings place organic French outlets and scored channels in
distinguishable regions of the embedding space.

## Falsification criterion

Fixed in the script: the family is **not discriminative** if

```
ROC-AUC <= 0.7    OR    silhouette <= 0.3
```

## The defect that must be fixed first

`eval_embedding_discrimination.py:77`:

```python
texts = [f"@{u}" for u in all_usernames]
```

The experiment embeds **channel handles** — the literal string `@somechannel` —
and nothing else. The deployed family (f) embeds the mean of a channel's 15
longest **messages** (`05-semantic-family.md` §5.1).

So the script does not test the family it names. A near-chance ROC-AUC on handle
strings is the expected outcome and carries no information about the method: two
handles are not separable because handles are arbitrary tokens, not because the
semantic signal is weak.

The June 2026 run produced exactly that, and it was recorded as a weak result
for family (f). That reading was wrong. The artefact is quarantined and may not
be cited — see `archive/2026-06-russosphere/README.md`.

**Fix:** encode the same channel representation the scorer uses — mean of the 15
longest messages, L2-normalized, via `src/embed/encoder.py` with the same cache —
so that the experiment and the deployed family share one code path.

## Second precondition

Before interpreting any output, verify that the mission's baseline and adversary
anchors **resolved**. On failure `embedding_signals.py:98` substitutes
`np.zeros(384)`, which silently sets `baseline_distance = 1.0` for every channel
(`../limitations.md` D10). A run with unresolved anchors will produce numbers
that look valid and mean nothing.

## Method

Encode the external organic-FR baseline channels and the scored channels with
the deployed representation. Report ROC-AUC of the baseline-versus-scored
separation, silhouette, and centroid separation.

## Command

```bash
uv run python scripts/bootstrap_baseline.py
uv run python scripts/eval_embedding_discrimination.py --mission <mission>
```

## Interpretation limits

The organic-FR baseline supplies **anchors**, not the organic *negatives*
Experiment 3 needs. A pass here would show that the embedding space distinguishes
mainstream French outlets from the scored corpus — which is a much weaker claim
than distinguishing hostile from organic coordination, and must not be reported
as the latter.
