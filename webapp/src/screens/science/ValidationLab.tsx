// Laboratoire de validation — transcription de docs/validation-lab.md.
import { DocPage, Section, List, Limit, Note } from './docs-ui'

export function ValidationLab() {
  return (
    <DocPage
      title="Laboratoire de validation"
      subtitle="Gold externe et corpus organique : le Validation Lab ferme deux faiblesses connues de l'état de validation — la circularité du test de récupération d'épisode connu, et l'absence de corpus organique français pour mesurer les faux positifs."
      source="docs/validation-lab.md"
    >
      <Note>
        Le Validation Lab ferme deux faiblesses connues de{' '}
        <code className="font-mono">docs/validation-state.md</code> :
        <List>
          <li>la circularité du test de récupération d'épisode connu ;</li>
          <li>l'absence de corpus organique français pour mesurer les faux positifs.</li>
        </List>
        Les schémas exécutables vivent dans <code className="font-mono">src/validation_lab/schema.py</code>.
      </Note>

      <Section title="Gold épisode externe">
        <p>
          Un gold épisode externe est un fichier JSON conforme à{' '}
          <code className="font-mono">ExternalGoldEpisode</code>. Il doit documenter :
        </p>
        <List>
          <li>une provenance externe ;</li>
          <li>
            une phrase d'indépendance expliquant que la liste n'est pas issue des scores Idéfix ni des
            allowlists du scorer ;
          </li>
          <li>au moins un canal <code className="font-mono">seed</code> ;</li>
          <li>
            des canaux identifiés par <code className="font-mono">username</code> ou{' '}
            <code className="font-mono">channel_id</code> ;
          </li>
          <li>une confidence et une référence source par canal.</li>
        </List>
        <p>
          Template : <code className="font-mono">data/eval/templates/gold_episode.example.json</code>.
        </p>
        <p>
          Les vrais fichiers utilisables par{' '}
          <code className="font-mono">scripts/eval_episode_recovery.py</code> doivent être placés sous{' '}
          <code className="font-mono">data/eval/</code> avec le nom{' '}
          <code className="font-mono">gold_episode_&lt;nom&gt;.json</code>. Les templates restent dans{' '}
          <code className="font-mono">data/eval/templates/</code> pour ne pas être consommés comme gold
          réels.
        </p>
      </Section>

      <Section title="Corpus organique">
        <p>
          Un corpus organique est un fichier JSON conforme à{' '}
          <code className="font-mono">OrganicControlCorpus</code>. Il contient des groupes coordonnés non
          hostiles : médias, institutions, militantisme, sport, événements civils ou autre catégorie
          documentée.
        </p>
        <p>
          Template :{' '}
          <code className="font-mono">data/eval/templates/organic_control_corpus.example.json</code>.
        </p>
        <p>
          Chaque groupe doit contenir au moins deux canaux et une rationale expliquant pourquoi la
          coordination est attendue ou organique.
        </p>
        <p>
          Les vrais fichiers utilisables par{' '}
          <code className="font-mono">scripts/eval_organic_control.py</code> doivent être placés sous{' '}
          <code className="font-mono">data/eval/</code> avec le nom{' '}
          <code className="font-mono">organic_control_&lt;nom&gt;.json</code>. Le script calcule combien
          de canaux organiques documentés remontent dans le top suspicion et déclenche une alarme de faux
          positif si :
        </p>
        <List>
          <li>au moins trois canaux organiques apparaissent dans le top 50 ;</li>
          <li>ou au moins deux canaux du même groupe organique apparaissent dans le top 50.</li>
        </List>
        <p>
          Si aucun corpus réel n'est présent, le script écrit un rapport non probant{' '}
          <code className="font-mono">data/eval/organic_control.json</code> au lieu d'inventer un verdict.
        </p>
      </Section>

      <Section title="Garde-fous">
        <Limit>
          <List>
            <li>
              Un gold épisode avec <code className="font-mono">excluded_from_scorer_inputs=false</code>{' '}
              est invalide.
            </li>
            <li>Un gold épisode sans canal <code className="font-mono">seed</code> est invalide.</li>
            <li>
              Un canal sans <code className="font-mono">username</code> ni{' '}
              <code className="font-mono">channel_id</code> est invalide.
            </li>
            <li>Un corpus organique sans groupe est invalide.</li>
            <li>Un groupe organique avec un seul canal est invalide.</li>
          </List>
        </Limit>
      </Section>

      <Section title="Prochain raccordement">
        <p>Le raccordement actuel :</p>
        <List>
          <li>
            <code className="font-mono">scripts/eval_episode_recovery.py</code> lit les fichiers{' '}
            <code className="font-mono">gold_episode_*.json</code> au format{' '}
            <code className="font-mono">ExternalGoldEpisode</code> v1, avec fallback sur l'ancien format{' '}
            <code className="font-mono">{'{episode, seeds, relays}'}</code>.
          </li>
          <li>
            <code className="font-mono">scripts/eval_organic_control.py</code> lit les fichiers{' '}
            <code className="font-mono">organic_control_*.json</code> au format{' '}
            <code className="font-mono">OrganicControlCorpus</code> v1 et publie{' '}
            <code className="font-mono">organic_control.json</code>.
          </li>
        </List>
        <p>Le prochain incrément doit :</p>
        <List>
          <li>produire au moins un corpus organique réel ;</li>
          <li>
            publier <code className="font-mono">docs/validation-state.md</code> v2 avec les nouveaux
            verdicts.
          </li>
        </List>
      </Section>
    </DocPage>
  )
}
