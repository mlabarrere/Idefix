// Chargeurs du bundle JSON statique (no-backend). fetch() relatif sur
// data/<mission>/… ; repli sur data/… (export plat historique). Échec -> null
// (états vides propres). Cache mémoire pour les détails canal (lazy au drill).
import type {
  ChannelDetail,
  ChannelsIndex,
  GraphData,
  Manifest,
  CommentersBundle,
  GanFootprint,
  RussosphereSnapshot,
  SnapshotDiff,
  StoriesBundle,
  ThemesBundle,
} from './types'

async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url, { cache: 'no-cache' })
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  }
}

// Tente data/<mission>/<file> puis data/<file> (bundle plat par défaut).
async function loadScoped<T>(missionId: string, file: string): Promise<T | null> {
  const scoped = await fetchJSON<T>(`data/${missionId}/${file}`)
  if (scoped !== null) return scoped
  return fetchJSON<T>(`data/${file}`)
}

export const loadManifest = (m: string) => loadScoped<Manifest>(m, 'manifest.json')
export const loadChannelsIndex = (m: string) => loadScoped<ChannelsIndex>(m, 'channels_index.json')
export const loadGraph = (m: string) => loadScoped<GraphData>(m, 'graph.json')
// Snapshot communautés : nom canonique `russosphere_snapshot.json` ; repli sur
// `russosphere.json` (nom plat de l'export legacy, encore utilisé par le bundle GAN).
export async function loadSnapshot(m: string): Promise<RussosphereSnapshot | null> {
  return (await loadScoped<RussosphereSnapshot>(m, 'russosphere_snapshot.json')) ?? loadScoped<RussosphereSnapshot>(m, 'russosphere.json')
}
// Snapshot communautés « LLM Embedding » — piste parallèle (scripts/analyze_communities_embed.py).
// Même schéma que loadSnapshot ; null si le bundle embedding n'a pas été généré.
export async function loadEmbedSnapshot(m: string): Promise<RussosphereSnapshot | null> {
  return loadScoped<RussosphereSnapshot>(m, `${m}_embed_snapshot.json`)
}
// Histoires (sélecteur narratif) — produit par scripts/build_stories.py.
export const loadStories = (m: string) => loadScoped<StoriesBundle>(m, 'stories.json')
// Thèmes (lentilles) — ensembles de canaux par thème, produits par export_static.
export const loadThemes = (m: string) => loadScoped<ThemesBundle>(m, 'themes.json')
// Empreinte GAN (OPSEC) — produit par scripts/build_gan_footprint.py.
export const loadGanFootprint = (m: string) => loadScoped<GanFootprint>(m, 'gan_footprint.json')
// Commentateurs des groupes liés (engagement) — scripts/build_commenters.py.
export const loadCommenters = (m: string) => loadScoped<CommentersBundle>(m, 'commenters.json')
// Diff de snapshots communautés entre runs — scripts/compare_snapshots.py.
export const loadSnapshotDiff = (m: string) => loadScoped<SnapshotDiff>(m, 'snapshot_diff.json')

// Détail canal (lazy, mémoïsé) — channels/<id>.json.
const _channelCache = new Map<string, ChannelDetail | null>()
export async function loadChannel(m: string, channelId: number): Promise<ChannelDetail | null> {
  const key = `${m}:${channelId}`
  if (_channelCache.has(key)) return _channelCache.get(key)!
  const d = await loadScoped<ChannelDetail>(m, `channels/${channelId}.json`)
  _channelCache.set(key, d)
  return d
}
