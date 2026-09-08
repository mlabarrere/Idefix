// Écran Paramètres — préférences d'interface, appliquées localement au
// navigateur. Réutilise les contrôles existants : ThemeToggle (state/theme),
// LanguageSwitcher (i18n) et l'état SnapshotMode (state/SnapshotMode). Aucune
// donnée distante : écran purement local, monté comme route enfant de mission
// (/m/:missionId/parametres).
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/patterns/PageHeader'
import { ThemeToggle } from '../app/ThemeToggle'
import { LanguageSwitcher } from '../app/LanguageSwitcher'
import { useSnapshotMode, type SnapshotMode } from '../state/SnapshotMode'
import { cn } from '@/lib/utils'

// Ligne de réglage : libellé + indice à gauche, contrôle à droite.
function SettingRow({ label, hint, control }: { label: string; hint?: string; control: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-4 last:border-b-0">
      <div className="space-y-0.5">
        <div className="text-sm font-medium text-foreground">{label}</div>
        {hint ? <div className="text-xs text-muted-foreground">{hint}</div> : null}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  )
}

const SNAPSHOT_OPTIONS: { value: SnapshotMode; label: string }[] = [
  { value: 'analytics', label: 'Analytics' },
  { value: 'embedding', label: 'LLM Embedding' },
]

// Segmenté « vue communautés » — pilote l'état SnapshotMode partagé.
function SnapshotModeControl() {
  const { mode, setMode } = useSnapshotMode()
  return (
    <div className="flex gap-1.5">
      {SNAPSHOT_OPTIONS.map((opt) => {
        const active = mode === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => setMode(opt.value)}
            aria-pressed={active}
            className={cn(
              'rounded-md border px-3 py-1.5 text-sm transition',
              active
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-muted-foreground hover:text-foreground',
            )}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

export function Settings() {
  const { t } = useTranslation()
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-6 py-8 space-y-6">
        <PageHeader
          title={t('settings.title')}
          subtitle={t('settings.subtitle')}
        />
        <section className="rounded-lg border border-border bg-card px-4">
          <SettingRow label={t('settings.themeLabel')} hint={t('settings.themeHint')} control={<ThemeToggle />} />
          <SettingRow label={t('settings.langLabel')} hint={t('settings.langHint')} control={<LanguageSwitcher />} />
          <SettingRow
            label={t('settings.communityLabel')}
            hint={t('settings.communityHint')}
            control={<SnapshotModeControl />}
          />
        </section>
      </div>
    </div>
  )
}
