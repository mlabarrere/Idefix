// État de validation du score de suspicion — transcription de docs/validation-state.md.
import { DocPage, Section, SubSection, Table, List, Limit, Note, Mono } from './docs-ui'

const PASS = <strong className="text-emerald-600 dark:text-emerald-400">PASS</strong>

export function ValidationState() {
  return (
    <DocPage
      title="État de validation"
      subtitle="Artefact de transparence du démonstrateur méthodologique : le score mesure-t-il une manipulation informationnelle, ou seulement une position structurale dans un graphe Telegram incomplet ? On répond par l'expérience."
      source="docs/validation-state.md"
    >
      <Note>
        <strong>Chiffres reproductibles</strong> (mise à jour 2026-06-29) : recalculés sur les{' '}
        <strong>vrais scores</strong> (<code className="font-mono">channel_scores</code>, russosphere ={' '}
        3 699 canaux ; graphe forward 3 680 nœuds / 6 889 arêtes). Régénérer :{' '}
        <code className="font-mono">python scripts/prep_eval_inputs.py --mission russosphere</code> puis{' '}
        <code className="font-mono">scripts/eval_*.py</code>. Résumés committés :{' '}
        <code className="font-mono">docs/metrics/*.json</code>. Audit complet :{' '}
        <code className="font-mono">docs/scientific-audit.md</code>. Bibliographie :{' '}
        <code className="font-mono">docs/references.md</code>.
      </Note>

      <Section title="Tableau de synthèse">
        <Table
          head={['Exp', 'Question', 'Verdict (calculé)', 'Force de preuve']}
          rows={[
            ['1', 'Juste de la centralité / popularité ?', <><strong>PASS</strong> — non</>, <><strong>Forte</strong> (0 label)</>],
            ['2', 'Récupère une opération connue (gold externe) ?', <strong>FAIBLE</strong>, <><strong>Faible</strong> (gold hypothétique, 3/12)</>],
            ['3', 'Distingue hostile vs organique ?', <strong>MITIGÉ + non stressé</strong>, <><strong>Faible</strong> (0 négatif organique)</>],
            ['f', 'Famille (f) sépare organique/scoré ?', <strong>FAIBLE + mal spécifié</strong>, <><strong>Faible</strong> (usernames ≠ contenu)</>],
            ['—', 'Significativité (ROC-AUC vs gold)', <strong>NON CALCULABLE</strong>, <><strong>Bloquée</strong> (0 négatif)</>],
          ]}
        />
      </Section>

      <Section title="Exp 1 — Ablation centralité/activité (eval_ablation_centrality.py) — PASS">
        <p>
          On compare le classement « suspicion » à des classements « bêtes » (centralité brute,
          activité). Réf. : Spearman (1904), ROC/AUC Fawcett (2006).
        </p>
        <List>
          <li>
            <code className="font-mono">Spearman(suspicion, in-degree)</code> = <strong>0,667</strong> ·{' '}
            <code className="font-mono">eigenvector</code> = <strong>0,537</strong> ·{' '}
            <code className="font-mono">influence-forward</code> = <strong>0,424</strong> ·{' '}
            <code className="font-mono">activité/engagement</code> = <strong>0,317</strong>.
          </li>
          <li>
            Recouvrement <strong>top-50</strong> suspicion ↔ centralité : <strong>Jaccard@50 ≤ 0,05</strong>{' '}
            (in-degree 0,020 ; eigenvector 0,053).
          </li>
          <li>
            Seuils de falsification (Spearman &gt; 0,90 OU Jaccard@50 &gt; 0,80) :{' '}
            <strong>non approchés</strong>.
          </li>
          <li>
            814/3 699 canaux à suspicion &gt; 0. Artefact :{' '}
            <code className="font-mono">docs/metrics/ablation_centrality.json</code>.
          </li>
        </List>
        <p>
          <strong>Conclusion :</strong> les canaux les plus suspects ne sont <strong>pas</strong> les
          plus centraux ni les plus actifs. Le score est <strong>séparable</strong> de la centralité
          (preuve forte, sans label). Verdict : {PASS}.
        </p>
      </Section>

      <Section title="Exp 2 — Récupération d'épisode connu (eval_episode_recovery.py) — FAIBLE">
        <p>
          Gold <strong>EXTERNE non circulaire</strong> (<code className="font-mono">data/eval/gold_episode_dugin.json</code>,{' '}
          <code className="font-mono">excluded_from_scorer_inputs=true</code>).
        </p>
        <List>
          <li>
            3/12 canaux gold présents dans le corpus ; recall@50 = <strong>0,167</strong> (hasard 0,162,{' '}
            <strong>×12,35</strong>) ; rang médian 50.
          </li>
          <li>Artefact : <code className="font-mono">docs/metrics/episode_recovery.json</code>.</li>
        </List>
        <Limit>
          <strong>Conclusion :</strong> au-dessus du hasard, mais <strong>caveat majeur</strong> : le
          gold est <strong>hypothétique</strong> (pas une vraie liste VIGINUM) et seuls 3/12 canaux sont
          dans le corpus → preuve faible. Un gold externe réel reste requis.
        </Limit>
      </Section>

      <Section title="Exp 3 — Discriminant hostile vs organique (eval_discriminant_organic.py) — MITIGÉ, non stressé">
        <List>
          <li>
            Parmi 446 canaux à coordination déclenchée :{' '}
            <code className="font-mono">Spearman(suspicion, ancrage_adverse)</code> = <strong>0,765</strong>{' '}
            (dominant) ; <code className="font-mono">valeur_coordination</code> = <strong>0,253</strong> ;{' '}
            base structurelle = <strong>0,488</strong>.
          </li>
          <li>Candidats « organiques » (forte coordination, ancrage adverse nul) : <strong>0</strong>.</li>
          <li>Artefact : <code className="font-mono">docs/metrics/discriminant_organic.json</code>.</li>
        </List>
        <Limit>
          <strong>Conclusion :</strong> ce qui sépare « hostile » repose surtout sur l'<strong>ancrage
          adverse</strong> (proxy grossier), pas sur la structure de coordination seule. Le corpus,
          amorcé sur l'adversaire, ne contient <strong>aucune coordination organique</strong> → le
          discriminant <strong>n'est pas stressé</strong>. Le système ne distingue donc pas robustement
          hostile / organique / viralité aujourd'hui.
        </Limit>
      </Section>

      <Section title="Exp f — Discrimination par embeddings (eval_embedding_discrimination.py) — FAIBLE + mal spécifié">
        <List>
          <li>ROC-AUC = <strong>0,506</strong> (≈ hasard) ; silhouette 0,003 ; séparation centroïdes 0,171.</li>
          <li>
            Artefact : <code className="font-mono">docs/metrics/embedding_discrimination_russosphere.json</code>.
          </li>
        </List>
        <Limit>
          <strong>Caveat méthodologique :</strong> le script embedde les <strong>usernames seuls</strong>{' '}
          (<code className="font-mono">@handle</code>), pas le <strong>contenu des messages</strong> comme
          la famille (f) déployée. Ce test ne mesure donc <strong>pas</strong> (f) telle que livrée.{' '}
          <strong>Correctif requis</strong> : ré-encoder sur le contenu avant toute conclusion.
        </Limit>
      </Section>

      <Section title="Significativité du scoring (eval_scoring_significance.py) — NON CALCULABLE">
        <p>
          <code className="font-mono">channel_gold</code> = <strong>12 positifs / 0 négatif</strong>{' '}
          (corpus organique absent) → ROC-AUC / test de permutation indéfinis. Réfs. méthodes prévues :
          permutation (Good, 2000), Benjamini-Hochberg (1995), bootstrap (Efron, 1979). Débloqué par le
          même manque que l'Exp 3.
        </p>
      </Section>

      <Section title="Synthèse honnête">
        <List>
          <li>
            ✅ <strong>Le score n'est pas de la centralité déguisée</strong> (Exp 1, preuve forte,{' '}
            <strong>reproductible</strong>).
          </li>
          <li>
            ⚠️ Récupération d'épisode <strong>au-dessus du hasard mais faible</strong> (gold hypothétique,
            Exp 2).
          </li>
          <li>
            ⚠️ <strong>Ne distingue pas robustement hostile / organique</strong> ; s'appuie sur l'ancrage
            adverse (Exp 3) ; significativité <strong>bloquée</strong> faute de négatifs.
          </li>
          <li>
            ⚠️ Discrimination embeddings <strong>mal spécifiée</strong> (usernames) — à recalculer sur le
            contenu (Exp f).
          </li>
        </List>
        <p>
          <strong>Deux manques bloquants (données/annotation humaine) :</strong>
        </p>
        <List>
          <li>
            <strong>Gold externe réel</strong> (non hypothétique) pour ≥1 épisode → rend Exp 2 probant.
          </li>
          <li>
            <strong>Corpus de coordination FRANÇAISE organique</strong> (la classe négative —
            actuellement 0) → débloque Exp 3 et la significativité (ROC-AUC).
          </li>
        </List>
        <Limit>
          Tant que ces manques tiennent, le système reste défendable <strong>comme démonstrateur T1</strong>{' '}
          (diffusion observable, séparable de la centralité), <strong>pas</strong> comme détecteur validé
          de manipulation.
        </Limit>
      </Section>

      <Section title="Reproduction">
        <Mono>
          Régénérer : scripts/prep_eval_inputs.py puis eval_ablation_centrality.py ·
          eval_discriminant_organic.py · eval_episode_recovery.py · eval_embedding_discrimination.py.
          Recalculé le 2026-06-29 sur scores réels (Supabase channel_scores).
        </Mono>
      </Section>
    </DocPage>
  )
}
