# Demo runbook — the narrative galaxy

The demo is **fully static**: the webapp reads a precomputed bundle. No
database, no Python server, no Telegram call while presenting.

## 0. Before the demo — generate the bundle

Analyst bundles are **not** in the repository (they are corpus-specific and
would publish numbers nobody can regenerate). Generate one first, with the
database running — see [`install.md`](./install.md) §3.

```bash
uv run python scripts/build_edges.py
uv run python scripts/tag_france.py
uv run python scripts/build_scores.py        --mission russosphere
uv run python scripts/analyze_communities.py --mission russosphere
uv run python scripts/analyze_porosity.py    --mission russosphere
uv run python scripts/export_static.py       --mission russosphere
uv run python scripts/build_stories.py       --mission russosphere
```

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
- No result is currently reproducible — the corpus behind the earlier figures
  has been decommissioned, and those artefacts are quarantined.
- Two gaps bound every stronger claim, both requiring human annotation: no
  organic-coordination corpus (the negative class), and no real external gold.
- There is a known language bias in the credibility prior (defect D1) that
  materially shapes the ranking, with an ablation protocol written to measure it.

## 4. If something breaks

- Blank page or empty states → the bundle is missing. Re-run §0.
- `npm run dev` unavailable → run `npm install` inside `webapp/` first.
- The database is needed **only** to regenerate the bundle, never during the
  demo itself.
