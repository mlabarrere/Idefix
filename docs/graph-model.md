# Modèle de graphe — référence développeur (Idéfix)

> Document destiné aux développeurs. Décrit la couche de données et le modèle de
> graphe *channel-centric* du démonstrateur Idéfix (traçage des propagateurs de
> désinformation sur Telegram, périmètre France — voir `CLAUDE.md`).
>
> Pour le **détail** du modèle (sémantique fine des arêtes, fenêtres de
> coordination, justification méthodologique), se reporter à
> `_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md`.
> Le présent fichier est le **résumé opérationnel** côté code.

---

## 1. Stack et conventions

- **Python 3.14**, environnement virtuel `.venv` (`./.venv/Scripts/python.exe` sous Windows).
- **PostgreSQL natif** = *source de vérité* (toutes les tables, voir §2). Pas de Docker (bloqué sur cette machine — `CLAUDE.md` §12).
- **Graphe en mémoire via `igraph` / `networkx`**, construit à la volée depuis PostgreSQL.
  **PAS de Neo4j, PAS de Kùzu** (pas de serveur, pas de Java, pas de wheel py3.14 disponible).
- **Pas de Docker, pas de Streamlit** (sauf l'utilitaire ponctuel de session). Frontend = `webapp/` React/Vite statique, sans backend.
- **Toujours préfixer le shell de `$env:PYTHONUTF8="1"`** (PowerShell) pour garantir
  l'encodage UTF-8 des sorties (titres de canaux, caractères accentués). Sous bash :
  `PYTHONUTF8=1 ...`.

Exemple d'invocation type :

```powershell
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py
```

---

## 2. Données — schéma PostgreSQL

Le schéma canonique est créé par les migrations Alembic (`alembic upgrade head`). Quatre tables baseline :

| Table | Rôle | Colonnes notables |
|---|---|---|
| `channels` | Canaux observés (catalogue + découvertes snowball) | `channel_id` (PK, BIGINT, stable à travers les rebrands de handle), `username`, `title`, `member_count`, `tier` (`hot`/`warm`/`cold`), `is_in_catalogue`, `extra` (JSONB — porte notamment `fr_score`) |
| `messages` | Messages backfillés | `message_id`, `channel_id` (FK), `timestamp`, `text`, `language`, `forward_from_channel_id`, `forward_from_message_id`, `forward_delay_seconds`, `views`, `forwards`, `media_type`, `media_hash`, `urls` (JSONB), `is_deleted` ; unicité `(channel_id, message_id)` |
| `episodes` | Registre des épisodes/revendications | `episode_id` (PK), `title`, `thematic_category`, `target_entity` (déf. `FR_integrity`), `claim_text`, `claim_variants`, `bge_m3_embedding`, `status` |
| `evidence_dossiers` | Dossiers de preuve produits | `dossier_id`, `episode_id` (FK), `attribution_tier` (T1/T2), `severity_tier`, `methodology_version_hash`, `scores` (JSONB), `evidence_channels`, `coverage_callout` (caveat *single-platform blindness*, obligatoire) |

### Particularités à connaître côté code

- **`messages.text`** porte le contenu. Mentions et URLs ne sont **pas** des colonnes
  premières de premier ordre : elles sont **dérivées du texte** via
  `src/normalizer/handlers.py` (voir §4).
- **`messages.urls`** (JSONB) est souvent **vide** — les canaux citent fréquemment des
  domaines en clair dans le texte plutôt qu'en entité Telegram. Ne pas s'y fier seul ;
  re-dériver depuis `text` via `extract_urls`.
- **`messages.forward_from_channel_id`** + `forward_delay_seconds` portent la lignée de
  *forward* — la primitive de propagation Telegram (étoile de profondeur 1, délais
  multi-jours à longue traîne). C'est l'arête `FORWARD` du graphe.
- **`channels.extra.fr_score`** (float, écrit par `tag_france.py` / `snowball_crawl.py`)
  est le score brut de pertinence-France au niveau canal. **Axiome #1 : on tague, on ne
  filtre pas** — `fr_score` module la sévérité, il n'exclut pas un canal du graphe.

---

## 3. Modèle de graphe *channel-centric*

L'unité du graphe est le **canal** (et, en complément, le **domaine** web cité). Les
messages sont des supports d'arêtes, pas des nœuds de premier ordre dans le modèle de
scoring.

**Nœuds** : `Channel` (+ `Domain` pour la couche adverse Pravda/Doppelganger).

**Arêtes** (multiplex — plusieurs types entre deux canaux peuvent coexister) :

| Arête | Sémantique | Dérivée de |
|---|---|---|
| `FORWARD` | A re-forwarde un message de B (origine → relayeur), pondérée par occurrence + délai | `messages.forward_from_channel_id` + `forward_delay_seconds` |
| `MENTIONS` | A @-mentionne le canal B dans son texte | `extract_mentions(text)` |
| `CITES_DOMAIN` | A cite un domaine web (hors plateformes/raccourcisseurs) | `extract_urls` + `canonical_domain` + `is_platform_host` |
| `CO_FORWARD` | A et B re-forwardent les mêmes origines (motif de coordination) | co-occurrence d'origines de forward |
| `COPYPASTA` | A et B publient un texte quasi-identique | similarité de texte (différé) |
| `CO_URL` | A et B citent les mêmes URLs dans une fenêtre Δt | co-citation fenêtrée |
| `MEDIA_REUSE` | A et B réutilisent le même média (pHash/dHash) | `media_hash` (différé) |

Les arêtes de **coordination** (`CO_FORWARD`, `CO_URL`, `COPYPASTA`, `MEDIA_REUSE`) sont
**fenêtrées dans le temps (Δt, multi-jours)** : la convergence de *plusieurs* signaux
faibles dans la fenêtre est le signal, pas un signal isolé (`CLAUDE.md` §7). Le détail des
seuils (D3lta : copypasta 0.693 / rewording 0.715 / translation 0.85) et des fenêtres est
dans le doc méthodologie référencé en tête.

> Le graphe de forward « réel » exploité aujourd'hui (`build_graph.py`,
> `detect_clusters.py`, `score_channels.py`) n'utilise pour l'instant que l'arête
> `FORWARD` agrégée origine → relayeur (self-loops exclus). Les autres types d'arêtes
> sont spécifiés mais pas encore tous matérialisés (voir §5).

