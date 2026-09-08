# Migrations de base de données — Alembic (Idéfix)

> Référence opérationnelle des migrations PostgreSQL. Alembic est désormais la
> **source de vérité du schéma** (auparavant : `scripts/init_db.py`, conservé pour
> mémoire mais figé). Périmètre : couche données uniquement — aucun contact
> Telegram/MTProto.

---

## 1. Stack et conventions

- **Python 3.14**, venv `./.venv/Scripts/python.exe`. Préfixer `$env:PYTHONUTF8="1"`
  (PowerShell) ou `PYTHONUTF8=1 ...` (bash).
- **PostgreSQL natif** (pas de Docker). `DATABASE_URL` dans `.env`, avec le suffixe
  `+asyncpg`.
- **Alembic en mode ASYNC** (template `alembic init -t async`). Choix imposé : aucun
  driver synchrone n'est installé (ni `psycopg2`, ni `psycopg` v3) — seul `asyncpg`
  est présent. Le moteur async de SQLAlchemy consomme directement l'URL `+asyncpg`,
  donc **aucun strip du suffixe n'est nécessaire**.
- `alembic/env.py` charge `DATABASE_URL` depuis `.env` via `python-dotenv` et l'injecte
  dans la config (`sqlalchemy.url`). L'URL n'est **pas** écrite dans `alembic.ini`
  (pas de credentials versionnés).
- **Migrations écrites À LA MAIN** (`op.execute`) — il n'y a pas de modèle ORM dans
  le projet, donc **pas d'autogenerate** (`target_metadata = None`).

