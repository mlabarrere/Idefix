// Vue d'ensemble de la bibliothèque scientifique : cartes vers chaque doc, groupées.
import { Link } from 'react-router-dom'
import { SCIENCE_DOCS, SCIENCE_GROUPS } from './registry'

export function ScienceHome() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-10 space-y-8">
        <header className="space-y-2">
          <h1 className="font-serif text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            Ressources scientifiques
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            La méthode, sa validation et son ancrage académique — les documents canoniques du dépôt,
            transcrits ici. En cas de divergence, le fichier <code className="font-mono">.md</code>{' '}
            cité fait foi.
          </p>
        </header>

        {SCIENCE_GROUPS.map((group) => {
          const docs = SCIENCE_DOCS.filter((d) => d.group === group)
          if (docs.length === 0) return null
          return (
            <section key={group} className="space-y-3">
              <h2 className="font-serif text-lg font-semibold text-gray-800 dark:text-gray-200">
                {group}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {docs.map((d) => {
                  const ready = !!d.Component
                  const card = (
                    <div
                      className={`h-full rounded-xl border p-4 transition ${
                        ready
                          ? 'border-gray-200 bg-white hover:border-indigo-300 hover:shadow-sm dark:border-gray-800 dark:bg-gray-900 dark:hover:border-indigo-500/40'
                          : 'border-dashed border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900/40'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-medium text-gray-900 dark:text-gray-100">{d.title}</h3>
                        {!ready && (
                          <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-300">
                            à venir
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{d.short}</p>
                      <p className="mt-2 font-mono text-[11px] text-gray-400 dark:text-gray-500">
                        {d.source}
                      </p>
                    </div>
                  )
                  return ready ? (
                    <Link key={d.slug} to={`/science/${d.slug}`} className="block">
                      {card}
                    </Link>
                  ) : (
                    <div key={d.slug}>{card}</div>
                  )
                })}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
