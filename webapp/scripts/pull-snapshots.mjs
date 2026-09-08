// Prebuild Vercel : "Vercel consomme Supabase".
// Récupère les snapshots communautés (clustering poussé hors-ligne) depuis
// Supabase et les écrit dans le bundle statique AVANT `vite build`. Le payload
// en base est déjà scrubbé au push (cf. src/shared/snapshot_store.py), donc on
// l'écrit tel quel. Identifiants = variables d'env Vercel (build-only) :
//   SUPABASE_URL + SUPABASE_KEY (service-role, jamais dans le bundle).
// Sans identifiants (dev local), on garde le bundle committé et on n'échoue pas.
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'

// (mission, label_source en base) -> fichier lu par la webapp (loaders.ts).
const SNAPSHOTS = [
  { mission: 'russosphere', label: 'analytics', file: 'public/data/russosphere/russosphere_snapshot.json' },
  { mission: 'russosphere', label: 'embedding', file: 'public/data/russosphere/russosphere_embed_snapshot.json' },
]

// La galaxie se rend en `layout: 'preset'` : elle EXIGE des coordonnées x/y par
// communauté, ajoutées hors-ligne par scripts/precompute_galaxy_layout.py et
// committées dans le fichier — le payload Supabase, lui, N'A PAS ces coords. Sans
// cette garde, le pull écrasait le fichier précalculé par un snapshot sans x/y →
// toutes les nébuleuses s'empilaient en (0,0) (cercles concentriques) EN PROD.
// On ne remplace donc le fichier committé QUE si le nouveau payload garde des
// coordonnées ; sinon on préserve le précalcul committé.
export const hasLayoutCoords = (snapshot) =>
  Array.isArray(snapshot?.communities) && snapshot.communities.some((c) => c?.x != null && c?.y != null)

// ponytail: timeout dur par requête — un fetch sans borne fait HANGER le build
// Vercel indéfiniment si Supabase stalle. Toute panne réseau (timeout inclus)
// dégrade vers le bundle committé au lieu d'échouer le déploiement.
const FETCH_TIMEOUT_MS = 20_000

async function main() {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_KEY
  if (!url || !key) {
    console.warn('[pull-snapshots] SUPABASE_URL/SUPABASE_KEY absents — bundle committé conservé.')
    return
  }

  const base = url.replace(/\/$/, '') + '/rest/v1/community_snapshots'
  const headers = { apikey: key, Authorization: `Bearer ${key}` }

  for (const { mission, label, file } of SNAPSHOTS) {
    const q = `mission=eq.${encodeURIComponent(mission)}&label_source=eq.${encodeURIComponent(label)}&select=snapshot`
    try {
      const res = await fetch(`${base}?${q}`, { headers, signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) })
      if (!res.ok) {
        console.warn(`[pull-snapshots] ${mission}/${label}: HTTP ${res.status} — fichier committé conservé.`)
        continue
      }
      const rows = await res.json()
      if (!rows.length) {
        console.warn(`[pull-snapshots] ${mission}/${label} absent en base — fichier committé conservé.`)
        continue
      }
      // Garde layout : ne pas détruire les coordonnées précalculées committées.
      if (!hasLayoutCoords(rows[0].snapshot)) {
        console.warn(`[pull-snapshots] ${mission}/${label} sans coords x/y — fichier committé (précalculé) conservé.`)
        continue
      }
      await mkdir(dirname(file), { recursive: true })
      await writeFile(file, JSON.stringify(rows[0].snapshot))
      console.log(`[pull-snapshots] ${mission}/${label} -> ${file}`)
    } catch (err) {
      console.warn(`[pull-snapshots] ${mission}/${label}: ${err?.name || 'erreur'} réseau — fichier committé conservé.`)
    }
  }
}

// N'exécute le pull que lancé directement (pas à l'import — pour le self-check).
if (import.meta.url === `file://${process.argv[1]}`) await main()
