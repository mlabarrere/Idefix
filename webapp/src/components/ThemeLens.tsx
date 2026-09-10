// Lentilles de THÈME / scénarios sur la galaxie unique (haut-gauche). Une galaxie,
// N scénarios : cliquer « Empreinte GAN » illumine les canaux qui parlent du GAN
// AU SEIN du graphe russophile — on VOIT où ils sont et leurs liens (demande Micky :
// « faire des liens entre russophilie / RN / GAN »). Réutilise highlightIds (dimming).
// Composant CONTRÔLÉ : les thèmes et l'id actif viennent du parent (état = URL).
import { useTranslation } from 'react-i18next'
import type { Theme } from '../data/types'

export function ThemeLens({
  themes,
  activeId,
  onPick,
}: {
  themes: Theme[]
  activeId: string | null
  onPick: (id: string | null) => void
}) {
  const { t: tr } = useTranslation()
  if (!themes.length) return null

  // Label de lentille : clé i18n par id de thème, repli sur le label de la donnée.
  const themeLabel = (t: Theme) => {
    const key = `graph.theme.${t.id}`
    const s = tr(key)
    return s === key ? t.label : s
  }

  // Avertissement méthodologique du scénario actif : clé spécifique par id
  // (scenario.warning.<id>), repli sur le générique. Un scénario montre des
  // INDICES documentés, jamais une preuve d'influence.
  const scenarioWarning = (id: string) => {
    const key = `scenario.warning.${id}`
    const s = tr(key)
    return s === key ? tr('scenario.warning') : s
  }

  return (
    <div>
      <div className="mb-1 px-1 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">{tr('graph.themeLens.heading')}</div>
      <div className="flex flex-wrap gap-1.5">
      {themes.map((t) => {
        const on = activeId === t.id
        return (
          <button
            key={t.id}
            onClick={() => onPick(on ? null : t.id)}
            className={`rounded-full px-2.5 py-1 text-xs ring-1 backdrop-blur transition ring-inset ${
              on ? 'text-white' : 'text-slate-300 ring-white/10 hover:ring-white/30'
            }`}
            style={on ? { background: t.color + '22', borderColor: t.color, color: t.color } : undefined}
            title={tr('channels.count', { n: t.channel_ids.length })}
          >
            <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: t.color }} />
            {themeLabel(t)} <span className="opacity-60">{t.channel_ids.length}</span>
          </button>
        )
      })}
      </div>
      {activeId && (
        <p className="epi-limit mt-2 px-1 text-[11px] leading-relaxed">⚠ {scenarioWarning(activeId)}</p>
      )}
    </div>
  )
}
