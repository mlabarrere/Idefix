# Demo runbook — Idéfix (galaxie narrative, statique)

> **Réécrit 2026-06-10.** L'ancienne démo (serveur FastAPI + cache pré-chauffé +
> `console-operateur.html`) est morte avec le Lot 0 d'allègement. La démo est
> désormais **100 % statique** : la webapp lit le bundle précalculé — aucune
> base, aucun serveur Python, aucun appel Telegram pendant la démo.

## 0. Pré-requis (une fois, AVANT la démo)

Le bundle doit exister sous `webapp/public/data/russosphere/` (et `gan/`).
S'il faut le régénérer (base PostgreSQL démarrée — cf. `ops-runbook.md` §1) :

```powershell
.\.venv\Scripts\python.exe scripts\build_edges.py
.\.venv\Scripts\python.exe scripts\tag_france.py
.\.venv\Scripts\python.exe scripts\build_scores.py
.\.venv\Scripts\python.exe scripts\analyze_communities.py
.\.venv\Scripts\python.exe scripts\analyze_porosity.py
.\.venv\Scripts\python.exe scripts\export_static.py
.\.venv\Scripts\python.exe scripts\build_stories.py
```

Puis : `cd webapp; npm run dev` (ou `npm run build` et servir `dist/`).

## 1. Fil de démo (≈ 5 minutes)

1. **Sélection de mission** — la page d'entrée montre « un moteur, N missions »
   (russosphère · GAN · DIRCOM planifiée), chaque carte portant son caveat.
2. **La galaxie** (russosphère) — 27 nébuleuses-communautés reconstruites depuis
   UNE graine légitime (@France24_fr). Survol = tooltips ; clic nébuleuse =
   bloom ; les ponts dorés relient les communautés.
3. **L'histoire** — bouton **Histoires** → « Influences russes → extrême droite
   FR ». Trois phases datées (déc 2025 → juin 2026). Cliquer « L'axe
   @arktosmedia → @InstitutILIADE s'installe » : la galaxie s'efface, les canaux
   de l'axe ressortent en or, la carte narrative raconte la trace (vélocités de
   reprise réelles, badge T2 « reconstruite des données »).
4. **Le drill** — clic sur @InstitutILIADE : ego-focus (voisins +1) + drawer =
   score explicable (5 familles + définitions), « Dans le récit », verrou
   multi-source, CoverageCallout. C'est la chaîne complète :
   **galaxie → histoire → canal → preuve**.
5. **Mission GAN** — switcher de mission → histoires « fuite Strava » et « drone
   Zhigulevsk » : phases datées documentées, badge « données partielles »
   (honnêteté : crawl GAN à venir), la couche attention-adverse (@rybar,
   @wargonzo) déjà résolue par le catalogue russosphère.

## 2. Messages clés (à dire pendant la démo)

- « On ne juge pas des contenus, on **reconstruit des structures de diffusion** » ;
- « Chaque chiffre se déplie jusqu'à son évidence — score **explicable**, pas boîte noire » ;
- « Telegram-only : on voit la couche d'**amorçage**, pas l'amplification de masse — dit sur chaque écran » ;
- « T1/T2 seulement ; l'attribution à un commanditaire (T3) est hors périmètre ».

## 3. Si quelque chose casse

- Page blanche / états vides → le bundle manque : relancer §0.
- `npm run dev` indisponible → `npm install` dans `webapp/` d'abord.
- La base n'est nécessaire QUE pour régénérer le bundle, jamais pendant la démo.
