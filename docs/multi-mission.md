# Idéfix — plateforme générique multi-mission (guide contributeur)

> Canonique : `CLAUDE.md` (bandeau 2026-06-09) ·
> `_bmad-output/planning-artifacts/scope-change-multi-mission-2026-06-09.md` ·
> `_bmad-output/planning-artifacts/architecture-multi-mission-2026-06-09.md`.

Idéfix est un **moteur Telegram theme-agnostique** + **N missions analytiques**.
Une mission est une **CONFIGURATION** (six profils + un scorer de pertinence),
jamais une fourche de code.

## Missions (`src/missions/`)

| Mission | Statut | Objet |
|---|---|---|
| `russosphere` | **défaut** | désinformation coordonnée visant l'image/l'intégrité de la France |
| `gan` | pilote | empreinte informationnelle observable sur Telegram du GAN (*Charles de Gaulle*) — OPSEC |
| `dircom_minarm` | planifié (`implemented=False`) | reprise/déformation des messages DIRCOM |

Chaque mission `src/missions/<name>/__init__.py` exporte `MISSION: MissionDefinition`
(cf. `src/missions/spec.py`) : `SourceUniverse`, `LexiconProfile`,
`TargetingProfile`, `ScoringProfile`, `DashboardProfile`, `ExportProfile`,
`relevance_scorer`. `src/missions/registry.py` les découvre par convention ;
`resolve_mission(name|None)` → défaut `russosphere`.

**Ajouter une mission = créer un package + sa `MISSION`** (aucune modification du moteur).

## Pipeline par mission (drapeau `--mission`)

```
crawl/backfill → build_edges → tag_<mission> → build_scores --mission <m>
              → analyze_* → export_static --mission <m> → build_stories --mission <m>
```

(`export_static` et `build_stories` ciblent par défaut
`webapp/public/data/<mission>/` — le `--out` explicite n'est plus nécessaire.)

- `--mission` absent ⇒ `russosphere` ⇒ **comportement historique byte-identique**
  (golden : la suite de tests reste verte).
- GAN : `scripts/tag_gan.py` écrit `channels.extra.gan_targeting` (MERGE, ne clobbe
  pas `fr_score`). `build_scores --mission gan` matérialise les scores `telegram_*`
  (visibility / velocity / source_diversity / disclosure_precision / propagation /
  adverse_attention) scopés mission (`channel_scores.mission`, alembic 0005/0006).

## Périmètre & secrets (load-bearing)

- **Telegram-only** : tous les scores GAN sont nommés `telegram_*` ; l'empreinte
  mesurée est l'**observable sur Telegram**, jamais l'empreinte totale (le cas
  Strava le démontre). Caveat permanent dans l'UI et chaque rapport.
- **Compte/session Telegram** = dépendance d'exécution (`src/ingestor/session.py` :
  env-vars `TELEGRAM_*` avec alias `TG_*`, `session_preflight`). **Jamais exporté** :
  `export_static` scrube les secrets par-clé ET par-valeur.
- **Arm-only** ; tiers **T1/T2** (T3 hors périmètre).

## Scoring (`src/scorer/`)

- `channel_suspicion.compute_channel_queue(..., profile, extra_families)` — paramétré
  par `ScoringProfile` (défaut = constantes historiques). Familles structurelles
  (b) cascade / (c) coordination / (d) récidive : theme-agnostiques.
- `telegram_footprint.py` — familles `telegram_*` (GAN). `eefi_rubric.py` — rubrique
  EEFI graduée (sévérités = **décision métier MinArm**, graine v0 à calibrer) pour
  `telegram_disclosure_precision`.
- `loader.make_prior_policy(suspect_threshold)` — `credibility_prior` mission-aware
  (GAN : prior neutre, pas de présomption de suspicion sur un actif ami).

## Interface analyste

`webapp/` (React + Vite + Tailwind + Headless UI, libre, build statique). Voir
`webapp/README.md`. Switcher de mission + bandeau Telegram-only permanent + vues
d'ensemble/canaux ; trajectoire graphe/timeline/drill-down/evidence en P2–P4.

## Validation

Backend : `.venv\Scripts\python.exe -m pytest` (suite verte ; non-régression du
chemin par défaut garantie par les golden tests). Le **chemin GAN bout-en-bout**
nécessite un crawl GAN (graines navales/défense + russosphère) pour peupler la base.
Webapp : `npm run build` + `npm run typecheck` dans `webapp/`.
