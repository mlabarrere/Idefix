# Demo runbook: the narrative galaxy

The demo is **fully static**: the interface reads a precomputed bundle. While
you present, nothing needs the database or a Python server, and nothing calls
Telegram.

<a id="generate-the-bundle"></a>

## 🚀 Before the demo: generate the bundle

The analyst bundles are **not** in the repository: they are specific to a
corpus and a run, and committing them would publish numbers nobody could
regenerate. Generate them from the public corpus by following the
[quickstart](./quickstart.md) up to the end of
[step 6](./quickstart.md#step-6). Once the Python environment is installed, one
command fetches the dataset, restores the database, and runs the pipeline,
without starting the interface:

```bash
uv run python scripts/bootstrap.py --no-webapp
```

The pipeline takes about an hour, so do this well before the demo. If the
database is already restored, re-running the pipeline alone is enough:

```bash
uv run python scripts/bootstrap.py pipeline
```

Then serve the interface, either with the dev server:

```bash
cd webapp
npm run dev
```

or as a production build, which you can serve from any static web server:

```bash
cd webapp
npm run build
npm run preview
```

Check it once in the browser you will present from, at
<http://localhost:5173> (dev server) or <http://localhost:4173> (preview).

## 🧭 The thread, in about five minutes

1. **The galaxy.** The interface opens on the `russosphere` galaxy: community
   nebulae reconstructed from a single legitimate seed channel. Hover for
   tooltips, and click a nebula to bloom it; golden bridges connect
   communities.
2. **The story.** Pick a narrative in the story bar. It has dated phases;
   clicking a phase dims the galaxy and highlights the channels on that axis in
   gold, and the narrative card recounts the trace with the observed relay
   delays.
3. **The drill-down.** Click a channel: the view focuses on its immediate
   neighbours, and a drawer shows the explainable score (each family's value
   and definition), its place in the narrative, the state of the multi-source
   gate, and the coverage callout. That is the full chain:
   **galaxy → story → channel → evidence.**
4. **A second mission.** Pick another mission in the switcher at the top of
   the sidebar, to show that the engine is a configuration, not a fork. Each
   mission carries its own caveat.

## 🧭 What to say

- 'We do not judge content. We **reconstruct diffusion structure**.'
- 'Every number unfolds to its evidence: the score is **explainable**, not a
  black box.'
- 'Telegram only: we see the **seeding** layer, not mass amplification. That
  caveat is on every screen.'
- 'T1 and T2 only. Attributing a campaign to a sponsor (T3) is out of scope.'

## 🧪 What to say if asked about validation

Do not overclaim. The honest position is short, and it is in
[the limitations](../limitations.md):

- The system is a **T1 demonstrator**, not a validated manipulation detector.
- The corpus is public (dataset `v1.0.0`), and anyone can rebuild what the demo
  shows from it. No experiment has yet been re-run on it, so there is no
  validation figure to quote; the earlier figures are quarantined and came from
  an earlier pipeline.
- Two gaps bound every stronger claim, and both need human annotation: there is
  no corpus of organic coordination (the negative class), and no real external
  gold standard.
- The credibility prior used to be a language partition
  ([D1](../limitations.md#d1)). The code is fixed, but how much the ranking
  moved has not been measured; the ablation protocol that measures it can now
  run on the public corpus.

## 🩺 If something breaks

| Symptom | Fix |
|---|---|
| Blank page or empty states | The bundle is missing: re-run [Before the demo](#generate-the-bundle) ([details](./troubleshooting.md#blank-page)) |
| `npm run dev` fails with `vite` not found | Run `npm ci` in `webapp/` first |
| Port 5173 is taken | Vite picks the next free port; open the `Local:` URL it prints ([details](./troubleshooting.md#webapp-port)) |

The database is needed **only** to regenerate the bundle, never during the demo
itself.
