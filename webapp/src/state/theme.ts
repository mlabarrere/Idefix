// Thème clair/sombre — standard Tailwind (classe .dark sur <html>), persistant.
import { useCallback, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'idefix-theme'

export function initialTheme(): Theme {
  const saved = localStorage.getItem(KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function applyTheme(t: Theme): void {
  document.documentElement.classList.toggle('dark', t === 'dark')
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => initialTheme())
  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === 'dark' ? 'light' : 'dark'
      applyTheme(next)
      localStorage.setItem(KEY, next)
      return next
    })
  }, [])
  return [theme, toggle]
}
