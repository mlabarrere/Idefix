# Scripts opérationnels — Idéfix

Ce répertoire regroupe les scripts utilitaires du démonstrateur Idéfix.

> **Vérité d'architecture (mise à jour 2026-10) — lire avant toute session.** Le
> livrable est la **webapp statique** (`webapp/`, React+Vite+Tailwind, **sans
> backend**) qui lit des **JSON précalculés** (bundle
> `webapp/public/data/<mission>/` produit hors-ligne par `export_static.py` +
> `analyze_*.py` + `build_stories.py`), intégralement côté navigateur. Python est
> **exclusivement** une **chaîne hors-ligne** : données brutes (corpus public
> restauré, **ou** ingestion MTProto via Hydrogram, optionnelle) → normalisation →
> dérivation des arêtes → scoring → analyse → export.
>
> **Chemin par défaut : le corpus public.** `bootstrap.py` télécharge et vérifie
> le dataset `v1.0.0` (épinglé par SHA-256 dans `dataset/manifest.json`), le
> restaure dans un PostgreSQL 17 **local via Docker Compose**
> (`docker-compose.yml`, `127.0.0.1:5433`, identifiants locaux
> `idefix`/`idefix`), applique les migrations, lance `pipeline.py` puis la
> webapp — sans identifiants Telegram ni `.env`. Supabase, ou tout autre
> PostgreSQL 17, reste une alternative via `DATABASE_URL`.
>
> **Le backend FastAPI (`src/api/`) et le frontend HTML/JS legacy (`frontend/`)
> ont été SUPPRIMÉS le 2026-06-10** (Lot 0 d'allègement), avec les scripts
> `debug_*`, `score_channels` et `build_graph`. Telegram uniquement (X abandonné
> 2026-05-26), client **Hydrogram** (jamais Pyrogram/Telethon), graphe
> NetworkX/igraph en mémoire + table `edges` PostgreSQL (pas de Neo4j, pas de
> Kùzu). La détection livrée est un **score de suspicion explicable par canal**
> (familles b, c, d actives, f optionnelle ; a et e jamais branchées — voir
> `docs/method/03-suspicion-score.md`) ; le GNN GraphSAGE+LSTM est une cible
> **ultérieure**.

## Classification des scripts (référence rapide)

Un nouvel intervenant doit pouvoir distinguer d'un coup d'œil ce qui fait partie
de la chaîne offline cible, ce qui est de l'outillage, et ce qui est obsolète.

| Groupe | Scripts | Rôle |
|---|---|---|
| **(0) REPRODUCTIBILITÉ** (point d'entrée par défaut) | `bootstrap` · `pipeline` · `release_dataset` | `bootstrap` : d'un clone vierge à la webapp sur le corpus public, en une commande (`make setup`). `pipeline` : exécute dans l'ordre toutes les étapes hors-ligne du groupe (A) pour une ou toutes les missions. `release_dataset` : fabrique les artefacts de la release du dataset public (côté mainteneur). Aucun appel Telegram. |
| **(A) CHAÎNE COURANTE** (pipeline offline cible) | `session_web` · `backfill` · `backfill_seeds` · `snowball_crawl` · `crawl_france_ukraine` · `paced_backfill` · `enrich_recrawl` · `build_edges` · `tag_france` · `tag_gan` · `build_scores` · `analyze_communities` · `analyze_porosity` · `export_static` · `build_stories` | De l'amorçage de la base à l'export du bundle statique `webapp/public/data/<mission>/`. Le schéma est créé par les migrations Alembic (`make migrate` / `alembic upgrade head`). Ordre logique : (`session_web` une fois) → acquisition (`backfill*` / crawlers ciblés — **optionnelle** : sur le corpus public restauré, la chaîne démarre à `build_edges`, et `pipeline.py` l'enchaîne) → `build_edges` → `tag_france` (ou `tag_gan --mission gan`) → `build_scores` → `analyze_communities` / `analyze_porosity` → `export_static` → **`build_stories`** (histoires du sélecteur narratif). |
| **(B) ÉTIQUETAGE / ANNOTATION** (supervision gold) | `build_label_batch` · `aggregate_labels` · `finalize_gold` · `build_channel_digests` | Construction de la vérité-terrain niveau canal (lot stratifié → agrégation multi-juges → gold validé). Lecture/écriture fichiers + DB, aucun appel Telegram. |
| **(C) ANALYSE** (exploration & dossiers) | `detect_clusters` · `build_dossier` | Outils d'analyse et de production de dossiers/inspection ; consomment la base ou le bundle statique, ne pilotent pas l'acquisition. |
| **(D) OUTILLAGE PARTAGÉ** | `_tg` | `_tg` fabrique le client Hydrogram en lecture seule pour d'éventuelles sondes ad-hoc. *(Les sondes ponctuelles `probe_*` / `forward_origins` / `resolve_discoveries` / `snowball_hop1` / `candidates` / `evidence_probe` / `fix_sensitive` / `explore_data` / `build_evidence` / `init_db` ont été supprimées le 2026-06-15 — l'historique git les conserve.)* |

> **Repère central.** `export_static.py` matérialise le bundle JSON sous
> `webapp/public/data/<mission>/` (défaut : `russosphere`), sans réimplémenter de
> logique (mêmes fonctions que le pipeline). `build_stories.py` y ajoute
> `stories.json` (histoires/phases datées). Point de jonction avec la webapp.

Les sections détaillées ci-dessous conservent les fiches par script. Elles
restent organisées par familles d'origine (sondes de diagnostic vs briques de
pipeline) ; se reporter à la table ci-dessus pour le rattachement à un groupe.

## Conventions communes

- **Interpréteur** : `./.venv/Scripts/python.exe` (Python 3.14), idéalement avec
  `PYTHONUTF8=1` pour garantir l'encodage UTF-8 des sorties (titres de canaux,
  caractères accentués).
