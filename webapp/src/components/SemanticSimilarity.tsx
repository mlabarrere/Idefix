// ponytail: standalone component pour embedding proximity — réutilise pattern ChannelDrawer
import { loadChannel } from '../data/loaders'
import { at, fmt } from '../graph/grammar'
import { useSelection } from '../state/SelectionContext'
import { useAsync } from '../ui'

interface Props {
  channelId: string
  missionId: string
}

export function SemanticSimilarity({ channelId, missionId }: Props) {
  const { select } = useSelection()
  const { data: c, loading } = useAsync(
    () => loadChannel(missionId, Number(channelId)),
    [missionId, channelId],
  )

  if (loading) return <div className="text-sm text-gray-600 dark:text-gray-400">Chargement…</div>
  if (!c) return null
  if (!c.embedding_proximity || c.embedding_proximity.length === 0) return null

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/40">
      <div className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-400">
        Canaux sémantiquement similaires
      </div>
      <div className="space-y-1">
        {c.embedding_proximity.map((sim, i) => (
          <button
            key={i}
            onClick={() => select(sim.channel_id)}
            className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs text-sky-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <span>{at(sim.handle)}</span>
            <span className="text-gray-400 dark:text-gray-500">cosine {fmt(sim.cosine)}</span>
          </button>
        ))}
      </div>
      <p className="mt-2 text-[10px] leading-snug text-gray-400 dark:text-gray-500">
        Proximité sémantique via embeddings (paraphrase-multilingual-MiniLM).
        Canaux produisant du contenu lexicalement proche.
      </p>
    </div>
  )
}
