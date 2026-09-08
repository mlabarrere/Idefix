// PageHeader — en-tête de page canonique (composite). Toute vue « écran » le
// monte en tête : un titre (string), un sous-titre optionnel et un emplacement
// d'actions optionnel (aligné à droite, ex. champ de recherche). Styling 100 %
// tokens sémantiques (text-foreground / text-muted-foreground / border-border) —
// bascule clair-sombre automatique via la couche de compatibilité shadcn.
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('flex items-start justify-between gap-4 border-b border-border pb-4', className)}>
      <div className="space-y-1">
        <h1 className="font-serif text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  )
}
