// Bascule clair/sombre (standard Tailwind, classe .dark).
import { useTranslation } from 'react-i18next'
import { useTheme } from '../state/theme'

export function ThemeToggle() {
  const { t } = useTranslation()
  const [theme, toggle] = useTheme()
  return (
    <button
      onClick={toggle}
      title={theme === 'dark' ? t('theme.toLight') : t('theme.toDark')}
      aria-label={t('theme.toggleAria')}
      className="rounded-md border border-gray-200 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
    >
      {theme === 'dark' ? '☀' : '☾'}
    </button>
  )
}
