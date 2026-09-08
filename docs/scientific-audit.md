# Audit scientifique de la méthode Idefix

> Système d'analyse de propagation et de coordination sur Telegram, multi-mission, à sorties **T1 / T2 « arm-only »** vers VIGINUM / Arcom.
> Document d'audit interne — registre académique. Date : 2026-06-29.
> **Source de vérité chiffrée :** `docs/metrics/_summary.json` et `docs/metrics/*.json` (calculés depuis Supabase ; corpus *russosphere* de 3699 canaux scorés ; graphe FORWARD de 3788 nœuds / 6889 arêtes). Tous les chiffres ci-dessous en sont extraits.

---

## 1. Objet & posture

Cet audit porte sur la **méthode scientifique**, non sur le code. Il ne juge pas la qualité d'implémentation ni l'ingénierie, mais la **validité des inférences** que le système autorise.

Posture calibrée, assumée comme telle :

- **Défendable.** Idefix est un **démonstrateur T1** : il met en évidence une **structure de diffusion observable** (qui relaie qui, vers quelles communautés, avec quel degré de récurrence) et démontre que cette structure est **séparable de la centralité brute** (cf. §5, Exp 1).
- **NON défendable en l'état.** Idefix **n'est pas** un détecteur de manipulation validé. Aucune des expériences disponibles ne démontre que les scores élevés correspondent à de la manipulation coordonnée plutôt qu'à de la simple proéminence adverse (cf. §5, Exp 3 ; §8, gaps bloquants).
- **Couverture.** **Telegram uniquement.** Aucune revendication n'est portée sur d'autres plateformes, ni sur des trajectoires cross-plateformes.

La règle de lecture de tout le document : **ce qui est mesuré au-dessus du hasard est rapporté comme tel ; ce qui n'est pas mesurable est déclaré bloqué, jamais comblé par de la prose.**

---

## 2. Ancrage des familles de score

On distingue trois statuts : **cité+implémenté** (référence académique + code), **implémenté sans citation** (choix de conception, à requalifier comme tel faute de référence), et **cité non implémenté** (seam réservé).

### 2.1 Familles avec ancrage

| Fam. | Intitulé | Statut | Ancrage / implémentation |
|------|----------|--------|--------------------------|
| (b) | Rôle en cascade | **Cité + implémenté** | Bridge Score, arXiv:2411.05922. Formule `10·in_degree + 7·eigenvector + 7·clustering`. `src/scorer/cascade_role.py`. |
| (d) | Récidive inter-épisodes | **Implémenté (approximation PoC)** | `src/scorer/recidivism.py`. Faute de table d'épisodes peuplée, l'implémentation **approxime** la récidive par la **récurrence structurelle dans le graphe de forward agrégé** — approximation explicitement documentée, à remplacer par une vraie séquence d'épisodes. |
| (f) | Cohérence sémantique | **Implémenté (opt-in)** | `src/scorer/embedding_signals.py`. Pondération **distance-baseline 0.4 + proximité-adversaire 0.6**. Modèle **MiniLM-L12-v2**, 384 dimensions. |
| (c) | Coordination | **Structurel implémenté ; texte différé** | Partie structurelle : **Jaccard des co-forwards**, `src/scorer/coordination.py`. Partie texte (D3lta) **différée** : seuils cités — **copypasta 0.693 / reformulation 0.715 / traduction 0.85** — mais **non câblés**. |
| (a) | Proximité de revendication (BGE-M3) | **Cité, NON implémenté** | Seam réservé. |
| (e) | Origine IA | **Cité, NON implémenté** | Seam réservé. |

### 2.2 Implémenté **mais non cité** — à requalifier en « choix de conception »

Les éléments suivants sont en production sans référence académique ; ils doivent être **assumés comme des choix de conception** et non présentés comme méthode validée :

- **Leiden** (détection de communautés) ;
- **Gate multi-source** (déclenchement conditionné à **≥ 2 familles** actives) ;
- **Modulateurs de sévérité** : **± 20 %** reforward, **± 15 %** domaine adverse, **± 20 %** ciblage ;
- **Taxonomie TF-IDF** : **28 patterns regex** ;
- **Percentile P75** du Bridge Score comme seuil ;
- **Paramètres des arêtes EMB_SIM** : **k = 5**, seuil **0.5**, `weight_scale` **3.0**.

Aucun de ces choix n'est invalide ; mais chacun est un **degré de liberté non justifié par la littérature**, donc une cible prioritaire d'analyse de sensibilité (§3, §8).

---

## 3. Rigueur statistique

### 3.1 Forces

Implémentées dans `src/scorer/significance.py` et `src/scorer/rigor.py` :

- **Modèle nul par randomisation d'extrémités** (*endpoint randomization*). C'est le bon choix pour la **topologie en étoile, profondeur 1**, de Telegram : le rewiring degree-preserving classique y est **dégénéré** (peu ou pas de configurations alternatives), alors que la randomisation d'extrémités produit un nul exploitable.
- **p-values add-one** — jamais nulles, ce qui évite les faux « p = 0 » des modèles nuls à échantillonnage fini.
- **Bootstrap** pour les intervalles de confiance.
- **Correction Benjamini-Hochberg** (contrôle du FDR) sur les tests multiples.
- **Combinaison de Stouffer** pour agréger les signaux indépendants.
- **RNG déterministe (seed 1312)** → bundle de résultats **reproductible**.

