// Switcher de langue — toujours visible (à côté de ThemeToggle).
// Pour l'instant un <select> natif stylé ; il deviendra un shadcn Select plus tard.
// La valeur active suit i18n.language ; onChange -> setLang (persiste + <html lang>).
import { useTranslation } from 'react-i18next'
import { setLang, SUPPORTED_LANGS, type Lang } from '../state/i18n'

const LABEL_KEY: Record<Lang, 'lang.fr' | 'lang.en' | 'lang.es' | 'lang.nl' | 'lang.lb' | 'lang.de'> = {
  fr: 'lang.fr',
  'en-GB': 'lang.en',
  es: 'lang.es',
  nl: 'lang.nl',
  lb: 'lang.lb',
  de: 'lang.de',
}

// Drapeaux (emoji regional-indicator) par langue — indice visuel dans le sélecteur.
const FLAG: Record<Lang, string> = {
  fr: '🇫🇷',
  'en-GB': '🇬🇧',
  es: '🇪🇸',
  nl: '🇳🇱',
  lb: '🇱🇺',
  de: '🇩🇪',
}

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const current = (SUPPORTED_LANGS as readonly string[]).includes(i18n.language)
    ? (i18n.language as Lang)
    : 'fr'

  return (
    <select
      value={current}
      onChange={(e) => setLang(e.target.value as Lang)}
      aria-label={t('lang.switcherAria')}
      className="cursor-pointer rounded-md border border-gray-200 bg-white px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800"
    >
      {SUPPORTED_LANGS.map((code) => (
        <option key={code} value={code}>
          {FLAG[code]} {t(LABEL_KEY[code])}
        </option>
      ))}
    </select>
  )
}
