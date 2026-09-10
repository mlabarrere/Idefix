// EmptyState — état vide neutre (titre + indice optionnel). Déplacé sous
// components/patterns/ (composite) puis ré-exporté par le baril src/ui.tsx, à
// props identiques (`title`, `hint`) pour ne pas toucher les sites d'appel.
export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-200 bg-gray-100 p-8 text-center dark:border-gray-800 dark:bg-gray-800">
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</div>
      {hint ? <div className="mt-1 text-xs text-gray-400 dark:text-gray-500">{hint}</div> : null}
    </div>
  )
}
