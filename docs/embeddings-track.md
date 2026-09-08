# Piste « embeddings locaux » (sentence-transformers)

Piste **parallèle** d'analyse par embeddings **locaux** — gratuite, rapide,
déterministe — qui remplace la piste **Mistral** (payante) pour améliorer la
qualité des **nœuds** (classification de canaux), des **communautés** (groupes
cohérents) et des **arêtes** (liens sémantiques). Elle n'écrase jamais le bundle
`russosphere` par défaut ni la table `channel_scores` : sorties dans des tables /
snapshots dédiés, exactement comme la piste Mistral.

## Installation

```bash
uv sync --extra embed        # tire sentence-transformers (torch)
```

Modèle par défaut : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(FR/RU/EN, rapide). Surcharge via `IDEFIX_EMBED_MODEL` ou `--model`. Import
**lazy** : le pipeline hors-ligne par défaut ne charge jamais torch.

## Composants

| Couche | Code | Sortie |
|---|---|---|
| Cœur | `src/embed/encoder.py` (`Embedder` : cache offline, throughput), `centroids.py`, `classify.py`, `community.py` | — |
| Nœuds | `scripts/classify_channels_embed.py` | table `channel_llm_scores` (`model=sentence-transformers/…`, coût 0) |
| Arêtes | `src/graph/edges.py::derive_text_sim_edges` + `scripts/build_edges.py --embed` | `edges` : `TEXT_SIM` / `TRANSLATION` |
| Communautés | `scripts/analyze_communities_embed.py` | `webapp/public/data/<mission>/<mission>_embed_snapshot.json` |
| Démo | webapp : switch galaxie **Analytics ↔ LLM Embedding** | callout chiffré (`stats.comparison`) |

## Pipeline type

```bash
uv run python scripts/build_edges.py --embed                       # arêtes sémantiques
uv run python scripts/classify_channels_embed.py --mission gan     # classification nœuds
uv run python scripts/analyze_communities_embed.py --mission russosphere   # snapshot communautés
uv run python scripts/eval_embeddings_classification.py --mission gan       # éval vs gold (coût 0)
```

Le switch frontend bascule entre `russosphere_snapshot.json` (Analytics) et
`russosphere_embed_snapshot.json` (Embedding) — mêmes canaux, mêmes graph.json,
seul le regroupement change.

## Calibration (load-bearing)

Les seuils `TEXT_SIM` 0.715 / `TRANSLATION` 0.85 et `flag_threshold` 0.30 sont
des **graines spécifiques au modèle** (issues de D3lta/BGE-M3) : ils n'ont pas de
valeur validée pour le modèle ST retenu. **À recalibrer** sur données réelles
avant de s'y fier :

```bash
uv run python scripts/calibrate_text_sim.py --limit 800
```

et l'éval `eval_embeddings_classification.py` contre le gold partagé
(`data/eval/gold_*.json`) donne precision/recall/F1, Spearman et Jaccard@K vs la
piste Mistral. Tant que la calibration n'est pas faite, traiter les sorties comme
**exploratoires** (cohérent avec la posture T1/T2 explicable d'Idéfix).
