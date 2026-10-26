# Idéfix web app

The multi-mission analyst interface. It is a static build with no backend: the
app reads JSON bundles produced offline by `scripts/export_static.py` and the
other pipeline stages, and does all filtering, search, and neighbourhood
computation in the browser. The Telegram-only scope caveat is always on
screen.

**Stack:** React, Vite, TypeScript, Tailwind CSS v4, and Radix UI primitives
composed in the shadcn/ui pattern, with Cytoscape.js for the graph, i18next for
translations, and React Router. Every dependency is free and open-source; no
commercial component library is needed.

For a full setup, database and pipeline included, follow
[`docs/ops/quickstart.md`](../docs/ops/quickstart.md). This page covers the web
app on its own.

## Requirements

- **Node.js** `^20.19.0` or `>=22.12.0`, the range Vite requires. CI uses
  Node.js 20.
- **npm**, which ships with Node.js.

## Commands

Run every command from `webapp/`. Install the exact locked dependencies first:

```bash
npm ci
```

| Command | What it does |
|---|---|
| `npm run dev` | Starts the Vite development server on <http://localhost:5173>. |
| `npm run build` | Pulls snapshots and the scored bundle from Supabase when credentials are set (see [Building](#building)), then builds the static site into `dist/`. |
| `npm run preview` | Serves the contents of `dist/` locally. |
| `npm run typecheck` | Type-checks with `tsc --noEmit`. |
| `npm run lint` | Runs ESLint. |
| `npm run i18n:parity` | Checks that every locale has every key, with no empty or missing value and no drifted placeholder. |
| `npm run ui:contract` | Design-system ratchet: violation counts may only go down from `ui-contract-baseline.json`. |
| `npm run check:galaxy-guard` | Self-test of the rule that stops a snapshot without layout coordinates from overwriting a precomputed one. |
| `npm run test:e2e` | Playwright smoke tests in Chromium. |

All but `dev`, `build`, `preview`, and `check:galaxy-guard` run in CI, in the
`ui-gate` workflow; see [`CONTRIBUTING.md`](../CONTRIBUTING.md#checks).

### End-to-end tests

Playwright starts the development server itself. It needs a bundle to display
and a Chromium browser. From the repository root, generate the synthetic
bundle:

```bash
uv run --no-project python scripts/make_fixture_bundle.py
```

Then, from `webapp/`, install Chromium once and run the tests:

```bash
npx playwright install chromium
```

```bash
npm run test:e2e
```

## Data

The app reads `public/data/<mission>/<file>`, falling back to
`public/data/<file>` for the old flat layout. The bundles are **not tracked in
this repository**: they are specific to one corpus and one run, so publishing
them would ship numbers nobody can regenerate (see
[`docs/limitations.md`](../docs/limitations.md), Part III). Without a bundle,
the app shows clean empty states that name the command to run.

There are two ways to get one:

- **The real bundle**, regenerated from the public corpus by the pipeline. The
  quickstart covers it; to rebuild one mission's bundle on the local
  database, run this from the repository root:

  ```bash
  uv run --extra embed python scripts/bootstrap.py pipeline --mission gan
  ```

- **A synthetic bundle**, deterministic and obviously fake, enough to explore
  the interface; nothing in it may be cited. Generate it with
  `make_fixture_bundle.py`, as in [End-to-end tests](#end-to-end-tests).

`scripts/export_static.py` and `scripts/build_stories.py` write to
`webapp/public/data/<mission>/` by default; see
[`scripts/README.md`](../scripts/README.md).

## Building

`npm run build` runs two pre-build steps before `vite build`.
`scripts/pull-snapshots.mjs` fetches the community snapshots, and
`scripts/pull-bundle.mjs` rebuilds the scored bundle from Supabase
`channel_scores`, both into `public/data/`. They are meant for the hosted
Vercel build and need `SUPABASE_URL` and `SUPABASE_KEY`. Without those
variables they print a warning and leave the local bundle untouched, so a
local build uses whatever is in `public/data/`. A snapshot without layout
coordinates never replaces one that has them.

> [!WARNING]
> `SUPABASE_KEY` is a service-role key. Set it only in the build environment;
> it must never reach the browser bundle or the repository.

## The interface

Routes are scoped by mission: `/m/russosphere`, `/m/gan`, and so on. The
detailed specification is in [`docs/product/frontend.md`](../docs/product/frontend.md),
and translation in [`docs/product/i18n.md`](../docs/product/i18n.md).

- **Galaxy** (`/m/<mission>`), the mission's home screen: communities drawn as
  nebulae that bloom into their channels on a click, multi-linked domains,
  filters, and search that flies to a channel.
- **Story bar**: a list of stories, each made of named, dated phases. Selecting
  a phase blooms the communities involved, dims the rest, and frames the
  member channels.
- **Ego focus**: clicking a channel fades the galaxy and labels its immediate
  neighbours.
- **Channel drawer**: the explainable score (each family, with its technical
  definition and the detail of the computation), the tier (T1 or T2), the
  channel's place in the stories, and the coverage callout.
- **Analysis** (`/m/<mission>/analyse`): the snapshot's statistics beside the
  full channel table, filterable and sortable.
- **Settings** (`/m/<mission>/parametres`): display options, including
  whether the galaxy shows the analytics communities or the communities
  grouped by embeddings.

## Performance budget

Keep these properties with every change:

- The bundle is sharded: a light index, and each channel's detail fetched
  lazily.
- Cytoscape.js is code-split: it loads with the galaxy, not with the app
  shell.
- No legacy `.js` twins are emitted.
- The galaxy draws a bounded meta-graph; channels are created only when a
  community blooms.
