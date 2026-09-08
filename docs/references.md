# Références académiques — projet Idefix

> **Note.** Ces références ancrent les **choix méthodologiques** d'Idefix : chaque
> méthode appliquée dans le code (détection de communautés, significativité,
> embeddings, signaux de coordination) renvoie ici à sa source canonique.
>
> Certaines méthodes sont citées comme **cibles / différées** et ne sont **pas
> encore implémentées** dans le PoC — notamment la similarité textuelle D3lta
> (VIGINUM), l'embedding multilingue BGE-M3, et l'approche GNN de
> MisinfoTeleGraph. Voir `docs/scientific-audit.md` pour l'état d'implémentation
> et l'écart entre cible et code actuel.
>
> Les DOI / identifiants arXiv ont été vérifiés lorsque disponibles. En cas
> d'incertitude sur un DOI précis, seuls Auteurs / Année / Titre / Venue sont
> donnés.

---

## Détection de communautés & graphes

- **Leiden.** Traag, V.A., Waltman, L., van Eck, N.J. (2019).
  *From Louvain to Leiden: guaranteeing well-connected communities.*
  Scientific Reports 9:5233. doi:10.1038/s41598-019-41695-z
- **Louvain.** Blondel, V.D., Guillaume, J.-L., Lambiotte, R., Lefebvre, E. (2008).
  *Fast unfolding of communities in large networks.*
  Journal of Statistical Mechanics: Theory and Experiment, P10008.
- **Modularité.** Newman, M.E.J., Girvan, M. (2004).
  *Finding and evaluating community structure in networks.*
  Physical Review E 69:026113. ; Newman, M.E.J. (2006).
  *Modularity and community structure in networks.*
  PNAS 103(23):8577-8582.
- **Centralité vecteur propre.** Bonacich, P. (1972).
  *Factoring and weighting approaches to status scores and clique identification.*
  Journal of Mathematical Sociology 2(1):113-120.
- **Bridge Score.** Shah, D., Ranka, H., Ng, L.H.X., Mehta, S. (2024).
  *Bridging Nodes and Narrative Flows: Identifying Intervention Targets for
  Disinformation on Telegram.* arXiv:2411.05922.

## Clustering / qualité de partition

- **Silhouette.** Rousseeuw, P.J. (1987).
  *Silhouettes: a graphical aid to the interpretation and validation of cluster
  analysis.* Journal of Computational and Applied Mathematics 20:53-65.
- **NMI (Normalized Mutual Information).** Danon, L., Díaz-Guilera, A., Duch, J.,
  Arenas, A. (2005). *Comparing community structure identification.*
  Journal of Statistical Mechanics, P09008.
- **ARI (Adjusted Rand Index).** Hubert, L., Arabie, P. (1985).
  *Comparing partitions.* Journal of Classification 2:193-218.

## Statistiques / significativité

- **Benjamini-Hochberg (FDR).** Benjamini, Y., Hochberg, Y. (1995).
  *Controlling the false discovery rate: a practical and powerful approach to
  multiple testing.* Journal of the Royal Statistical Society, Series B,
  57(1):289-300.
- **Combinaison de Stouffer.** Stouffer, S.A., Suchman, E.A., DeVinney, L.C.,
  Star, S.A., Williams, R.M. (1949). *The American Soldier, Vol. 1: Adjustment
  During Army Life.* Princeton University Press.
- **Bootstrap.** Efron, B. (1979). *Bootstrap methods: another look at the
  jackknife.* The Annals of Statistics 7(1):1-26. ; Efron, B., Tibshirani, R.J.
  (1993). *An Introduction to the Bootstrap.* Chapman & Hall.
- **Tests de permutation.** Good, P. (2000). *Permutation Tests: A Practical
  Guide to Resampling Methods for Testing Hypotheses.* Springer.
- **ROC-AUC.** Fawcett, T. (2006). *An introduction to ROC analysis.*
  Pattern Recognition Letters 27(8):861-874.
- **Corrélation de rang.** Spearman, C. (1904). *The proof and measurement of
  association between two things.* The American Journal of Psychology 15(1):72-101.

## NLP / embeddings

- **TF-IDF.** Spärck Jones, K. (1972). *A statistical interpretation of term
  specificity and its application in retrieval.* Journal of Documentation
  28(1):11-21. ; Salton, G., Buckley, C. (1988). *Term-weighting approaches in
  automatic text retrieval.* Information Processing & Management 24(5):513-523.
- **Sentence-BERT (SBERT).** Reimers, N., Gurevych, I. (2019).
  *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.*
  EMNLP-IJCNLP 2019. arXiv:1908.10084.
- **MiniLM.** Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., Zhou, M. (2020).
  *MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of
  Pre-Trained Transformers.* NeurIPS 2020. arXiv:2002.10957.
- **BGE-M3** *(cible / différé — non implémenté).* Chen, J., Xiao, S., Zhang, P.,
  Luo, K., Lian, D., Liu, Z. (2024). *BGE M3-Embedding: Multi-Lingual,
  Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge
  Distillation.* arXiv:2402.03216.

## Désinformation / coordination (CIB)

- **Coordinated Inauthentic Behavior (CIB).**
  Pacheco, D., Hui, P.-M., Torres-Lugo, C., Truong, B.T., Flammini, A.,
  Menczer, F. (2021). *Uncovering Coordinated Networks on Social Media: Methods
  and Case Studies.* ICWSM 2021. ;
  Giglietto, F., Righetti, N., Rossi, L., Marino, G. (2020). *It takes a village
  to manipulate the media: coordinated link sharing behavior during 2018 and
  2019 Italian elections.* Information, Communication & Society 23(6):867-891. ;
  Nizzoli, L., Tardelli, S., Avvenuti, M., Cresci, S., Tesconi, M. (2021).
  *Coordinated Behavior on Social Media in 2019 UK General Election.* ICWSM 2021.
- **MisinfoTeleGraph** *(cible / différé — GNN non implémenté).*
  Kalkbrenner, L., Solopova, V., Zeiler, S., Nickel, R., Kolossa, D. (2025).
  *MisinfoTeleGraph: Network-driven Misinformation Detection for German Telegram
  Messages.* arXiv:2506.22529.
- **VIGINUM D3lta** *(cible / différé — détection texte non implémentée).*
  Méthode de détection de similarité textuelle (copypasta / reformulation /
  traduction) développée par VIGINUM, le service français de vigilance et de
  protection contre les ingérences numériques étrangères. Outil open source
  publié par VIGINUM.
