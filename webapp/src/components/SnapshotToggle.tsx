// Switch galaxie « Analytics ↔ LLM Embedding ». À gauche le regroupement
// lexical/structurel (Leiden), à droite le regroupement par embeddings locaux.
// En une fraction de seconde on voit des communautés + arêtes de meilleure
// qualité ; le callout affiche les deltas CHIFFRÉS (cohésion, modularité) issus
// de stats.comparison — des mesures, jamais un « c'est mieux » creux.
import { loadEmbedSnapshot } from '../data/loaders'
import { useSelection } from '../state/SelectionContext'
import { useSnapshotMode } from '../state/SnapshotMode'
import { useAsync } from '../ui'

const PILL = 'rounded-full px-2.5 py-1 text-xs ring-1 ring-inset backdrop-blur transition'

export function SnapshotToggle() {
  const { missionId } = useSelection()
  const { mode, setMode } = useSnapshotMode()
  // Chargé seulement pour lire stats.comparison (le callout). Le HTTP cache le
  // partage avec le rendu galaxie qui charge le même fichier.
  const { data: embed } = useAsync(
    () => (mode === 'embedding' ? loadEmbedSnapshot(missionId) : Promise.resolve(null)),
    [missionId, mode],
  )
  const cmp = embed?.stats.comparison ?? null

  return (
    <div>
      <div className="mb-1 px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        Vue communautés
      </div>
      <div className="flex gap-1.5">
        <button
          onClick={() => setMode('analytics')}
          className={`${PILL} ${mode === 'analytics' ? 'bg-sky-500/20 text-sky-200 ring-sky-400/50' : 'text-slate-300 ring-white/10 hover:ring-white/30'}`}
        >
          Analytics
        </button>
        <button
          onClick={() => setMode('embedding')}
          className={`${PILL} ${mode === 'embedding' ? 'bg-amber-500/20 text-amber-200 ring-amber-400/50' : 'text-slate-300 ring-white/10 hover:ring-white/30'}`}
        >
          LLM Embedding
        </button>
      </div>

      {mode === 'embedding' && (
        <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {cmp ? (
            <>
              <div className="font-semibold">Regroupement par embeddings locaux (coût 0).</div>
              <ul className="mt-1 space-y-0.5 text-amber-100/90">
                <li>
                  Cohésion intra-groupe {cmp.intra_cohesion.analytics} → {cmp.intra_cohesion.embedding}
                  {cmp.intra_cohesion.gain_pct != null && (
                    <span className="font-semibold"> ({cmp.intra_cohesion.gain_pct > 0 ? '+' : ''}{cmp.intra_cohesion.gain_pct} %)</span>
                  )}
                </li>
                <li>Modularité {cmp.modularity.analytics} → {cmp.modularity.embedding}</li>
                <li>Communautés {cmp.n_communities.analytics} → {cmp.n_communities.embedding} · {cmp.n_bridges} ponts</li>
              </ul>
              <div className="mt-1 text-[10px] text-amber-100/60">
                Pourquoi mieux : les canaux sémantiquement proches sont regroupés (similarité de texte multilingue), pas seulement ceux structurellement liés — des ensembles plus cohérents et lisibles. Mesures, pas verdict.
              </div>
            </>
          ) : (
            <div className="text-amber-100/80">
              Snapshot embedding absent — générez-le :
              <code className="ml-1">python scripts/analyze_communities_embed.py --mission {missionId}</code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