- **Répertoire d'exécution** : lancer les scripts depuis la racine du dépôt
  (`python scripts/<nom>.py`). Les scripts du pipeline qui importent `src/`
  reposent sur cette racine ; les sondes importent le module frère `_tg`.
- **Configuration** : les scripts lisent `.env` (chargé automatiquement via
  `python-dotenv`, **sans écraser** l'environnement : une variable passée
  explicitement gagne). `bootstrap.py` ne lit jamais `.env` et injecte lui-même
  `DATABASE_URL` dans ses sous-processus. Variables :
  - `DATABASE_URL` — chaîne de connexion PostgreSQL (le suffixe `+asyncpg`
    est retiré à la volée pour `asyncpg.connect`). Base locale :
    `postgresql+asyncpg://idefix:idefix@localhost:5433/idefix` (valeur par
    défaut de `.env.example`) ;
  - `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING`,
    `TELEGRAM_PHONE_NUMBER` — **collecte uniquement**, accès MTProto en lecture
    seule (voir `docs/method/07-tiers-and-governance.md` §7.3). Les alias
    historiques `TG_API_ID`, `TG_API_HASH`, `TG_SESSION_STRING`, `TG_PHONE`
    restent acceptés ; les noms `TELEGRAM_*` priment (`src/ingestor/session.py`).
    Exception : `_tg.py` (sondes ad-hoc) ne lit que les alias `TG_*` ;
  - `IDEFIX_DB_PORT` (port local, défaut `5433`) et `IDEFIX_DATASET_BASE_URL`
    (miroir du dataset) — lus par `bootstrap.py`.

## Module partagé — `_tg.py`

Fabrique le client Hydrogram en lecture seule à partir de l'environnement
(`TG_API_ID` / `TG_API_HASH` / `TG_SESSION_STRING`), en factorisant le
*boilerplate* auparavant dupliqué dans chaque sonde. Appelle `load_dotenv()` à
l'import.

```python
from _tg import tg_client

async with tg_client("nom_session") as c:
    ...
```

> **Portée** : réservé aux sondes de diagnostic. Le chemin d'ingestion de
> production passe par `src/ingestor/client.py` (`TelegramClient.from_env`), qui
> gère la discipline FLOOD_WAIT et l'hygiène de compte. Ne pas router le code de
> pipeline par ce module.