### 3.2 Faiblesses

- **Famille (c) coordination : SANS modèle nul.** La p-value y est calculée comme `p = 1 − valeur` — c'est un **placebo**, pas un test de significativité. C'est la faiblesse statistique la plus grave du dispositif.
- **`n_bootstrap = 100`** : trop faible pour des IC stables ; **recommandé ≥ 1000**.
- **Paramètres EMB_SIM (k = 5 / seuil 0.5 / scale 3.0) : aucune analyse de sensibilité.** Les sorties dépendent de trois constantes non auditées.
- **Modèle d'embedding : aucune ablation.** MiniLM-L12-v2 est retenu sans comparaison contre des alternatives (e5, MPNet) — on ne sait pas si le choix de modèle porte les résultats.

---

## 4. Analytics vs embedding — le trade-off (chiffres réels)

Source : `docs/metrics/analytics_vs_embedding.json`. Corpus **galaxie échantillonné : 1170 nœuds communs** aux deux partitions.

| Métrique | Analytics | Embedding | Variation |
|----------|-----------|-----------|-----------|
| Cohésion intra-communauté (cosinus moyen) | 0.6709 | **0.7049** | **+ 5,1 %** |
| Silhouette (Rousseeuw 1987) | −0.2738 | **0.0214** | en hausse |
| Modularité (Newman 2006, graphe de LIENS) | **0.7547** | 0.6301 | **en baisse** |
| Communautés conservées (≥ 2 canaux) | 27 | 17 | — |
| Communautés brutes (singletons inclus) | 512 | 464 | — |
| Accord des partitions | — | — | **NMI 0.887 / ARI 0.528** |

### 4.1 Lecture du trade-off (load-bearing)

Le point central de cet audit. La baisse de modularité **n'est pas une régression** ; c'est la signature attendue de deux objectifs distincts :

- Les arêtes **EMB_SIM** rapprochent les canaux qui **« parlent pareil »** → la **cohésion sémantique monte** (+ 5,1 % ; silhouette de négative à légèrement positive).
- Ces mêmes arêtes **traversent les communautés structurelles** définies par les forwards → la **modularité au sens de Newman, qui se calcule sur le graphe de LIENS, baisse mécaniquement**.

Maximiser la cohésion sémantique et maximiser la modularité structurelle sont **deux objectifs différents** ; gagner sur l'un coûte sur l'autre. Présenter la baisse de modularité comme une dégradation serait une **erreur de cadre**.

### 4.2 Accord des partitions

**NMI 0.887** (élevé) + **ARI 0.528** (moyen) : l'embedding **conserve l'essentiel de la structure grossière** mais **réorganise ~la moitié de la structure fine**. C'est cohérent avec un signal additionnel non trivial, ni redondant ni bruit.

### 4.3 Correction apportée par cet audit

L'ancienne incohérence apparente sur `n_communities` (**512 vs 27**) provenait d'un **comptage incluant les singletons**. On expose désormais **les deux** mesures — communautés **conservées (≥ 2)** *et* **brutes** — ce qui lève l'ambiguïté.

---

## 5. État de validation — 4 expériences + significativité globale

Tous les chiffres sont reproductibles depuis les artefacts cités. Verdicts pris **tels que produits**, sans arrondi favorable.

### Exp 1 — Ablation centralité : **PASS**
Artefact : `docs/metrics/ablation_centrality.json` (3699 canaux ; **814** à suspicion > 0).

Spearman(suspicion, *baseline*) :

| Baseline | Spearman | Jaccard@50 |
|----------|----------|------------|
| in-degree | 0.667 | 0.020 |
| eigenvector | 0.537 | 0.053 |
| influence-forward | 0.424 | 0.099 |
| activité / engagement | 0.317 | 0.010 |
| *(composite cascade, témoin)* | *0.792* | *0.190* |

Seuils de **falsification** : Spearman > 0.90 **OU** Jaccard@50 > 0.80. **Aucun n'est approché.** Conclusion : **le score n'est pas de la centralité maquillée** — il porte un signal séparable des mesures de proéminence brute.

### Exp 2 — Récupération d'épisode (gold EXTERNE non circulaire) : **FAIBLE**
Artefact : `docs/metrics/episode_recovery.json`. Épisode « Dugin Eurasianist Network (External Gold) ».

- Taille du cluster gold : 12 ; **présents dans le corpus : 3**.
- **recall@50 = 0.167** vs hasard 0.162 → **× 12,35** au-dessus du contrôle aléatoire ; rang médian **50**.
- recall@20 = 0.0 ; recall@100 = 0.167.

**Caveat fort.** Le gold est **hypothétique** (pas un vrai gold VIGINUM) et l'**overlap est minuscule** (3 canaux). Le « × 12,35 » est arithmétiquement réel mais repose sur une base trop petite pour être probant. Verdict honnête : **indicatif, non concluant**.

