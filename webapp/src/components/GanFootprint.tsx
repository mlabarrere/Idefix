// Carte d'EMPREINTE GAN (OPSEC) — s'affiche quand la lentille « Empreinte GAN »
// est active. Auto-évaluation : combien de canaux observent le GAN, part
// d'origination (presse/OSINT) vs amplification adverse (russosphère),
// circulation interne, mentions du porte-avions. Canaux cliquables → drawer.
import { useTranslation } from 'react-i18next'
import { loadGanFootprint } from '../data/loaders'
import { useSelection } from '../state/SelectionContext'
import { useAsync } from '../ui'

export function GanFootprint() {
  const { t } = useTranslation()
  const { missionId, select } = useSelection()
  const { data: f } = useAsync(() => loadGanFootprint(missionId), [missionId])
  if (!f) return null

  const total = f.n_channels || 1
  const advPct = Math.round((f.n_adverse / total) * 100)
  const ChanRow = ({ c, color }: { c: { channel_id: number; username: string; gan_targeting: number }; color: string }) => (
    <button
      onClick={() => select(c.channel_id)}
      className="flex w-full items-center justify-between rounded px-1.5 py-0.5 text-left text-[11px] hover:bg-white/5"
    >
      <span className="truncate font-mono" style={{ color }}>@{c.username}</span>
      <span className="ml-2 shrink-0 text-slate-500">{c.gan_targeting.toFixed(2)}</span>
    </button>
  )

  return (
    <div className="rounded-lg border border-sky-400/30 bg-sky-400/[0.04] p-2.5">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold text-sky-300">{t('gan.title')}</span>
        <span className="font-mono text-xs text-slate-400">{t('gan.channels', { n: f.n_channels })}</span>
      </div>

      {/* origination vs amplification adverse */}
      <div className="mt-2">
        <div className="flex h-2 overflow-hidden rounded-full">
          <span className="bg-emerald-400/70" style={{ width: `${100 - advPct}%` }} />
          <span className="bg-rose-400/70" style={{ width: `${advPct}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[10px]">
          <span className="text-emerald-300">{t('gan.origination', { n: f.n_origination })}</span>
          <span className="text-rose-300">{t('gan.adverseShare', { n: f.n_adverse, pct: advPct })}</span>
        </div>
      </div>

      <p className="epi-hypothesis mt-2 text-[11px] leading-snug text-slate-300">
        {t('gan.prose', { pct: advPct })}
      </p>

      <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-slate-400">
        <div className="rounded bg-white/5 px-2 py-1">
          <div className="text-slate-200">{f.carrier_mentions}</div>{t('gan.carrierMentions')}
        </div>
        <div className="rounded bg-white/5 px-2 py-1">
          <div className="text-slate-200">
            {(f.internal_circulation.forward || 0) + (f.internal_circulation.media_reuse || 0) + (f.internal_circulation.co_forward || 0)}
          </div>{t('gan.internalLinks')}
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <div>
          <div className="mb-0.5 text-[10px] tracking-wide text-emerald-400/80 uppercase">{t('gan.origHead')}</div>
          {f.origination.slice(0, 6).map((c) => <ChanRow key={c.channel_id} c={c} color="#4ade80" />)}
        </div>
        <div>
          <div className="mb-0.5 text-[10px] tracking-wide text-rose-400/80 uppercase">{t('gan.advHead')}</div>
          {f.adverse.slice(0, 6).map((c) => <ChanRow key={c.channel_id} c={c} color="#f87171" />)}
        </div>
      </div>

      <p className="epi-limit mt-2 text-[10px] leading-snug text-slate-500">
        {t('gan.caveat')}
      </p>
    </div>
  )
}