---

## Section 1 — Reproductibilité (corpus public, orchestration)

Point d'entrée par défaut d'un nouvel intervenant. Aucun de ces scripts ne
contacte Telegram ni une API payante ; aucun ne lit `.env` pour se configurer.
Guide utilisateur : `docs/ops/quickstart.md`.

| Script | But | Usage | Dépendances |
|---|---|---|---|
| `bootstrap.py` | D'un clone vierge à la webapp, en une commande. Étapes (chacune est aussi une sous-commande) : `check` (Python 3.14, Docker + Compose v2, Node + npm, port libre, extra `embed`, manifeste valide) → `fetch` (téléchargement des fichiers de `dataset/manifest.json` dans `dataset/downloads/`, vérification taille + SHA-256, extraction sûre des archives) → `db` (`docker compose`, service `db` ; **base vide seulement** : restauration puis `alembic upgrade head` (sans effet sur `v1.0.0`, déjà à la révision de tête `0008` ; applique les révisions ajoutées après la release) ; une base qui contient des données est laissée intacte — ni restauration ni migration, la commande `alembic upgrade head` est affichée si le schéma est en retard) → `pipeline` (`pipeline.py`, `DATABASE_URL` locale injectée ; dans `all`, lancé automatiquement seulement sur une base restaurée par le bootstrap, jusqu'à une exécution complète — `bootstrap.py pipeline` l'exécute toujours) → `webapp` (`npm ci` si besoin, `npm run dev`). N'efface jamais de données ; relançable sans risque. Bibliothèque standard uniquement. | `uv run --extra embed python scripts/bootstrap.py [check\|fetch\|db\|pipeline\|webapp\|all] [--mission M] [--skip-embeddings] [--no-webapp] [--dataset-dir DIR]` — ou `make setup` | Docker, Node, `docker-compose.yml`, `dataset/manifest.json` ; env `IDEFIX_DB_PORT`, `IDEFIX_DATASET_BASE_URL` |
| `pipeline.py` | Exécute dans l'ordre toutes les étapes hors-ligne (groupe A, sans acquisition) pour une mission ou toutes, en sous-processus ; affiche la durée de chaque étape et s'arrête au premier échec. `--list` imprime l'ordre faisant foi. | `uv run --extra embed python scripts/pipeline.py --mission {russosphere,france_ukraine,gan,all} [--list] [--only ÉTAPE] [--from ÉTAPE] [--skip-embeddings]` — ou `make pipeline MISSION=…` | `DATABASE_URL` (environnement) |
| `release_dataset.py` | **Côté mainteneur.** Fabrique les artefacts de la release du dataset public à partir de l'instantané source — l'instantané **complet**, `comments` (identifiants, pseudonymes et textes de commentateurs) et tables dérivées d'une exécution antérieure compris — puis `dataset/manifest.json` (SHA-256, tailles, instantané source, comptes de lignes). Voir `dataset/README.md` et `dataset/DATASHEET.md`. | voir `dataset/README.md` | Docker, PostgreSQL 17 jetable |

---

## Section 2 — Pipeline (backfill, graphe, scoring, tag)

Briques du pipeline d'acquisition et de traitement. Les scripts d'acquisition
passent par `src/ingestor` (client de production + handlers) et appliquent la
discipline d'hygiène de compte (cadence jittée, FLOOD_WAIT).

