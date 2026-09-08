// StatCard — tuile d'indicateur clé (KPI). Reprend À L'IDENTIQUE l'apparence
// des tuiles « Chiffres clés » de la synthèse : libellé en capitales discrètes,
// valeur proéminente (chiffres tabulaires via .epi-computed) et indice/delta
// optionnel. Styling tokens sémantiques (bg-card / border-border /
// text-foreground / text-muted-foreground).
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface StatCardProps {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  className?: string
}

export function StatCard({ label, value, hint, className }: StatCardProps) {
  return (
    <div className={cn('rounded-lg border border-border bg-card p-4', className)}>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 epi-computed text-2xl font-semibold text-foreground">{value}</div>
      {hint ? <div className="text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  )
}
