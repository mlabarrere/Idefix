// Fabrique de coordination — transcription de docs/coordination-fabric.md.
import { DocPage, Section, Table, Note } from './docs-ui'

export function Coordination() {
  return (
    <DocPage
      title="Fabrique de coordination"
      subtitle="Registre des familles d'arêtes de coordination — statuts, méthodes, seuils et preuves attendues."
      source="docs/coordination-fabric.md"
    >
      <Note>
        La Fabrique de coordination centralise les familles d'arêtes de coordination, leurs statuts,
        méthodes, seuils et preuves attendues. Le registre exécutable vit dans{' '}
        <code className="font-mono">src/coordination_fabric/config.py</code>.
      </Note>

      <Section title="Signaux actifs">
        <Table
          head={['Edge', 'Méthode', 'Fenêtre']}
          rows={[
            [<code className="font-mono">CO_FORWARD</code>, 'Même origine forwardée dans la fenêtre.', '72 h'],
            [<code className="font-mono">CO_URL</code>, 'Même domaine registrable cité dans la fenêtre.', '72 h'],
            [<code className="font-mono">CO_URL_EXACT</code>, 'Même URL complète citée dans la fenêtre.', '72 h'],
            [<code className="font-mono">CO_HASHTAG</code>, 'Même hashtag cité dans la fenêtre.', '72 h'],
          ]}
        />
        <p>
          Ces signaux sont déjà matérialisés par <code className="font-mono">src/graph/edges.py</code>.
        </p>
      </Section>

      <Section title="Signaux réservés">
        <Table
          head={['Edge', 'Seuil graine', "Condition d'activation"]}
          rows={[
            [<code className="font-mono">COPYPASTA</code>, '0.693', 'Calibration D3lta ou équivalent sur corpus annoté.'],
            [<code className="font-mono">TEXT_SIM</code>, '0.715', 'Backend embeddings et seuils validés.'],
            [<code className="font-mono">TRANSLATION</code>, '0.85', 'Similarité cross-lingue calibrée.'],
            [<code className="font-mono">MEDIA_REUSE</code>, 'N/A', <><code className="font-mono">media_hash</code> alimenté réellement.</>],
          ]}
        />
      </Section>

      <Section title="Règle produit">
        <p>
          Un seul signal de coordination reste faible. La coordination devient probante quand plusieurs
          familles indépendantes convergent dans une même fenêtre, puis quand les faux positifs
          organiques sont mesurés par le Validation Lab.
        </p>
      </Section>
    </DocPage>
  )
}
