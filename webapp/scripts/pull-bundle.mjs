// Prebuild Vercel : reconstruit le bundle scoré depuis Supabase `channel_scores`.
// Le scoring est matérialisé hors-ligne (build_scores.py) ; ici on ne fait QUE
// lire le payload scoré via REST et écrire les fichiers que la webapp consomme :
//   public/data/<mission>/channels_index.json  (table Canaux + Synthèse)
//   public/data/<mission>/channels/<id>.json   (ChannelDrawer, lazy)
//   public/data/<mission>/manifest.json        (stats réelles)
// Sans identifiants (dev local), on garde le bundle committé et on n'échoue pas.
// Creds = variables d'env Vercel (SUPABASE_URL + SUPABASE_KEY service-role).
import { mkdir, writeFile } from 'node:fs/promises'

const url = process.env.SUPABASE_URL
const key = process.env.SUPABASE_KEY
if (!url || !key) {
  console.warn('[pull-bundle] SUPABASE_URL/SUPABASE_KEY absents — bundle committé conservé.')
  process.exit(0)
}

const REST = url.replace(/\/$/, '') + '/rest/v1'
const H = { apikey: key, Authorization: `Bearer ${key}` }
const PAGE = 1000 // plafond REST Supabase -> pagination
const TIMEOUT = 30_000
const MISSIONS = ['russosphere', 'gan'] // missions ayant des scores matérialisés

async function rest(path, { range } = {}) {
  const headers = { ...H }
  if (range) { headers.Range = range; headers.Prefer = 'count=exact' }
  const res = await fetch(`${REST}/${path}`, { headers, signal: AbortSignal.timeout(TIMEOUT) })
  if (!res.ok) throw new Error(`HTTP ${res.status} on ${path}`)
  return { rows: await res.json(), cr: res.headers.get('content-range') || '' }
}

async function count(table) {
  const { cr } = await rest(`${table}?select=*`, { range: '0-0' })
  return cr.includes('/') ? Number(cr.split('/').pop()) : 0
}

async function paginate(table, select, filt) {
  const out = []
  for (let off = 0; ; off += PAGE) {
    const { rows } = await rest(`${table}?select=${select}${filt ? '&' + filt : ''}`, {
      range: `${off}-${off + PAGE - 1}`,
    })
    out.push(...rows)
    if (rows.length < PAGE) return out
  }
}

const indexRow = (p) => ({
  channel_id: p.channel_id,
  username: p.username ?? null,
  title: p.title ?? null,
  suspicion: p.suspicion?.v ?? null,
  tier: p.tier ?? null,
  archetype: p.archetype ?? null,
  credibility_prior: p.credibility_prior ?? null,
  fr_score: p.fr_score ?? null,
  france_targeting: p.france_targeting ?? null,
  gate_met: p.gate?.met ?? null,
})

const nEdges = await count('edges')
const nMessages = await count('messages')

for (const mission of MISSIONS) {
  let rows
  try {
    rows = await paginate('channel_scores', 'payload', `mission=eq.${mission}`)
  } catch (err) {
    console.warn(`[pull-bundle] ${mission}: ${err.message} — bundle committé conservé.`)
    continue
  }
  if (!rows.length) { console.warn(`[pull-bundle] ${mission}: 0 score — sauté.`); continue }
  const payloads = rows.map((r) => r.payload)
  const dir = `public/data/${mission}`
  await mkdir(`${dir}/channels`, { recursive: true })

  let env = {}
  try {
    const { rows: m } = await rest(`scores_run_meta?select=envelope&mission=eq.${mission}&limit=1`)
    env = m[0]?.envelope || {}
  } catch { /* envelope optionnelle */ }

  await writeFile(`${dir}/channels_index.json`, JSON.stringify({
    generated_at: 'rest-build',
    total: payloads.length,
    coverage_callout: env.coverage_callout ?? null,
    symmetric_ratio: env.symmetric_ratio ?? null,
    channels: payloads.map(indexRow),
  }))
  await Promise.all(payloads.map((p) =>
    writeFile(`${dir}/channels/${p.channel_id}.json`, JSON.stringify(p))))
  await writeFile(`${dir}/manifest.json`, JSON.stringify({
    mission, generated_at: 'rest-build', source: 'supabase-rest-api (channel_scores)',
    stats: { n_channels: payloads.length, n_edges: nEdges, n_messages: nMessages },
  }, null, 2))

  const t2 = payloads.filter((p) => p.tier === 'T2').length
  console.log(`[pull-bundle] ${mission}: ${payloads.length} canaux (${t2} T2)`)
}
