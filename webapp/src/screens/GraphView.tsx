// Galaxie = l'outil de travail. Plein cadre + cockpit gauche (scénarios/thèmes,
// toggle analytics/embeddings). Le thème actif illumine ses canaux (dimming du
// reste) via highlightIds. L'état de travail (scénario + mode) est PERSISTÉ dans
// l'URL → une vue filtrée est partageable et rejouable (traçabilité analyste).
import { Suspense, lazy, useEffect } from 'react'
import { useOutletContext, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGraphModel } from '../graph/useGraphModel'
import { ChannelDrawer } from '../components/patterns/ChannelDrawer'
import { ThemeLens } from '../components/ThemeLens'
import { SnapshotToggle } from '../components/SnapshotToggle'
import { GanFootprint } from '../components/GanFootprint'
import { loadThemes } from '../data/loaders'
import type { SnapshotMode } from '../state/SnapshotMode'
import { SnapshotModeProvider, useSnapshotMode } from '../state/SnapshotMode'
import { EmptyState, Spinner, useAsync } from '../ui'

const GalaxyCanvas = lazy(() => import('../components/GalaxyCanvas').then((m) => ({ default: m.GalaxyCanvas })))

export function GraphView() {
  // Le provider doit englober la galaxie ET le cockpit (le toggle) : on isole
  // le corps dans GraphViewInner pour qu'il puisse lire le mode. Le mode initial
  // est réhydraté depuis l'URL (?mode=embedding) — pas d'effet, pas de boucle.
  const [params] = useSearchParams()
  const initialMode: SnapshotMode = params.get('mode') === 'embedding' ? 'embedding' : 'analytics'
  return (
    <SnapshotModeProvider initialMode={initialMode}>
      <GraphViewInner />
    </SnapshotModeProvider>
  )
}

function GraphViewInner() {
  const { t } = useTranslation()
  const { missionId } = useOutletContext<{ missionId: string }>()
  const { mode } = useSnapshotMode()
  const { model, loading } = useGraphModel(missionId, mode)
  const [params, setParams] = useSearchParams()

  // Thèmes chargés une seule fois ici (source unique) ; ThemeLens est contrôlé.
  const { data: themesBundle } = useAsync(() => loadThemes(missionId), [missionId])
  const themes = themesBundle?.themes ?? []

  // Scénario actif = dérivé de l'URL (source de vérité) → highlightIds. Aucune
  // copie d'état à resynchroniser : l'URL EST l'état.
  const activeTheme = themes.find((th) => th.id === params.get('scenario')) ?? null
  const highlightIds = activeTheme?.channel_ids ?? null

  const setScenario = (id: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (id) next.set('scenario', id)
        else next.delete('scenario')
        return next
      },
      { replace: true },
    )

  // Écrit le mode dans l'URL quand il change (analytics = défaut → param absent).
  useEffect(() => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (mode === 'embedding') next.set('mode', mode)
        else next.delete('mode')
        return next
      },
      { replace: true },
    )
  }, [mode, setParams])

  if (loading) return <Spinner />
  if (!model)
    return (
      <EmptyState
        title={t('graph.emptyTitle')}
        hint={t('graph.emptyHint', { missionId })}
      />
    )

  // Toutes les commandes vivent dans le cockpit gauche de la galaxie (cockpitTop).
  const cockpit = (
    <div className="flex flex-col gap-3">
      <SnapshotToggle />
      <ThemeLens themes={themes} activeId={activeTheme?.id ?? null} onPick={(id) => setScenario(id)} />
      {activeTheme?.id === 'gan' && <GanFootprint />}
      <div className="border-t border-white/10" />
    </div>
  )

  return (
    <div className="relative h-full w-full">
      <Suspense fallback={<div className="p-6"><Spinner /></div>}>
        <GalaxyCanvas model={model} highlightIds={highlightIds} cockpitTop={cockpit} />
      </Suspense>
      <ChannelDrawer model={model} />
    </div>
  )
}
