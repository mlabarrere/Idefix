# Frontend — the narrative galaxy

The frontend is `webapp/` (React, Vite, TypeScript, Tailwind, Radix). It is a
**static build with no backend**: the app consumes the precomputed JSON bundle
under `webapp/public/data/<mission>/`.

> The scientific documentation **does not live in the interface.** It used to —
> as hand-written TSX that duplicated the Markdown and had already drifted from
> it — and that section was removed. The repository is the single source; the
> app links to it.

## 1. One screen: the galaxy

The core experience is a **single screen** per mission (`/m/<mission>`), three
nested layers on one Cytoscape canvas.

| Layer | Gesture | What happens |
|---|---|---|
| **Galaxy** (default) | — | Nebulae are Leiden communities; golden arcs are bridges. Clicking a nebula blooms it into channels; hexagons are cited domains, deduplicated across links. Filters (credibility, archetype, sphere, node type) plus fly-to search. |
| **Stories** (top banner) | dropdown, phase chips | A story is a set of **named, dated phases** — not an animation. Selecting a phase auto-blooms the relevant spheres, fades everything else to 5%, golds the member channels and frames them. A narrative card shows the account, the key figure, and tier and data-status badges. Escape exits the phase. |
| **Ego-focus** (channel click) | node, table row, or search | The galaxy fades to 5%; what remains is the channel, its direct links (forwards oriented in orange, coordination dashed green, domain citations) and its immediate neighbours, labelled. The drawer opens. Escape or a background click returns. |

**The channel drawer** carries the analytical detail: suspicion score with its
`[lo, hi]` band, tier, interpreted archetype, multi-source gate state, the score
families expandable with a technical definition and per-signal evidence, the
calculation breakdown, narrative attachment, clickable pivots, and the permanent
coverage callout.

Two cautions the interface itself should be read with, both from
[`../limitations.md`](../limitations.md):

- The `[lo, hi]` band is a real bootstrap interval **only** for families (b) and
  (d). For every other family it is a hardcoded constant (D6).
- Suspicion values are max-normalized within a run, so they are comparable
  inside one bundle and **not** across bundles (D8).

## 2. Data — one static bundle per mission

Produced **offline** by the Python pipeline. Nothing is computed at runtime.

```
analyze_communities.py  -> <mission>_snapshot.json    [galaxy]
analyze_porosity.py     -> porosity_snapshot.json     [dated traces]
export_static.py        -> channels_index.json + channels/<id>.json (sharded)
                           + graph.json + episodes/ + manifest.json
build_stories.py        -> stories.json               [narrative selector]
```

Target: `webapp/public/data/<mission>/`. A light index plus **lazy fetch** of one
file per channel on drill-down.

**Bundles are not tracked in this repository** — they are corpus- and
run-specific, so publishing them would ship numbers nobody can regenerate.
Generate them before running the app — the one-command bootstrap does, from the
public corpus ([`../ops/quickstart.md`](../ops/quickstart.md)).

Stories are **discovered in the data, then edited**: derived from porosity
crossings where a crawl exists, editorial (with `data_status: "partial"` shown
in the UI) where it does not.

## 3. Performance

- **Sharded, lazy bundle:** the index loads up front, a channel loads on click.
- **Code splitting:** Cytoscape (~142 KB gzip) is loaded lazily.
- **Bounded view:** the galaxy renders the meta-graph of communities; individual
  channels exist only after a bloom, so the canvas never holds the full node set
  at once.
- Bounded fcose layouts (`numIter`), CSS transitions rather than a continuous
  physics loop outside the nebula "breathing".

## 4. Running it

```bash
cd webapp
npm run dev     # http://localhost:5173
npm run build   # static output -> webapp/dist/
```

## 5. Honesty requirements — non-negotiable

- The **coverage callout** (single-platform blindness) is permanent — sidebar,
  drawer, and a per-mission caveat.
- Tiers **T1 and T2 only**, never T3.
- Stories display their data status (`reconstructed from data`, `editorial`,
  `partial data` with uncrawled handles listed).
- Four epistemic treatments are distinguished visually: computed, hypothesis,
  evidence, limit.
- The interface must not present a number as more certain than
  [`../limitations.md`](../limitations.md) allows.
