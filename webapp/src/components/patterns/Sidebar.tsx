// Sidebar — primitives de navigation latérale (style Catalyst) : sections
// libellées + items (NavLink) à état actif. Composite réutilisé par la coquille
// produit (AppShell) et alignable sur la sous-nav Science. Styling 100 % tokens
// sémantiques (text-foreground / text-muted-foreground / bg-accent / border-border)
// → bascule clair-sombre automatique, aucun littéral de couleur.
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

/** Groupe d'items précédé d'un intitulé discret en capitales (optionnel). */
export function SidebarSection({
  heading,
  children,
  className,
}: {
  heading?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      {heading ? (
        <div className="px-3 pt-3 pb-1 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
          {heading}
        </div>
      ) : null}
      {children}
    </div>
  )
}

const itemBase =
  'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition'
const itemActive = 'bg-accent text-foreground'
const itemIdle = 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'

/** Item de navigation (NavLink). `end` pour matcher exactement l'index. */
export function SidebarItem({
  to,
  end,
  icon: Icon,
  children,
}: {
  to: string
  end?: boolean
  icon?: LucideIcon
  children: ReactNode
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => cn(itemBase, isActive ? itemActive : itemIdle)}
    >
      {Icon ? <Icon className="h-4 w-4 shrink-0" /> : null}
      <span className="truncate">{children}</span>
    </NavLink>
  )
}
