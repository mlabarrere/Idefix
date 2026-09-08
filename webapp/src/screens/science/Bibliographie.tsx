// Bibliographie académique — transcription de docs/references.md.
import { DocPage, Section, List, Ref, Id, Note } from './docs-ui'

export function Bibliographie() {
  return (
    <DocPage
      title="Références académiques"
      subtitle="Chaque méthode appliquée dans le code renvoie ici à sa source canonique."
      source="docs/references.md"
    >
      <Note>
        Ces références ancrent les <strong>choix méthodologiques</strong> d'Idéfix. Certaines
        méthodes sont citées comme <em>cibles / différées</em> et ne sont <strong>pas encore
        implémentées</strong> dans le PoC — notamment la similarité textuelle D3lta (VIGINUM),
        l'embedding multilingue BGE-M3 et l'approche GNN de MisinfoTeleGraph. Voir l'audit
        scientifique pour l'écart entre cible et code actuel. Les DOI / identifiants arXiv ont été
        vérifiés lorsque disponibles.
      </Note>

      <Section title="Détection de communautés & graphes">
        <List>
          <Ref tag="Leiden">
            Traag, V.A., Waltman, L., van Eck, N.J. (2019). <em>From Louvain to Leiden: guaranteeing
            well-connected communities.</em> Scientific Reports 9:5233.{' '}
            <Id>doi:10.1038/s41598-019-41695-z</Id>
          </Ref>
          <Ref tag="Louvain">
            Blondel, V.D., Guillaume, J.-L., Lambiotte, R., Lefebvre, E. (2008). <em>Fast unfolding of
            communities in large networks.</em> Journal of Statistical Mechanics: Theory and
            Experiment, P10008.
          </Ref>
          <Ref tag="Modularité">
            Newman, M.E.J., Girvan, M. (2004). <em>Finding and evaluating community structure in
            networks.</em> Physical Review E 69:026113. ; Newman, M.E.J. (2006). <em>Modularity and
            community structure in networks.</em> PNAS 103(23):8577-8582.
          </Ref>
          <Ref tag="Centralité vecteur propre">
            Bonacich, P. (1972). <em>Factoring and weighting approaches to status scores and clique
            identification.</em> Journal of Mathematical Sociology 2(1):113-120.
          </Ref>
          <Ref tag="Bridge Score">
            Shah, D., Ranka, H., Ng, L.H.X., Mehta, S. (2024). <em>Bridging Nodes and Narrative Flows:
            Identifying Intervention Targets for Disinformation on Telegram.</em> <Id>arXiv:2411.05922</Id>
          </Ref>
        </List>
      </Section>

      <Section title="Clustering / qualité de partition">
        <List>
          <Ref tag="Silhouette">
            Rousseeuw, P.J. (1987). <em>Silhouettes: a graphical aid to the interpretation and
            validation of cluster analysis.</em> Journal of Computational and Applied Mathematics
            20:53-65.
          </Ref>
          <Ref tag="NMI (Normalized Mutual Information)">
            Danon, L., Díaz-Guilera, A., Duch, J., Arenas, A. (2005). <em>Comparing community structure
            identification.</em> Journal of Statistical Mechanics, P09008.
          </Ref>
          <Ref tag="ARI (Adjusted Rand Index)">
            Hubert, L., Arabie, P. (1985). <em>Comparing partitions.</em> Journal of Classification
            2:193-218.
          </Ref>
        </List>
      </Section>

      <Section title="Statistiques / significativité">
        <List>
          <Ref tag="Benjamini-Hochberg (FDR)">
            Benjamini, Y., Hochberg, Y. (1995). <em>Controlling the false discovery rate: a practical
            and powerful approach to multiple testing.</em> Journal of the Royal Statistical Society,
            Series B, 57(1):289-300.
          </Ref>
          <Ref tag="Combinaison de Stouffer">
            Stouffer, S.A., Suchman, E.A., DeVinney, L.C., Star, S.A., Williams, R.M. (1949). <em>The
            American Soldier, Vol. 1: Adjustment During Army Life.</em> Princeton University Press.
          </Ref>
          <Ref tag="Bootstrap">
            Efron, B. (1979). <em>Bootstrap methods: another look at the jackknife.</em> The Annals of
            Statistics 7(1):1-26. ; Efron, B., Tibshirani, R.J. (1993). <em>An Introduction to the
            Bootstrap.</em> Chapman &amp; Hall.
          </Ref>
          <Ref tag="Tests de permutation">
            Good, P. (2000). <em>Permutation Tests: A Practical Guide to Resampling Methods for Testing
            Hypotheses.</em> Springer.
          </Ref>
          <Ref tag="ROC-AUC">
            Fawcett, T. (2006). <em>An introduction to ROC analysis.</em> Pattern Recognition Letters
            27(8):861-874.
          </Ref>
          <Ref tag="Corrélation de rang">
            Spearman, C. (1904). <em>The proof and measurement of association between two things.</em>{' '}
            The American Journal of Psychology 15(1):72-101.
          </Ref>
        </List>
      </Section>

      <Section title="NLP / embeddings">
        <List>
          <Ref tag="TF-IDF">
            Spärck Jones, K. (1972). <em>A statistical interpretation of term specificity and its
            application in retrieval.</em> Journal of Documentation 28(1):11-21. ; Salton, G., Buckley,
            C. (1988). <em>Term-weighting approaches in automatic text retrieval.</em> Information
            Processing &amp; Management 24(5):513-523.
          </Ref>
          <Ref tag="Sentence-BERT (SBERT)">
            Reimers, N., Gurevych, I. (2019). <em>Sentence-BERT: Sentence Embeddings using Siamese
            BERT-Networks.</em> EMNLP-IJCNLP 2019. <Id>arXiv:1908.10084</Id>
          </Ref>
          <Ref tag="MiniLM">
            Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., Zhou, M. (2020). <em>MiniLM: Deep
            Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers.</em>{' '}
            NeurIPS 2020. <Id>arXiv:2002.10957</Id>
          </Ref>
          <Ref tag="BGE-M3 (cible / différé — non implémenté)">
            Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., Liu, Z. (2024). <em>BGE M3-Embedding:
            Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through
            Self-Knowledge Distillation.</em> <Id>arXiv:2402.03216</Id>
          </Ref>
        </List>
      </Section>

      <Section title="Désinformation / coordination (CIB)">
        <List>
          <Ref tag="Coordinated Inauthentic Behavior (CIB)">
            Pacheco, D., Hui, P.-M., Torres-Lugo, C., Truong, B.T., Flammini, A., Menczer, F. (2021).{' '}
            <em>Uncovering Coordinated Networks on Social Media: Methods and Case Studies.</em> ICWSM
            2021. ; Giglietto, F., Righetti, N., Rossi, L., Marino, G. (2020). <em>It takes a village to
            manipulate the media: coordinated link sharing behavior during 2018 and 2019 Italian
            elections.</em> Information, Communication &amp; Society 23(6):867-891. ; Nizzoli, L.,
            Tardelli, S., Avvenuti, M., Cresci, S., Tesconi, M. (2021). <em>Coordinated Behavior on
            Social Media in 2019 UK General Election.</em> ICWSM 2021.
          </Ref>
          <Ref tag="MisinfoTeleGraph (cible / différé — GNN non implémenté)">
            Kalkbrenner, L., Solopova, V., Zeiler, S., Nickel, R., Kolossa, D. (2025).{' '}
            <em>MisinfoTeleGraph: Network-driven Misinformation Detection for German Telegram
            Messages.</em> <Id>arXiv:2506.22529</Id>
          </Ref>
          <Ref tag="VIGINUM D3lta (cible / différé — détection texte non implémentée)">
            Méthode de détection de similarité textuelle (copypasta / reformulation / traduction)
            développée par VIGINUM, le service français de vigilance et de protection contre les
            ingérences numériques étrangères. Outil open source publié par VIGINUM.
          </Ref>
        </List>
      </Section>
    </DocPage>
  )
}
