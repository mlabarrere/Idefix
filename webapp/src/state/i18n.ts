// Instance i18next (react-i18next) — fondation d'internationalisation.
// Modèle calqué sur state/theme.ts : un réglage persisté en localStorage + un
// effet de bord global sur <html> (ici l'attribut `lang`, là la classe `.dark`).
//
// Ressources embarquées au build (pas de backend, pas de chargement réseau) :
// l'app reste 100 % statique. Le français est la langue source / de repli.
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { fr } from './locales/fr'
import { en } from './locales/en'
import { es } from './locales/es'
import { nl } from './locales/nl'
import { lb } from './locales/lb'
import { de } from './locales/de'

export type Lang = 'fr' | 'en-GB' | 'es' | 'nl' | 'lb' | 'de'
export const SUPPORTED_LANGS: readonly Lang[] = ['fr', 'en-GB', 'es', 'nl', 'lb', 'de'] as const

const LANG_KEY = 'idefix-lang'

// Normalise un code de langue navigateur vers l'une de nos six langues.
// fr* -> fr, es* -> es, nl* -> nl, lb* -> lb, de* -> de, sinon en-GB.
function normalize(input: string | null | undefined): Lang {
  const l = (input ?? '').toLowerCase()
  if (l.startsWith('fr')) return 'fr'
  if (l.startsWith('es')) return 'es'
  if (l.startsWith('nl')) return 'nl'
  if (l.startsWith('lb')) return 'lb'
  if (l.startsWith('de')) return 'de'
  return 'en-GB'
}

// Résolution de la langue initiale : localStorage -> navigator.language -> 'fr'.
function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY)
    if (saved && (SUPPORTED_LANGS as readonly string[]).includes(saved)) {
      return saved as Lang
    }
  } catch {
    /* localStorage indisponible (mode privé strict) — on retombe sur le navigateur */
  }
  const nav = typeof navigator !== 'undefined' ? navigator.language : ''
  return nav ? normalize(nav) : 'fr'
}

// eslint-disable-next-line @typescript-eslint/no-floating-promises
i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    'en-GB': { translation: en },
    es: { translation: es },
    nl: { translation: nl },
    lb: { translation: lb },
    de: { translation: de },
  },
  lng: initialLang(),
  // Chaîne de repli explicite : le luxembourgeois (couverture CLDR/format fine,
  // §16.6) retombe sur l'allemand puis le français ; tout le reste sur le français.
  fallbackLng: { lb: ['de', 'fr'], default: ['fr'] },
  // Nos clés sont des littéraux pointés plats ('gate.title'), pas une arborescence :
  // on désactive le séparateur de clés pour ne pas les interpréter comme imbriquées.
  keySeparator: false,
  interpolation: { escapeValue: false },
})

// Effet de bord global à chaque changement de langue : persiste + met à jour <html lang>.
i18n.on('languageChanged', (lng) => {
  try {
    localStorage.setItem(LANG_KEY, lng)
  } catch {
    /* pas de persistance possible — on applique quand même l'attribut lang */
  }
  document.documentElement.lang = lng
})

// Applique l'attribut lang initial dès le chargement du module (avant le rendu).
document.documentElement.lang = i18n.language

// Change la langue active (déclenche `languageChanged` -> persistance + <html lang>).
export function setLang(lang: Lang): void {
  void i18n.changeLanguage(lang)
}

export default i18n
