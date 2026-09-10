# Idéfix — interface analyste multi-mission (webapp)

Analyst interface: **React + Vite + TypeScript + TailwindCSS v4 + Radix UI**
(free, MIT — no commercial dependency). **Static build, no backend**: the app
consumes JSON bundles produced offline by `scripts/export_static.py`. The
**Telegram-only** scope caveat is permanently displayed.

> Those bundles are **not tracked in this repository** — they are corpus- and
> run-specific, so publishing them would ship numbers nobody can regenerate.
> Generate one before running the app. See
> [`../docs/limitations.md`](../docs/limitations.md) Part III.

> Stack note: Catalyst (Tailwind Plus, commercial) is not required. The
> equivalent UX — sidebar, navbar, mission switcher, dense tables, dialogs,
> badges — is built on Radix primitives plus Tailwind.

## Lancer

```bash
cd webapp
npm install
npm run dev        # serveur de dev
npm run build      # build statique -> dist/
npm run typecheck  # vérification TypeScript
```

## Alimenter en données (par mission)

L'app lit `public/data/<mission>/…` (repli sur `public/data/<file>` pour
l'ancien bundle plat). `export_static.py` et `build_stories.py` ciblent
**par défaut** `webapp/public/data/<mission>/` :

```bash
# Depuis la racine du dépôt, après crawl + build_edges + build_scores :
python scripts/export_static.py                  # mission défaut (russosphere)
python scripts/build_stories.py                  # histoires (sélecteur narratif)
python scripts/export_static.py --mission gan    # bundle GAN
python scripts/build_stories.py --mission gan
```

Sans données, l'app affiche des **états vides propres** (et la commande à lancer).

## État (2026-06-10)

**Single-screen « galaxie narrative »** (cf. `docs/frontend.md`) :
- **Galaxie** = écran d'accueil de mission : nébuleuses-communautés, bloom au
  clic, domaines multi-liés, filtres, recherche fly-to ;
- **StoryBar** : dropdown d'histoires + **phases nommées avec dates** ; une phase
  auto-bloom les sphères concernées, estompe le reste à 5 %, cadre les membres ;
- **Ego-focus** : clic canal ⇒ galaxie effacée à 5 %, voisins +1 étiquetés ;
- **Drawer** : score explicable (5 familles + définitions techniques + détail du
  calcul), tier T1/T2, rattachement narratif, CoverageCallout ;
- Écrans secondaires : Épisodes · Canaux (tableaux).

## Performance (étoile polaire)

Bundle shardé (index léger + fetch lazy par canal) · Cytoscape **code-splitté**
(≈142 Ko gzip différé) · pas de jumeaux `.js` · galaxie = méta-graphe borné,
les canaux n'existent qu'au bloom. Tenir ces budgets à chaque évolution.
