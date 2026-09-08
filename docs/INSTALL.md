# Guide d'installation — Idéfix

Ce guide couvre l'installation complète d'Idéfix sur une machine de développement : base de données, environnement Python, clés Telegram, et webapp.

---

## Prérequis

| Outil | Version | Rôle |
|---|---|---|
| Python | ≥ 3.11 | Pipeline analytique |
| [uv](https://docs.astral.sh/uv/) | dernière | Gestionnaire de paquets Python |
| Node.js | ≥ 20 | Interface analyste (webapp) |
| Docker | ≥ 20 | Base de données PostgreSQL |
| Compte Telegram | — | Collecte via MTProto (lecture seule) |

### Installer uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installer Node.js

Télécharger depuis [nodejs.org](https://nodejs.org/) (LTS recommandé) ou via un gestionnaire de version (`nvm`, `fnm`, `volta`).

---

## 1. Cloner le dépôt

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
```

---

## 2. Environnement Python

```bash
# Dépendances de base + modèle d'embeddings local (recommandé)
uv sync --extra embed

# Pour le pipeline LLM optionnel (classification Mistral)
uv sync --extra llm

# Pour le développement
uv sync --extra dev
```

Le répertoire `.venv/` est créé à la racine du dépôt.

> **Windows :** préfixer chaque commande Python de `$env:PYTHONUTF8="1"` (PowerShell) ou `set PYTHONUTF8=1` (cmd) pour garantir l'encodage UTF-8 des sorties.

---

## 3. Base de données (PostgreSQL via Docker)

Idéfix utilise PostgreSQL 17. L'approche recommandée pour le développement est Docker.

```bash
# Démarrer le conteneur (persistant, redémarre automatiquement)
docker run -d \
  --name idefix-db \
  --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=disinfo \
  -e POSTGRES_PASSWORD=<un-mot-de-passe-local> \
  -e POSTGRES_DB=disinfo_trace \
  postgres:17-alpine

# Vérifier que PostgreSQL est prêt
docker exec idefix-db pg_isready -U disinfo -d disinfo_trace
```

Remplacer `<un-mot-de-passe-local>` par un mot de passe de votre choix (par exemple `idefix_local`).

> **Alternative Supabase :** pour un déploiement managé (production), créer un projet sur [supabase.com](https://supabase.com), récupérer la chaîne de connexion dans *Dashboard → Connect → Session pooler*, et l'utiliser comme `DATABASE_URL`.

### Appliquer les migrations

```bash
uv run alembic upgrade head
```

Cela crée toutes les tables (`channels`, `messages`, `edges`, `channel_scores`, etc.) jusqu'à la migration `0008`.

Vérifier :

```bash
uv run alembic current
# Doit afficher : 0008 (head)
```

---

## 4. Variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` et renseigner les valeurs suivantes.

### Base de données

```dotenv
DATABASE_URL=postgresql+asyncpg://disinfo:<mot-de-passe>@localhost:5432/disinfo_trace
```

### Telegram (voir section suivante)

```dotenv
TELEGRAM_API_ID=<votre-api-id>
TELEGRAM_API_HASH=<votre-api-hash>
TELEGRAM_SESSION_STRING=<généré via session_web.py>
TELEGRAM_PHONE_NUMBER=+33XXXXXXXXX
```

### Optionnel

```dotenv
MISTRAL_API_KEY=<clé-mistral>   # uniquement pour uv sync --extra llm
LOG_LEVEL=INFO
```

---

## 5. Obtenir les clés Telegram API

La collecte utilise le protocole **MTProto** (lecture seule, canaux publics uniquement). Vous avez besoin d'un compte Telegram et de deux identifiants.

> **Compte dédié recommandé :** utiliser un compte séparé de votre compte personnel, exclusivement dédié à la collecte. Le compte ne doit jamais être utilisé en parallèle (risque de FLOOD_WAIT et de bannissement).

### Étape 1 — Obtenir API_ID et API_HASH

1. Aller sur **[my.telegram.org](https://my.telegram.org)**
2. Se connecter avec le numéro de téléphone du compte dédié
3. Cliquer sur **"API development tools"**
4. Remplir le formulaire :
   - *App title* : `Idefix` (ou tout autre nom)
   - *Short name* : `idefix`
   - *Platform* : `Other`
   - *Description* : laisser vide ou brève description
5. Cliquer **"Create application"**
6. Copier **`App api_id`** → `TELEGRAM_API_ID` dans `.env`
7. Copier **`App api_hash`** → `TELEGRAM_API_HASH` dans `.env`

Ces identifiants sont liés à votre compte Telegram. **Ne les commitez jamais.** `.env` est dans `.gitignore`.

### Étape 2 — Générer la session string

La session string est un jeton persistant qui évite d'authentifier à chaque redémarrage.

```bash
# Installer les dépendances supplémentaires (interface Streamlit)
uv sync --extra session

# Lancer l'interface de génération (une seule fois)
uv run streamlit run scripts/session_web.py --server.port 8502
```

Ouvrir [http://localhost:8502](http://localhost:8502) dans votre navigateur :

1. Entrer votre numéro de téléphone (format international : `+33...`)
2. Entrer le code reçu par SMS ou dans l'app Telegram
3. Si 2FA activé : entrer le mot de passe
4. La session string s'affiche — la copier dans `TELEGRAM_SESSION_STRING` de `.env`

> La session string est un secret. Traitez-la comme un mot de passe. Elle donne accès à votre compte en lecture.

---

## 6. Webapp (interface analyste)

```bash
cd webapp
npm install
npm run dev        # serveur de développement → http://localhost:5173
```

La webapp lit les bundles JSON dans `webapp/public/data/`. Le dépôt inclut des données d'exemple pour les missions `russosphere` et `gan`. Aucune base de données ni session Telegram n'est nécessaire pour lancer la webapp.

```bash
# Build statique (production)
npm run build      # → webapp/dist/
npm run preview    # prévisualisation locale du build
```

---

## 7. Vérifier l'installation

```bash
# Tests Python (468 tests)
uv run python -m pytest

# TypeScript strict (frontend)
cd webapp && npx tsc --noEmit

# Connexion base de données
uv run python scripts/test_supabase_connection.py
```

---

## 8. Premier pipeline (optionnel)

Si vous souhaitez collecter de nouvelles données :

```bash
# 1. Migrations à jour
uv run alembic upgrade head

# 2. Backfill d'un canal public
uv run python scripts/backfill.py --channel @France24_fr --limit 500

# 3. Construire le graphe d'arêtes
uv run python scripts/build_edges.py

# 4. Calculer les scores de suspicion
uv run python scripts/build_scores.py --mission russosphere

# 5. Analyser les communautés
uv run python scripts/analyze_communities.py --mission russosphere

# 6. Exporter le bundle webapp
uv run python scripts/export_static.py --mission russosphere
uv run python scripts/build_stories.py --mission russosphere

# 7. Lancer la webapp
cd webapp && npm run dev
```

Voir [`docs/demo-runbook.md`](./demo-runbook.md) pour le fil complet de démonstration.

---

## Problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| `connection refused` sur le port 5432 | Conteneur Docker arrêté | `docker start idefix-db` |
| `FLOOD_WAIT` pendant le crawl | Trop de requêtes Telegram | Attendre le délai indiqué ; ne jamais paralléliser les sessions |
| `ModuleNotFoundError: sentence_transformers` | Extra `embed` non installé | `uv sync --extra embed` |
| `alembic current` affiche une révision ancienne | Migrations incomplètes | `uv run alembic upgrade head` |
| Page blanche dans la webapp | Bundle JSON manquant | Relancer `export_static.py` + `build_stories.py` |
| Encodage UTF-8 cassé (Windows) | Variable d'env manquante | `$env:PYTHONUTF8="1"` avant chaque commande |
