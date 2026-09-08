# Analytics vs Embedding — deux lectures de la même galaxie

Idefix détecte les communautés de canaux par **Leiden** [Traag et al., 2019] sur le
même graphe, selon deux pistes complémentaires. Ce document explique ce que chaque
piste optimise, les métriques qui les comparent, et le **trade-off** qui les sépare.
Chiffres : `docs/metrics/analytics_vs_embedding.json` (mission russosphere, galaxie
1170 nœuds). Références : `docs/references.md`.

## Les deux pistes

| Piste | Signal | Ce qu'elle optimise |
|-------|--------|---------------------|
| **Analytics** (lexical / TF-IDF) | structure des liens observés (forwards, mentions, co-citations) + vocabulaire | communautés **structurelles** : qui rediffuse qui |
| **Embedding** (sémantique) | graphe enrichi d'arêtes de similarité d'embeddings (`EMB_SIM`, k=5 plus proches voisins, seuil cosinus 0.5, poids = 3·cosinus) | communautés **sémantiques** : qui « parle pareil » |

Les arêtes `EMB_SIM` ne sont jamais persistées : elles donnent seulement à Leiden un
signal de contenu continu (embeddings locaux `paraphrase-multilingual-MiniLM-L12-v2`,
384-dim [Reimers & Gurevych, 2019 ; Wang et al., 2020]) là où le graphe structurel
est creux.

## Les métriques (et pourquoi chacune)

- **Cohésion intra** — cosinus moyen intra-communauté sur les embeddings. Plus haut =
  groupes plus homogènes thématiquement.
- **Silhouette** [Rousseeuw, 1987] — cohésion vs séparation des clusters dans l'espace
  d'embedding (∈ [−1, 1]).
- **Modularité** [Newman, 2006] — qualité de la partition sur le **graphe de liens**
  (fraction d'arêtes intra-communauté au-delà du hasard).
- **NMI / ARI** [Danon et al., 2005 ; Hubert & Arabie, 1985] — accord entre les deux
  partitions (1 = identiques, ~0 = sans rapport).

## Résultats (russosphere)

| Métrique | Analytics | Embedding | Lecture |
|----------|-----------|-----------|---------|
| Cohésion intra | 0.6709 | **0.7049** | +5.1 % — groupes plus cohérents sémantiquement |
| Silhouette (cosine) | −0.2738 | **0.0214** | s'améliore mais reste faible (clusters peu nets dans l'espace d'embedding) |
| Modularité | **0.7547** | 0.6301 | baisse — voir trade-off |
| Communautés conservées (≥2 canaux) | 27 | 17 | l'embedding fusionne des groupes |
| Communautés brutes (singletons inclus) | 512 | 464 | exposé pour transparence |
| NMI (accord partitions) | — | 0.887 | partitions globalement proches |
| ARI (accord partitions) | — | 0.528 | mais ~la moitié de la structure fine est réorganisée |

## Le trade-off (load-bearing)

> L'embedding **augmente la cohésion sémantique** mais **baisse la modularité**.

Ce n'est **pas** une régression — ce sont deux objectifs différents :

- la **modularité** récompense les arêtes intra-communauté **du graphe de liens**
  (diffusion observée) ;
- les arêtes `EMB_SIM` relient des canaux sémantiquement proches **même quand aucun
  forward ne les lie** — elles **traversent** donc les communautés structurelles, ce
  qui mécaniquement abaisse la modularité tout en remontant la cohésion de contenu.

NMI élevé (0.887) + ARI moyen (0.528) confirment : la piste embedding garde la macro-
structure mais **réorganise environ la moitié** des regroupements fins — exactement le
comportement attendu d'un signal de contenu ajouté à un signal de structure.

**Quand utiliser laquelle.** Analytics répond « qui rediffuse qui » (cartographie de
diffusion, livrable T1). Embedding répond « qui partage la même ligne éditoriale »
(cohérence thématique). Le commutateur galaxie bascule entre les deux snapshots ; le
bon défaut dépend de la question posée, pas d'une supériorité absolue.

## Note de correction

Une version antérieure du bloc `comparison` rapportait `n_communities` = 512/463
(toutes les communautés, **singletons inclus**), incohérent avec le snapshot (27/17,
communautés ≥2 canaux). Corrigé : `n_communities` = communautés **conservées**, et
`n_communities_raw` expose le compte brut (`src/embed/community.py::comparison_block`).
