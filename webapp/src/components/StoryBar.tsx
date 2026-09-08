// Bandeau NARRATIF — sélecteur d'« histoires » (UX rév. 2, couche 2).
// Distinct des filtres analytiques (coin haut-droit de la galaxie) : ici c'est
// l'objet ÉDITORIAL — un dropdown d'histoires, puis des PHASES NOMMÉES AVEC
// DATES (pas d'animation, pas de scrubber). Sélectionner une phase filtre la
// galaxie sur ses canaux (auto-bloom + estompage du reste, via onPhase).
// Honnêteté : badge « données partielles » quand des canaux manquent au bundle,
// tier T1/T2 affiché, jamais de verdict.
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { loadStories } from '../data/loaders'
import type { StoryPhase } from '../data/types'
import { useSelection } from '../state/SelectionContext'
import { useAsync } from '../ui'

// data_status (donnée du bundle) -> clé i18n. Fallback : le t() renvoie le code
// brut si absent du dictionnaire, reproduisant l'ancien `?? s.data_status`.
const STATUS_KEY: Record<string, string> = {
  derived: 'story.statusDerived',
  editorial: 'story.statusEditorial',
  partial: 'story.statusPartial',
}

export function StoryBar({ onPhase, onStoryActive }: { onPhase: (p: StoryPhase | null) => void; onStoryActive?: () => void }) {
  const { missionId, selected } = useSelection()
  const { t } = useTranslation()
  const { data } = useAsync(() => loadStories(missionId), [missionId])
  const [storyId, setStoryId] = useState<string | null>(null)
  const [phaseId, setPhaseId] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  const stories = useMemo(() => data?.stories ?? [], [data])
  const story = useMemo(() => stories.find((s) => s.id === storyId) ?? null, [stories, storyId])
  const phase = useMemo(() => story?.phases.find((p) => p.id === phaseId) ?? null, [story, phaseId])

  // La phase active pilote la galaxie (remontée au parent).
  useEffect(() => {
    onPhase(phase ?? null)
  }, [phase, onPhase])

  // Une histoire active prend la main sur la galaxie : on coupe toute sélection
  // d'épisode concurrente pour éviter deux illuminations simultanées.
  useEffect(() => {
    if (story && onStoryActive) onStoryActive()
  }, [story, onStoryActive])

  // Changement de mission => reset narratif.
  useEffect(() => {
    setStoryId(null)
    setPhaseId(null)
    setMenuOpen(false)
  }, [missionId])

  // Escape : si le drawer est fermé (pas de sélection), efface la phase active.
  // (Le drawer pose son propre Escape quand il est ouvert — un Escape = un pas.)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selected == null && phaseId != null) setPhaseId(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, phaseId])

  if (!stories.length) return null

  const chip = (on: boolean) =>
    `cursor-pointer select-none rounded-full px-3 py-1 text-xs ring-1 ring-inset transition ${
      on
        ? 'bg-amber-400/15 text-amber-200 ring-amber-400/50'
        : 'text-slate-300 ring-white/15 hover:ring-white/35'
    }`

  return (
    <div className="flex flex-col gap-2">
      <div className="px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{t('story.heading')}</div>
      {/* Rangée 1 : le sélecteur d'histoires */}
      <div className="relative">
        <button
          onClick={() => setMenuOpen((s) => !s)}
          className={`rounded-full border px-4 py-1.5 text-sm backdrop-blur transition ${
            story
              ? 'border-amber-400/50 bg-amber-400/10 text-amber-200'
              : 'border-white/15 bg-[#0a162e]/85 text-slate-200 hover:border-white/30'
          }`}
        >
          {story ? t('story.selectedPrefix', { title: story.title }) : t('story.pickerButton')}
        </button>
        {menuOpen && (
          <div className="absolute left-0 right-0 z-30 mt-1 rounded-xl border border-white/10 bg-[#0a162e] p-1.5 shadow-2xl">
            {stories.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  setStoryId(s.id)
                  setPhaseId(s.phases[0]?.id ?? null)
                  setMenuOpen(false)
                }}
                className="block w-full rounded-lg px-3 py-2 text-left hover:bg-white/5"
              >
                <span className="block text-sm text-slate-100">{s.title}</span>
                <span className="block text-xs text-slate-400">
                  {s.subtitle} ·{' '}
                  <span className={s.data_status === 'partial' ? 'text-amber-300/80' : ''}>
                    {t(STATUS_KEY[s.data_status] ?? s.data_status)}
                  </span>
                </span>
              </button>
            ))}
            {story && (
              <button
                onClick={() => {
                  setStoryId(null)
                  setPhaseId(null)
                  setMenuOpen(false)
                }}
                className="mt-1 block w-full rounded-lg border-t border-white/10 px-3 py-2 text-left text-xs text-slate-400 hover:bg-white/5"
              >
                {t('story.exit')}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Rangée 2 : les PHASES (nom + date — l'objet UX central, pas d'animation) */}
      {story && (
        <div className="flex flex-col gap-1">
          {story.phases.map((p) => (
            <button
              key={p.id}
              onClick={() => setPhaseId(phaseId === p.id ? null : p.id)}
              className={chip(phaseId === p.id) + ' text-left'}
              title={p.headline_stat}
            >
              {p.name} <span className="opacity-70">· {p.date_label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Rangée 3 : la carte narrative de la phase active */}
      {phase && story && (
        <div className="w-full rounded-lg border border-white/10 bg-[#0a162e] px-3 py-2">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm font-semibold text-slate-100">{phase.name}</span>
            <span className="shrink-0 font-mono text-xs text-amber-300">{phase.headline_stat}</span>
          </div>
          <p className="epi-evidence mt-1 text-xs leading-relaxed text-slate-300">{phase.narrative}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
            {story.tier && <span className="rounded bg-white/5 px-1.5 py-0.5">{story.tier}</span>}
            <span className="rounded bg-white/5 px-1.5 py-0.5">{t(STATUS_KEY[story.data_status] ?? story.data_status)}</span>
            {(phase.missing_usernames?.length ?? 0) > 0 && (
              <span className="epi-limit rounded bg-amber-400/10 px-1.5 py-0.5 text-amber-300/90">
                {t('story.uncrawledChannels', { list: phase.missing_usernames!.map((u) => '@' + u).join(', ') })}
              </span>
            )}
            {phase.channel_ids.length === 0 && (
              <span className="epi-limit">
                {t('story.noTelegramData')}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
