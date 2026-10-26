// Vercel prebuild: "Vercel reads Supabase".
// Fetches the community snapshots (clustering pushed offline) from Supabase and
// writes them into the static bundle BEFORE `vite build`. The stored payload is
// already scrubbed at push time (see src/shared/snapshot_store.py), so it is
// written as is. Credentials = Vercel env vars (build only):
//   SUPABASE_URL + SUPABASE_KEY (service role, never in the bundle).
// webapp/public/data/ is gitignored: no snapshot is committed. Without credentials
// (local dev) the script writes nothing, leaves the local files untouched, and
// does not fail the build.
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import { pathToFileURL } from 'node:url'

// (mission, label_source in the database) -> file the webapp reads (loaders.ts).
const SNAPSHOTS = [
  { mission: 'russosphere', label: 'analytics', file: 'public/data/russosphere/russosphere_snapshot.json' },
  { mission: 'russosphere', label: 'embedding', file: 'public/data/russosphere/russosphere_embed_snapshot.json' },
]

// The galaxy renders with `layout: 'preset'`: it REQUIRES x/y coordinates per
// community, added offline by scripts/precompute_galaxy_layout.py into the local
// file; the Supabase payload does NOT carry them. Without this guard the pull
// overwrote the precomputed file with a snapshot without x/y, and every nebula
// stacked at (0,0) (concentric circles) IN PRODUCTION. So the local file is
// replaced ONLY when the new payload keeps coordinates; otherwise it is kept.
export const hasLayoutCoords = (snapshot) =>
  Array.isArray(snapshot?.communities) && snapshot.communities.some((c) => c?.x != null && c?.y != null)

// Hard per-request timeout: an unbounded fetch HANGS the Vercel build forever if
// Supabase stalls. Any network failure (timeout included) leaves the local file
// as is instead of failing the deployment.
const FETCH_TIMEOUT_MS = 20_000

async function main() {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_KEY
  if (!url || !key) {
    console.warn(
      '[pull-snapshots] SUPABASE_URL/SUPABASE_KEY not set: skipped. public/data/ is left as ' +
        'is (no snapshot is committed; the offline pipeline, scripts/pipeline.py, builds them).',
    )
    return
  }

  const base = url.replace(/\/$/, '') + '/rest/v1/community_snapshots'
  const headers = { apikey: key, Authorization: `Bearer ${key}` }

  for (const { mission, label, file } of SNAPSHOTS) {
    const q = `mission=eq.${encodeURIComponent(mission)}&label_source=eq.${encodeURIComponent(label)}&select=snapshot`
    try {
      const res = await fetch(`${base}?${q}`, { headers, signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) })
      if (!res.ok) {
        console.warn(`[pull-snapshots] ${mission}/${label}: HTTP ${res.status}; ${file} left as is.`)
        continue
      }
      const rows = await res.json()
      if (!rows.length) {
        console.warn(`[pull-snapshots] ${mission}/${label}: not in the database; ${file} left as is.`)
        continue
      }
      // Layout guard: never destroy the precomputed coordinates.
      if (!hasLayoutCoords(rows[0].snapshot)) {
        console.warn(
          `[pull-snapshots] ${mission}/${label}: payload has no x/y coordinates; ` +
            `${file} (precomputed layout) left as is.`,
        )
        continue
      }
      await mkdir(dirname(file), { recursive: true })
      await writeFile(file, JSON.stringify(rows[0].snapshot))
      console.log(`[pull-snapshots] ${mission}/${label} -> ${file}`)
    } catch (err) {
      console.warn(
        `[pull-snapshots] ${mission}/${label}: network ${err?.name || 'error'}; ${file} left as is.`,
      )
    }
  }
}

// Run the pull only when executed directly (not on import, for the self-check).
// pathToFileURL: a plain `file://${argv[1]}` never matched on Windows (C:\ paths),
// so the pull silently never ran there.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main()
