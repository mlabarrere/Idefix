# Idéfix

[![CI](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml/badge.svg)](https://github.com/mlabarrere/Idefix/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](./pyproject.toml)

> **Système d'analyse de propagation et de coordination sur Telegram.**
> Démonstrateur (PoC) — cartographie de la diffusion coordonnée visant l'image, l'intégrité ou la souveraineté de la France.

**Idéfix n'est pas un détecteur de « fake news ».** Il ne juge jamais la véracité d'un message. Il décrit des *structures observables* de diffusion et de coordination, et restitue, pour chaque canal, les signaux concrets qui justifient son rang. Le livrable est une file d'examen priorisée, explicable et auditable — jamais un verdict.

La spécification scientifique complète est dans [`METHODOLOGY.md`](./METHODOLOGY.md) (document versionné, publié *avant* toute sortie de détection — exigence de résistance EIP). Ce README est le guide d'ingénierie : architecture, installation, exécution du pipeline.

**→ Nouveau sur le projet ? Commencer par [`docs/PRODUCT.md`](./docs/PRODUCT.md) (vue fonctionnelle) puis [`docs/QUICKSTART.md`](./docs/QUICKSTART.md).**

---

## 1. Principe

Idéfix est **un moteur, N missions**. Une mission est une *configuration* (univers de sources, lexique, poids de ciblage, profil de scoring, tableau de bord, export), jamais un fork de code. Les familles de signaux structurelles sont thématiquement neutres ; les missions diffèrent par leurs graines, lexiques, signaux de pertinence et pondérations.

| Mission | Statut | Objet |
|---------|--------|-------|
| `russosphere` | **active** | Désinformation coordonnée visant l'image / l'intégrité / la souveraineté de la France. |
| `gan` | données à venir | Empreinte informationnelle *observable sur Telegram* du groupe aéronaval (*Charles de Gaulle*) — objectif OPSEC. |
| `france_ukraine` | active | Narratifs visant la France dans le conflit ukrainien. |
| `dircom_minarm` | planifiée | Reprise / transformation / déformation des messages officiels DIRCOM MinArm. (`implemented=False`) |

**Contrainte porteuse (méta-contrainte 1) :** la pertinence thématique et le lien à une infrastructure adverse **modulent la sévérité, jamais l'inclusion**. Aucun canal n'est exclu de la file pour être hors-thème ; un canal sans suspicion structurelle reste à zéro quelle que soit sa pertinence.

---

## 2. Architecture

Le système se scinde en **deux moitiés strictement disjointes** : un pipeline analytique *hors-ligne* (Python) qui matérialise des bundles JSON, et une interface analyste *100 % statique* (React) qui ne lit que ces bundles. Le navigateur ne touche jamais la base de données.

```
┌─────────────────────────── PIPELINE HORS-LIGNE (Python) ───────────────────────────┐
│                                                                                      │
│  crawl ──▶ build_edges ──▶ build_scores ──▶ analyze_communities ──▶ export_static    │
│  (MTProto)   (graphe)      (suspicion +     (Leiden : TF-IDF        (bundles JSON)   │
│                             famille f)        + embeddings)              │            │
└─────────────────────────────────────────────────────────────────────────│───────────┘
                                                                          │
┌───────────────────── INTERFACE ANALYSTE (React, statique) ──────────── │ ──────────┐
│  webapp/public/data/<mission>/  ◀──────────────────────────────────────┘            │
│        │  bundles JSON pré-calculés, figés au déploiement                           │
│        ▼                                                                             │
│  vite build ──▶ webapp statique ──▶ navigateur (fetch JSON local, zéro backend)     │
└──────────────────────────────────────────────────────────────────────────────────── ┘
```

### Arborescence

```
Idefix/
├── METHODOLOGY.md          ← spécification scientifique versionnée (canonique)
├── README.md               ← ce fichier
├── src/
│   ├── ingestor/           ← client MTProto (canaux publics, lecture seule)
│   ├── normalizer/         ← texte, URLs, empreintes média ; ciblage thématique
│   ├── graph/              ← graphe multiplex centré-canal (NetworkX), I/O DB séparée du pur
│   ├── scorer/             ← familles de scores explicables (b/c/d + f embeddings)
│   ├── embed/              ← encodeur local (sentence-transformers), cache offline
│   ├── dossier/            ← assemblage « preuve-d'abord » des dossiers d'épisode
│   ├── missions/           ← une mission = une MissionDefinition (registry auto-découvert)
│   ├── validation_lab/     ← schémas de gold externe (validation non-circulaire)
│   └── shared/             ← DB, scrub des secrets, store de snapshots (push + pull)
├── scripts/                ← pipeline (crawl, build_*, mine_episodes, analyze_*, eval_*, export)
├── webapp/                 ← interface analyste React + Vite + TS + Tailwind (build statique)
├── alembic/                ← migrations PostgreSQL (head : 0008)
├── data/                   ← corpus d'éval, baseline organique, gold (en partie gitignored)
└── tests/                  ← suite pytest (468 tests) + tests frontend (tsc strict)
```

---

## 3. Stack technique

| Couche | Technologie | Notes |
|--------|-------------|-------|
| Ingestion | MTProto (client Telegram) | Canaux **publics** uniquement, un compte dédié en lecture, discipline `FLOOD_WAIT`. |
| Stockage | PostgreSQL 17 | Messages, arêtes, scores. Docker en développement, Supabase ou toute instance PostgreSQL en production. |
| Graphe | NetworkX `MultiDiGraph` (+ igraph/Leiden) | Reconstruit **en mémoire, à la demande**. Pas de base graphe serveur. |
| Scoring | Familles explicables (Python pur) | Somme pondérée bornée + gate multi-source. Aucun appel réseau. |
| Embeddings | `sentence-transformers` (local) | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, FR/RU/EN). Cache offline déterministe, coût 0 en relance. |
| Communautés | Leiden (deux pistes) | **analytics** (lexical/TF-IDF) et **embeddings** (arêtes de similarité sémantique). |
| Frontend | React 18 + Vite + TypeScript | Strict mode. Cytoscape (galaxie), Headless UI, Tailwind v4. **Build 100 % statique.** |
| Diffusion | Vercel / tout hébergeur statique | Build statique (`vite build`) — le navigateur ne lit que des JSON locaux, zéro backend. |

