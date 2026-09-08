// Audit scientifique de la méthode — transcription de docs/scientific-audit.md.
import { DocPage, Section, SubSection, Table, List, Limit, Note, Mono } from './docs-ui'

const PASS = <span className="font-semibold text-emerald-600 dark:text-emerald-400">PASS</span>
const em = (t: string) => <em>{t}</em>

export function AuditScientifique() {
  return (
    <DocPage
      title="Audit scientifique de la méthode"
      subtitle="Document d'audit interne — registre académique. Porte sur la validité des inférences, pas sur le code. Daté 2026-06-29."
      source="docs/scientific-audit.md"
    >
      <Note>
        Source de vérité chiffrée : <code className="font-mono">docs/metrics/_summary.json</code> et{' '}
        <code className="font-mono">docs/metrics/*.json</code> (calculés depuis Supabase ; corpus{' '}
        <em>russosphere</em> de 3699 canaux scorés ; graphe FORWARD de 3788 nœuds / 6889 arêtes). Tous
        les chiffres ci-dessous en sont extraits.
      </Note>

      <Section title="1. Objet & posture">
        <p>
          Cet audit porte sur la <strong>méthode scientifique</strong>, non sur le code. Il ne juge
          pas l'ingénierie, mais la <strong>validité des inférences</strong> que le système autorise.
        </p>
        <List>
          <li>
            <strong>Défendable.</strong> Idéfix est un <strong>démonstrateur T1</strong> : il met en
            évidence une <strong>structure de diffusion observable</strong> (qui relaie qui, vers
            quelles communautés, avec quel degré de récurrence) et démontre que cette structure est{' '}
            <strong>séparable de la centralité brute</strong> (Exp 1).
          </li>
          <li>
            <strong>NON défendable en l'état.</strong> Idéfix <strong>n'est pas</strong> un détecteur
            de manipulation validé. Aucune expérience ne démontre que les scores élevés correspondent
            à de la manipulation coordonnée plutôt qu'à de la simple proéminence adverse (Exp 3 ; §8).
          </li>
          <li>
            <strong>Couverture. Telegram uniquement.</strong> Aucune revendication sur d'autres
            plateformes, ni sur des trajectoires cross-plateformes.
          </li>
        </List>
        <Note>
          Règle de lecture de tout le document : <strong>ce qui est mesuré au-dessus du hasard est
          rapporté comme tel ; ce qui n'est pas mesurable est déclaré bloqué, jamais comblé par de la
          prose.</strong>
        </Note>
      </Section>

      <Section title="2. Ancrage des familles de score">
        <p>
          Trois statuts : <strong>cité+implémenté</strong>, <strong>implémenté sans citation</strong>{' '}
          (choix de conception), et <strong>cité non implémenté</strong> (seam réservé).
        </p>
        <SubSection title="2.1 Familles avec ancrage">
          <Table
            head={['Fam.', 'Intitulé', 'Statut', 'Ancrage / implémentation']}
            rows={[
              ['(b)', 'Rôle en cascade', <strong>Cité + implémenté</strong>, <>Bridge Score, arXiv:2411.05922. Formule <code className="font-mono">10·in_degree + 7·eigenvector + 7·clustering</code>. <code className="font-mono">src/scorer/cascade_role.py</code>.</>],
              ['(d)', 'Récidive inter-épisodes', <strong>Implémenté (approximation PoC)</strong>, <>Faute de table d'épisodes peuplée, l'implémentation <strong>approxime</strong> la récidive par la récurrence structurelle dans le graphe de forward agrégé — approximation documentée, à remplacer par une vraie séquence d'épisodes.</>],
              ['(f)', 'Cohérence sémantique', <strong>Implémenté (opt-in)</strong>, <>Pondération distance-baseline 0.4 + proximité-adversaire 0.6. Modèle <strong>MiniLM-L12-v2</strong>, 384 dimensions.</>],
              ['(c)', 'Coordination', <strong>Structurel implémenté ; texte différé</strong>, <>Structurel : Jaccard des co-forwards. Texte (D3lta) <strong>différé</strong> : seuils cités — copypasta 0.693 / reformulation 0.715 / traduction 0.85 — mais non câblés.</>],
              ['(a)', 'Proximité de revendication (BGE-M3)', <strong>Cité, NON implémenté</strong>, 'Seam réservé.'],
              ['(e)', 'Origine IA', <strong>Cité, NON implémenté</strong>, 'Seam réservé.'],
            ]}
          />
        </SubSection>
        <SubSection title="2.2 Implémenté mais non cité — à requalifier en « choix de conception »">
          <p>En production sans référence académique ; à assumer comme choix de conception :</p>
          <List>
            <li><strong>Leiden</strong> (détection de communautés) ;</li>
            <li><strong>Gate multi-source</strong> (déclenchement conditionné à ≥ 2 familles actives) ;</li>
            <li><strong>Modulateurs de sévérité</strong> : ± 20 % reforward, ± 15 % domaine adverse, ± 20 % ciblage ;</li>
            <li><strong>Taxonomie TF-IDF</strong> : 28 patterns regex ;</li>
            <li><strong>Percentile P75</strong> du Bridge Score comme seuil ;</li>
            <li><strong>Paramètres EMB_SIM</strong> : k = 5, seuil 0.5, <code className="font-mono">weight_scale</code> 3.0.</li>
          </List>
          <p>
            Aucun de ces choix n'est invalide ; mais chacun est un <strong>degré de liberté non
            justifié par la littérature</strong>, donc une cible prioritaire d'analyse de sensibilité.
          </p>
        </SubSection>
      </Section>

      <Section title="3. Rigueur statistique">
        <SubSection title="3.1 Forces">
          <List>
            <li><strong>Modèle nul par randomisation d'extrémités</strong> — le bon choix pour la topologie en étoile, profondeur 1, de Telegram, où le rewiring degree-preserving est dégénéré.</li>
            <li><strong>p-values add-one</strong> — jamais nulles, évite les faux « p = 0 ».</li>
            <li><strong>Bootstrap</strong> pour les intervalles de confiance.</li>
            <li><strong>Correction Benjamini-Hochberg</strong> (contrôle du FDR) sur les tests multiples.</li>
            <li><strong>Combinaison de Stouffer</strong> pour agréger les signaux indépendants.</li>
            <li><strong>RNG déterministe (seed 1312)</strong> → bundle de résultats reproductible.</li>
          </List>
        </SubSection>
        <SubSection title="3.2 Faiblesses">
          <List>
            <li><strong>Famille (c) coordination : SANS modèle nul.</strong> La p-value y est <code className="font-mono">p = 1 − valeur</code> — un placebo, pas un test. C'est la faiblesse statistique la plus grave.</li>
            <li><strong>n_bootstrap = 100</strong> : trop faible pour des IC stables ; recommandé ≥ 1000.</li>
            <li><strong>Paramètres EMB_SIM (k = 5 / seuil 0.5 / scale 3.0) : aucune analyse de sensibilité.</strong></li>
            <li><strong>Modèle d'embedding : aucune ablation.</strong> MiniLM-L12-v2 retenu sans comparaison (e5, MPNet).</li>
          </List>
        </SubSection>
      </Section>

      <Section title="4. Analytics vs embedding — le trade-off (chiffres réels)">
        <p>
          Source : <code className="font-mono">docs/metrics/analytics_vs_embedding.json</code>. Corpus
          galaxie échantillonné : 1170 nœuds communs aux deux partitions.
        </p>
        <Table
          head={['Métrique', 'Analytics', 'Embedding', 'Variation']}
          rows={[
            ['Cohésion intra-communauté (cosinus moyen)', '0.6709', <strong>0.7049</strong>, <strong>+ 5,1 %</strong>],
            ['Silhouette (Rousseeuw 1987)', '−0.2738', <strong>0.0214</strong>, 'en hausse'],
            ['Modularité (Newman 2006, graphe de LIENS)', <strong>0.7547</strong>, '0.6301', <strong>en baisse</strong>],
            ['Communautés conservées (≥ 2 canaux)', '27', '17', '—'],
            ['Communautés brutes (singletons inclus)', '512', '464', '—'],
            ['Accord des partitions', '—', '—', <strong>NMI 0.887 / ARI 0.528</strong>],
          ]}
        />
        <SubSection title="4.1 Lecture du trade-off (load-bearing)">
          <p>
            La baisse de modularité <strong>n'est pas une régression</strong> ; c'est la signature de
            deux objectifs distincts. Les arêtes EMB_SIM rapprochent les canaux qui {em('parlent pareil')} →
            la cohésion sémantique monte ; ces mêmes arêtes traversent les communautés structurelles
            des forwards → la modularité (Newman, sur le graphe de liens) baisse mécaniquement.
            Présenter cette baisse comme une dégradation serait une <strong>erreur de cadre</strong>.
          </p>
        </SubSection>
        <SubSection title="4.2 Accord des partitions">
          <p>
            <strong>NMI 0.887</strong> (élevé) + <strong>ARI 0.528</strong> (moyen) : l'embedding
            conserve l'essentiel de la structure grossière mais réorganise ~la moitié de la structure
            fine. Cohérent avec un signal additionnel non trivial, ni redondant ni bruit.
          </p>
        </SubSection>
        <SubSection title="4.3 Correction apportée par cet audit">
          <p>
            L'ancienne incohérence apparente sur <code className="font-mono">n_communities</code> (512 vs 27)
            venait d'un comptage incluant les singletons. On expose désormais les deux mesures —
            conservées (≥ 2) et brutes — ce qui lève l'ambiguïté.
          </p>
        </SubSection>
      </Section>

      <Section title="5. État de validation — 4 expériences + significativité globale">
        <p>Verdicts pris tels que produits, sans arrondi favorable.</p>
        <SubSection title="Exp 1 — Ablation centralité : PASS">
          <p>Artefact : <code className="font-mono">ablation_centrality.json</code> (3699 canaux ; 814 à suspicion &gt; 0). Spearman(suspicion, baseline) :</p>
          <Table
            head={['Baseline', 'Spearman', 'Jaccard@50']}
            rows={[
              ['in-degree', '0.667', '0.020'],
              ['eigenvector', '0.537', '0.053'],
              ['influence-forward', '0.424', '0.099'],
              ['activité / engagement', '0.317', '0.010'],
              [em('(composite cascade, témoin)'), em('0.792'), em('0.190')],
            ]}
          />
          <p>
            Seuils de falsification : Spearman &gt; 0.90 OU Jaccard@50 &gt; 0.80. <strong>Aucun n'est
            approché.</strong> Conclusion : {PASS} — le score n'est pas de la centralité maquillée.
          </p>
        </SubSection>
        <SubSection title="Exp 2 — Récupération d'épisode (gold EXTERNE non circulaire) : FAIBLE">
          <p>Artefact : <code className="font-mono">episode_recovery.json</code>. Épisode « Dugin Eurasianist Network (External Gold) ».</p>
          <List>
            <li>Taille du cluster gold : 12 ; présents dans le corpus : 3.</li>
            <li>recall@50 = 0.167 vs hasard 0.162 → × 12,35 au-dessus du contrôle ; rang médian 50.</li>
            <li>recall@20 = 0.0 ; recall@100 = 0.167.</li>
          </List>
          <Limit>
            <strong>Caveat fort.</strong> Le gold est hypothétique (pas un vrai gold VIGINUM) et
            l'overlap est minuscule (3 canaux). Le « × 12,35 » est arithmétiquement réel mais repose
            sur une base trop petite pour être probant. Verdict honnête : <strong>indicatif, non
            concluant</strong>.
          </Limit>
        </SubSection>
        <SubSection title="Exp 3 — Discriminant hostile / organique : MITIGÉ + bloqué">
          <p>Artefact : <code className="font-mono">discriminant_organic.json</code>. Parmi 446 canaux coordonnés (48 en T2) :</p>
          <List>
            <li>Spearman(suspicion, <strong>ancrage adverse</strong>) = <strong>0.765</strong> ← dominant ;</li>
            <li>Spearman(suspicion, coordination seule) = 0.253 ;</li>
            <li>Spearman(suspicion, base structurelle) = 0.488.</li>
          </List>
          <p>Lecture : la discrimination vient des boosts d'ancrage adverse, pas de la structure de coordination. Le score « voit » surtout qui est proche de l'adversaire, pas qui se coordonne.</p>
          <Limit>
            <strong>Blocage.</strong> 0 candidat organique dans le corpus (amorcé sur l'adversaire) → le
            discriminant n'est jamais stressé contre des négatifs. La règle de falsification (≥ 3
            organiques dans le top-50) est <strong>non testable</strong> en l'absence de négatifs.
          </Limit>
        </SubSection>
        <SubSection title="Exp f — Discrimination par embeddings : FAIBLE + décalage méthodologique">
          <p>Artefact : <code className="font-mono">embedding_discrimination_russosphere.json</code>.</p>
          <List>
            <li>ROC-AUC = 0.506 (≈ hasard ; cible &gt; 0.7) ; silhouette 0.003 ; séparation des centroïdes 0.171 (baseline FR organique externe n = 96 vs scored n = 3492).</li>
          </List>
          <Limit>
            <strong>Décalage critique.</strong> Le script embedde les usernames seuls (@handle), pas le
            contenu des messages comme la famille (f) déployée. <strong>Ce test ne teste donc pas la
            famille (f) telle que livrée.</strong> Recommandation : ré-encoder sur le contenu avant
            toute conclusion sur (f).
          </Limit>
        </SubSection>
        <SubSection title="Significativité globale du scoring : NON CALCULABLE">
          <p>
            <code className="font-mono">channel_gold</code> = 12 positifs / 0 négatif (corpus organique
            absent) → ROC-AUC indéfini. C'est le <strong>gap bloquant</strong> qui empêche toute
            affirmation de performance globale.
          </p>
        </SubSection>
      </Section>

      <Section title="6. Anomalie de calibration : gan vs russosphere">
        <Table
          head={['Mission', 'Canaux T2']}
          rows={[
            ['gan', <strong>1266</strong>],
            ['russosphere', <strong>48</strong>],
          ]}
        />
        <Limit>
          Écart d'un facteur ~26. À expliquer par les familles <code className="font-mono">telegram_*</code>{' '}
          (gate plus basse sur la mission <em>gan</em>), PAS par « plus de vrais positifs ». À traiter
          comme un artefact de calibration à réviser, non comme un résultat. Tant que les gates ne sont
          pas harmonisées, le volume T2 de <em>gan</em> n'est pas interprétable.
        </Limit>
      </Section>

      <Section title="7. Reproductibilité — avant → après cet audit">
        <Table
          head={['', 'Avant', 'Après']}
          rows={[
            ['Chiffres de validation', 'Prose uniquement', <strong>Artefacts JSON sous docs/metrics/</strong>],
            ['Scores', 'channels.json exporté avec suspicion = 0', <strong>Scores réels en base (Supabase)</strong>],
            ['Évaluations', 'Non rejouables', <strong>Recalculées et committées</strong>],
            ['Source citée', 'Divergente', <strong>Source unique, citée identiquement</strong>],
          ]}
        />
        <p>Gain net : d'affirmations narratives non vérifiables à un bundle de métriques reproductible et cité de façon univoque.</p>
      </Section>

      <Section title="8. Gaps bloquants & recommandations priorisées">
        <List>
          <li><strong>Corpus de coordination organique (négatifs).</strong> Débloque Exp 3 et la significativité globale. Requiert une annotation humaine. — priorité maximale.</li>
          <li><strong>Gold VIGINUM externe réel</strong> (remplacer le gold hypothétique) → rend Exp 2 probante.</li>
          <li><strong>Discrimination embeddings sur le CONTENU</strong> (messages), pas les usernames → rend Exp f valide.</li>
          <li><strong>Modèle nul pour la coordination (famille c)</strong> → supprime la p-value placebo.</li>
          <li><strong>Analyse de sensibilité EMB_SIM</strong> (k / seuil / scale) + ablation du modèle d'embedding.</li>
          <li><strong>n_bootstrap ≥ 1000.</strong></li>
        </List>
      </Section>

      <Section title="9. Verdict">
        <p>
          Idéfix est un <strong>démonstrateur T1 honnête et désormais reproductible</strong> : il
          établit, chiffres à l'appui, qu'une structure de diffusion observable existe et qu'elle est
          séparable de la centralité brute (Exp 1 PASS). Les revendications plus fortes — T2 comme
          détecteur de manipulation validé — restent <strong>bloquées</strong> par deux absences
          documentées : <strong>corpus de coordination organique (négatifs)</strong> et <strong>gold
          externe réel</strong>. Cette limite n'est pas masquée ; elle est la conclusion explicite de
          l'audit.
        </p>
        <Mono>
          Renvois : bibliographie complète (docs/references.md) · trade-off analytics vs embedding
          (docs/analytics-vs-embedding.md, artefact docs/metrics/analytics_vs_embedding.json).
        </Mono>
      </Section>
    </DocPage>
  )
}
