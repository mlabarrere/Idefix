// Coquille de la bibliothèque scientifique (section globale, hors mission).
// Header sobre (retour portfolio + thème) + sidebar groupée par thème + contenu routé.
import { NavLink, Outlet } from 'react-router-dom'
import { HeaderControls } from '../../app/HeaderControls'
import { SCIENCE_DOCS, SCIENCE_GROUPS } from './registry'

export function ScienceShell() {
  const linkCls = (active: boolean) =>
    `block rounded-md px-2 py-1.5 text-sm ${
      active
        ? 'bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'
    }`

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-4 border-b border-gray-200 px-4 dark:border-gray-800">
        <NavLink
          to="/m/russosphere"
          className="font-serif text-lg font-semibold tracking-tight text-indigo-600 dark:text-indigo-400"
        >
          ◆ IDÉFIX
        </NavLink>
        <span className="text-sm text-gray-400">/</span>
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          Ressources scientifiques
        </span>
        <div className="ml-auto">
          <HeaderControls />
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-64 shrink-0 overflow-y-auto border-r border-gray-200 p-3 dark:border-gray-800 sm:block">
          <NavLink to="/science" end className={({ isActive }) => linkCls(isActive)}>
            Vue d'ensemble
          </NavLink>
          {SCIENCE_GROUPS.map((group) => {
            const docs = SCIENCE_DOCS.filter((d) => d.group === group)
            if (docs.length === 0) return null
            return (
              <div key={group} className="mt-4">
                <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  {group}
                </div>
                {docs.map((d) => (
                  <NavLink
                    key={d.slug}
                    to={`/science/${d.slug}`}
                    className={({ isActive }) => linkCls(isActive)}
                  >
                    {d.title}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </aside>

        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
