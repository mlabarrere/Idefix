// Groupe de contrôles d'en-tête : switcher de langue + bascule de thème.
// Factorisé pour que les quatre emplacements (AppShell, ScienceShell, gate,
// portfolio) réutilisent exactement le même cluster.
import { LanguageSwitcher } from './LanguageSwitcher'
import { ThemeToggle } from './ThemeToggle'

export function HeaderControls() {
  return (
    <div className="flex items-center gap-2">
      <LanguageSwitcher />
      <ThemeToggle />
    </div>
  )
}
