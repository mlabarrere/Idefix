# Frontend — the narrative galaxy

The frontend is `webapp/` (React, Vite, TypeScript, Tailwind, Radix). It is a
**static build with no backend**: the app consumes the precomputed JSON bundle
under `webapp/public/data/<mission>/`.

> The scientific documentation **does not live in the interface.** It used to —
> as hand-written TSX that duplicated the Markdown and had already drifted from
> it — and that section was removed. The repository is the single source; the
> app links to it.

## 1. One screen: the galaxy

The core experience is a **single screen** per mission (the hash route
`#/m/russosphere`, and likewise for each mission), three nested layers on one
Cytoscape canvas. An `analyse` view and a settings view (`parametres`) sit
beside it (`webapp/src/router.tsx`).

| Layer | Gesture | What happens |
|---|---|---|
| **Galaxy** (default) | — | Nebulae are Leiden communities; golden arcs are bridges. Clicking a nebula blooms it into channels; hexagons are cited domains, deduplicated across links. Filters (credibility, archetype, sphere, node type) plus fly-to search. |
| **Stories** (top banner) | dropdown, phase chips | A story is a set of **named, dated phases** — not an animation. Selecting a phase auto-blooms the relevant spheres, fades everything else to 5%, golds the member channels and frames them. A narrative card shows the account, the key figure, and tier and data-status badges. Escape exits the phase. |
| **Ego-focus** (channel click) | node, table row, or search | The galaxy fades to about 7%; what remains is the channel, its direct links (forwards oriented in orange, coordination dashed green, domain citations) and its immediate neighbours, labelled. The drawer opens. Escape or a background click returns. |

**The channel drawer** carries the analytical detail: suspicion score with its
`[lo, hi]` band, tier, interpreted archetype, multi-source gate state, the score
families expandable with a technical definition and per-signal evidence, the
calculation breakdown, narrative attachment, clickable pivots, and the
commenters of the channel's linked discussion group: the IDs or usernames of
its most frequent commenters, with their comment counts. The drawer does not
show whether a channel is flagged.

Two cautions the interface itself should be read with, both from
[`../limitations.md`](../limitations.md):

- The `[lo, hi]` band is a real bootstrap interval **only** for families (b) and
  (d). For every other family it is a hard-coded constant
  ([D6](../limitations.md#d6)).
- Suspicion values are corpus-relative, so they are comparable inside one
  bundle and **not** across bundles ([D8](../limitations.md#d8)).

## 2. Data — one static bundle per mission

Produced **offline** by the Python pipeline. Nothing is computed at runtime.

The stages of `scripts/pipeline.py::STAGES` that write into the bundle:

```text
build_dossier.py              -> dugin_cluster.json            [russosphere only; not displayed]
analyze_communities.py        -> russosphere_snapshot.json     [galaxy; same name for every mission]
analyze_communities_embed.py  -> <mission>_embed_snapshot.json [embedding track]
precompute_galaxy_layout.py   -> x/y positions in both snapshots
analyze_porosity.py           -> porosity_snapshot.json        [russosphere only; read by build_stories]
mine_episodes.py              -> episodes_discovered.json      [russosphere only]
build_gan_footprint.py        -> gan_footprint.json
build_commenters.py           -> commenters.json               [commenter IDs and usernames]
export_static.py              -> manifest.json, channels_index.json, channels/<id>.json,
                                 channels.json, graph.json, themes.json, tasking.json, episodes/
build_stories.py              -> stories.json                  [narrative selector]
```

Target: `webapp/public/data/<mission>/`. A light index plus **lazy fetch** of one
file per channel on drill-down. The galaxy snapshot is computed on the whole
graph, whatever the mission.

**Bundles are not tracked in this repository** — they are corpus- and
run-specific, so publishing them would ship numbers nobody can regenerate.
Generate them before running the app — the one-command bootstrap does, from the
public corpus ([`../ops/quickstart.md`](../ops/quickstart.md)).

Stories are **discovered in the data, then edited**: derived from porosity
crossings where a crawl exists, editorial (with `data_status: "partial"` shown
in the UI) where it does not.

## 3. Performance

- **Sharded, lazy bundle:** the index loads up front, a channel loads on click.
- **Code splitting:** the Cytoscape canvas is loaded lazily
  (`webapp/src/screens/GraphView.tsx`).
- **Bounded view:** the galaxy renders the meta-graph of communities; individual
  channels exist only after a bloom, so the canvas never holds the full node set
  at once.
- No layout runs in the browser: positions are precomputed offline by
  `scripts/precompute_galaxy_layout.py` and drawn with Cytoscape's `preset`
  layout, with CSS transitions rather than a physics loop.

## 4. Running it

```bash
cd webapp
npm run dev     # http://localhost:5173
npm run build   # static output -> webapp/dist/
```

## 5. Honesty requirements — non-negotiable

- The **coverage callout** (single-platform blindness) must be visible. It is
  not today: the banner was removed, and only the `gan` footprint view shows a
  caveat ([D31](../limitations.md#d31)).
- Tiers **T1 and T2 only**, never T3.
- Stories display their data status (`reconstructed from data`, `editorial`,
  `partial data` with uncrawled handles listed).
- Four epistemic treatments are distinguished visually: computed, hypothesis,
  evidence, limit.
- The interface must not present a number as more certain than
  [`../limitations.md`](../limitations.md) allows.
