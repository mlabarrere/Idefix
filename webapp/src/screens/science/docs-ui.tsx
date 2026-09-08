// Primitives de rendu pour la bibliothèque scientifique (docs curés à la main en
// JSX — pas de rendu markdown, pas de dépendance ; cohérent avec la page
// Méthodologie). Source canonique = les .md du dépôt (docs/*.md, METHODOLOGY.md) ;
// ces composants en sont une transcription éditoriale stylée Tailwind v4.
import type { ReactNode } from 'react'

// En-tête + corps d'une page de doc, scrollable, largeur de lecture confortable.
export function DocPage({
  title,
  subtitle,
  source,
  children,
}: {
  title: string
  subtitle?: ReactNode
  source?: string // chemin du .md canonique (affiché en pied de page)
  children: ReactNode
}) {
  return (
    <div className="h-full overflow-y-auto">
      <article className="mx-auto max-w-3xl px-6 py-10 space-y-10">
        <header className="space-y-2">
          <h1 className="font-serif text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            {title}
          </h1>
          {subtitle ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          ) : null}
        </header>
        {children}
        {source ? (
          <footer className="border-t border-gray-200 pt-4 text-xs text-gray-400 dark:border-gray-800 dark:text-gray-500">
            Source canonique : <code className="font-mono">{source}</code>. Cette page en est une
            transcription éditoriale ; en cas de divergence, le fichier fait foi.
          </footer>
        ) : null}
      </article>
    </div>
  )
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-serif text-xl font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{children}</div>
    </section>
  )
}

export function SubSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="font-serif text-base font-semibold text-gray-800 dark:text-gray-200">{title}</h3>
      <div className="space-y-2 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{children}</div>
    </div>
  )
}

// Encart d'avertissement / limite (réutilise le langage epi-limit ambre du site).
// <div> (et non <p>) pour pouvoir contenir des blocs (listes, paragraphes).
export function Limit({ children }: { children: ReactNode }) {
  return (
    <div className="epi-limit space-y-2 rounded-md border border-amber-500/30 bg-amber-500/[0.06] px-3 py-2 text-sm">
      {children}
    </div>
  )
}

// Encart neutre (note de lecture, mise en garde non-ambre).
export function Note({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-400">
      {children}
    </div>
  )
}

// Ligne de formule / chiffres en mono, discrète.
export function Mono({ children }: { children: ReactNode }) {
  return <p className="font-mono text-xs text-gray-500 dark:text-gray-400">{children}</p>
}

// Tableau simple : en-têtes + lignes de cellules (ReactNode pour le gras/italique).
export function Table({ head, rows }: { head: ReactNode[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-300 dark:border-gray-700">
            {head.map((h, i) => (
              <th key={i} className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri} className="border-b border-gray-200 dark:border-gray-800">
              {r.map((c, ci) => (
                <td key={ci} className="px-3 py-2 align-top text-gray-700 dark:text-gray-300">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Liste à puces dense.
export function List({ children }: { children: ReactNode }) {
  return <ul className="space-y-1.5 list-disc pl-5 marker:text-gray-400">{children}</ul>
}

// Une référence bibliographique : libellé court (gras) + citation complète.
export function Ref({ tag, children }: { tag: string; children: ReactNode }) {
  return (
    <li>
      <span className="font-semibold text-gray-900 dark:text-gray-100">{tag}.</span>{' '}
      <span className="text-gray-700 dark:text-gray-300">{children}</span>
    </li>
  )
}

// Identifiant externe (DOI / arXiv) en mono discret.
export function Id({ children }: { children: ReactNode }) {
  return <code className="font-mono text-xs text-gray-500 dark:text-gray-400">{children}</code>
}
