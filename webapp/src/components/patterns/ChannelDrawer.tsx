// Drawer canal RICHE (slide-over) — PORTÉ de situation.js renderDrawer +
// renderInteractions, ENRICHI du "détail du calcul" (_components/_severity_detail),
// des DÉFINITIONS techniques de chaque score (visibles, pas seulement tooltip),
// du rattachement NARRATIF (histoires/phases) et de la CoverageCallout.
// Lit channels/<id>.json (lazy). Interactions cliquables = pivot.
//
// EXCEPTION ASSUMÉE au substrat shadcn/ui — panneau NON-MODAL et Radix-FREE.
// À l'image de la Galaxie plein-cadre, ce composite déroge volontairement à la
// règle « tout passe par shadcn/Radix ». On n'utilise PAS Radix Dialog/Sheet :
// leur focus-trap + blocage des pointeurs (pointer-events) + scroll-lock
// rendraient le graphe (galaxie) ET le tableau des canaux INERTES tant que le
// panneau est ouvert. Or l'UX repose sur l'inverse : garder l'arrière-plan
// pleinement interactif (sélectionner un autre nœud/ligne pivote le panneau sans
// le fermer). D'où un <aside> bespoke, positionné, sans overlay bloquant.
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { loadChannel, loadCommenters, loadStories } from '@/data/loaders'
import type { ChannelDetail, ScoreFamily, SeverityDetail } from '@/data/types'
import { archInterp, at, fmt, fmtDur, scoreHelp, tgUrl } from '@/graph/grammar'
import type { GraphModel } from '@/graph/useGraphModel'
import { nameOf } from '@/graph/useGraphModel'
import { useSelection } from '@/state/SelectionContext'
import { useAsync } from '@/ui'
import { Badge } from '@/components/ui/badge'

const FAM_ORDER = ['a', 'b', 'c', 'd', 'e', 'f']
const famKeys = (s: Record<string, ScoreFamily>) => {
  const known = FAM_ORDER.filter((k) => k in s)
  const extra = Object.keys(s).filter((k) => !FAM_ORDER.includes(k))
  return [...known, ...extra]
}

function FamilyCard({ k, s }: { k: string; s: ScoreFamily }) {
  const { t } = useTranslation()
  const help = scoreHelp(k)
  return (
    <details className="rounded-md border border-border bg-muted">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2">
        <span
          className="flex h-6 w-6 items-center justify-center rounded text-xs font-bold"
          style={{ color: s.c, background: s.c + '22', border: `1px solid ${s.c}55` }}
        >
          {k.startsWith('telegram_') ? '·' : k}
        </span>
        <span className="flex-1">
          <span className="text-sm text-foreground" title={help}>
            {s.n}
            {s.na ? <span className="epi-limit ml-1 text-xs">{t('drawer.naV0')}</span> : ''}
          </span>
          <span className="mt-1 block h-1.5 w-full overflow-hidden rounded bg-foreground/10">
            <span className="block h-full rounded" style={{ width: `${s.na ? 0 : Math.round((s.v || 0) * 100)}%`, background: s.c }} />
          </span>
        </span>
        <span className="epi-computed text-sm font-semibold" style={{ color: s.c }}>
          {fmt(s.v)}
        </span>
      </summary>
      <div className="border-t border-border px-3 py-2">
        {help && (
          <p className="mb-1.5 border-b border-border pb-1.5 text-[11px] leading-snug text-muted-foreground">
            <span className="font-medium text-foreground">{t('drawer.definition')}</span>
            {help}
          </p>
        )}
        {(s.ev || []).map(([key, val], i) => (
          <div key={i} className="flex justify-between gap-3 py-0.5 text-xs">
            <span className="epi-evidence text-muted-foreground">{String(key)}</span>
            <span className="epi-evidence text-right text-foreground">{String(val)}</span>
          </div>
        ))}
      </div>
    </details>
  )
}