---

## 4. Le score de suspicion (vue d'ingénieur)

Le score combine des familles de signaux **indépendantes**, chacune affichée avec sa contribution (poids × valeur). Détails et justification scientifique dans [`METHODOLOGY.md §3`](./METHODOLOGY.md).

| Famille | Statut | Méthode |
|---------|--------|---------|
| **b** · Rôle en cascade | active | Bridge-Score (in-degree, vecteur propre, clustering) sur le graphe de forwards. |
| **c** · Coordination | active | Arêtes de coordination fenêtrées (Δt) : co-forwards, quasi-doublons de texte, co-URL. |
| **d** · Récidive inter-épisodes | active | Influence de forward + récurrence du canal d'amorçage. |
| **f** · Cohérence sémantique | **active** *(embeddings)* | Distance à une baseline FR organique + proximité à des canaux adversaires connus. `src/scorer/embedding_signals.py` |
| a · Proximité revendication · e · Origine IA | réservées | Seams câblables (registre de revendications / détecteurs GenAI). |

**Gate multi-source :** un canal ne franchit la gate que si **≥ 2 familles distinctes** sont déclenchées. La liste exacte des familles déclenchées est matérialisée (`channel_scores.gate_families`, migration `0008`) — l'attribution de tier (T1/T2) est mécanique et auditable.

---

## 5. Installation

Prérequis : Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Node 20+ (webapp), Docker (PostgreSQL).

```bash
# Dépendances Python (extra `embed` pour les familles sémantiques)
uv sync --extra embed

# Base de données PostgreSQL (Docker)
docker run -d --name idefix-db --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=disinfo -e POSTGRES_PASSWORD=<mot-de-passe> \
  -e POSTGRES_DB=disinfo_trace postgres:17-alpine

# Variables d'environnement
cp .env.example .env   # puis éditer DATABASE_URL + credentials Telegram

# Migrations
uv run alembic upgrade head
```

**Guide complet (Telegram API, session string, webapp) :** [`docs/INSTALL.md`](./docs/INSTALL.md)