### Exp 3 — Discriminant hostile / organique : **MITIGÉ + bloqué**
Artefact : `docs/metrics/discriminant_organic.json`. Parmi **446** canaux coordonnés (**48** en T2) :

- Spearman(suspicion, **ancrage adverse**) = **0.765** ← **dominant** ;
- Spearman(suspicion, **coordination seule**) = 0.253 ;
- Spearman(suspicion, **base structurelle**) = 0.488.

Lecture : **la discrimination vient des boosts d'ancrage adverse, pas de la structure de coordination.** Le score « voit » surtout *qui est proche de l'adversaire*, pas *qui se coordonne*.

**Blocage.** **0 candidat organique** dans le corpus (corpus amorcé sur l'adversaire) → le discriminant **n'est jamais stressé** contre des négatifs. On ne peut donc pas savoir s'il distinguerait coordination hostile et coordination organique légitime. Règle de falsification associée (≥ 3 organiques confirmés dans le top-50) **non testable** en l'absence de négatifs.

### Exp f — Discrimination par embeddings : **FAIBLE + décalage méthodologique**
Artefact : `docs/metrics/embedding_discrimination_russosphere.json`.

- **ROC-AUC = 0.506** (≈ hasard ; cible > 0.7) ; **silhouette 0.003** ; séparation des centroïdes 0.171 (baseline FR organique externe n = 96 vs scored n = 3492).

**Décalage critique.** Le script embedde les **usernames seuls** (`@handle`), **pas le contenu des messages** comme le fait la famille (f) déployée. **Ce test ne teste donc pas la famille (f) telle que livrée.** Le ROC-AUC ≈ 0.5 mesure l'inséparabilité des *handles*, ce qui est attendu et non informatif sur la méthode réelle.
**Recommandation :** **ré-encoder sur le contenu** (embeddings de messages) avant toute conclusion sur (f).

### Significativité globale du scoring (ROC-AUC vs gold / permutation / calibration) : **NON CALCULABLE**
`channel_gold` = **12 positifs / 0 négatif** (corpus organique absent) → **ROC-AUC indéfini**. C'est le **gap bloquant** qui empêche toute affirmation de performance globale.

---

## 6. Anomalie de calibration : *gan* vs *russosphere*

| Mission | Canaux T2 |
|---------|-----------|
| gan | **1266** |
| russosphere | **48** |

Écart d'un facteur ~26. **À expliquer par les familles `telegram_*` (gate plus basse sur la mission *gan*), PAS par « plus de vrais positifs ».** À **traiter comme un artefact de calibration à réviser**, non comme un résultat. Tant que les gates ne sont pas harmonisées et documentées, le volume T2 de *gan* n'est pas interprétable.

---

## 7. Reproductibilité — avant → après cet audit

| | Avant | Après |
|---|-------|-------|
| Chiffres de validation | **Prose uniquement** (`docs/validation-state.md`, METHODOLOGY §8) | **Artefacts JSON** matérialisés sous `docs/metrics/` |
| Scores | `channels.json` exporté avec **suspicion = 0** ; aucun artefact | Scores réels en base (**Supabase `channel_scores`**) |
| Évaluations | Non rejouables | **Recalculées et committées** |
| Source citée | Divergente | **Source unique**, citée identiquement par METHODOLOGY §8 **et** `validation-state.md` |

Gain net : on passe d'affirmations narratives non vérifiables à un **bundle de métriques reproductible et cité de façon univoque**.

---

## 8. Gaps bloquants & recommandations priorisées

1. **Corpus de coordination organique (négatifs).** Débloque **Exp 3** *et* la significativité globale (ROC-AUC). Requiert une **annotation humaine**. — *priorité maximale.*
2. **Gold VIGINUM externe réel** (remplacer le gold hypothétique) → rend **Exp 2** probante.
3. **Discrimination embeddings sur le CONTENU** (messages), pas les usernames → rend **Exp f** valide pour la famille (f) déployée.
4. **Modèle nul pour la coordination (famille c)** → supprime la p-value placebo (§3.2).
5. **Analyse de sensibilité EMB_SIM** (k / seuil / scale) **+ ablation du modèle d'embedding** (MiniLM vs e5 / MPNet).
6. **`n_bootstrap ≥ 1000`.**

---

## 9. Verdict

Idefix est un **démonstrateur T1 honnête et désormais reproductible** : il établit, chiffres à l'appui, qu'une structure de diffusion observable existe et qu'elle est **séparable de la centralité brute** (Exp 1 PASS). Les revendications plus fortes — **T2 comme détecteur de manipulation validé** — restent **bloquées** par deux absences documentées : **corpus de coordination organique (négatifs)** et **gold externe réel**. Cette limite n'est pas masquée ; elle est la conclusion explicite de l'audit.

---

### Renvois

- Bibliographie et références complètes : [`docs/references.md`](./references.md).
- Détail du trade-off analytics vs embedding : [`docs/analytics-vs-embedding.md`](./analytics-vs-embedding.md) (artefact chiffré : [`docs/metrics/analytics_vs_embedding.json`](./metrics/analytics_vs_embedding.json)).
