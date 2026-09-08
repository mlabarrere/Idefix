// Modèle de graphe en mémoire — PORTÉ de situation.js (enrichNodes / buildAdj /
// buildCommColors). Joint graph.json × channels_index × russosphere_snapshot.
import { useEffect, useState } from 'react'
import { loadChannelsIndex, loadEmbedSnapshot, loadGraph, loadSnapshot } from '../data/loaders'
import type { GraphData, GraphEdge } from '../data/types'
import type { SnapshotMode } from '../state/SnapshotMode'
import { FR_SIDE_MIN } from './grammar'

export interface EnrichedNode {
  cid: number
  username: string
  title: string
  arch: string | null
  cred: string
  eng: number
  fr: number | null
  susp: number
  tier: string | null
  ft: number
  gate_met: boolean
  degraded: boolean
  side: 'RU' | 'FR'
}

export interface AdjEntry {
  fwdFrom: { cid: number; count?: number; delay?: number | null }[]
  fwdTo: { cid: number; count?: number; delay?: number | null }[]
  coord: { cid: number; type: string; count?: number; dt?: number | null }[]
  domains: { domain: string; count?: number }[]
  mentions: { cid: number; count?: number }[]
  mentionedBy: { cid: number; count?: number }[]
}

export interface GraphModel {
  nodes: Map<number, EnrichedNode>
  adj: Map<number, AdjEntry>
  commColor: Map<number, string>
  communityOf: Map<number, number>
  communityLabel: Map<number, string>
  communities: { id: number; label: string; color: string; size: number }[]
  edges: GraphEdge[]
}

const edgeEnds = (e: GraphEdge): [number | string | undefined, number | string | undefined] => [
  e.source != null ? e.source : e.a,
  e.target != null ? e.target : e.b,
]

function buildModel(
  graph: GraphData,
  index: Awaited<ReturnType<typeof loadChannelsIndex>>,
  snap: Awaited<ReturnType<typeof loadSnapshot>>,
): GraphModel {
  const byId = new Map<number, NonNullable<typeof index>['channels'][number]>()
  for (const c of index?.channels ?? []) byId.set(c.channel_id, c)

  const commColor = new Map<number, string>()
  const communityOf = new Map<number, number>()
  const communityLabel = new Map<number, string>()
  for (const com of snap?.communities ?? []) {
    communityLabel.set(com.id, com.label)
    for (const ch of com.channels ?? []) {
      if (ch.channel_id != null) {
        commColor.set(ch.channel_id, com.color || '#3a4a63')
        communityOf.set(ch.channel_id, com.id)
      }
    }
  }

  const nodes = new Map<number, EnrichedNode>()
  for (const n of graph.nodes) {
    if (!('channel_id' in n)) continue
    const cid = n.channel_id
    const ix = byId.get(cid)
    const fr = n.fr_score != null ? n.fr_score : (ix?.fr_score ?? null)
    nodes.set(cid, {
      cid,
      username: n.username,
      title: n.title,
      arch: ix?.archetype ?? n.archetype ?? null,
      cred: n.credibility_prior || ix?.credibility_prior || 'other',
      eng: n.engagement || 0,
      fr,
      susp: ix?.suspicion ?? 0,
      tier: ix?.tier ?? null,
      ft: ix?.france_targeting ?? 0,
      gate_met: !!ix?.gate_met,
      degraded: !!(n.confidence && n.confidence.level === 'degraded'),
      side: (fr ?? 0) >= FR_SIDE_MIN ? 'FR' : 'RU',
    })
  }

  const adj = new Map<number, AdjEntry>()
  const get = (id: number): AdjEntry => {
    let a = adj.get(id)
    if (!a) {
      a = { fwdFrom: [], fwdTo: [], coord: [], domains: [], mentions: [], mentionedBy: [] }
      adj.set(id, a)
    }
    return a
  }
  for (const e of graph.edges) {
    const [src, tgt] = edgeEnds(e)
    if (e.family === 'propagation' && e.type === 'FORWARD' && typeof src === 'number' && typeof tgt === 'number') {
      get(tgt).fwdFrom.push({ cid: src, count: e.count, delay: e.delay_seconds })
      get(src).fwdTo.push({ cid: tgt, count: e.count, delay: e.delay_seconds })
    } else if (e.family === 'coordination' && typeof src === 'number' && typeof tgt === 'number') {
      get(src).coord.push({ cid: tgt, type: e.type, count: e.count, dt: e.dt_seconds })
      get(tgt).coord.push({ cid: src, type: e.type, count: e.count, dt: e.dt_seconds })
    } else if (e.family === 'influence' && e.type === 'CITES_DOMAIN' && typeof src === 'number' && typeof tgt === 'string') {
      get(src).domains.push({ domain: tgt, count: e.count })
    } else if (e.family === 'influence' && e.type === 'MENTIONS' && typeof src === 'number' && typeof tgt === 'number') {
      get(src).mentions.push({ cid: tgt, count: e.count })
      get(tgt).mentionedBy.push({ cid: src, count: e.count })
    }
  }
  const byCount = (x: { count?: number }, y: { count?: number }) => (y.count || 0) - (x.count || 0)
  for (const a of adj.values()) {
    a.fwdFrom.sort(byCount)
    a.fwdTo.sort(byCount)
    a.coord.sort(byCount)
    a.domains.sort(byCount)
  }

  const communities = (snap?.communities ?? [])
    .map((c) => ({ id: c.id, label: c.label, color: c.color, size: c.size }))
    .sort((a, b) => b.size - a.size)

  return { nodes, adj, commColor, communityOf, communityLabel, communities, edges: graph.edges }
}

export function useGraphModel(
  missionId: string,
  mode: SnapshotMode = 'analytics',
): { model: GraphModel | null; loading: boolean } {
  const [model, setModel] = useState<GraphModel | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let alive = true
    setLoading(true)
    // 'embedding' charge le snapshot communautés regroupé par embeddings ; on
    // retombe sur le snapshot Analytics si le bundle embedding est absent.
    const snapLoader =
      mode === 'embedding'
        ? loadEmbedSnapshot(missionId).then((s) => s ?? loadSnapshot(missionId))
        : loadSnapshot(missionId)
    Promise.all([loadGraph(missionId), loadChannelsIndex(missionId), snapLoader]).then(
      ([graph, index, snap]) => {
        if (!alive) return
        setModel(graph ? buildModel(graph, index, snap) : null)
        setLoading(false)
      },
    )
    return () => {
      alive = false
    }
  }, [missionId, mode])
  return { model, loading }
}

export function nameOf(model: GraphModel | null, cid: number): string {
  const n = model?.nodes.get(cid)
  return n?.username || '#' + cid
}
