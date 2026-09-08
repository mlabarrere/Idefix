// Poches informationnelles et dossiers de preuve — transcription de docs/pockets-and-dossiers.md.
import { DocPage, Section, Table, List, Note, Mono } from './docs-ui'

export function PochesDossiers() {
  return (
    <DocPage
      title="Poches & dossiers de preuve"
      subtitle="Début du Lot 4 : rendre les poches mesurables et préparer un dossier de preuve v1 fondé sur le contrat analytique."
      source="docs/pockets-and-dossiers.md"
    >
      <Section title="Pocket score">
        <p>
          Le score de poche est calculé par <code className="font-mono">src/pockets/scoring.py</code>.
          Il combine des signaux bornés dans <code className="font-mono">[0,1]</code> :
        </p>
        <Table
          head={['Signal', 'Poids', 'Sens']}
          rows={[
            [<code className="font-mono">claim_exposure</code>, '0.25', 'Exposition à des claims documentés.'],
            [<code className="font-mono">coordination_density</code>, '0.25', 'Densité interne de coordination.'],
            [<code className="font-mono">bridge_presence</code>, '0.15', 'Présence de canaux ponts.'],
            [<code className="font-mono">recidivism</code>, '0.15', 'Récurrence multi-épisodes.'],
            [<code className="font-mono">stability</code>, '0.10', 'Persistance temporelle.'],
            [<code className="font-mono">volume</code>, '0.10', 'Volume observé.'],
          ]}
        />
        <p>
          <code className="font-mono">coverage</code> est un multiplicateur : il ne peut que réduire le
          score si la couverture est dégradée.
        </p>
      </Section>

      <Section title="Typologie">
        <p>
          <code className="font-mono">infer_pocket_type</code> classe une poche en :
        </p>
        <List>
          <li><code className="font-mono">diffusion</code></li>
          <li><code className="font-mono">coordination</code></li>
          <li><code className="font-mono">bridging</code></li>
          <li><code className="font-mono">recidivism</code></li>
          <li><code className="font-mono">mixed</code></li>
        </List>
        <p>
          Quand plusieurs signaux dominants sont proches, la poche est{' '}
          <code className="font-mono">mixed</code>.
        </p>
      </Section>

      <Section title="Dossier v1">
        <p>
          Le dossier v1 vit dans <code className="font-mono">src/dossier/v1.py</code>. Il assemble :
        </p>
        <List>
          <li><code className="font-mono">EpisodeRecord</code></li>
          <li><code className="font-mono">ScoreRunRecord</code></li>
          <li><code className="font-mono">ChannelRoleEvidence</code></li>
          <li><code className="font-mono">PocketRecord</code></li>
          <li><code className="font-mono">CoordinationEdgeEvidence</code></li>
          <li><code className="font-mono">MessageEvidence</code></li>
          <li><code className="font-mono">CoverageLimit</code></li>
          <li><code className="font-mono">MethodVersion</code></li>
        </List>
        <p>
          Le dossier v1 garde les contraintes institutionnelles : T1/T2 seulement, coverage callout
          obligatoire, versions méthodologiques traçables.
        </p>
      </Section>

      <Section title="Exemple depuis bundle statique">
        <p>
          <code className="font-mono">scripts/build_dossier_v1_example.py</code> génère un dossier{' '}
          <code className="font-mono">EvidenceDossierV1</code> depuis un bundle déjà exporté sous{' '}
          <code className="font-mono">webapp/public/data/&lt;mission&gt;/</code>, sans base PostgreSQL
          et sans appel Telegram.
        </p>
        <p>Commandes :</p>
        <Mono>.\.venv\Scripts\python.exe scripts\build_dossier_v1_example.py --mission russosphere</Mono>
        <Mono>.\.venv\Scripts\python.exe scripts\build_dossier_v1_example.py --mission gan</Mono>
        <p>Sorties locales régénérables, non versionnées :</p>
        <List>
          <li><code className="font-mono">data/dossiers/evidence_dossier_v1_russosphere_example.json</code></li>
          <li><code className="font-mono">data/dossiers/evidence_dossier_v1_gan_example.json</code></li>
        </List>
        <Note>
          Ces dossiers sont des exemples de structure de preuve. Ils ne remplacent pas une revue
          analyste et ne constituent pas un verdict opérationnel.
        </Note>
      </Section>

      <Section title="Raccords restants">
        <p>Le Lot 4 n'est pas terminé tant que :</p>
        <List>
          <li>les scripts communautaires ne produisent pas encore des <code className="font-mono">PocketRecord</code> réels ;</li>
          <li><code className="font-mono">export_static.py</code> n'exporte pas encore <code className="font-mono">pockets/</code> ;</li>
          <li>la webapp n'affiche pas encore une vue de poche ;</li>
          <li><code className="font-mono">EvidenceDossierV1</code> n'est pas encore le dossier principal de l'export, même si des exemples peuvent maintenant être générés depuis les bundles statiques.</li>
        </List>
      </Section>
    </DocPage>
  )
}
