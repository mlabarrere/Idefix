// Analyse — écran fusionné Synthèse + Canaux (route /m/:missionId/analyse).
// À GAUCHE : les statistiques RÉELLES du snapshot (santé des données, communautés,
// modularité, densité d'arêtes = arêtes / nœud, canaux T2 corroborés) — aucun
// constat inventé, tout est calculé depuis le manifest + le snapshot + l'index.
// À DROITE : la table analyste complète (filtre handle/titre + tri par colonne),
// déléguée au pattern DataTable. La sélection reste partagée (SelectionContext).
import { useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { loadManifest, loadChannelsIndex, loadSnapshot } from '../data/loaders'
import { getMission } from '../data/missions'
import { fmt } from '../graph/grammar'
import { Badge, EmptyState, Spinner, useAsync } from '../ui'
import { SnapshotDiff } from '../components/SnapshotDiff'
import { PageHeader } from '../components/patterns/PageHeader'
import { StatCard } from '../components/patterns/StatCard'
import { DataTable, type DataTableColumn } from '../components/patterns/DataTable'
import type { ChannelIndexRow } from '../data/types'

type SortId = 'canal' | 'suspicion' | 'tier' | 'archetype' | 'ciblage' | 'gate'
type SortDir = 'asc' | 'desc'

// Accesseurs de tri : numériques pour suspicion/ciblage/gate, textuels sinon.
const ACCESS: Record<SortId, (c: ChannelIndexRow) => number | string> = {
  canal: (c) => (c.username ?? c.title ?? `#${c.channel_id}`).toLowerCase(),
  suspicion: (c) => c.suspicion ?? -1,
  tier: (c) => c.tier ?? '',
  archetype: (c) => c.archetype ?? '',
  ciblage: (c) => c.france_targeting ?? -1,
  gate: (c) => (c.gate_met ? 1 : 0),
}

export function Analyse() {
  const { t } = useTranslation()
  const { missionId } = useOutletContext<{ missionId: string }>()
  const mission = getMission(missionId)
  const { data: manifest, loading: lm } = useAsync(() => loadManifest(missionId), [missionId])
  const { data: index, loading: li } = useAsync(() => loadChannelsIndex(missionId), [missionId])
  const { data: snap } = useAsync(() => loadSnapshot(missionId), [missionId])

  const [q, setQ] = useState('')
  const [sort, setSort] = useState<{ id: SortId; dir: SortDir }>({ id: 'suspicion', dir: 'desc' })

  const channels = index?.channels ?? []
  const nT2 = channels.filter((c) => c.tier === 'T2').length
  // Densité d'arêtes du graphe = arêtes / nœuds (indicateur de connectivité réel).
  const nEdges = manifest?.stats?.n_edges ?? snap?.stats?.n_edges
  const nNodes = snap?.stats?.n_nodes ?? manifest?.stats?.n_channels
  const density = nEdges != null && nNodes ? nEdges / nNodes : undefined

  // En-tête de colonne cliquable → bascule le tri (indicateur ▲/▼).
  const sortHeader = (id: SortId, label: string) => (
    <button
      type="button"
      onClick={() => setSort((s) => ({ id, dir: s.id === id && s.dir === 'desc' ? 'asc' : 'desc' }))}
      className="flex items-center gap-1 tracking-wide uppercase hover:text-foreground"
    >
      {label}
      <span className="text-[10px]">{sort.id === id ? (sort.dir === 'desc' ? '▼' : '▲') : ''}</span>
    </button>
  )

  const columns = useMemo<DataTableColumn<ChannelIndexRow>[]>(
    () => [
      { id: 'canal', header: sortHeader('canal', t('channels.colCanal')), className: 'text-foreground', cell: (c) => <span className="truncate">{c.username ?? c.title ?? `#${c.channel_id}`}</span> },
      { id: 'suspicion', header: sortHeader('suspicion', t('channels.colSuspicion')), className: 'epi-computed text-foreground', cell: (c) => fmt(c.suspicion) },
      { id: 'tier', header: sortHeader('tier', t('channels.colTier')), cell: (c) => (c.tier ? <Badge tone={c.tier === 'T2' ? 'red' : 'slate'}>{c.tier}</Badge> : '—') },
      { id: 'archetype', header: sortHeader('archetype', t('channels.colArchetype')), className: 'text-muted-foreground', cell: (c) => c.archetype ?? '—' },
      { id: 'ciblage', header: sortHeader('ciblage', t('channels.colCiblage')), className: 'epi-computed text-muted-foreground', cell: (c) => fmt(c.france_targeting) },
      { id: 'gate', header: sortHeader('gate', t('channels.colGate')), cell: (c) => (c.gate_met ? <Badge tone="green">✓</Badge> : <Badge tone="slate">—</Badge>) },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t, sort],
  )

  const rows = useMemo<ChannelIndexRow[]>(() => {
    let r = index?.channels ?? []
    if (q.trim()) {
      const needle = q.toLowerCase()
      r = r.filter(
        (c) => (c.username ?? '').toLowerCase().includes(needle) || (c.title ?? '').toLowerCase().includes(needle),
      )
    }
    const acc = ACCESS[sort.id]
    const sign = sort.dir === 'desc' ? -1 : 1
    return [...r].sort((a, b) => {
      const va = acc(a)
      const vb = acc(b)
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sign
      return String(va).localeCompare(String(vb)) * sign
    })
  }, [index, q, sort])

  if (lm || li) return <div className="p-6"><Spinner /></div>

  const hasData = !!manifest || channels.length > 0

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <PageHeader
          title={mission ? t(`mission.${mission.id}.label`) : missionId}
          subtitle={mission ? t(`mission.${mission.id}.description`) : undefined}
        />

        {!hasData ? (
          <div className="mt-6">
            <EmptyState title={t('overview.emptyTitle')} hint={t('overview.emptyHint', { missionId })} />
          </div>
        ) : (
          <div className="mt-6 grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
            {/* ── Rail de statistiques (gauche) ── */}
            <aside className="space-y-6">
              <section className="space-y-3">
                <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">{t('overview.dataHealth')}</h2>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  {manifest?.generated_at && <Badge tone="slate">{t('overview.generated', { date: manifest.generated_at.slice(0, 10) })}</Badge>}
                  {manifest?.version && <Badge tone="slate">v{manifest.version}</Badge>}
                  <Badge tone={manifest?.public ? 'amber' : 'green'}>{manifest?.public ? t('overview.bundlePartial') : t('overview.bundleComplete')}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label={t('overview.statChannels')} value={fmt(manifest?.stats?.n_channels ?? channels.length)} />
                  <StatCard label={t('overview.statEdges')} value={fmt(nEdges)} />
                  <StatCard label={t('overview.statMessages')} value={fmt(manifest?.stats?.n_messages)} />
                  <StatCard label={t('overview.statDensity')} value={fmt(density)} hint={t('overview.hintDensity')} />
                </div>
              </section>

              <section className="space-y-3">
                <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">{t('overview.keyFigures')}</h2>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label={t('overview.statCommunities')} value={fmt(snap?.stats?.n_communities)} hint={snap?.stats ? t('overview.hintModularity', { value: snap.stats.modularity }) : undefined} />
                  <StatCard label={t('overview.statT2')} value={fmt(nT2)} hint={t('overview.hintT2')} />
                </div>
              </section>

              {/* Évolution — diff communautés entre runs (absence gracieuse). */}
              <SnapshotDiff missionId={missionId} />
            </aside>

            {/* ── Table analyste (droite) ── */}
            <div className="min-w-0 space-y-3">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
                  {t('channels.title')} <span className="text-muted-foreground/70">· {t('channels.count', { n: rows.length })}</span>
                </h2>
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder={t('channels.searchPlaceholder')}
                  className="w-64 max-w-[45%] rounded-md border border-border bg-muted px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                />
              </div>
              {rows.length === 0 ? (
                <EmptyState title={t('channels.emptyMatch')} />
              ) : (
                <DataTable columns={columns} rows={rows.slice(0, 300)} rowKey={(c) => c.channel_id} />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
