// Gates des capacités avancées — transcription de docs/advanced-capability-gates.md.
import { DocPage, Section, Table, List, Note } from './docs-ui'

export function CapacitesAvancees() {
  return (
    <DocPage
      title="Gates de capacités avancées"
      subtitle="Les capacités B9 sont conditionnelles : elles ne doivent pas entrer dans le chemin production tant que leurs données, seuils, limites et besoin sponsor ne sont pas explicites."
      source="docs/advanced-capability-gates.md"
    >
      <Section title="Capacités couvertes">
        <p>
          Le gate exécutable vit dans{' '}
          <code className="font-mono">src/readiness/advanced_capabilities.py</code>.
        </p>
        <Table
          head={['Capacité', 'Décision par défaut', 'Conditions minimales']}
          rows={[
            [
              <code className="font-mono">media_reuse</code>,
              'Bloquée',
              <><code className="font-mono">media_hash</code> alimenté, edges non vides, seuil documenté, contrôle organique, besoin sponsor confirmé.</>,
            ],
            [
              <code className="font-mono">genai_origin_probability</code>,
              'Bloquée',
              'Détecteur choisi, limites OOD documentées, calibration disponible, faux positifs revus, besoin sponsor confirmé.',
            ],
            [
              <code className="font-mono">gnn_misinfotelegraph_fr</code>,
              'Bloquée',
              'Gold set disponible, labels équilibrés, volume suffisant, baseline dépassée, explicabilité documentée, besoin sponsor confirmé.',
            ],
            [
              <code className="font-mono">stix_serializer</code>,
              'Bloquée',
              'Chaîne CSIRT confirmée, mapping documenté, marquage TLP défini, consommateur validé, besoin sponsor confirmé.',
            ],
          ]}
        />
      </Section>

      <Section title="Utilité">
        <p>
          Ce gate évite qu'une capacité techniquement séduisante devienne une promesse produit non
          défendable.
        </p>
        <p>Exemples :</p>
        <List>
          <li>sur l'infosphère France/Ukraine, un GNN ne doit pas remplacer le score explicable tant qu'il n'a pas de gold set channel-level équilibré ;</li>
          <li>sur le GAN / Charles de Gaulle, <code className="font-mono">MEDIA_REUSE</code> ne doit être activé que si les hashes médias sont réellement alimentés et produisent des edges vérifiables ;</li>
          <li>STIX reste conditionnel à une chaîne CSIRT sponsor qui consomme effectivement ce format.</li>
        </List>
      </Section>

      <Section title="Statut">
        <Note>
          Au 2026-06-15, ces capacités restent <strong>hors chemin critique</strong>. Le module de gate
          permet de rendre leur activation testable sans les activer.
        </Note>
      </Section>
    </DocPage>
  )
}
