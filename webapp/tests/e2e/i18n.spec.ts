import { test, expect } from './fixtures'

// Bascule de langue via le <select> natif (LanguageSwitcher, HeaderControls).
// Le seul <select> natif de l'écran mission est le switcher de langue (le sélecteur
// de mission est un combobox Radix à base de bouton, pas un <select>).
test.describe('i18n', () => {
  test('FR → EN change les libellés de nav + persiste + met à jour <html lang>', async ({ page }) => {
    await page.goto('/#/m/russosphere')

    const nav = page.getByRole('navigation')
    // Départ en français (locale fr-FR ⇒ i18n = 'fr').
    await expect(nav.getByRole('link', { name: 'Analyse' })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('lang', 'fr')

    // Un unique <select> natif = le switcher de langue.
    const langSelect = page.locator('select')
    await expect(langSelect).toHaveCount(1)
    await langSelect.selectOption('en-GB')

    // Le libellé de nav change vers la valeur anglaise (en.ts : nav.analyse = 'Analysis').
    await expect(nav.getByRole('link', { name: 'Analysis' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Analyse' })).toHaveCount(0)

    // Persistance localStorage + attribut <html lang>.
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('idefix-lang')))
      .toBe('en-GB')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en-GB')

    // Retour au français (langue-agnostique : on recible le <select>).
    await langSelect.selectOption('fr')
    await expect(nav.getByRole('link', { name: 'Analyse' })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
  })
})