> **Note asyncpg (load-bearing).** Le dialecte asyncpg de SQLAlchemy utilise le
> protocole *prepared statement*, qui **refuse plusieurs commandes SQL dans un seul
> `execute`** (`cannot insert multiple commands into a prepared statement`). Chaque
> migration émet donc **une instruction par appel `op.execute`** (les DDL sont des
> listes d'instructions, pas un bloc multi-statements). `init_db.py` y échappait car
> il utilisait `asyncpg` brut (protocole *simple query*).

---

## 2. Révisions

| Rév. | Nom | Contenu |
|---|---|---|
| `0001` | baseline | Recrée à l'identique les 4 tables historiques (`channels`, `messages`, `episodes`, `evidence_dossiers`) + index, copie fidèle de `scripts/init_db.py`. Idempotent (`IF NOT EXISTS`). |
| `0002` | edges | Crée la table `edges` matérialisant le graphe multiplex centré-canal (cf. `_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md` §2.3). Additive. |
| `0003` | enrich | Enrichit la couche ingestion (re-crawl) : `messages.media_hash` = `file_unique_id` Telegram (+ index), `channels.description` (bio), nouvelle table `comments` (commentateurs de groupes publics liés — base légale RGPD documentée dans le fichier). Additive. |
| `0004` | perf | Matérialisation des scores : table `channel_scores` (1 ligne/canal, `suspicion` indexée DESC, `archetype`, `payload` = objet canal du contrat) + table 1-ligne `scores_run_meta` (enveloppe : `coverage_callout`, `symmetric_ratio`) + 2 index hot-path sur `messages` (`idx_messages_text_notnull` partiel pour france_targeting, `idx_messages_channel_ts_desc` pour le fenêtrage recency). Alimentée hors-ligne par `scripts/build_scores.py`. Additive. |
| `0005` | mission_scoped_scores | Scores portés par mission (scoping multi-mission des `channel_scores`). Additive. |
| `0006` | mission_composite_pk | Clé primaire composite intégrant la mission. |
| `0007` | channel_llm_scores | Scores LLM par canal (piste sémantique). Additive. |
| `0008` | add_gate_families | Matérialise l'ensemble des familles déclenchées par canal (`gate_families`, gate multi-sources traçable). Additive. |

`alembic heads` → `0008 (head)` (une seule head, historique linéaire).

> **Pipeline de matérialisation (rév. 0004).** Après chaque crawl, l'ordre est
> `build_edges.py → build_scores.py → analyze_communities.py`. `build_scores.py`
> calcule UNE fois (hors chemin de requête) ce que l'API recomputait à la volée
> (france_targeting sur tous les messages + projection forward + eigenvector +
> coordination + récidivisme) et l'écrit dans `channel_scores`/`scores_run_meta`.
> L'API ne fait plus que **lire** ce précalculé (file triée + archétypes), avec
> **repli live** si la table est vide. Mesuré 2026-06-06 : `/api/channels?top_k=50`
> **29,6 s (live) → 4 ms (précalculé)** ; `/neighborhood` **379 ms/clic → 0 ms**
> (graphe + archétypes mémoïsés, eigenvector éliminé). Voir `docs/demo-runbook.md` §0.

---

## 3. Procédure de transition — base DÉJÀ PEUPLÉE (cas local/prod actuel)

La base réelle existe déjà (tables créées historiquement par `init_db.py`, peuplée :
421 canaux, ~15 800 messages) et **ne contient pas** de table `alembic_version`. Il ne
faut PAS ré-exécuter `0001` (qui recréerait les tables) : on l'**estampille**.

```powershell
$env:PYTHONUTF8="1"
# 1. Marquer la baseline comme DÉJÀ appliquée — n'exécute AUCUN DDL :
./.venv/Scripts/python.exe -m alembic stamp 0001
# 2. Appliquer les migrations suivantes (ici 0002, purement additive) :
./.venv/Scripts/python.exe -m alembic upgrade head
```

Après cela : `alembic current` → `0002 (head)`, la table `edges` existe, et les tables
peuplées sont **intactes**.

---

## 4. Procédure — base NEUVE (machine vierge)

```powershell
$env:PYTHONUTF8="1"
./.venv/Scripts/python.exe -m alembic upgrade head
```

Crée les 4 tables baseline **puis** `edges`. (`init_db.py` n'est plus nécessaire ;
il reste comme documentation historique du schéma d'origine.)

---

## 5. Créer une nouvelle migration

```powershell
$env:PYTHONUTF8="1"
./.venv/Scripts/python.exe -m alembic revision --rev-id 0003 -m "ma_migration"
```

Éditer ensuite `alembic/versions/0003_*.py` : remplir `upgrade()` / `downgrade()` avec
des `op.execute(...)` — **une instruction SQL par appel** (voir la note asyncpg §1).
Toujours fournir un `downgrade()` propre.

---

## 6. Table `edges` (rév. 0002) — schéma

Projection persistante du graphe multiplex centré-canal. Une arête vise **soit** un
autre canal (`dst_channel_id`), **soit** un domaine web (`dst_domain`) — jamais les
deux, jamais aucun (contrainte `ck_edges_exactly_one_dst`).

Familles / types (graph-model §2.3) : `FORWARD`, `MENTIONS`, `CITES_DOMAIN`
(propagation/influence) ; `CO_FORWARD`, `COPYPASTA`/`TEXT_SIM`, `CO_URL`,
`MEDIA_REUSE` (coordination, non-dirigées, fenêtrées Δt).

Attributs notables : `count`/`weight` (arête agrégée) ; `delay_seconds` (FORWARD) ;
`text_sim` (COPYPASTA) ; `window_delta_seconds` + `window_start`/`window_end` (fenêtre
Δt de coordination — le temps discrimine coordination vs coïncidence, §2.3.2) ;
`attrs` JSONB (fourre-tout : domaine partagé d'un CO_URL, pHash d'un MEDIA_REUSE,
nb d'origines communes d'un CO_FORWARD…).

**Clé d'unicité pour l'upsert d'arête agrégée :** index unique
`uq_edges_src_dst_type` sur
`(src_channel_id, COALESCE(dst_channel_id, -1), COALESCE(dst_domain, ''), edge_type)`.
Le `COALESCE` est nécessaire car PostgreSQL traite les `NULL` comme **distincts** dans
une contrainte UNIQUE classique — sans lui, deux arêtes canal→domaine identiques
(dont `dst_channel_id` est NULL) passeraient. Un `channel_id` Telegram n'est jamais
`-1` et `''` n'est jamais un domaine réel : sentinelles sûres.
