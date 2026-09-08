# Frontend Idéfix — la galaxie narrative (P6)

> **Refonte 2026-06-10.** Le frontend est **`webapp/`** (React + Vite + TS +
> Tailwind + Headless UI), **build statique sans backend** : l'app consomme le
> bundle JSON précalculé `webapp/public/data/<mission>/`. Le frontend HTML/JS
> legacy (`frontend/`) et le serveur FastAPI (`src/api/`) ont été **supprimés**
> (Lot 0 d'allègement, 2026-06-10). Spec de design : UX rév. 2
> (`_bmad-output/planning-artifacts/ux-design-specification.md`).

---

## 1. Single-screen : la galaxie

L'expérience cœur tient sur **un seul écran** par mission (`/m/<mission>`) —
trois couches imbriquées sur le même canvas Cytoscape :

| Couche | Geste | Ce qui se passe |
|---|---|---|
| **Galaxie** (défaut) | — | Nébuleuses = communautés (Leiden), arcs-ponts dorés, fond étoilé. Clic nébuleuse → bloom (éclosion en canaux) ; hexagones = domaines cités, dédupliqués multi-liés. Filtres (crédibilité / archétype / sphère / type de nœud) + recherche fly-to. |
| **Histoires** (bandeau narratif haut) | dropdown + chips de phases | Une histoire = des **phases nommées AVEC dates** (pas d'animation). Sélectionner une phase **auto-bloom** les sphères concernées, **estompe le reste à 5 %**, met en or les canaux membres et cadre dessus. Carte narrative (récit + chiffre clé + badges T1/T2 et statut de données). Escape ⇒ quitte la phase. |
| **Ego-focus** (clic canal) | clic nœud / tableau / recherche | La galaxie **s'efface à 5 %** ; restent le canal central, ses liens directs (forward orange orienté · coordination verte pointillée · citations de domaines) et ses voisins +1, étiquetés. Le **drawer** s'ouvre. Escape / clic fond ⇒ retour. |

**Le drawer canal** (clic) garde toute la richesse analytique : score de suspicion
+ bande [lo–hi], tier T1/T2, archétype interprété, verrou multi-source, **5
familles dépliables avec DÉFINITION technique + évidence par signal**, « détail
du calcul » (poids × valeur, boosts de sévérité), **rattachement narratif**
(« Dans le récit — histoire X → phase Y »), interactions cliquables (pivot), et
la **CoverageCallout** permanente (cécité Telegram-only).

## 2. Données — bundle statique par mission (zéro infra)

Produit **offline** par le pipeline Python (aucun appel runtime) :

```
analyze_communities.py  → russosphere_snapshot.json   [galaxie]
analyze_porosity.py     → porosity_snapshot.json      [traces RU→FR datées]
export_static.py        → channels_index.json + channels/<id>.json (shardé)
                          + graph.json + episodes/ + manifest.json
build_stories.py        → stories.json                [sélecteur narratif]
```

Cible : `webapp/public/data/<mission>/` (missions : `russosphere` défaut · `gan`).
Index léger + **fetch lazy** d'un fichier par canal au drill. Les histoires sont
**découvertes dans les données puis éditorialisées** : dérivées des croisements
de porosité pour la russosphère, éditoriales (sources ouvertes, `data_status:
"partial"` affiché) pour le GAN tant que le crawl n'a pas tourné.

## 3. Performance — étoile polaire

- **Bundle shardé + lazy** : l'index (~0,7 Mo) au chargement, un canal au clic.
- **Code-split** : Cytoscape (≈142 Ko gzip) chargé paresseusement.
- **Pas de jumeaux `.js`** (le repli `file://` du frontend mort n'est plus émis).
- **Vue bornée** : la galaxie rend le méta-graphe (≈27 nébuleuses), les canaux
  n'existent qu'au bloom — jamais 1 700 nœuds d'un coup.
- Layouts fcose bornés (`numIter`), transitions CSS Cytoscape (pas de physique
  en boucle hors « respiration » des nébuleuses).

## 4. Lancer

```powershell
cd webapp; npm run dev     # http://localhost:5173/
cd webapp; npm run build   # statique -> webapp/dist/
```

## 5. Honnêteté (non négociable)

- CoverageCallout (**cécité mono-plateforme** Telegram) permanente — sidebar,
  drawer, et caveat par mission (GAN : « empreinte observable, jamais totale ») ;
- Tiers **T1/T2** uniquement, jamais T3 (commanditaire) ;
- Histoires : statut de données affiché (`reconstruite des données` /
  `éditoriale` / `données partielles` + handles non crawlés listés) ;
- 4 traitements épistémiques (calculé / hypothèse / preuve / limite) ;
- Cf. `docs/validation-state.md` (falsification du score).