| Script | But | Usage | Dépendances |
|---|---|---|---|
| `session_web.py` | Interface web (Streamlit) de génération d'une chaîne de session MTProto persistante : saisie du numéro, envoi du code, connexion (2FA gérée), puis écriture de `TG_SESSION_STRING` / `TG_PHONE` dans `.env`. | `streamlit run scripts/session_web.py --server.port 8502` | streamlit, hydrogram, `TG_API_ID`, `TG_API_HASH` |
| `backfill.py` | Backfill d'un canal unique vers PostgreSQL via le client de production (`TelegramClient.from_env`) et `backfill_channel`. Journalisation structlog. | `python scripts/backfill.py --channel @Vbachir --limit 500` | `src/ingestor`, asyncpg, structlog, `DATABASE_URL` |
| `backfill_seeds.py` | Backfill du socle de graines accessibles (hubs FR + ancre adverse documentée) en une seule session, pour l'hygiène de compte. Accepte des canaux en arguments pour des hops arbitraires. | `python scripts/backfill_seeds.py [@canal ...]` | `src/ingestor`, asyncpg, `DATABASE_URL` |
| `crawl_france_ukraine.py` | Campagne bornée France–Ukraine/russophone : refresh des canaux pertinents + découverte d'origines via forwards cyrilliques ; verrou global, préflight, cadence 90–150 s. | `python scripts/crawl_france_ukraine.py [--dry-run]` | Hydrogram, asyncpg, `DATABASE_URL` |
| `snowball_crawl.py` | Crawl borné de la frontière snowball (hop-N) : sélectionne les canaux les plus *forwardés* non encore backfillés, les backfille (plafonné, jitté), puis étiquette tous les canaux d'un score de pertinence-France brut dans `channels.extra`. **Écrit en base.** | `python scripts/snowball_crawl.py` | `src/ingestor`, asyncpg, `DATABASE_URL` |
| `paced_backfill.py` | **(Groupe A)** Démon de backfill **cadencé** (48h) qui remplit en continu les coquilles cataloguées-mais-vides, pile sous la limite tolérée (jitté, adaptatif, reprenable), pour ne jamais faire bannir le compte +33. Sérialisé, un seul process. **Écrit en base.** | `python scripts/paced_backfill.py` (détaché) | `src/ingestor`, asyncpg, `DATABASE_URL` |
| `enrich_recrawl.py` | **(Groupe A)** Re-crawl d'enrichissement (une seule session sérialisée) sur un ensemble de canaux EXISTANTS : capture `media_hash` (file_unique_id, sans téléchargement), bio de canal, et commentateurs du groupe de discussion public lié (table `comments`, base légale RGPD §8). **Écrit en base.** | `python scripts/enrich_recrawl.py` | `src/ingestor`, asyncpg, `DATABASE_URL` |
| `build_edges.py` | **(Groupe A)** Peuple la table `edges` (graphe multiplex centré-canal) : dérive toutes les familles d'arêtes (FORWARD / MENTIONS / CITES_DOMAIN / CO_FORWARD / CO_URL / CO_URL_EXACT / CO_HASHTAG / MEDIA_REUSE) depuis les messages et le texte déjà stockés, UPSERT idempotent. Logique dans `src/graph/edges.py`. **Écrit en base, aucun appel Telegram.** | `python scripts/build_edges.py [--window-hours 72]` | asyncpg, `src/graph`, `DATABASE_URL` |
| `build_scores.py` | **(Groupe A)** Matérialise les scores de suspicion PAR CANAL (`channel_scores` + `scores_run_meta`) une fois, hors chemin de requête (france_targeting + projection forward + eigenvector + coordination + récidivisme). À lancer APRÈS un crawl + `build_edges.py`. Idempotent par mission (`DELETE … WHERE mission = $1` puis réécriture, dans une transaction ; les autres missions sont conservées). **Écrit en base.** | `python scripts/build_scores.py` | asyncpg, `src/`, `DATABASE_URL` |
| `analyze_communities.py` | **(Groupe A)** Snapshot « russosphère » : depuis une seule graine légitime, détection de communautés (Leiden/igraph) + ponts inter-communautés (betweenness), labels thématiques auto, vue méta-nœuds. **Lecture seule PostgreSQL.** | `python scripts/analyze_communities.py` | asyncpg, igraph, networkx ; sortie : `webapp/public/data/russosphere/russosphere_snapshot.json` |
| `analyze_porosity.py` | **(Groupe A)** Extrait les traces de **porosité** russo-sphère → extrême droite FR (réutilisation média + vélocité, thème `france_targeting` trans-langue, domaine adverse co-cité). Traces nommées et vérifiables, jamais gonflées ; T1/T2 uniquement. **Lecture seule PostgreSQL.** | `python scripts/analyze_porosity.py` | asyncpg ; sortie : `webapp/public/data/russosphere/porosity_snapshot.json` |
| `export_static.py` | **(Groupe A)** Exporteur **STATIQUE** : matérialise le bundle de la webapp (channels_index + channels/ shardé, graph.json, episodes/, manifest, snapshots), scrub des secrets par clé ET par valeur. **Lecture seule PostgreSQL, aucun appel Telegram, idempotent.** | `python scripts/export_static.py [--mission gan] [--public]` | asyncpg, `src/`, `DATABASE_URL` ; sortie : `webapp/public/data/<mission>/` |
| `build_stories.py` | **(Groupe A — étape terminale)** Construit `stories.json` (sélecteur narratif : histoires → phases nommées+datées → canaux). Dérive l'histoire de porosité des données (russosphère) + fusionne les histoires éditoriales (`src/missions/<mission>/stories.py`), handles résolus contre le bundle, manques marqués `partial`. **Offline pur (lit/écrit le bundle), aucune DB.** | `python scripts/build_stories.py [--mission gan]` | sortie : `webapp/public/data/<mission>/stories.json` |
| `tag_gan.py` | **(Groupe A, mission GAN)** Étiquette `channels.extra.gan_targeting` (lexique GAN multilingue via le moteur `targeting.py`) — MERGE, ne clobbe pas `fr_score`. **Écrit en base.** | `python scripts/tag_gan.py` | asyncpg, `src/missions/gan`, `DATABASE_URL` |
| `tag_france.py` | Étiquette chaque canal backfillé d'un score de pertinence-France brut (mots-clés, regex `~*` côté PostgreSQL) stocké dans `channels.extra.fr_score`. Axiome #1 : *étiqueter, ne pas filtrer*. **Écrit en base.** | `python scripts/tag_france.py` | asyncpg, `DATABASE_URL` |

