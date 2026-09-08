// Mode de snapshot de la galaxie : 'analytics' (communautés lexicales/structurelles)
// vs 'embedding' (communautés regroupées par embeddings locaux). Le switch ne change
// QUE la source du snapshot (mêmes canaux, même graph.json) — léger, comme
// SelectionContext.
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

export type SnapshotMode = 'analytics' | 'embedding'

interface SnapshotModeState {
  mode: SnapshotMode
  setMode: (m: SnapshotMode) => void
}

const Ctx = createContext<SnapshotModeState | null>(null)

export function SnapshotModeProvider({ children, initialMode = 'analytics' }: { children: ReactNode; initialMode?: SnapshotMode }) {
  const [mode, setMode] = useState<SnapshotMode>(initialMode)
  const value = useMemo<SnapshotModeState>(() => ({ mode, setMode }), [mode])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSnapshotMode(): SnapshotModeState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useSnapshotMode must be used within SnapshotModeProvider')
  return v
}
