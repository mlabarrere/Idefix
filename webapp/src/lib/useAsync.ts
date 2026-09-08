import { useEffect, useState } from "react"

// useAsync — hook de chargement asynchrone simple (états loading / données).
// Extrait du baril src/ui.tsx vers la couche lib/ (Phase 2B) ; ré-exporté à
// l'identique (même signature) pour ne pas toucher les sites d'appel.
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[]
): { data: T | null; loading: boolean } {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let alive = true
    setLoading(true)
    fn().then((d) => {
      if (alive) {
        setData(d)
        setLoading(false)
      }
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return { data, loading }
}
