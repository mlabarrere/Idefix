# Demo runbook — the narrative galaxy

The demo is **fully static**: the webapp reads a precomputed bundle. No
database, no Python server, no Telegram call while presenting.

## 0. Before the demo — generate the bundle

Analyst bundles are **not** in the repository (they are corpus-specific and
would publish numbers nobody can regenerate). Generate them from the public
corpus first — see [`quickstart.md`](./quickstart.md):

```bash
uv run --extra embed python scripts/bootstrap.py --no-webapp   # fetch, restore, run the pipeline
```

If the database is already restored, re-running only the pipeline is enough:
`uv run --extra embed python scripts/bootstrap.py pipeline` (or `make pipeline`).

Then `cd webapp && npm run dev`, or `npm run build` and serve `dist/`.

## 1. The thread — about five minutes

1. **Mission selection.** The entry page shows "one engine, N missions", each
   card carrying its own caveat.
2. **The galaxy.** Community nebulae reconstructed from a single legitimate
   seed channel. Hover for tooltips, click a nebula to bloom it; golden bridges
   connect communities.
3. **The story.** *Stories* → pick a narrative. Dated phases; clicking a phase
   dims the galaxy, highlights the channels on that axis in gold, and the
   narrative card recounts the trace with observed relay delays.
4. **The drill-down.** Click a channel: ego-focus on its immediate neighbours,
   plus a drawer with the explainable score (per-family values and
   definitions), its place in the narrative, the multi-source gate state, and
   the coverage callout. That is the full chain —
   **galaxy → story → channel → evidence.**
5. **A second mission.** Switch missions to show that the engine is a
   configuration, not a fork.

## 2. What to say

- "We do not judge content. We **reconstruct diffusion structure**."
- "Every number unfolds to its evidence — the score is **explainable**, not a
  black box."
- "Telegram only: we see the **seeding** layer, not mass amplification. That
  caveat is on every screen."
- "T1 and T2 only. Attribution to a sponsor (T3) is out of scope."

## 3. What to say if asked about validation

Do not overclaim. The honest position is short and it is in
[`../limitations.md`](../limitations.md):

- The system is a **T1 demonstrator**, not a validated manipulation detector.
- The corpus is public (dataset `v1.0.0`) and anyone can rebuild what the demo
  shows from it. No experiment has yet been re-run on it, so there is no
  validation figure to quote; the earlier figures are quarantined and came from
  an earlier pipeline.
- Two gaps bound every stronger claim, both requiring human annotation: no
  organic-coordination corpus (the negative class), and no real external gold.
- The credibility prior used to be a language partition (defect D1). The code
  is fixed, but how much the ranking moved has not been measured; the ablation
  protocol that measures it can now run on the public corpus.

## 4. If something breaks

- Blank page or empty states → the bundle is missing. Re-run §0.
- `npm run dev` unavailable → run `npm ci` inside `webapp/` first.
- The database is needed **only** to regenerate the bundle, never during the
  demo itself.
