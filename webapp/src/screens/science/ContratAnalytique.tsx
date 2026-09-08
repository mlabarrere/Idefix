// Contrat analytique — transcription de docs/analytical-contract.md.
import { DocPage, Section, Table, List, Note } from './docs-ui'

export function ContratAnalytique() {
  return (
    <DocPage
      title="Contrat analytique"
      subtitle="Le langage commun entre scoring, dossiers de preuve, export statique, validation et webapp."
      source="docs/analytical-contract.md"
    >
      <Note>
        Ce document fixe le langage commun entre scoring, dossiers de preuve, export statique,
        validation et webapp. Les modèles exécutables vivent dans{' '}
        <code className="font-mono">src/shared/analytical_contract.py</code>.
      </Note>

      <Section title="Principe">
        <p>
          Idéfix ne produit pas un verdict automatique. Il produit des objets analytiques auditables :
          claims, épisodes, preuves de message, arêtes de coordination, poches, runs de score et
          dossiers. Chaque objet doit porter sa mission, sa fenêtre temporelle quand elle existe, sa
          méthode, ses limites et ses versions.
        </p>
      </Section>

      <Section title="Objets canoniques">
        <Table
          head={['Objet', 'Rôle', 'Statut']}
          rows={[
            [<code className="font-mono">ClaimRecord</code>, 'Revendication canonique issue du registry.', 'Lot 1 actif'],
            [<code className="font-mono">ClaimVariant</code>, "Variante linguistique ou sémantique d'un claim.", 'Lot 1 actif'],
            [<code className="font-mono">EpisodeRecord</code>, 'Épisode suivi : un ou plusieurs claims sur une fenêtre.', 'Lot 1 actif'],
            [<code className="font-mono">MessageEvidence</code>, 'Preuve message-level rattachable à claim, edge, poche ou dossier.', 'Lot 1 actif'],
            [<code className="font-mono">CoordinationEdgeEvidence</code>, 'Relation coordonnée entre deux canaux avec méthode, seuil et score.', 'Lot 1 actif'],
            [<code className="font-mono">ChannelRoleEvidence</code>, 'Rôle de canal et preuves associées.', 'Lot 1 actif'],
            [<code className="font-mono">PocketRecord</code>, 'Poche informationnelle mesurable sur une fenêtre.', 'Lot 1 actif'],
            [<code className="font-mono">ScoreRunRecord</code>, "Enveloppe d'un run de scoring mission-scopé.", 'Lot 1 actif'],
            [<code className="font-mono">CoverageLimit</code>, "Limite d'observation déclarée.", 'Lot 1 actif'],
            [<code className="font-mono">MethodVersion</code>, 'Versions nécessaires à la reproductibilité.', 'Lot 1 actif'],
          ]}
        />
      </Section>

      <Section title="Registry claims v0">
        <p>
          Le fichier historique <code className="font-mono">data/claims/claims_fr.jsonl</code> reste la
          seed registry du PoC. Il est normalisé par <code className="font-mono">src/registry/claims.py</code>{' '}
          vers <code className="font-mono">ClaimRecord</code>. Cette étape ne branche pas encore{' '}
          <code className="font-mono">claim_proximity</code> dans le scoring ; elle stabilise le format
          qui permettra de le faire proprement au lot suivant.
        </p>
      </Section>

      <Section title="Contraintes">
        <List>
          <li><code className="font-mono">AttributionTier</code> est limité à <code className="font-mono">T1</code> / <code className="font-mono">T2</code>.</li>
          <li><code className="font-mono">ClaimRecord.claim_id</code> et <code className="font-mono">canonical_text</code> sont obligatoires.</li>
          <li><code className="font-mono">PocketRecord</code> doit contenir au moins un canal.</li>
          <li>Les scores bornés sont dans <code className="font-mono">[0,1]</code>.</li>
          <li>Les arêtes de coordination doivent déclarer une méthode.</li>
          <li>
            Les outputs doivent porter <code className="font-mono">methodology_version_hash</code> au
            minimum, puis les versions scorer / edge-builder / claim-matcher quand disponibles.
          </li>
        </List>
      </Section>

      <Section title="Prochain raccordement">
        <p>Le Lot 2 devra brancher ce contrat sur :</p>
        <List>
          <li>la table PostgreSQL <code className="font-mono">episodes</code> ;</li>
          <li>le calcul <code className="font-mono">claim_proximity</code> ;</li>
          <li>l'export statique <code className="font-mono">episodes/</code> ;</li>
          <li><code className="font-mono">Evidence Dossier v1</code> ;</li>
          <li>la validation externe.</li>
        </List>
      </Section>
    </DocPage>
  )
}
