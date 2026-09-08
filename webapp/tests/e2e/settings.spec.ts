import { test, expect } from './fixtures'

// Écran Paramètres (/#/m/russosphere/parametres) — thème + langue + vue communautés.
test.describe('settings', () => {
  test('affiche les contrôles thème, langue et snapshot', async ({ page }) => {
    await page.goto('/#/m/russosphere/parametres')

    await expect(page.getByRole('heading', { name: 'Paramètres' })).toBeVisible()

    // Libellés des trois lignes de réglage.
    await expect(page.getByText('Thème', { exact: true })).toBeVisible()
    await expect(page.getByText('Langue', { exact: true })).toBeVisible()
    await expect(page.getByText('Vue communautés', { exact: true })).toBeVisible()

    // Contrôle snapshot (Analytics / LLM Embedding).
    await expect(page.getByRole('button', { name: 'Analytics' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'LLM Embedding' })).toBeVisible()

    // Un <select> de langue est présent dans la ligne « Langue » (au moins un
    // <select> natif sur l'écran — le header en a aussi un).
    await expect(page.locator('select').first()).toBeVisible()
  })
})