---

## 4. Extracteurs — `src/normalizer/handlers.py`

Toutes les dérivations texte → signal de graphe vivent ici. Fonctions pures, testables
sans réseau (voir `tests/normalizer/test_extract.py`).

| Fonction | Entrée → Sortie | Notes |
|---|---|---|
| `extract_mentions(text)` | texte → `list[str]` de usernames (minuscule, sans `@`, dédupliqués) | regex anti-e-mail / anti `t.me/@handle` ; usernames 5–32 car. |
| `extract_urls(text)` | texte → `list[str]` d'URLs légèrement canonicalisées (`scheme://netloc/path`) | ponctuation traînante retirée, déduplication |
| `canonical_domain(url)` | URL → host registrable minuscule (`www.` retiré, port/userinfo retirés) ou `None` | heuristique netloc (pas de public-suffix list) |
| `is_platform_host(domain)` | domaine → `bool` | `True` pour t.me/x.com/youtube/raccourcisseurs → exclus du signal `CITES_DOMAIN` |
| `compute_media_hash(file_path)` | chemin fichier → pHash hex ou `None` | **nécessite le fichier média téléchargé** ; `imagehash.phash` |
| `detect_language(text)` | texte → code ISO 639-1 ou `None` | `langdetect` ; `None` si texte < 20 car. |
| `clean_text(text)` | texte → texte sans markdown gras/souligné | normalisation légère |

### Exemples d'usage

```python
from src.normalizer.handlers import (
    extract_mentions, extract_urls, canonical_domain, is_platform_host,
)

text = "Relayez @Vbachir — preuves sur https://news-pravda.com/fr/article.html"

extract_mentions(text)        # -> ["vbachir"]
urls = extract_urls(text)     # -> ["https://news-pravda.com/fr/article.html"]
dom = canonical_domain(urls[0])   # -> "news-pravda.com"
is_platform_host(dom)         # -> False  => garde l'arête CITES_DOMAIN
is_platform_host("t.me")      # -> True   => exclue du signal adverse
```

```python
# Empreinte média : suppose le fichier déjà téléchargé sur disque
from src.normalizer.handlers import compute_media_hash
h = compute_media_hash("data/media/abc123.jpg")  # -> "f0e1..." ou None
```

---

## 5. À construire (pas encore fait)

Spécifié dans le modèle, non encore matérialisé en base/code :

- **Table `edges`** persistant le graphe multiplex (au-delà du forward agrégé recalculé à
  la volée).
- **Dérivation multiplex** des arêtes `MENTIONS` / `CITES_DOMAIN` / `CO_FORWARD` /
  `CO_URL` / `COPYPASTA` / `MEDIA_REUSE` à partir du texte et des médias.
- **Score de suspicion par canal** consolidant les cinq familles (claim proximity /
  cascade role / coordination / recidivism / GenAI-origin) au niveau canal — la direction
  de classification **niveau canal** retenue (voir `scripts/build_channel_digests.py`).

Le crawl `scripts/snowball_crawl.py --waves N --cap M` **grossit le graphe** en
backfillant la frontière des canaux les plus *forwardés* non encore ingérés (capillarité
en profondeur sur N vagues). **Un seul processus, sérialisé, un seul compte +33** — ne
jamais paralléliser MTProto (règle dure d'hygiène de compte).

---

## 6. Comment lancer les choses

```powershell
# Tests des couches concernées
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe -m pytest tests/labeling tests/normalizer -q

# Initialiser / migrer le schéma DB (idempotent)
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe -m alembic upgrade head

# Grossir le graphe (Telegram, sérialisé, compte +33)
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/snowball_crawl.py --waves 3 --cap 20

# (Re)tagger la pertinence-France des canaux
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/tag_france.py

# Détection de grappes coordonnées (lecture seule, igraph)
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py
$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py --seed @Dugin_Aleksandr --hops 5
```

Voir `scripts/README.md` pour l'inventaire complet des scripts et leur contact (ou non)
avec Telegram.