---

## Inventaire synthétique

Tableau de référence rapide pour tous les scripts cœur. Colonne « Telegram » :
**⛔ sérialisé** = ouvre une session MTProto (un seul compte +33, jamais parallélisé) ;
**non** = lecture/écriture locale (PostgreSQL, fichiers) sans appel réseau Telegram.
Préfixer le shell de `$env:PYTHONUTF8="1"` (PowerShell).

| Script | But | Entrée | Sortie | Telegram |
|---|---|---|---|---|
| `bootstrap.py` | **(0)** Mise en place reproductible sur le corpus public : vérification, téléchargement vérifié, base locale Compose, pipeline, webapp. | `dataset/manifest.json` | base locale restaurée + bundles `webapp/public/data/<mission>/` | non |
| `pipeline.py` | **(0)** Enchaîne les étapes hors-ligne d'une ou de toutes les missions. | PostgreSQL (`DATABASE_URL`) | tables dérivées + bundles | non |
| `release_dataset.py` | **(0, mainteneur)** Artefacts de la release du dataset public (instantané complet + manifeste épinglé). | instantané source | fichiers de release + `dataset/manifest.json` | non |
| `tag_france.py` | Score de pertinence-France brut par canal (mots-clés, regex `~*`). Axiome #1 : tag, ne filtre pas. | `messages.text` | `channels.extra.fr_score` | non |
| `snowball_crawl.py` | Crawl borné de la frontière snowball (hop-N, **multi-vagues**) : backfill des canaux les plus *forwardés* non ingérés (capé, jitté), puis re-tag France. | frontière `channels` / `messages` | messages backfillés + `fr_score` | ⛔ sérialisé |
| `build_label_batch.py` | Échantillon stratifié reproductible d'items à labelliser (2 portes France + lien revendication TF-IDF). Lecture DB seule, aucun appel réseau. | PostgreSQL (`messages`/`episodes`/`channels`) | `data/annotations/<batch_id>.jsonl` (+ `__needs_manual_screening.jsonl`) | non |
| `aggregate_labels.py` | Agrège les fichiers de juges LLM, calcule le kappa (Cohen/Fleiss), sépare candidats gold et file d'arbitrage (juges anonymisés). | `judgments/<batch_id>__*.jsonl` | `__agreement.json`, `__gold_candidates.jsonl`, `__arbitration_queue.jsonl`, `__arbitration_resolved.template.jsonl` | non |
| `finalize_gold.py` | Fusionne candidats gold + arbitrages humains en `gold.jsonl` (GoldLabel validés Pydantic, idempotent, arbitrage humain prime). | `__gold_candidates.jsonl` + `__agreement.json` + `__arbitration_resolved.jsonl` | `data/annotations/gold.jsonl` | non |
| `build_channel_digests.py` | **Direction retenue (niveau canal).** Digest par canal actif : stats, comportement de forward (de/vers qui), échantillons anti-France — pour classer le *canal*. Lecture DB seule. | PostgreSQL (canaux actifs) | `data/annotations/channel_digests.jsonl` + `.md` | non |
| `detect_clusters.py` | Détection de grappes coordonnées sur le graphe de forward (communautés igraph multilevel/Louvain pondéré), score des motifs de coordination, voisinage K-hops optionnel. | `messages` (arêtes forward) | classement de grappes (stdout) | non |
| `build_dossier.py` | Dossier réel du cluster Dugin/Geopolitika ; scores (b)(c)(d) réels, (a)(e) en stub explicite. Écrit le contrat webapp. | PostgreSQL | `webapp/public/data/russosphere/dugin_cluster.json` | non |
| `build_edges.py` | **(A)** Peuple la table `edges` (graphe multiplex centré-canal, 8 familles d'arêtes) depuis les messages/texte stockés ; UPSERT idempotent. Logique dans `src/graph/edges.py`. | PostgreSQL | table `edges` | non |
| `build_scores.py` | **(A)** Matérialise les scores de suspicion par canal (`channel_scores` + `scores_run_meta`, scopés mission) hors chemin de requête. À lancer après crawl + `build_edges.py`. | PostgreSQL | `channel_scores`, `scores_run_meta` | non |
| `tag_gan.py` | **(A, mission GAN)** Étiquette `channels.extra.gan_targeting` (lexique GAN, MERGE sans clobber `fr_score`). | PostgreSQL | `channels.extra.gan_targeting` | non |
| `analyze_communities.py` | **(A)** Snapshot russosphère : communautés (Leiden/igraph) + ponts (betweenness) depuis une graine légitime. | PostgreSQL | `webapp/public/data/russosphere/russosphere_snapshot.json` | non |
| `analyze_porosity.py` | **(A)** Traces de porosité russo-sphère → extrême droite FR (média + vélocité, thème trans-langue, domaine co-cité). | PostgreSQL | `webapp/public/data/russosphere/porosity_snapshot.json` | non |
| `export_static.py` | **(A)** Exporteur statique : bundle complet de la webapp (index shardé, graphe, épisodes, manifest), scrub des secrets. | PostgreSQL | `webapp/public/data/<mission>/` | non |
| `build_stories.py` | **(A — terminale)** Histoires du sélecteur narratif (dérivées des données + éditoriales, handles résolus, statut `partial` honnête). | bundle JSON | `webapp/public/data/<mission>/stories.json` | non |
| `paced_backfill.py` | **(A)** Démon de backfill cadencé (48h) remplissant les coquilles vides, sous la limite tolérée, sérialisé. | `DATABASE_URL` | messages backfillés | ⛔ sérialisé |
| `enrich_recrawl.py` | **(A)** Re-crawl d'enrichissement (média_hash, bio, commentateurs du groupe public lié) en une session sérialisée. | `DATABASE_URL` | `media_hash`, `description`, table `comments` | ⛔ sérialisé |
| `backfill.py` | Backfill d'un canal unique via le client de production. | `@canal`, `DATABASE_URL` | messages backfillés | ⛔ sérialisé |
| `backfill_seeds.py` | Backfill du socle de graines accessibles en une session (hygiène de compte). | `[@canal ...]` | messages backfillés | ⛔ sérialisé |
