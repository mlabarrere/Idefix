# References

Every entry below was **resolved against Crossref or arXiv** and its authors,
year, venue, volume and pages verified. Entries that could not be verified, or
that grounded no implemented method, were removed.

Each entry states **where it is used**. A reference that grounds nothing in the
code is not listed as if it did.

Machine-readable form: [`references.bib`](./references.bib).

---

## Community detection and graph structure

**Traag, V. A., Waltman, L., & van Eck, N. J. (2019).** From Louvain to Leiden:
guaranteeing well-connected communities. *Scientific Reports*, 9, 5233.
doi:[10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z)
→ *Used:* the community-detection algorithm, `scripts/analyze_communities.py`.
Note that the resolution parameter is set by inspection, not by the paper — see
`../limitations.md` D14.

**Blondel, V. D., Guillaume, J.-L., Lambiotte, R., & Lefebvre, E. (2008).** Fast
unfolding of communities in large networks. *Journal of Statistical Mechanics*,
2008(10), P10008.
doi:[10.1088/1742-5468/2008/10/P10008](https://doi.org/10.1088/1742-5468/2008/10/P10008)
→ *Used:* `scripts/detect_clusters.py` (`community_multilevel`).

**Newman, M. E. J., & Girvan, M. (2004).** Finding and evaluating community
structure in networks. *Physical Review E*, 69(2), 026113.
doi:[10.1103/PhysRevE.69.026113](https://doi.org/10.1103/PhysRevE.69.026113)

**Newman, M. E. J. (2006).** Modularity and community structure in networks.
*PNAS*, 103(23), 8577–8582.
doi:[10.1073/pnas.0601602103](https://doi.org/10.1073/pnas.0601602103)
→ *Used:* the modularity figure reported for both community tracks.

**Bonacich, P. (1972).** Factoring and weighting approaches to status scores and
clique identification. *The Journal of Mathematical Sociology*, 2(1), 113–120.
→ *Used:* the eigenvector-centrality term of family (b). In practice that term
is numerically negligible at corpus scale — `../limitations.md` D9.

**Shah, D., Ranka, H., Ng, L. H. X., & Mehta, S. (2024).** Bridging Nodes and
Narrative Flows: Identifying Intervention Targets for Disinformation on
Telegram. arXiv:[2411.05922](https://arxiv.org/abs/2411.05922)
→ *Used:* family (b), the Bridge Score composite, `src/scorer/cascade_role.py`.

## Cluster and partition quality

**Rousseeuw, P. J. (1987).** Silhouettes: a graphical aid to the interpretation
and validation of cluster analysis. *Journal of Computational and Applied
Mathematics*, 20, 53–65.
→ *Used:* silhouette scores in the community comparison.

**Danon, L., Díaz-Guilera, A., Duch, J., & Arenas, A. (2005).** Comparing
community structure identification. *Journal of Statistical Mechanics*,
2005(09), P09008.
doi:[10.1088/1742-5468/2005/09/P09008](https://doi.org/10.1088/1742-5468/2005/09/P09008)
→ *Used:* NMI between the analytics and embedding partitions.

**Hubert, L., & Arabie, P. (1985).** Comparing partitions. *Journal of
Classification*, 2(1), 193–218.
→ *Used:* ARI between the analytics and embedding partitions.

## Statistics and significance

**Benjamini, Y., & Hochberg, Y. (1995).** Controlling the false discovery rate:
a practical and powerful approach to multiple testing. *Journal of the Royal
Statistical Society, Series B*, 57(1), 289–300.
→ *Used:* FDR control across channels, `src/scorer/significance.py:197-211`
(via `statsmodels`).

**Stouffer, S. A., Suchman, E. A., DeVinney, L. C., Star, S. A., & Williams,
R. M. (1949).** *The American Soldier, Vol. 1: Adjustment During Army Life.*
Princeton University Press.
→ *Used:* weighted p-value combination, `significance.py:180-194`. Note the
independence assumption is violated in the current pipeline —
`../limitations.md` D3.

**Efron, B. (1979).** Bootstrap methods: another look at the jackknife. *The
Annals of Statistics*, 7(1), 1–26.
→ *Used:* confidence intervals for families (b) and (d). Currently run at
`n_bootstrap = 100`, which is too low — `../limitations.md` D7.

**Good, P. (2000).** *Permutation Tests: A Practical Guide to Resampling Methods
for Testing Hypotheses.* Springer.
→ *Used:* the randomized-endpoint null model, `significance.py:42-75`.

**Fawcett, T. (2006).** An introduction to ROC analysis. *Pattern Recognition
Letters*, 27(8), 861–874.
→ *Used:* the evaluation protocols in `../experiments/`.

**Spearman, C. (1904).** The proof and measurement of association between two
things. *The American Journal of Psychology*, 15(1), 72–101.
→ *Used:* rank correlation in the ablation protocols.

## NLP and embeddings

**Spärck Jones, K. (1972).** A statistical interpretation of term specificity and
its application in retrieval. *Journal of Documentation*, 28(1), 11–21.
→ *Used:* TF-IDF labelling of communities and episodes.

**Reimers, N., & Gurevych, I. (2019).** Sentence-BERT: Sentence Embeddings using
Siamese BERT-Networks. *EMNLP-IJCNLP 2019.*
arXiv:[1908.10084](https://arxiv.org/abs/1908.10084)
→ *Used:* the sentence-embedding approach behind family (f) and the embedding
community track.

**Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., & Zhou, M. (2020).** MiniLM:
Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained
Transformers. *NeurIPS 2020.* arXiv:[2002.10957](https://arxiv.org/abs/2002.10957)
→ *Used:* the deployed encoder,
`paraphrase-multilingual-MiniLM-L12-v2`. No ablation against alternative
encoders has been run — `../limitations.md` D14.

## Coordinated inauthentic behaviour

**Pacheco, D., Hui, P.-M., Torres-Lugo, C., Truong, B. T., Flammini, A., &
Menczer, F. (2021).** Uncovering Coordinated Networks on Social Media: Methods
and Case Studies. *Proceedings of the International AAAI Conference on Web and
Social Media*, 15(1), 455–466.
doi:[10.1609/icwsm.v15i1.18075](https://doi.org/10.1609/icwsm.v15i1.18075)
→ *Framing:* coordination detected from shared behavioural artefacts within a
time window — the family of methods that `02-graph-model.md` §2.2 belongs to.

**Giglietto, F., Righetti, N., Rossi, L., & Marino, G. (2020).** It takes a
village to manipulate the media: coordinated link sharing behavior during 2018
and 2019 Italian elections. *Information, Communication & Society*, 23(6),
867–891.
→ *Framing:* coordinated link sharing, the direct antecedent of the `CO_URL` and
`CO_URL_EXACT` families.

**Nizzoli, L., Tardelli, S., Avvenuti, M., Cresci, S., & Tesconi, M. (2021).**
Coordinated Behavior on Social Media in 2019 UK General Election. *Proceedings
of the International AAAI Conference on Web and Social Media*, 15, 443–454.
→ *Framing:* thresholding and validation of coordination networks.

## Cited as provenance of a constant, not as an implemented method

**VIGINUM — D3lta.** Text-similarity detection (copypasta, rewording,
translation) published as open source by VIGINUM, the French service for
vigilance and protection against foreign digital interference.
→ *Provenance only:* the constants `TEXT_SIM_THRESHOLD = 0.715` and
`TRANSLATION_THRESHOLD = 0.85` (`src/graph/edges.py:454-455`) were taken from
this work. **They are applied to a different embedding model and have never been
calibrated for it** — `../limitations.md` D13. The D3lta method itself is *not*
implemented here.

## Related work, not implemented

**Kalkbrenner, L., Solopova, V., Zeiler, S., Nickel, R., & Kolossa, D. (2025).**
MisinfoTeleGraph: Network-driven Misinformation Detection for German Telegram
Messages. arXiv:[2506.22529](https://arxiv.org/abs/2506.22529)
→ *Not implemented.* A GraphSAGE+LSTM classifier over Telegram forward
structure. Listed because it is the closest published system to this problem and
informed the graph schema, **not** because any part of it runs here. An earlier
version of this project's methodology described such a network as the detection
core; it never was.