function CalcDetail({ c }: { c: ChannelDetail }) {
  const { t } = useTranslation()
  const comp = c._components
  if (!comp) return null
  const sev = comp._severity_detail as SeverityDetail | undefined
  const hasTriggered = FAM_ORDER.some(
    (k) => !!comp[k] && typeof comp[k] === 'object' && 'weight' in (comp[k] as object),
  )
  return (
    <details className="rounded-md border border-border bg-muted/40">
      <summary className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-primary">
        {t('drawer.calcTitle')}
      </summary>
      <div className="space-y-2 px-3 py-2 text-xs">
        <div className="epi-evidence space-y-0.5">
          {FAM_ORDER.map((k) => {
            const x = comp[k]
            if (!x || typeof x !== 'object' || !('weight' in (x as object))) return null
            const o = x as { weight: number; value: number | null; contribution?: number }
            return (
              <div key={k} className="flex justify-between gap-3">
                <span className="text-muted-foreground">{t('drawer.calcRow', { k, weight: fmt(o.weight), value: o.value == null ? 'N/A' : fmt(o.value) })}</span>
                <span className="text-foreground">= {fmt(o.contribution ?? 0)}</span>
              </div>
            )
          })}
        </div>
        <div className="epi-evidence flex justify-between border-t border-border pt-1">
          <span className="text-muted-foreground">{t('drawer.calcBase')}</span>
          <span className="text-foreground">{fmt(comp._base)}</span>
        </div>
        {sev && (
          <div className="epi-evidence space-y-0.5">
            <div className="flex justify-between"><span className="text-muted-foreground">{t('drawer.boostReforward')}</span><span className="text-foreground">+{fmt(sev.reforward_boost)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">{t('drawer.boostAdversary', { n: sev.adversary_domain_citations ?? 0 })}</span><span className="text-foreground">+{fmt(sev.adversary_boost)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">{t('drawer.boostTargeting')}</span><span className="text-foreground">+{fmt(sev.france_boost)}</span></div>
            <div className="flex justify-between font-semibold"><span className="text-primary/80">{t('drawer.severityFactor')}</span><span className="text-primary">× {fmt(comp._severity_factor ?? sev.factor)}</span></div>
          </div>
        )}
        <div className="epi-evidence flex justify-between border-t border-border pt-1 font-semibold">
          <span className="text-muted-foreground">{t('drawer.combinedSuspicion')}</span>
          <span className="text-foreground">{fmt(comp._combined)}</span>
        </div>
        <p className="pt-1 text-[11px] text-muted-foreground">{t('drawer.calcFormula')}</p>
        {!hasTriggered && <p className="text-muted-foreground">{t('drawer.noFamilyTriggered')}</p>}
      </div>
    </details>
  )
}

function Interactions({ model, cid }: { model: GraphModel; cid: number }) {
  const { t } = useTranslation()
  const { select } = useSelection()
  const a = model.adj.get(cid)
  if (!a) return null
  const Group = ({ title, items }: { title: string; items: { cid: number; count?: number; meta?: string }[] }) =>
    items.length === 0 ? null : (
      <div className="mb-2">
        <div className="mb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          {title} <span className="text-muted-foreground">{items.length}</span>
        </div>
        {items.slice(0, 8).map((x, i) => (
          <button
            key={i}
            onClick={() => select(x.cid)}
            className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-xs text-telegram hover:bg-accent"
          >
            <span>{at(nameOf(model, x.cid))}</span>
            <span className="text-muted-foreground">{x.meta ?? `${x.count || 0}×`}</span>
          </button>
        ))}
      </div>
    )
  return (
    <div>
      <div className="mt-4 mb-2 text-sm font-medium text-muted-foreground">{t('drawer.interactions')}</div>
      <Group title={t('drawer.relaysFrom')} items={a.fwdFrom.map((x) => ({ cid: x.cid, meta: `${x.count || 0}× · ${fmtDur(x.delay)}` }))} />
      <Group title={t('drawer.relayedBy')} items={a.fwdTo.map((x) => ({ cid: x.cid, count: x.count }))} />
      <Group title={t('drawer.coordinatedWith')} items={a.coord.map((x) => ({ cid: x.cid, meta: `${x.type} · ${x.count || 0}` }))} />
      {a.domains.length > 0 && (
        <div className="mb-2">
          <div className="mb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{t('drawer.citesDomains')} {a.domains.length}</div>
          {a.domains.slice(0, 8).map((x, i) => (
            <div key={i} className="flex justify-between px-2 py-1 text-xs text-muted-foreground">
              <span>{x.domain}</span>
              <span className="text-muted-foreground">{x.count || 0}×</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ChannelDrawer({ model }: { model: GraphModel }) {
  const { t } = useTranslation()
  const { missionId, selected, select } = useSelection()
  const [c, setC] = useState<ChannelDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const open = selected != null

  // Commentateurs du groupe de discussion lié (engagement observable).
  const { data: commentersData } = useAsync(() => loadCommenters(missionId), [missionId])
  const commenters = selected != null ? commentersData?.channels[String(selected)] : undefined

  // Rattachement narratif : dans quelles histoires/phases ce canal apparaît.
  const { data: storiesData } = useAsync(() => loadStories(missionId), [missionId])
  const memberships = useMemo(() => {
    if (!storiesData || selected == null) return []
    const out: { storyTitle: string; phaseName: string; dateLabel: string }[] = []
    for (const s of storiesData.stories)
      for (const p of s.phases)
        if ((p.channel_ids || []).includes(selected))
          out.push({ storyTitle: s.title, phaseName: p.name, dateLabel: p.date_label })
    return out
  }, [storiesData, selected])

  useEffect(() => {
    if (selected == null) return
    let alive = true
    setLoading(true)
    setC(null)
    loadChannel(missionId, selected).then((d) => {
      if (alive) {
        setC(d)
        setLoading(false)
      }
    })
    return () => {
      alive = false
    }
  }, [selected, missionId])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') select(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, select])

  const url = c ? tgUrl(c.username) : null
  const su = c?.suspicion ?? { v: 0, lo: 0, hi: 0 }
  const commId = selected != null ? model.communityOf.get(selected) : undefined
  const commLabel = commId != null ? model.communityLabel.get(commId) : undefined

  // Panneau NON-MODAL : pas de fond grisé bloquant — le graphe et le tableau
  // restent cliquables (on peut sélectionner un autre nœud sans fermer le drawer).
  if (!open) return null
  return (
    <aside className="fixed top-14 right-0 bottom-0 z-30 w-full max-w-md overflow-y-auto border-l border-border bg-card p-5 shadow-2xl">
      {loading || !c ? (
            <div className="text-sm text-muted-foreground">{loading ? t('common.loading') : t('drawer.notInIndex')}</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-lg font-semibold">
                    <span className="handle">{at(c.username || '#' + c.channel_id)}</span>
                    {url && (
                      <a href={url} target="_blank" rel="noopener" className="ml-2 text-sm font-normal text-telegram hover:underline" title={t('drawer.openTelegram')}>
                        ↗ t.me
                      </a>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">{c.title || ''} · fr_score {fmt(c.fr_score)}</div>
                </div>
                <button onClick={() => select(null)} className="rounded p-1 text-muted-foreground hover:bg-accent" aria-label={t('drawer.close')}>✕</button>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="epi-computed text-3xl font-semibold text-foreground">{fmt(su.v)}</span>
                <span className="epi-computed text-sm text-muted-foreground">[{fmt(su.lo)}–{fmt(su.hi)}]</span>
                {c.tier && <span className="ml-auto text-xs text-muted-foreground">{c.tier} · {c.tier === 'T1' ? t('drawer.tierT1') : t('drawer.tierT2')}</span>}
              </div>

              <div className="flex flex-wrap gap-2">
                {c.archetype && <Badge tone="amber">{c.archetype}</Badge>}
                <Badge tone={c.credibility_prior === 'suspect' ? 'red' : c.credibility_prior === 'legit' ? 'green' : 'slate'}>{c.credibility_prior}</Badge>
                {commLabel && <Badge tone="slate">{commLabel}</Badge>}
              </div>

              {c.archetype && archInterp(c.archetype) && (
                <p className="epi-hypothesis text-sm">{t('drawer.whyArchetype')} {archInterp(c.archetype)}</p>
              )}

              {memberships.length > 0 && (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/[0.06] px-3 py-2 text-xs">
                  <span className="font-medium text-amber-700 dark:text-amber-300">{t('drawer.inNarrative')}</span>
                  {memberships.map((m, i) => (
                    <span key={i} className="text-foreground">
                      {i > 0 && ' · '}
                      {m.storyTitle} → <span className="font-medium">{m.phaseName}</span> ({m.dateLabel})
                    </span>
                  ))}
                </div>
              )}

              {c.gate && (
                <div className={`rounded-md border px-3 py-2 text-xs ${c.gate.met ? 'border-emerald-500/30 bg-emerald-500/[0.05] text-emerald-300' : 'border-border text-muted-foreground'}`}>
                  <span className="font-medium">
                    {c.gate.met ? t('drawer.gateMet') : t('drawer.gateUnmet')}
                  </span>{' '}
                  — {c.gate.met ? t('drawer.gateMetDetail') : t('drawer.gateUnmetDetail')}{' '}
                  {c.gate.detail}
                </div>
              )}

              <div className="space-y-1.5">
                <div className="text-sm font-medium text-muted-foreground">{t('drawer.fiveFamilies')}</div>
                {famKeys(c.scores).map((k) => (
                  <FamilyCard key={k} k={k} s={c.scores[k]} />
                ))}
              </div>

              <CalcDetail c={c} />

              {c.scores.f && (
                <details className="rounded-md border border-border bg-muted/40">
                  <summary className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-primary">
                    {t('drawer.semanticTitle')}
                  </summary>
                  <div className="space-y-2 px-3 py-2 text-xs">
                    {c.scores.f.ev.find(([k]) => k === 'baseline_distance') && (
                      <div>
                        <div className="mb-1 text-muted-foreground">
                          {t('drawer.baselineDistance')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="epi-evidence text-foreground">
                            {fmt(Number(c.scores.f.ev.find(([k]) => k === 'baseline_distance')?.[1] ?? 0))}
                          </span>
                          <span className="h-2 flex-1 overflow-hidden rounded bg-foreground/10">
                            <span
                              className="block h-full rounded"
                              style={{
                                width: `${Math.round(Number(c.scores.f.ev.find(([k]) => k === 'baseline_distance')?.[1] ?? 0) * 100)}%`,
                                background: c.scores.f.c,
                              }}
                            />
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {t('drawer.baselineScale')}
                        </p>
                      </div>
                    )}
                    {c.embedding_proximity && c.embedding_proximity.length > 0 && (
                      <div className="border-t border-border pt-2">
                        <div className="mb-1 text-muted-foreground">
                          {t('drawer.similarChannels')}
                        </div>
                        {c.embedding_proximity.slice(0, 3).map((sim, i) => (
                          <div key={i} className="flex justify-between gap-3 py-0.5">
                            <button
                              onClick={() => select(sim.channel_id)}
                              className="text-left text-telegram hover:underline"
                            >
                              {at(sim.handle)}
                            </button>
                            <span className="epi-evidence text-muted-foreground">
                              {fmt(sim.cosine)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </details>
              )}

              {commenters && commenters.n_comments > 0 && (
                <details className="rounded-md border border-border bg-muted/40">
                  <summary className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-foreground">
                    {t('drawer.commenters')} <span className="text-muted-foreground">{t('drawer.commentersCount', { n: commenters.n_commenters, m: commenters.n_comments })}</span>
                  </summary>
                  <div className="px-3 py-2">
                    {commenters.top.map((u, i) => (
                      <div key={i} className="flex justify-between gap-3 py-0.5 text-xs">
                        <span className="font-mono text-telegram">
                          {u.username ? '@' + u.username : '#' + u.id}
                        </span>
                        <span className="text-muted-foreground">{u.count}×</span>
                      </div>
                    ))}
                    <p className="epi-limit mt-1.5 text-[10px] leading-snug text-muted-foreground">
                      {t('drawer.commentersNote')}
                    </p>
                  </div>
                </details>
              )}

              <Interactions model={model} cid={c.channel_id} />
            </div>
          )}
    </aside>
  )
}
