// État de sélection PARTAGÉ (graphe ⇄ tableau ⇄ drawer). Un clic n'importe où
// pose `selected` ; le drawer charge le détail ; graphe et tableau se surlignent.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

interface SelectionState {
  missionId: string
  selected: number | null
  select: (id: number | null) => void
}

const Ctx = createContext<SelectionState | null>(null)

export function SelectionProvider({ missionId, children }: { missionId: string; children: ReactNode }) {
  const [selected, setSelected] = useState<number | null>(null)
  const select = useCallback((id: number | null) => setSelected(id), [])
  const value = useMemo<SelectionState>(
    () => ({ missionId, selected, select }),
    [missionId, selected, select],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSelection(): SelectionState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useSelection must be used within SelectionProvider')
  return v
}
