# Idéfix — interface analyste multi-mission (webapp)

Interface analyste **React + Vite + TypeScript + TailwindCSS v4 + Headless UI**
(composants libres, MIT — pas de dépendance commerciale). **Build statique,
sans backend** : l'app consomme les bundles JSON produits hors-ligne par
`scripts/export_static.py`. Périmètre **Telegram-only** affiché en permanence.

> Choix de stack (2026-06-09) : Catalyst (Tailwind Plus, commercial) n'est PAS
> requis ; l'UX équivalente (sidebar, navbar, switcher de mission, tables denses,
> dialogs, badges) est bâtie sur Headless UI + Tailwind. Migrable vers Catalyst
> ultérieurement si une licence est acquise.

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