**Démarrage rapide sans collecte (webapp sur données d'exemple) :** [`docs/QUICKSTART.md`](./docs/QUICKSTART.md)

---

## 6. Exécution du pipeline

Tout le pipeline est *scopé par mission* (`--mission <nom>`, défaut : `russosphere`) et **idempotent** (réécriture atomique par run, jamais de `TRUNCATE` transverse). Lecture/écriture PostgreSQL uniquement — aucun appel Telegram hors de l'étape de collecte.

```bash
# 0. Schéma à jour (head : 0008)
uv run alembic upgrade head

# 1. Collecte (historique + veille étagée)
uv run python scripts/crawl.py --mission russosphere

# 2. Graphe : familles d'arêtes (forwards, mentions, co-citations…)
uv run python scripts/build_edges.py

# 3. Score de suspicion — avec famille (f) sémantique
uv run python scripts/build_scores.py --mission russosphere --embeddings

# 4. Découverte d'épisodes (clusters + pourquoi sémantique)
uv run python scripts/mine_episodes.py --mission russosphere

# 5. Communautés (deux pistes : analytics + embeddings)
uv run python scripts/analyze_communities.py        --mission russosphere
uv run python scripts/analyze_communities_embed.py  --mission russosphere

# 6. Export du bundle statique vers webapp/public/data/<mission>/
uv run python scripts/export_static.py --mission russosphere
```

### Validation (non-circulaire)

```bash
uv run python scripts/bootstrap_baseline.py                              # corpus FR organique (une fois)
uv run python scripts/eval_embedding_discrimination.py --mission russosphere   # ROC-AUC baseline vs scorés
uv run python scripts/eval_episode_recovery.py        --mission russosphere   # recall vs gold EXTERNE
uv run python scripts/compare_snapshots.py            --mission russosphere   # dérive temporelle des communautés
```

---

## 7. Interface analyste (webapp)

```bash
cd webapp
npm install
npm run dev        # serveur de dev Vite → http://localhost:5173
npm run build      # vite build → dist/ statique (déployable partout)
npm run preview    # prévisualisation du build de prod
```

La webapp lit les bundles JSON dans `webapp/public/data/<mission>/` (produits par `export_static.py`). **Le navigateur ne touche jamais la base de données** — consultation 100 % statique.

---

## 8. Tests

```bash
uv run python -m pytest                       # suite backend (468 tests)
cd webapp && npx tsc --noEmit                 # typecheck strict du frontend
```

---

## 9. Limite fondamentale (déclarée dans chaque sortie)

> **Couverture Telegram uniquement.** La couche d'amplification de masse (X / autres plateformes) n'est pas observée. Une opération atteignant la France principalement via d'autres plateformes, sans étape Telegram, **ne sera pas détectée.** Ce qui est mesuré est une empreinte *observable sur Telegram*, jamais l'empreinte totale d'un phénomène.

Cette limite est un champ obligatoire et validé de chaque bundle exporté. Voir [`METHODOLOGY.md §5`](./METHODOLOGY.md) pour les limites permanentes additionnelles, et `§8` pour l'état de validation honnête (ce qui est prouvé, indicatif, ou pas encore testable).

---

## 10. Gouvernance

- **Arm-only** : les sorties vont aux destinataires institutionnels désignés (VIGINUM / Arcom pour la mission par défaut ; cellule OPSEC pour GAN) — jamais aux plateformes, au public, aux candidats ou à la presse.
- **Vocabulaire en tiers** (T1/T2/T3) plutôt que « vrai/faux » ; toute revendication T3 (attribution au monde réel) est hors périmètre et constitue un défaut signalable.
- **Corroboration multi-source structurelle** : pas de label T2 ni de sévérité escaladée sans ≥ 2 familles indépendantes déclenchées.
- **Collecte respectueuse des ToS** : canaux publics seulement, pas de scraping hors-ToS, pas de désanonymisation ; les identifiants de membres ne sont pas collectés ; les secrets sont expurgés (clé par clé et valeur par valeur) de chaque export.

---

## 11. Licence & contribution

- **Licence** : [Apache-2.0](./LICENSE).
- **Contribuer** : voir [`CONTRIBUTING.md`](./CONTRIBUTING.md) et le [code de conduite](./CODE_OF_CONDUCT.md).
- **Sécurité** : signaler une vulnérabilité via [`SECURITY.md`](./SECURITY.md) — jamais en issue publique.
- **Citer** : voir [`CITATION.cff`](./CITATION.cff).
- **Historique** : [`CHANGELOG.md`](./CHANGELOG.md).
