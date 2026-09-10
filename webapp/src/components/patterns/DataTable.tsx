// DataTable — enveloppe de tableau légère et stylée, générique sur colonnes +
// lignes. En-tête, corps, survol de ligne (+ zébrure optionnelle) et défilement
// horizontal responsive (overflow-x-auto). AUCUNE dépendance lourde (pas de
// tanstack) : la recherche / le tri / la pagination éventuels restent la
// responsabilité de l'écran appelant, qui passe déjà `rows` filtrées/triées.
// Styling tokens sémantiques (bg-muted / border-border / divide-border / …).
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface DataTableColumn<T> {
  id: string
  header: ReactNode
  cell: (row: T) => ReactNode
  /** Classes appliquées à chaque <td> (alignement, couleur, .epi-computed…). */
  className?: string
  /** Classes appliquées au <th> correspondant. */
  headerClassName?: string
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  /** Clic sur une ligne (sélection / drawer). Rend la ligne cliquable. */
  onRowClick?: (row: T) => void
  /** Classes par ligne (surlignage de sélection, etc.). */
  rowClassName?: (row: T) => string | undefined
  /** Zébrure alternée (désactivée par défaut pour rester sobre). */
  zebra?: boolean
  className?: string
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  rowClassName,
  zebra = false,
  className,
}: DataTableProps<T>) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-border', className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted text-left text-xs tracking-wide text-muted-foreground uppercase">
          <tr>
            {columns.map((col) => (
              <th key={col.id} className={cn('px-3 py-2', col.headerClassName)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                zebra && 'even:bg-muted/40',
                'hover:bg-muted',
                onRowClick && 'cursor-pointer',
                rowClassName?.(row),
              )}
            >
              {columns.map((col) => (
                <td key={col.id} className={cn('px-3 py-2', col.className)}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
