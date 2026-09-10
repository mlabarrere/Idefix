// Section « Évolution » — comment les communautés ont changé entre deux runs
// (scripts/compare_snapshots.py → snapshot_diff.json). Absence gracieuse : la
// plupart des missions n'ont pas encore de diff, on ne rend rien.
import { loadSnapshotDiff } from '../data/loaders'
import { useAsync } from '../ui'

// `channels_drifted` peut être un nombre OU un tableau selon le run.
const count = (v: number | unknown[] | undefined): number | undefined =>
  Array.isArray(v) ? v.length : v

function Chip({ label, value }: { label: string; value?: number }) {
  if (value == null) return null
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
      <div className="text-[10px] tracking-wide text-gray-500 uppercase dark:text-gray-400">{label}</div>
      <div className="epi-computed text-lg font-semibold text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  )
}

export function SnapshotDiff({ missionId }: { missionId: string }) {
  const { data: diff } = useAsync(() => loadSnapshotDiff(missionId), [missionId])
  if (!diff) return null

  const cmp = diff.compared_snapshots
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold tracking-wide text-gray-500 uppercase dark:text-gray-400">
        Évolution{cmp && cmp.length === 2 ? ` · ${cmp[0]} → ${cmp[1]}` : ''}
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Chip label="Apparus" value={diff.channels_appeared} />
        <Chip label="Disparus" value={diff.channels_disappeared} />
        <Chip label="Dérivés" value={count(diff.channels_drifted)} />
        <Chip label="Fusions" value={diff.communities_merged} />
        <Chip label="Scissions" value={diff.communities_split} />
      </div>
      {diff.flag_high_drift && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
          ⚠ {diff.flag_high_drift}
        </div>
      )}
    </section>
  )
}
